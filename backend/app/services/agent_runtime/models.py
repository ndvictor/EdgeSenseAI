from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AgentType = Literal["deterministic_agent", "ml_agent", "llm_agent", "orchestrator_agent"]
AgentStatus = Literal["registered", "not_implemented", "ready"]


class AgentDescriptor(BaseModel):
    agent_key: str
    display_name: str
    stage_number: int | None = None
    role: str
    agent_type: AgentType
    status: AgentStatus
    uses_llm: bool = False
    allowed_tools: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    input_schema_name: str | None = None
    output_schema_name: str | None = None
    safety_notes: list[str] = Field(default_factory=list)


class AgentRunRequest(BaseModel):
    workflow_run_id: str | None = None
    agent_key: str
    inputs: dict
    context: dict = Field(default_factory=dict)
    dry_run: bool = True
    requested_stage: int | None = None
    idempotency_key: str | None = None


AgentRunStatus = Literal["recorded", "completed", "blocked", "failed", "duplicate"]


class AgentRunResult(BaseModel):
    run_id: str
    workflow_run_id: str
    agent_key: str
    status: AgentRunStatus
    decision: dict = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str
    next_agent: str | None = None
    artifacts: dict = Field(default_factory=dict)
    trace_id: str
    trace: list[dict] = Field(default_factory=list)
    idempotency_key: str
    inputs_hash: str
    created_at: str


class WorkflowRunCreateRequest(BaseModel):
    workflow_name: str = "US Stock Day-Trading Paper Workflow v1"
    asset_class: str = "stock"
    horizon: str = "day_trading"
    mode: str = "paper_first"
    source: str = "manual"
    metadata: dict = Field(default_factory=dict)


WorkflowRunStatus = Literal["created", "running", "paused", "blocked", "completed", "failed"]


class WorkflowRunRecord(BaseModel):
    workflow_run_id: str
    workflow_name: str
    asset_class: str
    horizon: str
    mode: str
    source: str
    status: WorkflowRunStatus = "created"
    current_stage: int | None = None
    current_agent_key: str | None = None
    stage_states: dict = Field(default_factory=dict)
    agent_run_ids: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    metadata: dict = Field(default_factory=dict)


class AgentRuntimeStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["agent_runtime_foundation_v1"] = "agent_runtime_foundation_v1"
    updated_at: str
    summary: dict
    safety: dict


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

