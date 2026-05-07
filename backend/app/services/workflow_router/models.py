from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


SessionKey = Literal["pre_market", "market_open", "post_market", "after_hours"]
MarketRegime = Literal["risk_on", "risk_off", "choppy", "high_volatility", "unknown"]
VolatilityState = Literal["low", "normal", "elevated", "extreme"]
LiquidityState = Literal["good", "acceptable", "poor", "unknown"]
QualityStatus = Literal["pass", "warn", "fail"]
UrgencyLevel = Literal["low", "medium", "high", "critical"]

ProofStatus = Literal["proven", "paper_passed", "backtest_required", "research_only", "unknown"]
PaperStatus = Literal["passed", "testing", "not_started", "unknown"]

WorkflowKey = Literal[
    "baseline_fast_path",
    "adjusted_research_path",
    "paper_only_path",
    "backtest_queue_path",
    "observe_only_path",
    "no_trade_path",
]
WorkflowMode = Literal["baseline", "adjusted", "blocked"]

CheckerOutcome = Literal["pass", "warn", "fail"]


class MarketCondition(BaseModel):
    regime: MarketRegime
    volatility_state: VolatilityState
    liquidity_state: LiquidityState
    data_quality: QualityStatus
    urgency: UrgencyLevel


class StrategyOrResponseStatus(BaseModel):
    proof_status: ProofStatus
    paper_status: PaperStatus
    requires_backtest: bool
    already_backtested: bool


class AccountState(BaseModel):
    risk_budget_available: bool
    paper_trading_enabled: bool
    live_trading_enabled: bool
    human_approval_required: bool


class ExecutionState(BaseModel):
    broker_ready: bool
    spread_pass: bool
    slippage_pass: bool


class WorkflowRouteRequest(BaseModel):
    session: SessionKey
    market_condition: MarketCondition
    strategy_or_response_status: StrategyOrResponseStatus
    account_state: AccountState
    execution_state: ExecutionState


class CheckerResult(BaseModel):
    status: CheckerOutcome
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class WorkflowRouteDecision(BaseModel):
    decision_id: str
    stage_number: int = 5
    stage_name: str = "Workflow Router"
    selected_workflow: WorkflowKey
    workflow_mode: WorkflowMode
    reason: str
    llm_used: bool = False

    allowed_next_stages: list[str] = Field(
        default_factory=lambda: [
            "watchlist_builder",
            "strategy_requirements_checker",
            "trigger_monitoring",
            "execution_planner",
        ]
    )
    blocked_stages: list[BlockedStage] = Field(default_factory=list)

    checkers: dict[str, CheckerResult]
    next_action: str
    created_at: str


class WorkflowRouterStageMeta(BaseModel):
    stage_number: int = 5
    stage_name: str = "Workflow Router"
    stage_key: str = "workflow_router"


class WorkflowRouterStatusChecker(BaseModel):
    key: str
    label: str
    status: Literal["ready", "warning", "error", "disabled"]
    uses_llm: bool = False


class WorkflowRouterStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: WorkflowRouterStageMeta
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_workflows: list[WorkflowKey]
    checkers: list[WorkflowRouterStatusChecker]


def iso_utc_now() -> str:
    # Keep formatting consistent with other services (no microseconds, Z suffix).
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

