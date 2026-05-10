from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowCarryForwardState(BaseModel):
    workflow_run_id: str | None = None
    orchestrator_run_id: str | None = None
    asset_class: str = "stock"
    horizon: str = "day_trading"
    mode: str = "paper_first"
    source: str = "runtime"
    symbols: list[str] = Field(default_factory=list)
    workflow_request_symbols: list[str] = Field(default_factory=list)
    discovery_mode: bool = False
    candidate_source: str | None = None
    raw_candidate_count: int = 0
    filtered_candidate_count: int = 0
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
    qlib_version: str | None = None
    qlib_artifact_id: str | None = None
    qlib_artifact_counts: dict[str, int] = Field(default_factory=dict)
    proof_id: str | None = None
    evidence_blockers: list[str] = Field(default_factory=list)
    evidence_warnings: list[str] = Field(default_factory=list)
    provider_status: dict[str, Any] = Field(default_factory=dict)
    provider_name: str | None = None
    source_mode: str | None = None
    using_non_real_data: bool = False
    usable_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[str] = Field(default_factory=list)
    latest_snapshot_status: str | None = None
    latest_snapshot_count: int = 0
    feature_store_status: str | None = None
    feature_row_count: int = 0
    feature_rows: list[dict[str, Any]] = Field(default_factory=list)
    scanner_candidates: list[dict[str, Any]] = Field(default_factory=list)
    watchlist: list[dict[str, Any] | str] = Field(default_factory=list)
    persistence_status: str | None = None
    freshness_status: str | None = None
    kafka_status: str = "configured_optional_not_active"
    latest_price: float | None = None
    spread_bps: float | None = None
    avg_dollar_volume: float | None = None
    planned_risk_dollars: float | None = None
    open_positions: int = 0
    day_trades_used: int = 0
    account_equity: float = 1000.0
    max_risk_per_trade_percent: float = 0.5
    max_daily_loss_percent: float = 1.5
    max_open_positions: int = 1
    max_trades_per_day: int = 3
    small_account_decision: str | None = None
    max_risk_dollars: float | None = None
    max_daily_loss_dollars: float | None = None
    feasible_symbols: list[str] = Field(default_factory=list)
    small_account_rejected_symbols: list[str] = Field(default_factory=list)
    small_account_blockers: list[str] = Field(default_factory=list)
    small_account_warnings: list[str] = Field(default_factory=list)
    account_feasibility_decision: str | None = None
    account_feasibility_blockers: list[str] = Field(default_factory=list)
    account_feasibility_warnings: list[str] = Field(default_factory=list)
    buying_power: float | None = None
    fractional_trading_enabled: bool = True
    execution_mode: str = "plan_only"
    paper_trading_enabled: bool | None = None
    live_trading_enabled: bool | None = None
    broker_execution_enabled: bool | None = None
    account_owner_gates: dict[str, Any] = Field(default_factory=dict)
    alpha_recommendation: dict[str, Any] = Field(default_factory=dict)
    alpha_status: str | None = None
    alpha_selected_symbol: str | None = None
    alpha_strategy_key: str | None = None
    alpha_score: float | None = None
    alpha_reason: str | None = None
    alpha_blockers: list[str] = Field(default_factory=list)
    alpha_warnings: list[str] = Field(default_factory=list)
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
        data["llm_used_for_trade_decision"] = False
        return data
