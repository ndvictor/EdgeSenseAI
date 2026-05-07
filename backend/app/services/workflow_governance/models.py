from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class WorkflowGovernanceStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["workflow_governance_v1"] = "workflow_governance_v1"
    updated_at: str
    summary: dict[str, Any]


class WorkflowGovernanceCheckRequest(BaseModel):
    workflow_run_id: str | None = None
    asset_class: str = "stock"
    horizon: str = "day_trading"
    mode: str = "paper_first"
    source: str = "manual"
    symbols: list[str] = Field(default_factory=list)
    dry_run: bool = True
    require_human_approval: bool = True
    allow_submit: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowGovernanceCheckResponse(BaseModel):
    status: Literal["ok"] = "ok"
    decision: Literal["allowed", "blocked", "warning"]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    gates: dict[str, Any] = Field(default_factory=dict)
    limits: dict[str, Any] = Field(default_factory=dict)
    next_action: str = ""
    created_at: str


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

