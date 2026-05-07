from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TriggerState = Literal["not_ready", "armed", "fired", "expired", "missed", "invalidated", "blocked"]
HorizonKey = Literal["day_trading"]
AssetClassKey = Literal["stock", "option", "crypto", "etf"]


class CheckerResult(BaseModel):
    status: Literal["pass", "warn", "fail"]
    message: str


class BlockedStage(BaseModel):
    stage: str
    reason: str


class WorkflowContext(BaseModel):
    selected_workflow: str
    workflow_mode: str
    session: str


class EligibilityContext(BaseModel):
    eligible: bool
    eligibility_status: Literal["eligible", "paper_only", "research_only", "blocked"]
    strategy_key: str
    strategy_group: str


class TriggerCandidate(BaseModel):
    symbol: str = Field(min_length=1)
    asset_class: AssetClassKey
    horizon: HorizonKey
    trigger_key: str = Field(min_length=1)
    created_at: str
    expires_at: str
    trigger_price: float
    current_price: float
    vwap: float


class CurrentState(BaseModel):
    evaluated_at: str
    data_quality: Literal["pass", "warn", "fail"]
    spread_pass: bool
    volume_confirms: bool
    price_above_trigger: bool
    price_above_vwap: bool
    invalidation_hit: bool


class TriggerMonitoringEvaluateRequest(BaseModel):
    workflow_context: WorkflowContext
    eligibility_context: EligibilityContext
    trigger_candidate: TriggerCandidate
    current_state: CurrentState


class TimingInfo(BaseModel):
    created_at: str
    expires_at: str
    evaluated_at: str
    seconds_to_expiration: int
    is_expired: bool
    is_within_window: bool


class TriggerEvaluation(BaseModel):
    evaluation_id: str
    stage_number: int = 8
    stage_name: str = "Trigger Monitoring"
    symbol: str
    asset_class: str
    horizon: str
    trigger_key: str
    trigger_state: TriggerState
    llm_used: bool = False
    reason: str
    timing: TimingInfo
    requirements_passed: list[str] = Field(default_factory=list)
    requirements_failed: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checkers: dict[str, CheckerResult] = Field(default_factory=dict)
    allowed_next_stages: list[str] = Field(default_factory=lambda: ["execution_planner"])
    blocked_next_stages: list[BlockedStage] = Field(
        default_factory=lambda: [
            BlockedStage(
                stage="trade_execution",
                reason="Execution must wait for Stage 9 Execution Planner and execution prechecks.",
            )
        ]
    )
    next_action: str
    created_at: str


class TriggerMonitoringStatusResponse(BaseModel):
    status: Literal["ok"]
    stage: dict
    data_mode: Literal["rules_v1"]
    updated_at: str
    summary: dict
    supported_trigger_states: list[str]
    checkers: list[dict]
    integration_notes: list[str]


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

