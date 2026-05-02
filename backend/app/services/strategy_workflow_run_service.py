from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.agents.portfolio_manager_agent import run_portfolio_manager_agent
from app.agents.risk_manager_agent import run_risk_manager_agent
from app.services.auto_run_control_service import get_auto_run_state
from app.services.feature_store_service import FeatureStoreRunRequest, run_feature_store_pipeline
from app.services.model_orchestrator_service import ModelRunPlanRequest, ModelRunRequest, plan_model_runs, run_model_orchestrator
from app.strategies.registry import get_strategy


StrategyWorkflowTrigger = Literal["manual", "scheduled", "scanner_match"]


class StrategyWorkflowRunRequest(BaseModel):
    strategy_key: str
    symbol: str
    asset_class: str = "stock"
    horizon: str = "swing"
    matched_signal_key: str | None = None
    matched_signal_name: str | None = None
    source_scan_run_id: str | None = None
    trigger_type: StrategyWorkflowTrigger = "manual"
    data_source: str = "auto"
    account_size: float | None = None
    max_risk_per_trade: float | None = None


class StrategyWorkflowTraceStep(BaseModel):
    step_name: str
    status: str
    started_at: datetime
    completed_at: datetime
    duration_ms: int
    summary: str
    data_source: str = "placeholder"
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class StrategyWorkflowRunResult(BaseModel):
    workflow_run_id: str
    source_scan_run_id: str | None = None
    trigger_type: StrategyWorkflowTrigger
    strategy_key: str
    symbol: str
    asset_class: str
    horizon: str
    matched_signal_key: str | None = None
    matched_signal_name: str | None = None
    required_agents: list[str] = Field(default_factory=list)
    required_models: list[str] = Field(default_factory=list)
    data_quality: dict[str, Any] = Field(default_factory=dict)
    feature_row: dict[str, Any] = Field(default_factory=dict)
    model_plan: dict[str, Any] = Field(default_factory=dict)
    model_outputs: list[dict[str, Any]] = Field(default_factory=list)
    risk_review: dict[str, Any] = Field(default_factory=dict)
    portfolio_decision: dict[str, Any] = Field(default_factory=dict)
    recommendation: dict[str, Any] = Field(default_factory=dict)
    approval_required: bool = True
    paper_trade_allowed: bool = False
    live_trading_allowed: bool = False
    status: str
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    trace: list[StrategyWorkflowTraceStep] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime
    duration_ms: int


class StrategyWorkflowRunSummary(BaseModel):
    total_runs: int
    workflow_runs_today: int
    latest_run: StrategyWorkflowRunResult | None = None
    runs: list[StrategyWorkflowRunResult] = Field(default_factory=list)


_WORKFLOW_RUNS: list[StrategyWorkflowRunResult] = []


def _step(
    *,
    step_name: str,
    started_at: datetime,
    summary: str,
    status: str = "completed",
    data_source: str = "placeholder",
    metadata: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> StrategyWorkflowTraceStep:
    completed_at = datetime.utcnow()
    return StrategyWorkflowTraceStep(
        step_name=step_name,
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
        summary=summary,
        data_source=data_source,
        metadata=metadata or {},
        warnings=warnings or [],
        errors=errors or [],
    )


def _record(result: StrategyWorkflowRunResult) -> StrategyWorkflowRunResult:
    _WORKFLOW_RUNS.insert(0, result)
    del _WORKFLOW_RUNS[250:]
    return result


def _best_model_score(model_outputs: list[dict[str, Any]], symbol: str) -> float | None:
    for output in model_outputs:
        if output.get("model_name") == "weighted_ranker_v1" and output.get("rank_score") is not None:
            return float(output.get("rank_score") or 0)
        if output.get("model") == "weighted_ranker":
            for score in output.get("scores", []):
                if score.get("ticker") == symbol.upper():
                    return float(score.get("score") or 0)
    return None


def run_strategy_workflow_from_signal(request: StrategyWorkflowRunRequest) -> StrategyWorkflowRunResult:
    started_at = datetime.utcnow()
    trace: list[StrategyWorkflowTraceStep] = []
    warnings = ["Research/paper-only workflow. No broker API or trade execution is called."]
    errors: list[str] = []
    workflow_run_id = f"swf-{uuid4().hex[:12]}"
    strategy = get_strategy(request.strategy_key)
    safety_state = get_auto_run_state()

    if strategy is None:
        errors.append(f"Unknown strategy: {request.strategy_key}")
        completed_at = datetime.utcnow()
        return _record(
            StrategyWorkflowRunResult(
                workflow_run_id=workflow_run_id,
                source_scan_run_id=request.source_scan_run_id,
                trigger_type=request.trigger_type,
                strategy_key=request.strategy_key,
                symbol=request.symbol.upper(),
                asset_class=request.asset_class,
                horizon=request.horizon,
                matched_signal_key=request.matched_signal_key,
                matched_signal_name=request.matched_signal_name,
                status="failed",
                warnings=warnings,
                errors=errors,
                approval_required=True,
                paper_trade_allowed=False,
                live_trading_allowed=False,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
            )
        )

    step_started = datetime.utcnow()
    feature_run = run_feature_store_pipeline(
        FeatureStoreRunRequest(symbol=request.symbol, asset_class=request.asset_class or strategy.asset_class, horizon=request.horizon or strategy.timeframe, source=request.data_source)
    )
    trace.append(
        _step(
            step_name="data_quality_and_feature_store",
            started_at=step_started,
            summary=f"Quality={feature_run.quality_report.quality_status}; feature row stored for {feature_run.row.ticker}.",
            data_source=feature_run.quality_report.data_source,
            metadata={"quality_report": feature_run.quality_report.model_dump(), "feature_row_id": feature_run.row.id},
            warnings=feature_run.warnings,
        )
    )
    if feature_run.quality_report.quality_status == "fail":
        warnings.append("Data quality failed; recommendation remains watch-only.")

    step_started = datetime.utcnow()
    model_plan = plan_model_runs(
        ModelRunPlanRequest(symbols=[request.symbol], asset_class=request.asset_class or strategy.asset_class, horizon=request.horizon or strategy.timeframe, source=request.data_source, feature_rows=[feature_run.row])
    )
    trace.append(_step(step_name="model_plan", started_at=step_started, summary=f"Planned {len(model_plan.models)} model(s).", data_source=model_plan.data_source, metadata=model_plan.model_dump(), warnings=model_plan.warnings))

    step_started = datetime.utcnow()
    model_run = run_model_orchestrator(
        ModelRunRequest(symbols=[request.symbol], asset_class=request.asset_class or strategy.asset_class, horizon=request.horizon or strategy.timeframe, source=request.data_source, feature_rows=[feature_run.row])
    )
    trace.append(_step(step_name="model_run", started_at=step_started, summary=f"Model orchestrator returned {len(model_run.results)} output(s).", data_source=model_run.data_source, metadata={"results_count": len(model_run.results)}, warnings=model_run.warnings))
    warnings.extend(model_run.warnings)

    current_price = feature_run.normalized_snapshot.price
    detected_signal = {
        "symbol": request.symbol.upper(),
        "signal_key": request.matched_signal_key or "manual_strategy_workflow",
        "signal_name": request.matched_signal_name or request.matched_signal_key or "Manual strategy workflow",
        "current_price": current_price,
        "entry_price": current_price,
        "data_source": feature_run.quality_report.data_source,
    }

    step_started = datetime.utcnow()
    risk_agent = run_risk_manager_agent(
        {
            "workflow_name": "strategy_workflow_runner",
            "detected_signals": [detected_signal],
            "account_size": request.account_size,
            "max_risk_per_trade": request.max_risk_per_trade,
        }
    )
    risk_review = risk_agent.metadata
    trace.append(_step(step_name="risk_review", started_at=step_started, summary=risk_agent.summary, status=risk_agent.status, data_source=risk_agent.data_source, metadata=risk_agent.model_dump(), warnings=risk_agent.warnings, errors=risk_agent.errors))
    risk_passed = any(review.get("passed") for review in risk_review.get("reviews", []))

    step_started = datetime.utcnow()
    portfolio_agent = run_portfolio_manager_agent({"workflow_name": "strategy_workflow_runner", "detected_signals": [detected_signal], "risk_reviews": risk_review.get("reviews", [])})
    portfolio_decision = portfolio_agent.metadata.get("decision", {})
    trace.append(_step(step_name="portfolio_manager", started_at=step_started, summary=portfolio_agent.summary, status=portfolio_agent.status, data_source=portfolio_agent.data_source, metadata=portfolio_agent.model_dump(), warnings=portfolio_agent.warnings, errors=portfolio_agent.errors))

    model_score = _best_model_score(model_run.results, request.symbol)
    paper_trade_allowed = bool(safety_state.paper_trading_enabled and risk_passed and feature_run.quality_report.quality_status in {"pass", "warn"})
    recommendation = {
        "action": "paper_review_candidate" if paper_trade_allowed else "watch_only",
        "symbol": request.symbol.upper(),
        "strategy_key": strategy.strategy_key,
        "matched_signal": request.matched_signal_name or request.matched_signal_key or "manual",
        "model_score": model_score,
        "data_quality": feature_run.quality_report.quality_status,
        "risk_passed": risk_passed,
        "next_action": "Send to human approval queue before any paper action." if paper_trade_allowed else "Review blockers before treating this as actionable.",
        "paper_only": True,
    }

    completed_at = datetime.utcnow()
    return _record(
        StrategyWorkflowRunResult(
            workflow_run_id=workflow_run_id,
            source_scan_run_id=request.source_scan_run_id,
            trigger_type=request.trigger_type,
            strategy_key=strategy.strategy_key,
            symbol=request.symbol.upper(),
            asset_class=request.asset_class or strategy.asset_class,
            horizon=request.horizon or strategy.timeframe,
            matched_signal_key=request.matched_signal_key,
            matched_signal_name=request.matched_signal_name,
            required_agents=strategy.required_agents,
            required_models=strategy.required_models,
            data_quality=feature_run.quality_report.model_dump(),
            feature_row=feature_run.row.model_dump(),
            model_plan=model_plan.model_dump(),
            model_outputs=model_run.results,
            risk_review=risk_review,
            portfolio_decision=portfolio_decision,
            recommendation=recommendation,
            approval_required=True,
            paper_trade_allowed=paper_trade_allowed,
            live_trading_allowed=False,
            status="completed_with_approval_required" if paper_trade_allowed else "completed_watch_only",
            warnings=warnings + risk_agent.warnings + portfolio_agent.warnings,
            errors=errors + risk_agent.errors + portfolio_agent.errors,
            trace=trace,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=max(0, int((completed_at - started_at).total_seconds() * 1000)),
        )
    )


def list_strategy_workflow_runs(limit: int = 25) -> list[StrategyWorkflowRunResult]:
    return _WORKFLOW_RUNS[: max(1, min(limit, 100))]


def get_latest_strategy_workflow_run() -> StrategyWorkflowRunResult | None:
    return _WORKFLOW_RUNS[0] if _WORKFLOW_RUNS else None


def get_strategy_workflow_run(workflow_run_id: str) -> StrategyWorkflowRunResult | None:
    return next((run for run in _WORKFLOW_RUNS if run.workflow_run_id == workflow_run_id), None)


def get_strategy_workflow_run_summary(limit: int = 25) -> StrategyWorkflowRunSummary:
    today = datetime.utcnow().date()
    return StrategyWorkflowRunSummary(
        total_runs=len(_WORKFLOW_RUNS),
        workflow_runs_today=sum(1 for run in _WORKFLOW_RUNS if run.started_at.date() == today),
        latest_run=get_latest_strategy_workflow_run(),
        runs=list_strategy_workflow_runs(limit),
    )
