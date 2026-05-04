"""Recommendation Pipeline Service.

Orchestrates steps 14-19 from latest meta-model ensemble signal.

NO paid LLM calls.
NO live execution.
Human approval required.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.agent_validation_service import (
    AgentValidationRequest,
    AgentValidationResponse,
    get_latest_agent_validation,
    run_agent_validation,
)
from app.services.capital_allocation_service import (
    CapitalAllocationRequest,
    CapitalAllocationResponse,
    create_capital_allocation_plan,
    get_latest_capital_allocation,
)
from app.services.llm_budget_gate_service import (
    LLMBudgetGateRequest,
    LLMBudgetGateResponse,
    evaluate_llm_budget_gate,
    get_latest_llm_budget_gate,
)
from app.services.meta_model_ensemble_service import (
    EnsembleSignal,
    MetaModelEnsembleResponse,
    get_latest_meta_model_ensemble,
)
from app.services.no_trade_service import (
    NoTradeRequest,
    NoTradeResponse,
    evaluate_no_trade,
    get_latest_no_trade,
)
from app.services.persistence_service import (
    get_latest_recommendation_pipeline_run,
    save_recommendation_pipeline_run,
)
from app.services.recommendation_lifecycle_service import (
    CreateRecommendationRequest,
    RecommendationLifecycleRecord,
    RecommendationStatus,
    create_recommendation,
)
from app.services.risk_manager_service import (
    RiskReviewRequest,
    RiskReviewResponse,
    get_latest_risk_review,
    review_risk,
)


class RecommendationPipelineRequest(BaseModel):
    """Request to run recommendation pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    use_latest_ensemble: bool = True
    ensemble_signal: dict[str, Any] | None = None
    symbol: str | None = None
    account_equity: float = Field(default=1000, ge=0)
    buying_power: float = Field(default=1000, ge=0)
    allow_paid_llm: bool = False
    dry_run: bool = True


class PipelineStage(BaseModel):
    """A stage in the pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    stage: str
    status: Literal["pending", "running", "completed", "blocked", "skipped"]
    result: dict[str, Any] | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PipelineRecommendation(BaseModel):
    """A recommendation produced by the pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    id: str
    symbol: str
    action_label: str
    status: RecommendationStatus
    final_signal_score: float
    confidence: float
    risk_status: str
    no_trade_decision: str
    llm_policy: str
    capital_allocation_dollars: float
    position_size_units: float
    entry_zone_low: float
    entry_zone_high: float
    stop_loss: float
    target_price: float
    reward_risk_ratio: float
    paper_trade_allowed: bool
    live_trading_allowed: bool = False
    approval_required: bool = True
    reason: str
    data_source: str = "pipeline_generated"
    signal_source: str = "meta_model_ensemble"
    model_source: str = "meta_model_ensemble_service"
    model_used: str = "ensemble_signal"
    agent_source: str = "agent_validation_service,risk_manager_service,no_trade_service,capital_allocation_service"
    llm_source: str = "llm_budget_gate_service"
    llm_used: str = "none_paid_dry_run_policy"
    market_data_source: str = "placeholder_current_price"
    price_source_detail: str = "capital allocation currently uses placeholder current_price=100.0; not live market price"
    real_market_data_used: bool = False
    final_trade_decision_allowed: bool = False


class RecommendationPipelineResponse(BaseModel):
    """Response from recommendation pipeline."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal[
        "no_signal_available",
        "llm_gate_skipped",
        "agent_validation_blocked",
        "risk_blocked",
        "no_trade",
        "capital_allocation_blocked",
        "recommendation_created",
        "completed",
    ]
    symbol: str | None = None
    llm_budget_gate: LLMBudgetGateResponse | None = None
    agent_validation: AgentValidationResponse | None = None
    risk_review: RiskReviewResponse | None = None
    no_trade: NoTradeResponse | None = None
    capital_allocation: CapitalAllocationResponse | None = None
    recommendation: PipelineRecommendation | None = None
    stages: list[PipelineStage]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    source_provenance: dict[str, Any] = Field(default_factory=dict)
    started_at: datetime
    completed_at: datetime


# In-memory storage
_LATEST_PIPELINE_RUN: RecommendationPipelineResponse | None = None


def _build_source_provenance(real_market_data_used: bool = False) -> dict[str, Any]:
    return {
        "data_source": "pipeline_generated",
        "signal_source": "meta_model_ensemble_service",
        "model_source": "meta_model_ensemble_service",
        "model_used": "ensemble_signal",
        "agent_source": "agent_validation_service,risk_manager_service,no_trade_service,capital_allocation_service",
        "llm_source": "llm_budget_gate_service",
        "llm_used": "none_paid_dry_run_policy",
        "market_data_source": "placeholder_current_price",
        "price_source_detail": "capital allocation currently uses placeholder current_price=100.0; not live market price",
        "real_market_data_used": real_market_data_used,
        "final_trade_decision_allowed": False,
    }


def _pipeline_from_record(row: dict) -> RecommendationPipelineResponse | None:
    try:
        stages = []
        for key in ["llm_budget_gate", "agent_validation", "risk_review", "no_trade", "capital_allocation"]:
            if row.get(key):
                stages.append({"stage": key, "status": "completed", "result": row.get(key), "blockers": [], "warnings": []})
        return RecommendationPipelineResponse.model_validate({
            "run_id": row.get("run_id"),
            "status": row.get("status"),
            "symbol": row.get("symbol"),
            "llm_budget_gate": row.get("llm_budget_gate"),
            "agent_validation": row.get("agent_validation"),
            "risk_review": row.get("risk_review"),
            "no_trade": row.get("no_trade"),
            "capital_allocation": row.get("capital_allocation"),
            "recommendation": row.get("recommendation"),
            "stages": stages,
            "blockers": row.get("blockers") or [],
            "warnings": row.get("warnings") or [],
            "source_provenance": row.get("source_provenance") or _build_source_provenance(False),
            "started_at": row.get("started_at"),
            "completed_at": row.get("completed_at"),
        })
    except Exception:
        return None


def _blocked_response(
    run_id: str,
    status: str,
    symbol: str | None,
    stages: list[PipelineStage],
    blockers: list[str],
    warnings: list[str],
    started_at: datetime,
    **kwargs: Any,
) -> RecommendationPipelineResponse:
    return RecommendationPipelineResponse(
        run_id=run_id,
        status=status,  # type: ignore[arg-type]
        symbol=symbol,
        stages=stages,
        blockers=blockers,
        warnings=warnings,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
        source_provenance=_build_source_provenance(False),
        **kwargs,
    )


def run_recommendation_pipeline(request: RecommendationPipelineRequest) -> RecommendationPipelineResponse:
    """Run recommendation pipeline.

    Rules:
    - If no ensemble signal, return no_signal_available.
    - Stop early if blocked/no_trade.
    - Do not call paid LLM.
    - Do not create recommendation for blocked signals.
    - If recommendation created, status pending_review.
    - No live execution.
    """
    run_id = f"rec-pipe-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)
    stages: list[PipelineStage] = []
    blockers: list[str] = []
    warnings: list[str] = []

    # Step 1: Get ensemble signal
    ensemble_signal: EnsembleSignal | None = None
    if request.use_latest_ensemble:
        latest_ensemble = get_latest_meta_model_ensemble()
        if latest_ensemble and latest_ensemble.passed_signals:
            # Use first passing signal
            ensemble_signal = latest_ensemble.passed_signals[0]
        elif latest_ensemble and latest_ensemble.watch_signals:
            # Fall back to watch signal
            ensemble_signal = latest_ensemble.watch_signals[0]
    elif request.ensemble_signal:
        # Parse from request
        ensemble_signal = EnsembleSignal(**request.ensemble_signal)

    if ensemble_signal is None:
        return _blocked_response(
            run_id=run_id,
            status="no_signal_available",
            symbol=request.symbol,
            stages=[PipelineStage(stage="ensemble_signal", status="blocked", blockers=["no_ensemble_signal_available"])],
            blockers=["no_ensemble_signal_available"],
            warnings=warnings,
            started_at=started_at,
            llm_budget_gate=None,
            agent_validation=None,
            risk_review=None,
            no_trade=None,
            capital_allocation=None,
            recommendation=None,
        )

    symbol = ensemble_signal.symbol
    final_score = ensemble_signal.final_signal_score
    confidence = ensemble_signal.confidence

    stages.append(PipelineStage(stage="ensemble_signal", status="completed"))

    # Step 2: LLM Budget Gate
    llm_gate = evaluate_llm_budget_gate(
        LLMBudgetGateRequest(
            symbol=symbol,
            final_signal_score=final_score,
            confidence=confidence,
            allow_paid_llm=request.allow_paid_llm,
            dry_run=request.dry_run,
        )
    )
    stages.append(
        PipelineStage(
            stage="llm_budget_gate",
            status="completed" if llm_gate.status == "approved" else "skipped",
            blockers=llm_gate.blockers,
            warnings=llm_gate.warnings,
        )
    )

    # Step 3: Agent Validation
    agent_val = run_agent_validation(
        AgentValidationRequest(
            ensemble_signal=ensemble_signal.model_dump(),
            symbol=symbol,
            final_signal_score=final_score,
            confidence=confidence,
            llm_policy=llm_gate.llm_validation_policy,
            dry_run=request.dry_run,
        )
    )
    stages.append(
        PipelineStage(
            stage="agent_validation",
            status="completed" if agent_val.status in ("pass", "watch") else "blocked",
            blockers=agent_val.blockers,
            warnings=agent_val.warnings,
        )
    )

    if agent_val.status == "blocked":
        return _blocked_response(
            run_id=run_id,
            status="agent_validation_blocked",
            symbol=symbol,
            llm_budget_gate=llm_gate,
            agent_validation=agent_val,
            risk_review=None,
            no_trade=None,
            capital_allocation=None,
            recommendation=None,
            stages=stages,
            blockers=agent_val.blockers,
            warnings=warnings + agent_val.warnings,
            started_at=started_at,
        )

    # Step 4: Risk Review
    risk_review = review_risk(
        RiskReviewRequest(
            symbol=symbol,
            final_signal_score=final_score,
            confidence=confidence,
            account_equity=request.account_equity,
            buying_power=request.buying_power,
            data_quality="pass" if agent_val.status == "pass" else "degraded",
        )
    )
    stages.append(
        PipelineStage(
            stage="risk_review",
            status="completed" if risk_review.status != "blocked" else "blocked",
            blockers=risk_review.blockers,
            warnings=risk_review.warnings,
        )
    )

    if risk_review.status == "blocked":
        return _blocked_response(
            run_id=run_id,
            status="risk_blocked",
            symbol=symbol,
            llm_budget_gate=llm_gate,
            agent_validation=agent_val,
            risk_review=risk_review,
            no_trade=None,
            capital_allocation=None,
            recommendation=None,
            stages=stages,
            blockers=risk_review.blockers,
            warnings=warnings + risk_review.warnings,
            started_at=started_at,
        )

    # Step 5: No-Trade Evaluation
    no_trade = evaluate_no_trade(
        NoTradeRequest(
            final_signal_score=final_score,
            confidence=confidence,
            risk_status=risk_review.status,
            buying_power=request.buying_power,
            account_equity=request.account_equity,
        )
    )
    stages.append(
        PipelineStage(
            stage="no_trade",
            status="completed" if no_trade.decision == "trade_allowed" else "blocked",
            blockers=no_trade.blockers,
            warnings=no_trade.warnings,
        )
    )

    if no_trade.decision in ("no_trade", "preserve_capital"):
        return _blocked_response(
            run_id=run_id,
            status="no_trade",
            symbol=symbol,
            llm_budget_gate=llm_gate,
            agent_validation=agent_val,
            risk_review=risk_review,
            no_trade=no_trade,
            capital_allocation=None,
            recommendation=None,
            stages=stages,
            blockers=no_trade.blockers,
            warnings=warnings + no_trade.warnings,
            started_at=started_at,
        )

    # Step 6: Capital Allocation
    # Explicit placeholder until wired to provider-backed quote/feature row.
    current_price = 100.0
    warnings.append("capital_allocation_current_price_is_placeholder_100_not_live_market_data")

    cap_alloc = create_capital_allocation_plan(
        CapitalAllocationRequest(
            symbol=symbol,
            current_price=current_price,
            final_signal_score=final_score,
            confidence=confidence,
            risk_status=risk_review.status,
            account_equity=request.account_equity,
            buying_power=request.buying_power,
        )
    )
    stages.append(
        PipelineStage(
            stage="capital_allocation",
            status="completed" if cap_alloc.status == "plan_created" else "blocked",
            blockers=cap_alloc.blockers,
            warnings=cap_alloc.warnings,
        )
    )

    if cap_alloc.status == "blocked":
        return _blocked_response(
            run_id=run_id,
            status="capital_allocation_blocked",
            symbol=symbol,
            llm_budget_gate=llm_gate,
            agent_validation=agent_val,
            risk_review=risk_review,
            no_trade=no_trade,
            capital_allocation=cap_alloc,
            recommendation=None,
            stages=stages,
            blockers=cap_alloc.blockers,
            warnings=warnings + cap_alloc.warnings,
            started_at=started_at,
        )

    # Step 7: Create Recommendation
    action_label = "long" if "long" in ensemble_signal.trigger_type.lower() else "short" if "short" in ensemble_signal.trigger_type.lower() else "watch"

    rec_request = CreateRecommendationRequest(
        symbol=symbol,
        score=final_score,
        confidence=confidence,
        action_label=action_label,
        reason=f"Pipeline passed all gates. RR={cap_alloc.reward_risk_ratio:.2f}. "
               f"Risk: {risk_review.status}. No-trade: {no_trade.decision}.",
        risk_factors=risk_review.warnings + risk_review.blockers + ["price_source_placeholder_100_not_live_market_data"],
        workflow_run_id=run_id,
    )

    rec_record = create_recommendation(rec_request)
    provenance = _build_source_provenance(False)

    pipeline_rec = PipelineRecommendation(
        id=rec_record.id,
        symbol=rec_record.symbol,
        action_label=rec_record.action_label,
        status=rec_record.status,
        final_signal_score=final_score,
        confidence=confidence,
        risk_status=risk_review.status,
        no_trade_decision=no_trade.decision,
        llm_policy=llm_gate.llm_validation_policy,
        capital_allocation_dollars=cap_alloc.capital_allocation_dollars,
        position_size_units=cap_alloc.position_size_units,
        entry_zone_low=cap_alloc.entry_zone_low,
        entry_zone_high=cap_alloc.entry_zone_high,
        stop_loss=cap_alloc.stop_loss,
        target_price=cap_alloc.target_price,
        reward_risk_ratio=cap_alloc.reward_risk_ratio,
        paper_trade_allowed=cap_alloc.paper_trade_allowed,
        live_trading_allowed=False,
        approval_required=True,
        reason=rec_record.reason,
        **provenance,
    )

    stages.append(PipelineStage(stage="recommendation", status="completed"))

    result = RecommendationPipelineResponse(
        run_id=run_id,
        status="recommendation_created",
        symbol=symbol,
        llm_budget_gate=llm_gate,
        agent_validation=agent_val,
        risk_review=risk_review,
        no_trade=no_trade,
        capital_allocation=cap_alloc,
        recommendation=pipeline_rec,
        stages=stages,
        blockers=[],
        warnings=warnings,
        source_provenance=provenance,
        started_at=started_at,
        completed_at=datetime.now(timezone.utc),
    )

    # Store latest
    global _LATEST_PIPELINE_RUN
    _LATEST_PIPELINE_RUN = result
    save_recommendation_pipeline_run(result)

    return result


def get_latest_recommendation_pipeline() -> RecommendationPipelineResponse | None:
    """Get the latest recommendation pipeline run."""
    row = get_latest_recommendation_pipeline_run()
    if row:
        restored = _pipeline_from_record(row)
        if restored:
            return restored
    return _LATEST_PIPELINE_RUN
