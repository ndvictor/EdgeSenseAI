from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ImplementationStatus = Literal["present", "partial_existing", "existing_gated", "backlog"]


class StageHealth(BaseModel):
    stage_number: int
    stage_name: str
    stage_key: str
    backend_status: str
    frontend_status: str
    endpoint_family: str
    ui_route: str
    latest_available: bool
    safety_role: str
    next_action: str


class StageDescriptor(BaseModel):
    stage_number: int
    stage_name: str
    stage_key: str
    implementation_status: ImplementationStatus
    backend_endpoint_family: str
    frontend_route: str
    uses_llm: bool = False
    submits_orders: bool = False
    broker_called: bool = False
    safety_notes: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    next_stage_keys: list[str] = Field(default_factory=list)
    recommended_operator_action: str


class RunbookStatusResponse(BaseModel):
    status: Literal["ok"]
    data_mode: Literal["aggregated_status_v1"]
    updated_at: str
    scope: dict
    summary: dict
    master_gates: dict
    stage_health: list[StageHealth]


class RunbookStagesResponse(BaseModel):
    status: Literal["ok"]
    data_mode: Literal["stage_inventory_v1"]
    updated_at: str
    stages: list[StageDescriptor]


class RunbookLatestResponse(BaseModel):
    status: Literal["ok"]
    data_mode: Literal["latest_snapshot_v1"]
    latest: dict
    message: str


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

