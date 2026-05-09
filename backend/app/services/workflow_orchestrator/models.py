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
    stop_at_stage: int = 100
    dry_run: bool = True
    require_human_approval: bool = True
    allow_submit: bool = False
    account_equity: float = 1000.0
    max_risk_per_trade_percent: float = 0.5
    max_daily_loss_percent: float = 1.5
    max_open_positions: int = 1
    max_trades_per_day: int = 3
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
    governance_blockers: list[str] = Field(default_factory=list)
    preview_continued_despite_governance_blockers: bool = False
    preview_continued_after_approval_boundary: bool = False
    source_mode: str = "manual"
    using_mock_data: bool = False
    provider_status: dict[str, Any] = Field(default_factory=dict)
    provider_name: str | None = None
    usable_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[str] = Field(default_factory=list)
    latest_snapshot_status: str | None = None
    latest_snapshot_count: int = 0
    feature_store_status: str | None = None
    feature_row_count: int = 0
    persistence_status: str | None = None
    freshness_status: str | None = None
    kafka_status: str = "configured_optional_not_active"
    qlib_available: bool | None = None
    qlib_version: str | None = None
    qlib_artifact_id: str | None = None
    qlib_artifact_counts: dict[str, int] = Field(default_factory=dict)
    selected_model_key: str | None = None
    selected_model_keys: list[str] = Field(default_factory=list)
    selected_strategy_key: str | None = None
    strategy_key: str | None = None
    proof_status: str | None = None
    proof_id: str | None = None
    evidence_blockers: list[str] = Field(default_factory=list)
    evidence_warnings: list[str] = Field(default_factory=list)
    small_account_decision: str | None = None
    max_risk_dollars: float | None = None
    max_daily_loss_dollars: float | None = None
    feasible_symbols: list[str] = Field(default_factory=list)
    small_account_rejected_symbols: list[str] = Field(default_factory=list)
    small_account_blockers: list[str] = Field(default_factory=list)
    small_account_warnings: list[str] = Field(default_factory=list)
    allow_submit: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    llm_used: bool = False
    created_at: str
    updated_at: str
    supported_horizons: list[str] = Field(default_factory=lambda: ["day_trading"])
    blocked_horizons: list[str] = Field(default_factory=lambda: ["swing_trading", "swing", "multi_day", "overnight", "position_trade"])


def new_orchestrator_id() -> str:
    return f"orc_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

