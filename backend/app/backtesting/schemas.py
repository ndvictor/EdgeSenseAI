from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExecutionCheckStatus = Literal[
    "not_configured",
    "pending",
    "ready",
    "running",
    "passed",
    "failed",
    "blocked",
]

PromotionGateStatus = Literal[
    "contract_ready",
    "data_ready",
    "backtest_running",
    "backtest_passed",
    "execution_sim_passed",
    "risk_validated",
    "paper_ready",
    "blocked",
]


class ExecutionSimulationCheck(BaseModel):
    name: str
    status: ExecutionCheckStatus
    message: str = ""


class BacktestProfileActionBody(BaseModel):
    profile_name: str = Field(..., min_length=1, description="Strategy / backtest profile identifier from summary.")


class BacktestStubResponse(BaseModel):
    """Honest stub: service not implemented; no fabricated fills or PnL."""

    status: Literal["not_configured"] = "not_configured"
    message: str
    profile_name: str | None = None


class BacktestRunResponse(BacktestStubResponse):
    job_id: str | None = None


class ExecutionSimulationResponse(BacktestStubResponse):
    checks: list[ExecutionSimulationCheck] = Field(default_factory=list)
    promotion_gate: PromotionGateStatus | str = "contract_ready"


class RiskValidationResponse(BacktestStubResponse):
    checks: list[ExecutionSimulationCheck] = Field(default_factory=list)


class PromoteToPaperResponse(BacktestStubResponse):
    blocked_reasons: list[str] = Field(default_factory=list)
