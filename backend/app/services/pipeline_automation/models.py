from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class PipelineAutomationRunRequest(BaseModel):
    """Single-entry automated pipeline that prepares inputs then runs the workflow orchestrator.

    This is intentionally deterministic and safe:
    - It can run in dry_run mode without order submission.
    - It does not submit orders unless the downstream orchestrator is explicitly configured to allow it.
    """

    model_config = ConfigDict(protected_namespaces=())

    asset_class: str = "stock"
    horizon: str = "day_trading"
    mode: str = "paper_first"
    source: str = "auto"

    seed_symbols: list[str] = Field(default_factory=list)
    max_candidates: int = 10

    dry_run: bool = True
    require_human_approval: bool = True
    stop_at_stage: int = 100

    metadata: dict[str, Any] = Field(default_factory=dict)


class PipelineAutomationRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    pipeline_run_id: str
    status: Literal["completed_preview", "blocked", "failed"]
    orchestrator_run_id: str | None = None
    workflow_run_id: str | None = None

    selected_symbols: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifacts: dict[str, Any] = Field(default_factory=dict)

    next_action: str = ""
    created_at: str
    updated_at: str


def new_pipeline_run_id() -> str:
    return f"pipe_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

