from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.schemas import AccountRiskProfile, ModelVote, PricePlan, Recommendation, RiskPlan, TradeRecommendation
from app.services.feature_store_service import FeatureStoreRunRequest, FeatureStoreRunResponse, run_feature_store_pipeline
from app.services.model_orchestrator_service import ModelRunRequest, ModelRunResponse, run_model_orchestrator
from app.services.persistence_service import (
    get_latest_decision_workflow_run as get_latest_decision_workflow_run_db,
    list_decision_workflow_runs as list_decision_workflow_runs_db,
    save_decision_workflow_run,
)
from app.services.recommendation_lifecycle_service import CreateRecommendationRequest, create_recommendation

MIN_MODEL_SCORE_TO_WATCH = 60
DEFAULT_MIN_REWARD_RISK_RATIO = 3.0


class DecisionWorkflowRunRequest(BaseModel):
    symbols: list[str] = Field(default_factory=list)
    asset_class: str = "stock"
    horizon: Literal["intraday", "day_trade", "swing", "one_month"] | str = "swing"
    source: str = "auto"
    strategy_key: str | None = None
    max_candidates: int = 5
    allow_mock: bool = False


class DecisionCandidate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: str
    horizon: str
    source: str
    provider: str | None = None
    data_quality: str
    status: str
    rank: int | None = None
    final_score: int = 0
    confidence: float = 0.0
    current_price: float | None = None
    buy_zone_low: float | None = None
    buy_zone_high: float | None = None
    stop_loss: float | None = None
    target_price: float | None = None
    reward_risk_ratio: float | None = None
    feature_row_id: str | None = None
    model_outputs: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""


class DecisionWorkflowRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: str
    source: str
    horizon: str
    symbols_requested: list[str]
    candidates: list[DecisionCandidate]
    top_action: TradeRecommendation | None = None
    recommendations: list[Recommendation] = Field(default_factory=list)
    feature_runs: list[dict[str, Any]] = Field(default_factory=list)
    model_runs: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime
    duration_ms: int


_LATEST_DECISION_RUN: DecisionWorkflowRunResponse | None = None
_DECISION_RUNS: list[DecisionWorkflowRunResponse] = []


def _empty_response(request: DecisionWorkflowRunRequest, started_at: datetime, message: str) -> DecisionWorkflowRunResponse:
    completed_at = datetime.utcnow()
    return DecisionWorkflowRunResponse(
        run_id=f"dwf-{uuid4().hex[:12]}",
        status="no_symbols_selected",
        source=request.source,
        horizon=request.horizon,
        symbols_requested=[],
        candidates=[],
        top_action=None,
        recommendations=[],
        feature_runs=[],
        model_runs=[],
        blockers=[message],
        warnings=[],
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
    )


def _as_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _scale_score(score: float | None) -> int:
    if score is None:
        return 0
    scaled = score * 100 if 0 <= score <= 1 else score
    return int(max(0, min(100, round(scaled))))


def _dedupe_outputs(outputs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, Any]] = []
    for output in outputs:
        key = (
            str(output.get("model_name") or output.get("model") or "unknown"),
            str(output.get("status") or "unknown"),
            str(output.get("rank_score") or output.get("prediction_score") or output.get("reason") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(output)
    return unique


def _best_model_score(model_run: ModelRunResponse, symbol: str) -> tuple[float | None, list[dict[str, Any]]]:
    outputs = _dedupe_outputs(list(model_run.model_outputs or []))
    best_score: float | None = None
    normalized_outputs: list[dict[str, Any]] = []
    for output in outputs:
        normalized_outputs.append(output)
        for field in ["rank_score", "score", "probability_score", "expected_return_score", "volatility_adjusted_score"]:
            score = _as_float(output.get(field))
            if score is not None:
                best_score = max(best_score or 0.0, score)
        for row in output.get("scores", []) if isinstance(output.get("scores"), list) else []:
            ticker = str(row.get("ticker") or row.get("symbol") or "").upper()
            if ticker == symbol.upper():
                score = _as_float(row.get("score") or row.get("rank_score"))
                if score is not None:
                    best_score = max(best_score or 0.0, score)
    return best_score, normalized_outputs


def _price_from_feature_run(feature_run: FeatureStoreRunResponse) -> float | None:
    return _as_float(feature_run.normalized_snapshot.price)


def _build_candidate(symbol: str, request: DecisionWorkflowRunRequest) -> tuple[DecisionCandidate, dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    warnings: list[str] = []
    feature_run = run_feature_store_pipeline(
        FeatureStoreRunRequest(
            symbol=symbol,
            asset_class=request.asset_class,
            horizon=request.horizon,
            source=request.source,
        )
    )
    warnings.extend(feature_run.warnings)
    quality = feature_run.quality_report.quality_status
    normalized = feature_run.normalized_snapshot
    price = _price_from_feature_run(feature_run)

    if quality == "fail":
        blockers.extend(feature_run.quality_report.blockers or ["Data quality failed."])
    if normalized.is_mock and not request.allow_mock:
        blockers.append("Mock data is blocked for decision workflow unless allow_mock=true.")
    if price is None:
        blockers.append("No current price returned from selected source.")

    model_run = run_model_orchestrator(
        ModelRunRequest(
            symbols=[symbol],
            asset_class=request.asset_class,
            horizon=request.horizon,
            source=request.source,
            strategy_key=request.strategy_key,
            feature_rows=[feature_run.row],
        )
    )
    warnings.extend(model_run.warnings)
    model_score, model_outputs = _best_model_score(model_run, symbol)
    if model_score is None:
        blockers.append("No completed model score returned. Weighted ranker may be blocked by missing feature quality.")

    base_score = _scale_score(model_score)
    confidence = round(max(0.0, min(0.95, base_score / 100)), 2)
    stop_loss = target_price = buy_low = buy_high = reward_risk = None
    min_reward_risk = DEFAULT_MIN_REWARD_RISK_RATIO
    if price:
        buy_low = price * 0.995
        buy_high = price * 1.005
        stop_loss = price * 0.97
        risk_per_share = price - stop_loss
        target_price = price + (risk_per_share * min_reward_risk)
        reward_risk = (target_price - price) / risk_per_share if risk_per_share > 0 else None

    if base_score < MIN_MODEL_SCORE_TO_WATCH:
        blockers.append(f"Model score {base_score}/100 is below watch threshold {MIN_MODEL_SCORE_TO_WATCH}/100.")
    if reward_risk is not None and reward_risk < min_reward_risk:
        blockers.append(f"Reward/risk {reward_risk:.2f}R is below minimum {min_reward_risk:.2f}R.")

    status = "candidate_ready" if not blockers else "blocked"
    reason = (
        "Feature-store row and model score passed source-backed watch threshold. Send to risk/approval workflow before any paper action."
        if status == "candidate_ready"
        else "Blocked until source data, feature quality, model score threshold, and reward/risk are usable."
    )
    candidate = DecisionCandidate(
        symbol=symbol.upper(),
        asset_class=request.asset_class,
        horizon=request.horizon,
        source=request.source,
        provider=normalized.provider,
        data_quality=quality,
        status=status,
        final_score=base_score,
        confidence=confidence,
        current_price=round(price, 4) if price is not None else None,
        buy_zone_low=round(buy_low, 4) if buy_low is not None else None,
        buy_zone_high=round(buy_high, 4) if buy_high is not None else None,
        stop_loss=round(stop_loss, 4) if stop_loss is not None else None,
        target_price=round(target_price, 4) if target_price is not None else None,
        reward_risk_ratio=round(reward_risk, 2) if reward_risk is not None else None,
        feature_row_id=feature_run.row.id,
        model_outputs=model_outputs,
        blockers=blockers,
        warnings=warnings,
        reason=reason,
    )
    return candidate, feature_run.model_dump(mode="json"), model_run.model_dump(mode="json")


def _candidate_to_trade_recommendation(candidate: DecisionCandidate, account_profile: AccountRiskProfile) -> TradeRecommendation | None:
    if candidate.status != "candidate_ready" or candidate.current_price is None:
        return None
    if candidate.buy_zone_low is None or candidate.buy_zone_high is None or candidate.stop_loss is None or candidate.target_price is None:
        return None
    if candidate.reward_risk_ratio is not None and candidate.reward_risk_ratio < account_profile.min_reward_risk_ratio:
        return None
    max_risk_dollars = account_profile.account_equity * (account_profile.max_risk_per_trade_percent / 100)
    return TradeRecommendation(
        symbol=candidate.symbol,
        asset_class="crypto" if candidate.asset_class == "crypto" or "-USD" in candidate.symbol else "stock",
        action="watch",
        action_label="MODEL WATCH CANDIDATE",
        horizon=candidate.horizon if candidate.horizon in {"intraday", "day_trade", "swing", "one_month"} else "swing",
        confidence=candidate.confidence,
        final_score=candidate.final_score,
        urgency="high" if candidate.final_score >= 80 else "medium" if candidate.final_score >= 65 else "low",
        price_plan=PricePlan(
            current_price=candidate.current_price,
            buy_zone_low=candidate.buy_zone_low,
            buy_zone_high=candidate.buy_zone_high,
            stop_loss=candidate.stop_loss,
            target_price=candidate.target_price,
            target_2_price=None,
        ),
        risk_plan=RiskPlan(
            position_size_dollars=0.0,
            max_dollar_risk=round(max_risk_dollars, 2),
            max_loss_percent=account_profile.max_risk_per_trade_percent,
            expected_return_percent=round(((candidate.target_price - candidate.current_price) / candidate.current_price) * 100, 2),
            reward_risk_ratio=candidate.reward_risk_ratio or 0.0,
            account_fit="requires_human_approval_before_paper_trade",
        ),
        model_votes=[
            ModelVote(model="Feature Store", status="active", signal="neutral", confidence=1.0, explanation=f"Feature row {candidate.feature_row_id} created with quality={candidate.data_quality}."),
            ModelVote(model="Model Orchestrator", status="active", signal="bullish" if candidate.final_score >= 60 else "neutral", confidence=candidate.confidence, explanation=f"Best model score={candidate.final_score}/100 from source={candidate.source}."),
            ModelVote(model="Risk Gate", status="active", signal="neutral", confidence=0.8, explanation="Recommendation remains watch-only until human approval and paper-trade validation."),
        ],
        final_reason=candidate.reason,
        invalidation_rules=[
            "Block if source data quality becomes fail or unavailable.",
            "Block if model score drops below strategy threshold.",
            "Block if spread/liquidity/risk gate fails.",
        ],
        risk_factors=candidate.blockers + candidate.warnings,
        data_mode="live" if candidate.source != "mock" else "synthetic_prototype",
        execution_enabled=False,
        research_only=True,
    )


def _candidate_to_recommendation(candidate: DecisionCandidate) -> Recommendation:
    return Recommendation(
        symbol=candidate.symbol,
        asset_class="crypto" if candidate.asset_class == "crypto" or "-USD" in candidate.symbol else "stock",
        horizon=candidate.horizon,
        final_decision="model_watch_candidate" if candidate.status == "candidate_ready" else "blocked",
        final_score=candidate.final_score,
        confidence=candidate.confidence,
        reward_risk_ratio=candidate.reward_risk_ratio or 0.0,
        account_fit="approval_required" if candidate.status == "candidate_ready" else "blocked",
        model_stack=[str(output.get("model_name") or output.get("model") or "model_output") for output in candidate.model_outputs[:4]],
        reason=candidate.reason,
        risk_factors=candidate.blockers + candidate.warnings,
    )


def run_decision_workflow(request: DecisionWorkflowRunRequest, account_profile: AccountRiskProfile | None = None) -> DecisionWorkflowRunResponse:
    global _LATEST_DECISION_RUN
    started_at = datetime.utcnow()
    account_profile = account_profile or AccountRiskProfile()
    warnings: list[str] = []
    blockers: list[str] = []
    symbols = [symbol.strip().upper() for symbol in request.symbols if symbol.strip()]
    if not symbols:
        response = _empty_response(request, started_at, "No symbols selected. Add symbols from a watchlist, scanner, or explicit workflow request.")
        _LATEST_DECISION_RUN = response
        _DECISION_RUNS.insert(0, response)
        del _DECISION_RUNS[100:]
        return response
    if request.source == "mock" and not request.allow_mock:
        blockers.append("source=mock requested but allow_mock=false. Candidates will be blocked from actionable status.")

    candidates: list[DecisionCandidate] = []
    feature_runs: list[dict[str, Any]] = []
    model_runs: list[dict[str, Any]] = []
    for symbol in symbols:
        try:
            candidate, feature_run, model_run = _build_candidate(symbol, request)
            candidates.append(candidate)
            feature_runs.append(feature_run)
            model_runs.append(model_run)
        except Exception as exc:
            candidates.append(
                DecisionCandidate(
                    symbol=symbol,
                    asset_class=request.asset_class,
                    horizon=request.horizon,
                    source=request.source,
                    data_quality="fail",
                    status="blocked",
                    blockers=[str(exc)],
                    reason="Workflow failed for this symbol.",
                )
            )
            blockers.append(f"{symbol}: {exc}")

    ranked = sorted(candidates, key=lambda item: (item.status == "candidate_ready", item.final_score), reverse=True)
    for index, candidate in enumerate(ranked, start=1):
        candidate.rank = index
    limited = ranked[: max(1, min(request.max_candidates, 25))]
    ready = [candidate for candidate in limited if candidate.status == "candidate_ready"]
    top_candidate = ready[0] if ready else None
    top_action = _candidate_to_trade_recommendation(top_candidate, account_profile) if top_candidate else None
    recommendations = [_candidate_to_recommendation(candidate) for candidate in limited]
    status = "completed_with_candidates" if top_action else "completed_no_actionable_candidates"

    # Create recommendation lifecycle records for candidate_ready candidates
    workflow_run_id = f"dwf-{uuid4().hex[:12]}"
    for candidate in ready:
        try:
            create_recommendation(
                CreateRecommendationRequest(
                    symbol=candidate.symbol,
                    asset_class=candidate.asset_class,
                    horizon=candidate.horizon,
                    source=request.source,
                    feature_row_id=candidate.feature_row_id,
                    score=candidate.final_score,
                    confidence=candidate.confidence,
                    action_label="MODEL WATCH CANDIDATE",
                    reason=candidate.reason,
                    risk_factors=candidate.blockers + candidate.warnings,
                    workflow_run_id=workflow_run_id,
                )
            )
        except Exception as exc:
            warnings.append(f"Failed to create recommendation lifecycle for {candidate.symbol}: {exc}")

    completed_at = datetime.utcnow()
    response = DecisionWorkflowRunResponse(
        run_id=workflow_run_id,
        status=status,
        source=request.source,
        horizon=request.horizon,
        symbols_requested=symbols,
        candidates=limited,
        top_action=top_action,
        recommendations=recommendations,
        feature_runs=feature_runs,
        model_runs=model_runs,
        blockers=blockers,
        warnings=warnings,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
    )

    # Persist to database if available (best effort)
    try:
        save_decision_workflow_run(response)
    except Exception:
        pass  # Continue even if DB save fails

    _LATEST_DECISION_RUN = response
    _DECISION_RUNS.insert(0, response)
    del _DECISION_RUNS[100:]
    return response


def get_latest_decision_workflow_run() -> DecisionWorkflowRunResponse | None:
    """Get the latest decision workflow run.

    Checks database first, falls back to in-memory storage.
    """
    # Try database first
    try:
        db_row = get_latest_decision_workflow_run_db()
        if db_row:
            # Convert DB row to response model
            return DecisionWorkflowRunResponse(**db_row)
    except Exception:
        pass

    # Fallback to in-memory
    return _LATEST_DECISION_RUN


def list_decision_workflow_runs(limit: int = 20) -> list[DecisionWorkflowRunResponse]:
    """List decision workflow runs.

    Checks database first, falls back to in-memory storage.
    """
    # Try database first
    try:
        db_rows = list_decision_workflow_runs_db(limit)
        if db_rows:
            return [DecisionWorkflowRunResponse(**row) for row in db_rows]
    except Exception:
        pass

    # Fallback to in-memory
    return _DECISION_RUNS[: max(1, min(limit, 100))]


def build_default_decision_workflow(account_profile: AccountRiskProfile | None = None) -> DecisionWorkflowRunResponse:
    return run_decision_workflow(
        DecisionWorkflowRunRequest(
            symbols=[],
            source="auto",
            horizon="swing",
            max_candidates=5,
            allow_mock=False,
        ),
        account_profile=account_profile,
    )
