"""Signal Scoring Models Service.

Scores triggered events using available model outputs.
This is NOT final recommendation - just scoring.

NO fake unavailable model outputs.
NO LLM.
NO recommendation.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.models.weighted_ranker import WeightedRankerOutput, run_weighted_ranker_v1
from app.services.event_scanner_models_service import (
    EventScannerMatchedEvent,
    get_latest_event_scan,
)
from app.services.feature_store_service import FeatureStoreRow
from app.services.historical_similarity_service import (
    HistoricalSimilarityResponse,
    run_historical_similarity_search,
)
from app.services.model_runner_service import run_xgboost_ranker_safe
from app.strategies.registry import StrategyConfig, get_strategy


class ScoredSignal(BaseModel):
    """A signal with scores from multiple models."""

    model_config = ConfigDict(protected_namespaces=())

    signal_id: str
    symbol: str
    strategy_key: str | None = None
    trigger_type: str
    raw_signal_score: int  # From event scanner
    weighted_ranker_score: int = Field(..., ge=0, le=100)
    xgboost_score: int | None = None  # Null if not trained
    historical_similarity_score: int | None = None  # Null if unavailable
    liquidity_score: int | None = None
    regime_alignment_score: int | None = None
    data_quality_score: int = Field(..., ge=0, le=100)
    signal_score: int = Field(..., ge=0, le=100)  # Final aggregated
    confidence: float = Field(..., ge=0, le=1)
    model_outputs: dict[str, Any] = Field(default_factory=dict)
    skipped_models: list[dict[str, Any]] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SignalScoringRequest(BaseModel):
    """Request to run signal scoring."""

    model_config = ConfigDict(protected_namespaces=())

    events: list[EventScannerMatchedEvent] = Field(default_factory=list)
    use_latest_events: bool = True
    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    strategy_key: str | None = None
    allow_mock: bool = False


class SignalScoringResponse(BaseModel):
    """Response from signal scoring run."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "no_events", "failed"]
    scored_signals: list[ScoredSignal] = Field(default_factory=list)
    skipped_signals: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: str
    completed_at: str
    duration_ms: int


# In-memory storage
_LATEST_SCORING: SignalScoringResponse | None = None
_SCORING_HISTORY: list[SignalScoringResponse] = []


def _score_with_weighted_ranker(
    event: EventScannerMatchedEvent,
    strategy_config: StrategyConfig | None,
) -> tuple[int, dict[str, Any]]:
    """Score with weighted ranker if feature row available."""
    # Create minimal feature row from event data
    feature_row = FeatureStoreRow(
        symbol=event.symbol,
        source="event_scanner",
        price=event.event_data.get("price"),
        volume=event.event_data.get("volume"),
        rvol=event.event_data.get("rvol"),
        trend_strength=event.event_data.get("trend_strength"),
        ema_alignment=event.event_data.get("ema_alignment"),
        spread_pct=event.event_data.get("spread_pct"),
    )

    if strategy_config:
        result = run_weighted_ranker_v1(feature_row, strategy_config)
        if result and result.universe_score is not None:
            return int(result.universe_score), result.model_dump()

    # Fallback to event score if no feature row
    return event.raw_signal_score, {"note": "Using raw event score (no feature data)"}


def _score_with_xgboost(
    event: EventScannerMatchedEvent,
    strategy_config: StrategyConfig | None,
) -> tuple[int | None, dict[str, Any]]:
    """Score with XGBoost if available. Returns None if not trained."""
    feature_row = FeatureStoreRow(
        symbol=event.symbol,
        source="event_scanner",
    )

    if strategy_config:
        result = run_xgboost_ranker_safe(feature_row, strategy_config)
        status = result.get("status", "not_available")

        if status == "completed":
            return int(result.get("score", 0)), result
        elif status == "not_trained":
            return None, {"status": "not_trained", "reason": "XGBoost model not trained"}
        else:
            return None, {"status": status, "reason": result.get("reason", "XGBoost unavailable")}

    return None, {"status": "no_strategy", "reason": "No strategy config for XGBoost"}


def _score_with_historical_similarity(
    event: EventScannerMatchedEvent,
) -> tuple[int | None, dict[str, Any]]:
    """Score with historical similarity if available."""
    try:
        result = run_historical_similarity_search(
            request=HistoricalSimilarityRequest(
                symbol=event.symbol,
                strategy_key=event.strategy_key,
                max_results=5,
                min_similarity=0.60,
            )
        )

        if result.status in ["completed", "degraded"] and result.similarity_score:
            # Convert similarity score (0-1) to 0-100 scale
            score = int(result.similarity_score * 100)
            return score, {
                "similarity_score": result.similarity_score,
                "matches_count": len(result.matches),
                "outcome_summary": result.outcome_summary,
            }
        elif result.status == "unavailable":
            return None, {"status": "unavailable", "reason": "Vector memory unavailable"}
        else:
            return None, {"status": result.status, "reason": "No suitable historical matches"}

    except Exception as e:
        return None, {"status": "error", "reason": str(e)}


def _compute_data_quality_score(event: EventScannerMatchedEvent) -> int:
    """Compute data quality score from event data freshness."""
    # Default to fair score if no info
    base_score = 70

    # Adjust based on event confidence (proxy for data quality)
    if event.event_confidence >= 0.8:
        base_score += 15
    elif event.event_confidence < 0.5:
        base_score -= 20

    return max(0, min(100, base_score))


def _aggregate_signal_score(
    raw_score: int,
    weighted_ranker: int,
    xgboost: int | None,
    historical: int | None,
    liquidity: int | None,
    regime: int | None,
    data_quality: int,
) -> tuple[int, float, list[dict[str, Any]]]:
    """Aggregate multiple model scores into final signal score."""
    scores: list[tuple[int, float]] = []
    components: list[dict[str, Any]] = []

    # Always include these
    scores.append((weighted_ranker, 0.30))
    components.append({"model": "weighted_ranker", "score": weighted_ranker, "weight": 0.30})

    scores.append((data_quality, 0.20))
    components.append({"model": "data_quality", "score": data_quality, "weight": 0.20})

    # Optional scores - only include if available
    if xgboost is not None:
        scores.append((xgboost, 0.15))
        components.append({"model": "xgboost", "score": xgboost, "weight": 0.15})

    if historical is not None:
        scores.append((historical, 0.15))
        components.append({"model": "historical_similarity", "score": historical, "weight": 0.15})

    if liquidity is not None:
        scores.append((liquidity, 0.10))
        components.append({"model": "liquidity", "score": liquidity, "weight": 0.10})

    if regime is not None:
        scores.append((regime, 0.10))
        components.append({"model": "regime_alignment", "score": regime, "weight": 0.10})

    # Normalize weights
    total_weight = sum(w for _, w in scores)
    if total_weight == 0:
        return 50, 0.5, components

    # Calculate weighted score
    weighted_sum = sum(s * w for s, w in scores)
    final_score = int(weighted_sum / total_weight)

    # Confidence based on number of models contributing
    model_count = len(scores)
    confidence = min(1.0, 0.4 + (model_count * 0.15))

    return final_score, round(confidence, 2), components


def run_signal_scoring(request: SignalScoringRequest) -> SignalScoringResponse:
    """Run signal scoring on matched events.

    Uses available models:
    - Weighted ranker (primary)
    - XGBoost (if trained)
    - Historical similarity (if available)

    NO fake unavailable outputs.
    NO LLM.
    NO recommendation.
    """
    global _LATEST_SCORING, _SCORING_HISTORY

    run_id = f"score-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)

    blockers: list[str] = []
    warnings: list[str] = []
    scored_signals: list[ScoredSignal] = []
    skipped_signals: list[dict[str, Any]] = []

    # Get events to score
    events: list[EventScannerMatchedEvent] = []
    if request.events:
        events = request.events
    elif request.use_latest_events:
        latest_scan = get_latest_event_scan()
        if latest_scan and latest_scan.matched_events:
            events = latest_scan.matched_events
            warnings.append(f"Using {len(events)} events from latest scan")
        else:
            blockers.append("No latest events available")
    else:
        blockers.append("No events provided and use_latest_events=false")

    if not events:
        completed_at = datetime.now(timezone.utc)
        return SignalScoringResponse(
            run_id=run_id,
            status="no_events",
            scored_signals=[],
            skipped_signals=[],
            blockers=blockers,
            warnings=warnings,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        )

    # Score each event
    for event in events:
        try:
            # Get strategy config
            strategy_config = None
            if event.strategy_key:
                strategy_config = get_strategy(event.strategy_key)

            # Score with available models
            weighted_score, weighted_output = _score_with_weighted_ranker(event, strategy_config)
            xgboost_score, xgboost_output = _score_with_xgboost(event, strategy_config)
            hist_score, hist_output = _score_with_historical_similarity(event)
            data_quality = _compute_data_quality_score(event)

            # Build skipped models list
            skipped_models: list[dict[str, Any]] = []
            if xgboost_score is None:
                skipped_models.append({
                    "model": "xgboost_ranker",
                    "reason": xgboost_output.get("reason", "Not available"),
                    "status": xgboost_output.get("status", "unknown"),
                })
            if hist_score is None:
                skipped_models.append({
                    "model": "historical_similarity",
                    "reason": hist_output.get("reason", "Not available"),
                    "status": hist_output.get("status", "unknown"),
                })

            # Aggregate scores
            final_score, confidence, components = _aggregate_signal_score(
                raw_score=event.raw_signal_score,
                weighted_ranker=weighted_score,
                xgboost=xgboost_score,
                historical=hist_score,
                liquidity=None,  # Not implemented in event scanner
                regime=None,  # Would need regime context
                data_quality=data_quality,
            )

            # Build reasons
            reasons = [
                f"Weighted ranker: {weighted_score}/100",
                f"Data quality: {data_quality}/100",
            ]
            if xgboost_score:
                reasons.append(f"XGBoost: {xgboost_score}/100")
            if hist_score:
                reasons.append(f"Historical similarity: {hist_score}/100")

            scored = ScoredSignal(
                signal_id=f"sig-{uuid4().hex[:12]}",
                symbol=event.symbol,
                strategy_key=event.strategy_key,
                trigger_type=event.trigger_type,
                raw_signal_score=event.raw_signal_score,
                weighted_ranker_score=weighted_score,
                xgboost_score=xgboost_score,
                historical_similarity_score=hist_score,
                liquidity_score=None,
                regime_alignment_score=None,
                data_quality_score=data_quality,
                signal_score=final_score,
                confidence=confidence,
                model_outputs={
                    "weighted_ranker": weighted_output,
                    "xgboost": xgboost_output if xgboost_score else None,
                    "historical_similarity": hist_output if hist_score else None,
                },
                skipped_models=skipped_models,
                reasons=reasons,
                blockers=[],
                warnings=[],
            )
            scored_signals.append(scored)

        except Exception as e:
            skipped_signals.append({
                "symbol": event.symbol,
                "event_id": event.event_id,
                "reason": f"Scoring error: {str(e)}",
            })

    completed_at = datetime.now(timezone.utc)

    # Determine status
    status: Literal["completed", "partial", "no_events", "failed"] = "completed"
    if not scored_signals:
        status = "no_events"
    elif skipped_signals or warnings:
        status = "partial"

    response = SignalScoringResponse(
        run_id=run_id,
        status=status,
        scored_signals=scored_signals,
        skipped_signals=skipped_signals,
        blockers=blockers,
        warnings=warnings,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
    )

    # Store
    _LATEST_SCORING = response
    _SCORING_HISTORY.append(response)

    if len(_SCORING_HISTORY) > 100:
        _SCORING_HISTORY = _SCORING_HISTORY[-100:]

    return response


def get_latest_signal_scoring() -> SignalScoringResponse | None:
    """Get the most recent signal scoring run."""
    return _LATEST_SCORING


def list_signal_scoring_runs(limit: int = 20) -> list[SignalScoringResponse]:
    """List recent signal scoring runs."""
    return _SCORING_HISTORY[-limit:]
