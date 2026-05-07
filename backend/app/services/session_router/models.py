from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


MarketKey = Literal["us_equities"]
CalendarMode = Literal["us_equities_basic"]

SessionKey = Literal["pre_market", "market_open", "post_market", "after_hours", "closed", "holiday", "unknown"]


class SessionEvaluateRequest(BaseModel):
    timestamp: str | None = None
    timezone: str = "America/Chicago"
    market: str = "us_equities"
    use_current_time: bool = False


class BlockedWorkflowBias(BaseModel):
    workflow: str
    reason: str


class SessionEvaluation(BaseModel):
    session_id: str
    stage_number: int = 3
    stage_name: str = "Session Router"
    session: SessionKey
    market: MarketKey = "us_equities"
    timezone: str = "America/Chicago"
    evaluated_at: str
    market_date: str
    is_trading_day: bool
    is_holiday: bool = False
    llm_used: bool = False

    allowed_workflow_bias: list[str] = Field(default_factory=list)
    blocked_workflow_bias: list[BlockedWorkflowBias] = Field(default_factory=list)
    session_notes: list[str] = Field(default_factory=list)
    next_action: str


class SessionRouterStageMeta(BaseModel):
    stage_number: int = 3
    stage_name: str = "Session Router"
    stage_key: str = "session_router"


class SessionRouterStatusChecker(BaseModel):
    key: str
    label: str
    status: Literal["ready", "warning", "error", "disabled"]
    uses_llm: bool = False


class SessionRouterStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: SessionRouterStageMeta
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_sessions: list[SessionKey]
    checkers: list[SessionRouterStatusChecker]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

