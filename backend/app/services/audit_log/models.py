from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class AuditLogStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["workflow_audit_log_v1"] = "workflow_audit_log_v1"
    updated_at: str
    summary: dict[str, Any]


class AuditEventCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    audit_id: str | None = None
    workflow_run_id: str | None = None
    orchestrator_run_id: str | None = None
    agent_run_id: str | None = None
    event_type: str
    actor: str = "system"
    severity: str = "info"
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class AuditEventOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    audit_id: str
    workflow_run_id: str | None
    orchestrator_run_id: str | None
    agent_run_id: str | None
    event_type: str
    actor: str
    severity: str
    message: str
    metadata: dict[str, Any]
    created_at: str


def new_audit_id() -> str:
    return f"audit_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

