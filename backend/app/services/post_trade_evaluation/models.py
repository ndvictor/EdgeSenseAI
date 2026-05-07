from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


OutcomeLabel = Literal[
    "win",
    "loss",
    "flat",
    "fakeout",
    "late_entry",
    "rule_violation",
    "slippage_issue",
    "stopped_out",
    "target_hit",
    "time_stop",
    "thesis_invalidated",
]

OutcomeStatus = Literal["positive", "negative", "neutral", "review_needed", "blocked"]


class CheckerResult(BaseModel):
    status: Literal["pass", "warn", "fail"]
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class TradeInput(BaseModel):
    trade_id: str
    symbol: str
    asset_class: str
    horizon: str
    side: Literal["long"]
    quantity: int
    planned_entry_price: float
    actual_entry_price: float
    planned_exit_price: float
    actual_exit_price: float
    stop_loss: float
    target_price: float
    opened_at: str
    closed_at: str
    exit_reason: str


class WorkflowContextInput(BaseModel):
    selected_workflow: str
    strategy_key: str
    trigger_key: str
    session: str


class ThesisOutcomeInput(BaseModel):
    thesis_valid_at_exit: bool
    invalidation_hit: bool
    price_above_vwap_at_exit: bool
    volume_confirmed_at_exit: bool
    relative_strength_positive_at_exit: bool


class ExecutionQualityInput(BaseModel):
    planned_entry_price: float
    actual_entry_price: float
    planned_exit_price: float
    actual_exit_price: float
    max_allowed_slippage_percent: float = 0.15


class RuleComplianceInput(BaseModel):
    entered_after_trigger: bool
    used_approved_strategy: bool
    respected_position_size: bool
    respected_stop_loss: bool
    respected_master_admin_gates: bool
    human_approval_obtained: bool


class PostTradeEvaluationEvaluateRequest(BaseModel):
    trade: TradeInput
    workflow_context: WorkflowContextInput
    thesis_outcome: ThesisOutcomeInput
    execution_quality: ExecutionQualityInput
    rule_compliance: RuleComplianceInput


class PnlResult(BaseModel):
    realized_pnl: float
    realized_pnl_percent: float
    gross_entry_notional: float
    gross_exit_notional: float


class RiskResult(BaseModel):
    risk_per_share: float
    r_multiple: float
    planned_reward_risk: float


class ExecutionQualityResult(BaseModel):
    entry_slippage_percent: float
    exit_slippage_percent: float
    slippage_status: Literal["pass", "warn", "fail"]


class RuleComplianceResult(BaseModel):
    compliant: bool
    failed_rules: list[str] = Field(default_factory=list)
    passed_rules: list[str] = Field(default_factory=list)


class AttributionResult(BaseModel):
    primary_driver: str
    secondary_driver: str | None = None
    session: str
    strategy_key: str
    trigger_key: str


class PostTradeEvaluationResult(BaseModel):
    evaluation_id: str
    stage_number: int = 13
    stage_name: str = "Post-Trade Evaluation"
    trade_id: str
    symbol: str
    asset_class: str
    horizon: str
    outcome_label: OutcomeLabel
    outcome_status: OutcomeStatus
    llm_used: bool = False
    pnl: PnlResult
    risk_result: RiskResult
    execution_quality_result: ExecutionQualityResult
    rule_compliance_result: RuleComplianceResult
    attribution: AttributionResult
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkers: dict[str, CheckerResult] = Field(default_factory=dict)
    allowed_next_stages: list[str] = Field(default_factory=list)
    blocked_next_stages: list[BlockedStage] = Field(default_factory=list)
    next_action: str
    created_at: str


class PostTradeEvaluationStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: dict
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_outcome_labels: list[str]
    checkers: list[dict]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

