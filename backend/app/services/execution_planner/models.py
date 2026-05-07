from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PlanStatus = Literal["planned", "blocked"]
OrderStyle = Literal["limit", "market"]
StopMethod = Literal["atr"]


class CheckerResult(BaseModel):
    status: Literal["pass", "warn", "fail"]
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class TriggerEvaluationStub(BaseModel):
    trigger_state: str
    symbol: str
    asset_class: str
    horizon: str
    trigger_key: str


class MarketSnapshot(BaseModel):
    current_price: float
    vwap: float
    atr: float
    bid: float | None = None
    ask: float | None = None
    spread_percent: float
    volume_confirms: bool


class AccountState(BaseModel):
    account_equity: float
    cash: float
    risk_budget_available: bool
    max_risk_per_trade_percent: float
    max_position_size_percent: float
    paper_trading_enabled: bool
    live_trading_enabled: bool
    human_approval_required: bool
    execution_enabled: bool


class PlanningPreferences(BaseModel):
    order_style: str = "limit"
    stop_method: str = "atr"
    target_reward_risk: float = 2.0
    atr_stop_multiplier: float = 1.0
    max_spread_percent: float = 0.15


class ExecutionPlannerPlanRequest(BaseModel):
    trigger_evaluation: TriggerEvaluationStub
    market_snapshot: MarketSnapshot
    account_state: AccountState
    planning_preferences: PlanningPreferences


class EntryPlan(BaseModel):
    order_type: str
    side: Literal["buy"]
    limit_price: float | None = None
    reference_price: float


class RiskPlan(BaseModel):
    stop_loss: float
    target_price: float
    risk_per_share: float
    reward_per_share: float
    reward_risk_ratio: float
    max_dollar_risk: float


class SizingPlan(BaseModel):
    planned_quantity: int
    planned_notional: float
    position_size_percent: float
    max_allowed_notional: float
    sizing_status: Literal["ok", "capped"]


class ExecutionReadiness(BaseModel):
    spread_pass: bool
    slippage_pass: bool
    workflow_enabled: bool
    execution_enabled: bool
    paper_trading_enabled: bool
    live_trading_enabled: bool
    broker_execution_enabled: bool
    human_approval_required: bool
    emergency_stop: bool
    force_close_requested: bool


class ExecutionPlan(BaseModel):
    plan_id: str
    stage_number: int = 9
    stage_name: str = "Execution Planner"
    symbol: str
    asset_class: str
    horizon: str
    plan_status: PlanStatus
    llm_used: bool = False
    entry: EntryPlan
    risk: RiskPlan
    sizing: SizingPlan
    execution_readiness: ExecutionReadiness
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkers: dict[str, CheckerResult] = Field(default_factory=dict)
    allowed_next_stages: list[str] = Field(default_factory=list)
    blocked_next_stages: list[BlockedStage] = Field(
        default_factory=lambda: [
            BlockedStage(stage="trade_execution", reason="Execution is disabled or plan blockers exist.")
        ]
    )
    next_action: str
    created_at: str


class HandoffPreferences(BaseModel):
    org_slug: str = "default"
    source: str = "execution_planner"
    allow_submit: bool = False
    require_human_approval: bool = True


class ExecutionPlanHandoffInput(BaseModel):
    """Subset of Stage-9 plan used for safe precheck handoff."""

    plan_id: str
    symbol: str
    asset_class: str
    horizon: str
    plan_status: str
    entry: EntryPlan
    risk: RiskPlan
    sizing: SizingPlan
    execution_readiness: ExecutionReadiness
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExecutionPrecheckPreview(BaseModel):
    status: Literal["passed", "blocked", "failed"]
    steps: list[dict] = Field(default_factory=list)


class ExecutionRequestPreview(BaseModel):
    org_slug: str
    symbol: str
    asset_class: str
    side: str
    quantity: int
    order_type: str
    limit_price: float | None = None
    time_in_force: str = "day"
    source: str = "execution_planner"
    reason: str = "stage_9_execution_plan_precheck"
    human_approval_confirmed: bool = False
    metadata: dict = Field(default_factory=dict)


class PrecheckHandoffRequest(BaseModel):
    execution_plan: ExecutionPlanHandoffInput
    handoff_preferences: HandoffPreferences = Field(default_factory=HandoffPreferences)


class ExecutionPlannerHandoff(BaseModel):
    handoff_id: str
    stage_number: int = 9
    handoff_to_stage: int = 10
    handoff_type: Literal["execution_precheck"] = "execution_precheck"
    plan_id: str
    symbol: str
    precheck_status: Literal["passed", "blocked", "failed"]
    llm_used: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    execution_request_preview: ExecutionRequestPreview
    precheck: ExecutionPrecheckPreview
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    allowed_next_stages: list[str] = Field(default_factory=list)
    blocked_next_stages: list[BlockedStage] = Field(
        default_factory=lambda: [
            BlockedStage(stage="trade_execution", reason="This handoff only runs precheck. It never submits orders.")
        ]
    )
    next_action: str
    created_at: str


class PrecheckHandoffResponse(BaseModel):
    status: Literal["ok"]
    handoff: ExecutionPlannerHandoff


class ExecutionPlannerStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: dict
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    checkers: list[dict]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

