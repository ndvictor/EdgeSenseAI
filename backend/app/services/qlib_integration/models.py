from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class QlibStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["qlib_integration_v1"] = "qlib_integration_v1"
    updated_at: str
    qlib_available: bool
    qlib_version: str | None = None
    configured: bool = False
    artifact_count: int = 0
    latest_signal_count: int = 0
    latest_backtest_count: int = 0
    latest_model_count: int = 0
    summary: dict = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_action: str = ""


class QlibSignalScoreCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    artifact_id: str | None = None
    symbol: str = ""
    symbols: list[str] = Field(default_factory=list)
    asset_class: str = "stock"
    horizon: str = "day_trading"
    strategy_key: str | None = None
    model_key: str | None = None
    scores: dict[str, Any] = Field(default_factory=dict)  # externally supplied qlib-like scores
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "external"


class QlibBacktestRecordCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    artifact_id: str | None = None
    asset_class: str = "stock"
    horizon: str = "day_trading"
    strategy_key: str | None = None
    model_key: str | None = None
    symbol: str | None = None
    artifact_path: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "external"


class QlibModelArtifactRegisterCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    artifact_id: str | None = None
    asset_class: str = "stock"
    horizon: str = "day_trading"
    model_key: str
    model_name: str | None = None
    artifact_path: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source: str = "external"


class QlibArtifactCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    artifact_id: str | None = None
    artifact_type: str
    model_key: str | None = None
    strategy_key: str | None = None
    symbol: str | None = None
    symbols: list[str] = Field(default_factory=list)
    asset_class: str = "stock"
    horizon: str = "day_trading"
    qlib_available: bool = False
    qlib_version: str | None = None
    artifact_status: str = "recorded"
    artifact_path: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    scores: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class QlibArtifactOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    artifact_id: str
    artifact_type: str
    model_key: str | None
    strategy_key: str | None
    symbol: str | None
    symbols: list[str] = Field(default_factory=list)
    asset_class: str
    horizon: str
    qlib_available: bool
    qlib_version: str | None
    artifact_status: str
    artifact_path: str | None
    metrics: dict[str, Any]
    scores: dict[str, Any]
    metadata: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    created_at: str
    updated_at: str


def new_artifact_id(prefix: str = "qa") -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

