from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentTraceEvent(BaseModel):
    run_id: str
    workflow_name: str
    agent_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
    confidence: float | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "placeholder"


class AgentRunResult(BaseModel):
    run_id: str | None = None
    workflow_name: str | None = None
    agent_name: str
    status: str
    summary: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    confidence: float
    input_summary: str | None = None
    output_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "placeholder"


class AgentDecision(BaseModel):
    run_id: str | None = None
    workflow_name: str | None = None
    agent_name: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: float | None = None
    confidence: float
    input_summary: str | None = None
    output_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "placeholder"


class WorkflowRunResult(BaseModel):
    run_id: str
    workflow_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None = None
    duration_ms: float | None = None
    confidence: float | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "placeholder"
