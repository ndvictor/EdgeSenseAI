"""Pydantic schemas for deep-agent runtime requests and tool contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class DeepAgentToolSpec(BaseModel):
    """Declarative description of a tool callable by the supervisor or a subagent."""

    name: str
    description: str = ""
    json_schema: dict[str, Any] = Field(default_factory=dict)


class DeepAgentRunContext(BaseModel):
    """Immutable-enough context passed through a deep-agent run."""

    workflow_run_id: str | None = None
    orchestrator_run_id: str | None = None
    trace_id: str | None = None
    mode: Literal["dry_run", "paper", "live_shadow"] = "dry_run"
    metadata: dict[str, Any] = Field(default_factory=dict)
