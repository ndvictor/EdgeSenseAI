from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


WorkflowMode = Literal["baseline", "adjusted", "blocked"]
WorkflowKey = Literal[
    "baseline_fast_path",
    "adjusted_research_path",
    "paper_only_path",
    "backtest_queue_path",
    "observe_only_path",
    "no_trade_path",
]
SessionKey = Literal["pre_market", "market_open", "post_market", "after_hours", "closed", "holiday", "unknown"]

StrategyGroup = Literal[
    "regime_aware_momentum",
    "catalyst_event_driven",
    "rvol_vwap_breakout",
    "cross_sectional_ranking",
    "options_quality_volatility",
    "execution_quality",
    "lob_microstructure_research",
]

ProofStatus = Literal["proven", "paper_passed", "backtest_required", "research_only", "unknown", "blocked"]
PaperStatus = Literal["passed", "testing", "not_started", "unknown"]

MarketRegime = Literal["risk_on", "risk_off", "choppy", "high_volatility", "unknown"]
VolatilityState = Literal["low", "normal", "elevated", "extreme"]
LiquidityState = Literal["good", "acceptable", "poor", "unknown"]
QualityStatus = Literal["pass", "warn", "fail"]
UrgencyLevel = Literal["low", "medium", "high", "critical"]

CheckerOutcome = Literal["pass", "warn", "fail"]
EligibilityStatus = Literal["eligible", "paper_only", "research_only", "blocked"]


class WorkflowContext(BaseModel):
    selected_workflow: WorkflowKey
    workflow_mode: WorkflowMode
    session: SessionKey


class StrategyCandidate(BaseModel):
    strategy_key: str
    strategy_group: StrategyGroup
    proof_status: ProofStatus
    paper_status: PaperStatus
    requires_backtest: bool
    already_backtested: bool


class MarketCondition(BaseModel):
    regime: MarketRegime
    volatility_state: VolatilityState
    liquidity_state: LiquidityState
    data_quality: QualityStatus
    urgency: UrgencyLevel


class Features(BaseModel):
    rvol_elevated: bool = False
    price_above_vwap: bool = False
    vwap_reclaiming: bool = False
    relative_strength_positive: bool = False
    catalyst_confirmed: bool = False
    volume_confirms: bool = False
    spread_pass: bool = False
    risk_reward_pass: bool = False


class AccountState(BaseModel):
    risk_budget_available: bool
    paper_trading_enabled: bool
    live_trading_enabled: bool
    human_approval_required: bool


class StrategyEligibilityCheckRequest(BaseModel):
    workflow_context: WorkflowContext
    strategy_candidate: StrategyCandidate
    market_condition: MarketCondition
    features: Features
    account_state: AccountState


class CheckerResult(BaseModel):
    status: CheckerOutcome
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class StrategyEligibilityResult(BaseModel):
    check_id: str
    stage_number: int = 7
    stage_name: str = "Strategy Requirements & Eligibility Checker"

    strategy_key: str
    strategy_group: StrategyGroup
    eligible: bool
    eligibility_status: EligibilityStatus
    llm_used: bool = False
    reason: str
    proof_status: ProofStatus
    paper_status: PaperStatus

    requirements_passed: list[str] = Field(default_factory=list)
    requirements_failed: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    checkers: dict[str, CheckerResult]

    allowed_next_stages: list[str] = Field(default_factory=lambda: ["trigger_monitoring", "execution_planner"])
    blocked_next_stages: list[BlockedStage] = Field(
        default_factory=lambda: [
            BlockedStage(
                stage="trade_execution",
                reason="Execution must wait for trigger monitoring and execution planning.",
            )
        ]
    )
    next_action: str
    created_at: str


class StrategyEligibilityStageMeta(BaseModel):
    stage_number: int = 7
    stage_name: str = "Strategy Requirements & Eligibility Checker"
    stage_key: str = "strategy_eligibility"


class StrategyEligibilityStatusChecker(BaseModel):
    key: str
    label: str
    status: Literal["ready", "warning", "error", "disabled"]
    uses_llm: bool = False


class StrategyEligibilityStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: StrategyEligibilityStageMeta
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_strategy_groups: list[StrategyGroup]
    checkers: list[StrategyEligibilityStatusChecker]


SUPPORTED_STRATEGY_GROUPS: list[StrategyGroup] = [
    "regime_aware_momentum",
    "catalyst_event_driven",
    "rvol_vwap_breakout",
    "cross_sectional_ranking",
    "options_quality_volatility",
    "execution_quality",
    "lob_microstructure_research",
]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

