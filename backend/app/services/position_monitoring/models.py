from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


PositionAction = Literal["hold", "watch", "reduce", "exit_review", "blocked"]
PositionStatus = Literal["healthy", "warning", "exit_review", "blocked"]


class CheckerResult(BaseModel):
    status: Literal["pass", "warn", "fail"]
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class PositionInput(BaseModel):
    position_id: str
    symbol: str
    asset_class: str
    horizon: str
    side: Literal["long"]
    quantity: float
    entry_price: float
    current_price: float
    stop_loss: float | None = None
    target_price: float | None = None
    opened_at: str


class ThesisInput(BaseModel):
    strategy_key: str
    trigger_key: str
    vwap: float | None = None
    price_above_vwap: bool
    volume_confirms: bool
    relative_strength_positive: bool
    invalidation_hit: bool


class RiskStateInput(BaseModel):
    account_equity: float
    max_daily_loss_percent: float
    current_daily_loss_percent: float
    max_position_size_percent: float
    force_close_requested: bool
    emergency_stop: bool


class MonitoringPreferences(BaseModel):
    time_stop_minutes: int = 45
    reduce_at_r_multiple: float = 1.5
    exit_at_thesis_invalid: bool = True


class PositionMonitoringEvaluateRequest(BaseModel):
    position: PositionInput
    thesis: ThesisInput
    risk_state: RiskStateInput
    monitoring_preferences: MonitoringPreferences = Field(default_factory=MonitoringPreferences)
    evaluated_at: str


class PnlInfo(BaseModel):
    unrealized_pnl: float
    unrealized_pnl_percent: float
    r_multiple: float


class RiskInfo(BaseModel):
    risk_per_share: float
    current_distance_to_stop: float | None
    distance_to_target: float | None
    position_notional: float
    position_size_percent: float
    daily_loss_percent: float


class ThesisValidity(BaseModel):
    valid: bool
    score: float
    failed_reasons: list[str] = Field(default_factory=list)
    passed_reasons: list[str] = Field(default_factory=list)


class PositionEvaluation(BaseModel):
    evaluation_id: str
    stage_number: int = 11
    stage_name: str = "Position Monitoring"
    position_id: str
    symbol: str
    asset_class: str
    horizon: str
    position_status: PositionStatus
    recommended_action: PositionAction
    llm_used: bool = False
    pnl: PnlInfo
    risk: RiskInfo
    thesis_validity: ThesisValidity
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkers: dict[str, CheckerResult] = Field(default_factory=dict)
    allowed_next_stages: list[str] = Field(default_factory=lambda: ["position_monitoring"])
    blocked_next_stages: list[BlockedStage] = Field(
        default_factory=lambda: [
            BlockedStage(stage="close_position", reason="No close-position review required.")
        ]
    )
    next_action: str
    created_at: str


class PositionMonitoringStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: dict
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_position_actions: list[str]
    checkers: list[dict]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

