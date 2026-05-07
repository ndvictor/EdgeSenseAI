from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class OrchestratorStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["workflow_orchestrator_v1"] = "workflow_orchestrator_v1"
    updated_at: str
    summary: dict[str, Any]


class OrchestratorRunRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    workflow_name: str = "US Stock Day-Trading Paper Workflow v1"
    asset_class: str = "stock"
    horizon: str = "day_trading"
    mode: str = "paper_first"
    source: str = "manual"
    symbols: list[str] = Field(default_factory=lambda: ["AMD"])
    strategy_key: str | None = None
    max_candidates: int = 5
    stop_at_stage: int = 9
    dry_run: bool = True
    require_human_approval: bool = True
    allow_submit: bool = False
    simulated_position: bool = False
    simulated_closed_trade: bool = False
    idempotency_key: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OrchestratorRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    orchestrator_run_id: str
    workflow_run_id: str
    status: Literal["completed_preview", "paused_for_approval", "blocked", "failed", "stopped"]
    current_stage: int | None
    current_agent_key: str | None
    stage_timeline: list[dict[str, Any]] = Field(default_factory=list)
    agent_run_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str = ""
    approval_required: bool = True
    approval_id: str | None = None
    execution_boundary_reached: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    llm_used: bool = False
    created_at: str
    updated_at: str


def new_orchestrator_id() -> str:
    return f"orc_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

