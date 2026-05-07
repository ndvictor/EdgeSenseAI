from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class ProofRegistryStatusResponse(BaseModel):
    status: Literal["ok"] = "ok"
    data_mode: Literal["proof_registry_v1"] = "proof_registry_v1"
    updated_at: str
    summary: dict


class ProofRegistryRecordCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    proof_id: str | None = None
    symbol: str = "AMD"
    asset_class: str = "stock"
    horizon: str = "day_trading"
    strategy_key: str = "stock_day_trading"
    model_key: str | None = None
    proof_type: str = "backtest"
    proof_status: str = "proof_required"
    sample_size: int = 0
    win_rate: float = 0.0
    avg_r_multiple: float = 0.0
    sharpe_ratio: float | None = None
    max_drawdown_r: float | None = None
    slippage_fail_rate: float | None = None
    rule_violation_rate: float | None = None
    backtest_run_id: str | None = None
    paper_run_id: str | None = None
    source: str = "manual"
    evidence: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ProofRegistryRecordOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    proof_id: str
    symbol: str
    asset_class: str
    horizon: str
    strategy_key: str
    model_key: str | None
    proof_type: str
    proof_status: str
    sample_size: int
    win_rate: float
    avg_r_multiple: float
    sharpe_ratio: float | None
    max_drawdown_r: float | None
    slippage_fail_rate: float | None
    rule_violation_rate: float | None
    backtest_run_id: str | None
    paper_run_id: str | None
    source: str
    evidence: dict[str, Any]
    blockers: list[str]
    warnings: list[str]
    created_at: str
    updated_at: str


def new_proof_id() -> str:
    return f"proof_{uuid4().hex[:12]}"


def iso_utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

