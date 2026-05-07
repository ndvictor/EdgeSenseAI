from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelEvidenceStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["model_evidence_v1"] = "model_evidence_v1"
    updated_at: str
    summary: dict


class ModelEvidenceCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    evidence_id: str | None = None
    model_key: str = "weighted_ranker_v1"
    model_name: str = "Weighted Ranker V1"
    model_family: str = "deterministic_baseline"
    asset_class: str = "stock"
    horizon: str = "day_trading"
    status: str = "recorded"
    score: float | None = None
    confidence: float | None = None
    rank: int | None = None
    drift_status: str | None = None
    training_status: str | None = None
    backtest_status: str | None = None
    paper_status: str | None = None
    qlib_artifact_id: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ModelEvidenceOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    evidence_id: str
    model_key: str
    model_name: str
    model_family: str
    asset_class: str
    horizon: str
    status: str
    score: float | None
    confidence: float | None
    rank: int | None
    drift_status: str | None
    training_status: str | None
    backtest_status: str | None
    paper_status: str | None
    qlib_artifact_id: str | None
    metrics: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    created_at: str
    updated_at: str


def new_evidence_id() -> str:
    return f"mev_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

