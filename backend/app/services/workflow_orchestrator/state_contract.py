from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowCarryForwardState(BaseModel):
    workflow_run_id: str | None = None
    orchestrator_run_id: str | None = None
    asset_class: str = "stock"
    horizon: str = "day_trading"
    mode: str = "paper_first"
    source: str = "mock"
    symbols: list[str] = Field(default_factory=list)
    symbol: str | None = None
    selected_symbol: str | None = None
    market_context: dict[str, Any] = Field(default_factory=dict)
    regime: str | None = None
    strategy_key: str | None = None
    selected_strategy_key: str | None = None
    selected_model_key: str | None = None
    selected_model_keys: list[str] = Field(default_factory=list)
    proof_status: str | None = None
    qlib_available: bool | None = None
    qlib_artifact_id: str | None = None
    account_equity: float = 1000.0
    max_risk_per_trade_percent: float = 0.5
    max_daily_loss_percent: float = 1.5
    max_open_positions: int = 1
    max_trades_per_day: int = 3
    approval_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    submitted_order: bool = False
    broker_called: bool = False
    llm_used: bool = False

    def to_agent_inputs(self) -> dict[str, Any]:
        data = self.model_dump()
        data["allow_submit"] = False
        data["submitted_order"] = False
        data["broker_called"] = False
        data["llm_used"] = False
        return data
