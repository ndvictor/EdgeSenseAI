from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ApprovalQueueStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["approval_queue_v1"] = "approval_queue_v1"
    updated_at: str
    summary: dict[str, Any]


class ApprovalItemCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    approval_id: str | None = None
    workflow_run_id: str
    orchestrator_run_id: str | None = None
    agent_run_id: str | None = None
    approval_type: str = "execution_boundary"
    status: str = "pending"
    requested_action: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    required_approver: str | None = None
    approval_reason: str | None = None
    expires_at: str | None = None


class ApprovalActionRequest(BaseModel):
    actor: str = "owner"
    reason: str | None = None


class ApprovalItemOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    approval_id: str
    workflow_run_id: str
    orchestrator_run_id: str | None
    agent_run_id: str | None
    approval_type: str
    status: str
    requested_action: dict[str, Any]
    risk_summary: dict[str, Any]
    required_approver: str | None
    approved_by: str | None
    rejected_by: str | None
    approval_reason: str | None
    expires_at: str | None
    created_at: str
    updated_at: str


def new_approval_id() -> str:
    return f"appr_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

