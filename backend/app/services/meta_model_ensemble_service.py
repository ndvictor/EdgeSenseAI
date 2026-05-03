"""Meta-Model Ensemble Scorer Service.

Combines scored signals into final signal confidence before LLM/risk validation.
This is still pre-recommendation.

NO recommendation.
NO LLM.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.candidate_universe_service import add_candidate
from app.services.signal_scoring_service import (
    ScoredSignal,
    SignalScoringResponse,
    get_latest_signal_scoring,
)


class EnsembleSignal(BaseModel):
    """A signal with final ensemble score."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    strategy_key: str | None = None
    trigger_type: str
    final_signal_score: int = Field(..., ge=0, le=100)
    confidence: float = Field(..., ge=0, le=1)
    model_agreement: float = Field(..., ge=0, le=1)
    primary_reason: str
    disagreement: list[str] = Field(default_factory=list)
    components: list[dict[str, Any]] = Field(default_factory=list)
    status: Literal["pass", "watch", "blocked"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    scored_signal_id: str | None = None


class MetaModelEnsembleRequest(BaseModel):
    """Request to run meta-model ensemble."""

    model_config = ConfigDict(protected_namespaces=())

    scored_signals: list[ScoredSignal] = Field(default_factory=list)
    use_latest_scored_signals: bool = True
    regime: str | None = None
    strategy_key: str | None = None
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    model_weights: dict[str, float] | None = None
    promote_to_candidates: bool = False
    include_watch: bool = False  # If true, include watch status signals


class MetaModelEnsembleResponse(BaseModel):
    """Response from meta-model ensemble run."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "no_signals", "failed"]
    ensemble_signals: list[EnsembleSignal] = Field(default_factory=list)
    passed_signals: list[str] = Field(default_factory=list)
    watch_signals: list[str] = Field(default_factory=list)
    blocked_signals: list[str] = Field(default_factory=list)
    model_weights_used: dict[str, float]
    promoted_candidates: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: str
    completed_at: str
    duration_ms: int


# Default baseline weights
DEFAULT_WEIGHTS: dict[str, float] = {
    "weighted_ranker_score": 0.30,
    "data_quality_score": 0.20,
    "regime_alignment_score": 0.15,
    "historical_similarity_score": 0.15,
    "liquidity_score": 0.10,
    "raw_signal_score": 0.10,
}

# In-memory storage
_LATEST_ENSEMBLE: MetaModelEnsembleResponse | None = None
_ENSEMBLE_HISTORY: list[MetaModelEnsembleResponse] = []


def _normalize_weights(weights: dict[str, float]) -> dict[str, float]:
    """Normalize weights to sum to 1.0."""
    total = sum(weights.values())
    if total == 0:
        return DEFAULT_WEIGHTS
    return {k: v / total for k, v in weights.items()}


def _calculate_model_agreement(
    components: list[dict[str, Any]],
    final_score: int,
) -> float:
    """Calculate how well models agree with final score."""
    if not components:
        return 0.5

    differences = []
    for comp in components:
        score = comp.get("score", 50)
        diff = abs(score - final_score) / 100  # Normalize to 0-1
        differences.append(1 - diff)  # Convert to agreement

    return round(sum(differences) / len(differences), 2)


def _determine_signal_status(
    final_score: int,
    data_quality: int,
    include_watch: bool,
) -> tuple[Literal["pass", "watch", "blocked"], list[str], list[str]]:
    """Determine signal status based on scores.

    Rules:
    - data_quality < 50: blocked
    - final_score >= 75: pass
    - final_score 60-74: watch (if include_watch=true)
    - final_score < 60: blocked
    """
    blockers: list[str] = []
    warnings: list[str] = []

    # Data quality gate
    if data_quality < 50:
        blockers.append(f"Data quality too low ({data_quality}/100)")
        return "blocked", blockers, warnings

    # Score thresholds
    if final_score >= 75:
        return "pass", blockers, warnings
    elif final_score >= 60:
        if include_watch:
            warnings.append(f"Score {final_score} in watch range (60-74)")
            return "watch", blockers, warnings
        else:
            blockers.append(f"Score {final_score} below pass threshold (75), watch not enabled")
            return "blocked", blockers, warnings
    else:
        blockers.append(f"Score {final_score} below minimum threshold (60)")
        return "blocked", blockers, warnings


def _build_ensemble_signal(
    scored: ScoredSignal,
    weights: dict[str, float],
    include_watch: bool,
) -> EnsembleSignal:
    """Build ensemble signal from scored signal."""

    # Collect available component scores
    components: list[dict[str, Any]] = []

    if scored.weighted_ranker_score is not None:
        components.append({
            "model": "weighted_ranker",
            "score": scored.weighted_ranker_score,
            "weight": weights.get("weighted_ranker_score", 0.30),
        })

    if scored.data_quality_score is not None:
        components.append({
            "model": "data_quality",
            "score": scored.data_quality_score,
            "weight": weights.get("data_quality_score", 0.20),
        })

    if scored.historical_similarity_score is not None:
        components.append({
            "model": "historical_similarity",
            "score": scored.historical_similarity_score,
            "weight": weights.get("historical_similarity_score", 0.15),
        })

    if scored.liquidity_score is not None:
        components.append({
            "model": "liquidity",
            "score": scored.liquidity_score,
            "weight": weights.get("liquidity_score", 0.10),
        })

    if scored.regime_alignment_score is not None:
        components.append({
            "model": "regime_alignment",
            "score": scored.regime_alignment_score,
            "weight": weights.get("regime_alignment_score", 0.15),
        })

    if scored.raw_signal_score is not None:
        components.append({
            "model": "raw_signal",
            "score": scored.raw_signal_score,
            "weight": weights.get("raw_signal_score", 0.10),
        })

    # Normalize weights for available components
    available_weight = sum(c["weight"] for c in components)
    if available_weight > 0:
        for comp in components:
            comp["normalized_weight"] = comp["weight"] / available_weight

    # Calculate weighted final score
    weighted_sum = sum(c["score"] * c.get("normalized_weight", c["weight"]) for c in components)
    final_score = int(weighted_sum) if components else scored.signal_score

    # Model agreement
    agreement = _calculate_model_agreement(components, final_score)

    # Determine status
    status, blockers, warnings = _determine_signal_status(
        final_score=final_score,
        data_quality=scored.data_quality_score,
        include_watch=include_watch,
    )

    # Build primary reason
    primary_components = sorted(components, key=lambda x: x.get("normalized_weight", x["weight"]), reverse=True)[:2]
    primary_reason = f"Top drivers: {', '.join(c['model'] for c in primary_components)}"

    # Disagreement detection
    disagreements: list[str] = []
    for comp in components:
        score = comp["score"]
        if abs(score - final_score) > 20:
            disagreements.append(f"{comp['model']} diverges significantly ({score} vs {final_score})")

    return EnsembleSignal(
        symbol=scored.symbol,
        strategy_key=scored.strategy_key,
        trigger_type=scored.trigger_type,
        final_signal_score=final_score,
        confidence=scored.confidence,
        model_agreement=agreement,
        primary_reason=primary_reason,
        disagreement=disagreements,
        components=components,
        status=status,
        blockers=blockers,
        warnings=warnings,
        scored_signal_id=scored.signal_id,
    )


def run_meta_model_ensemble(
    request: MetaModelEnsembleRequest,
) -> MetaModelEnsembleResponse:
    """Run meta-model ensemble on scored signals.

    Combines multiple model scores with configurable weights.
    Re-normalizes if components unavailable.

    NO recommendation.
    NO LLM.
    """
    global _LATEST_ENSEMBLE, _ENSEMBLE_HISTORY

    run_id = f"meta-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)

    blockers: list[str] = []
    warnings: list[str] = []
    ensemble_signals: list[EnsembleSignal] = []

    # Get weights
    weights = request.model_weights if request.model_weights else DEFAULT_WEIGHTS
    weights = _normalize_weights(weights)

    # Get scored signals
    scored_signals: list[ScoredSignal] = []
    if request.scored_signals:
        scored_signals = request.scored_signals
    elif request.use_latest_scored_signals:
        latest = get_latest_signal_scoring()
        if latest and latest.scored_signals:
            scored_signals = latest.scored_signals
            warnings.append(f"Using {len(scored_signals)} signals from latest scoring run")
        else:
            blockers.append("No latest scored signals available")
    else:
        blockers.append("No scored signals provided and use_latest_scored_signals=false")

    if not scored_signals:
        completed_at = datetime.now(timezone.utc)
        return MetaModelEnsembleResponse(
            run_id=run_id,
            status="no_signals",
            ensemble_signals=[],
            passed_signals=[],
            watch_signals=[],
            blocked_signals=[],
            model_weights_used=weights,
            promoted_candidates=[],
            blockers=blockers,
            warnings=warnings,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        )

    # Build ensemble signals
    passed: list[str] = []
    watch: list[str] = []
    blocked: list[str] = []

    for scored in scored_signals:
        try:
            ensemble = _build_ensemble_signal(
                scored=scored,
                weights=weights,
                include_watch=request.include_watch,
            )
            ensemble_signals.append(ensemble)

            if ensemble.status == "pass":
                passed.append(ensemble.symbol)
            elif ensemble.status == "watch":
                watch.append(ensemble.symbol)
            else:
                blocked.append(ensemble.symbol)

        except Exception as e:
            warnings.append(f"Failed to build ensemble for {scored.symbol}: {str(e)}")

    completed_at = datetime.now(timezone.utc)

    # Promote passing signals to candidates if requested
    promoted: list[str] = []
    if request.promote_to_candidates:
        for ensemble in ensemble_signals:
            if ensemble.status == "pass" or (request.include_watch and ensemble.status == "watch"):
                try:
                    add_candidate(
                        symbol=ensemble.symbol,
                        source_type="meta_model_ensemble",
                        source_run_id=run_id,
                        metadata={
                            "final_score": ensemble.final_signal_score,
                            "confidence": ensemble.confidence,
                            "strategy_key": ensemble.strategy_key,
                        },
                    )
                    promoted.append(ensemble.symbol)
                except Exception as e:
                    warnings.append(f"Failed to promote {ensemble.symbol} to candidates: {str(e)}")

    # Determine status
    status: Literal["completed", "partial", "no_signals", "failed"] = "completed"
    if not ensemble_signals:
        status = "no_signals"
    elif warnings or not passed:
        status = "partial"

    response = MetaModelEnsembleResponse(
        run_id=run_id,
        status=status,
        ensemble_signals=ensemble_signals,
        passed_signals=passed,
        watch_signals=watch,
        blocked_signals=blocked,
        model_weights_used=weights,
        promoted_candidates=promoted,
        blockers=blockers,
        warnings=warnings,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
    )

    # Store
    _LATEST_ENSEMBLE = response
    _ENSEMBLE_HISTORY.append(response)

    if len(_ENSEMBLE_HISTORY) > 100:
        _ENSEMBLE_HISTORY = _ENSEMBLE_HISTORY[-100:]

    return response


def get_latest_meta_model_ensemble() -> MetaModelEnsembleResponse | None:
    """Get the most recent meta-model ensemble run."""
    return _LATEST_ENSEMBLE


def list_meta_model_ensemble_runs(limit: int = 20) -> list[MetaModelEnsembleResponse]:
    """List recent meta-model ensemble runs."""
    return _ENSEMBLE_HISTORY[-limit:]


def promote_passing_signals_to_candidates(
    include_watch: bool = False,
    min_score: int = 60,
) -> dict[str, Any]:
    """Promote passing signals from latest ensemble to candidate universe."""
    latest = _LATEST_ENSEMBLE
    if not latest:
        return {"success": False, "message": "No ensemble run available", "promoted_count": 0}

    promoted: list[str] = []
    for signal in latest.ensemble_signals:
        if signal.status == "pass" or (include_watch and signal.status == "watch"):
            if signal.final_signal_score >= min_score:
                try:
                    add_candidate(
                        symbol=signal.symbol,
                        source_type="meta_model_ensemble",
                        source_run_id=latest.run_id,
                        metadata={
                            "final_score": signal.final_signal_score,
                            "confidence": signal.confidence,
                            "status": signal.status,
                        },
                    )
                    promoted.append(signal.symbol)
                except Exception:
                    pass

    return {
        "success": True,
        "promoted_count": len(promoted),
        "promoted_symbols": promoted,
        "source_run_id": latest.run_id,
    }
