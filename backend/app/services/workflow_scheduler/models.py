from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class SchedulerStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["workflow_scheduler_v1"] = "workflow_scheduler_v1"
    updated_at: str
    summary: dict[str, Any]


class ScheduleCreateRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    schedule_id: str | None = None
    name: str
    enabled: bool = True
    schedule_type: str = "interval"
    cron_expression: str | None = None
    interval_seconds: int | None = 300
    workflow_request: dict[str, Any] = Field(default_factory=dict)
    max_runs_per_day: int = 50


class ScheduleOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    schedule_id: str
    name: str
    enabled: bool
    schedule_type: str
    cron_expression: str | None
    interval_seconds: int | None
    workflow_request: dict[str, Any]
    max_runs_per_day: int
    last_run_at: str | None
    next_run_at: str | None
    created_at: str
    updated_at: str


class SchedulerRunOnceRequest(BaseModel):
    workflow_request: dict[str, Any] = Field(default_factory=dict)


def new_schedule_id() -> str:
    return f"sch_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

