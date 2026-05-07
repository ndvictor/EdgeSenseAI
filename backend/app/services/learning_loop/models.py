from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


LearningAction = Literal[
    "promote_candidate",
    "keep_monitoring",
    "demote_to_paper",
    "demote_to_research",
    "block_strategy",
    "review_needed",
]


class CheckerResult(BaseModel):
    status: Literal["pass", "warn", "fail"]
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class RecentOutcome(BaseModel):
    trade_id: str
    outcome_label: str
    outcome_status: str
    realized_pnl: float
    r_multiple: float
    slippage_status: Literal["pass", "warn", "fail"]
    rule_compliant: bool


class CurrentStatus(BaseModel):
    promotion_status: str | None = None
    proof_status: str | None = None
    sample_size: int | None = None
    current_drawdown_r: float | None = None
    last_10_avg_r: float | None = None


class Thresholds(BaseModel):
    min_sample_size_for_promotion: int = 20
    min_avg_r_for_promotion: float = 0.35
    max_drawdown_r_before_demotion: float = -3.0
    max_rule_violation_rate: float = 0.10
    max_slippage_fail_rate: float = 0.15


class LearningLoopEvaluateRequest(BaseModel):
    strategy_key: str
    strategy_group: str
    asset_class: str
    horizon: str
    workflow_key: str
    recent_outcomes: list[RecentOutcome] = Field(default_factory=list)
    current_status: CurrentStatus = Field(default_factory=CurrentStatus)
    thresholds: Thresholds = Field(default_factory=Thresholds)


class LearningMetrics(BaseModel):
    sample_size: int
    wins: int
    losses: int
    flats: int
    win_rate: float
    avg_r_multiple: float
    avg_realized_pnl: float
    rule_violation_rate: float
    slippage_fail_rate: float
    current_drawdown_r: float | None = None


class DriftInfo(BaseModel):
    drift_detected: bool
    drift_reason: str | None = None


class PromotionInfo(BaseModel):
    eligible_for_promotion: bool
    promotion_target: str | None = None
    blocked_reasons: list[str] = Field(default_factory=list)


class DemotionInfo(BaseModel):
    demotion_required: bool
    demotion_target: str | None = None
    reasons: list[str] = Field(default_factory=list)


class LearningLoopDecision(BaseModel):
    decision_id: str
    stage_number: int = 14
    stage_name: str = "Learning Loop"
    strategy_key: str
    strategy_group: str
    asset_class: str
    horizon: str
    learning_action: LearningAction
    llm_used: bool = False
    metrics: LearningMetrics
    drift: DriftInfo
    promotion: PromotionInfo
    demotion: DemotionInfo
    reason: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkers: dict[str, CheckerResult] = Field(default_factory=dict)
    allowed_next_stages: list[str] = Field(default_factory=list)
    blocked_next_stages: list[BlockedStage] = Field(default_factory=list)
    next_action: str
    created_at: str


class LearningLoopStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: dict
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_learning_actions: list[str]
    checkers: list[dict]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

