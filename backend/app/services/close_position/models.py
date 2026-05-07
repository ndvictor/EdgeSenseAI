from __future__ import annotations

from datetime import datetime
from math import floor
from typing import Literal

from pydantic import BaseModel, Field


ReviewAction = Literal["hold", "reduce_review", "close_review", "blocked"]
ReviewStatus = Literal["ready", "blocked"]


class CheckerResult(BaseModel):
    status: Literal["pass", "warn", "fail"]
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class PositionEvaluationInput(BaseModel):
    evaluation_id: str
    position_id: str
    symbol: str
    asset_class: str
    horizon: str
    position_status: str
    recommended_action: str
    pnl: dict
    risk: dict
    thesis_validity: dict
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PositionStub(BaseModel):
    quantity: int
    side: Literal["long"]
    current_price: float
    entry_price: float


class MasterAdminInput(BaseModel):
    workflow_enabled: bool
    execution_enabled: bool
    paper_trading_enabled: bool
    live_trading_enabled: bool
    broker_execution_enabled: bool
    human_approval_required: bool
    emergency_stop: bool
    force_close_requested: bool


class ReviewPreferences(BaseModel):
    reduce_percent: int = 50
    close_reason: str = "stage_11_exit_review"
    order_style: Literal["market", "limit"] = "market"
    allow_submit: bool = False


class CloseOrderPreview(BaseModel):
    symbol: str
    side: Literal["sell"] = "sell"
    quantity: int
    order_type: Literal["market", "limit"]
    limit_price: float | None = None
    time_in_force: Literal["day"] = "day"
    source: str = "close_position_review"
    reason: str
    human_approval_confirmed: bool = False


class ClosePositionReviewRequest(BaseModel):
    position_evaluation: PositionEvaluationInput
    position: PositionStub
    master_admin: MasterAdminInput
    review_preferences: ReviewPreferences = Field(default_factory=ReviewPreferences)


class ClosePositionReviewResult(BaseModel):
    review_id: str
    stage_number: int = 12
    stage_name: str = "Close Position"
    position_id: str
    symbol: str
    asset_class: str
    horizon: str
    review_action: ReviewAction
    review_status: ReviewStatus
    llm_used: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    reason: str
    close_order_preview: CloseOrderPreview | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkers: dict[str, CheckerResult] = Field(default_factory=dict)
    allowed_next_stages: list[str] = Field(default_factory=list)
    blocked_next_stages: list[BlockedStage] = Field(
        default_factory=lambda: [
            BlockedStage(
                stage="trade_execution",
                reason="Stage 12 v1 only prepares close/reduce review. It never submits orders.",
            )
        ]
    )
    next_action: str
    created_at: str


class ClosePositionStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: dict
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_review_actions: list[str]
    checkers: list[dict]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def reduced_qty(full_qty: int, percent: int) -> int:
    return int(floor(full_qty * max(0, min(100, percent)) / 100.0))

