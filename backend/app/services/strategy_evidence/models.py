from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class StrategyEvidenceStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["strategy_evidence_v1"] = "strategy_evidence_v1"
    updated_at: str
    summary: dict


class StrategyEvidenceCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    evidence_id: str | None = None
    strategy_key: str = "stock_day_trading"
    strategy_group: str = "stock"
    asset_class: str = "stock"
    horizon: str = "day_trading"
    status: str = "recorded"
    strategy_score: float | None = None
    regime_fit: float | None = None
    proof_status: str | None = None
    selected_model_keys: list[str] = Field(default_factory=list)
    scanner_needs: list[str] = Field(default_factory=list)
    data_needs: list[str] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StrategyEvidenceOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    evidence_id: str
    strategy_key: str
    strategy_group: str
    asset_class: str
    horizon: str
    status: str
    strategy_score: float | None
    regime_fit: float | None
    proof_status: str | None
    selected_model_keys: list[str]
    scanner_needs: list[str]
    data_needs: list[str]
    metrics: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    created_at: str
    updated_at: str


def new_evidence_id() -> str:
    return f"sev_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

