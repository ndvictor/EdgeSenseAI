"""Typed schemas for EdgeSense execution workflow."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ExecutionMode = Literal["paper", "simulated", "live_disabled", "live"]
AssetClass = Literal["stock", "option", "crypto", "etf"]
OrderSide = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "stop", "stop_limit"]
TimeInForce = Literal["day", "gtc", "ioc", "opg", "cls", "fok"]
ExecutionSource = Literal["signal", "recommendation", "manual", "model_lab", "backtest"]
ExecutionStatus = Literal[
    "blocked",
    "pending_approval",
    "submitted",
    "filled",
    "partially_filled",
    "rejected",
    "canceled",
    "error",
]


class PrecheckStepResult(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    passed: bool
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)
    source_timestamps: dict[str, str] = Field(default_factory=dict)


class PrecheckSummary(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    passed: bool
    steps: list[PrecheckStepResult]
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PostcheckSummary(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    submission_ok: bool | None = None
    fill_quality_ok: bool | None = None
    slippage_pct: float | None = None
    position_sync_ok: bool | None = None
    risk_state_updated: bool | None = None
    journal_entry_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class ExecutionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    org_slug: str = "default"
    user_id: str | None = None
    recommendation_id: str | None = None
    strategy_id: str | None = None
    symbol: str = Field(min_length=1)
    asset_class: AssetClass = "stock"
    side: OrderSide
    quantity: float | None = None
    notional: float | None = None
    order_type: OrderType = "limit"
    limit_price: float | None = None
    stop_price: float | None = None
    time_in_force: TimeInForce = "day"
    execution_mode: ExecutionMode | None = None
    reason: str = ""
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)
    source: ExecutionSource = "manual"
    metadata: dict[str, Any] = Field(default_factory=dict)
    human_approval_confirmed: bool = False
    client_request_id: str | None = None
    stop_loss_price: float | None = Field(
        default=None,
        description="Required for risk precheck unless metadata.exempt_stop_loss=true",
    )


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: ExecutionStatus
    execution_mode: str
    order_id: str | None = None
    broker_order_id: str | None = None
    symbol: str
    side: OrderSide
    requested_quantity: float | None = None
    submitted_quantity: float | None = None
    requested_price: float | None = None
    submitted_price: float | None = None
    precheck_summary: PrecheckSummary
    postcheck_summary: PostcheckSummary | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    audit_id: str
    message: str
    created_at: datetime | None = None


class ExecutionApproveRequest(BaseModel):
    audit_id: str
    approved_by: str | None = "human"
    org_slug: str = "default"


class ExecutionRejectRequest(BaseModel):
    audit_id: str
    reason: str = ""
    org_slug: str = "default"
