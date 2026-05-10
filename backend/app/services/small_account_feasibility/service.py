from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.fractional_sizing_service import (
    DEFAULT_EXPECTED_R,
    MAX_DAILY_LOSS_PCT,
    MAX_POSITION_NOTIONAL_PCT,
    MAX_RISK_PER_TRADE_PCT,
    AccountFeasibilityInput,
    evaluate_account_feasibility,
)


class SmallAccountFeasibilityRequest(BaseModel):
    # ``account_equity`` and ``buying_power`` are intentionally optional with no
    # defaults: real account state must come from the workflow input (Alpaca
    # snapshot, paper account, or owner policy). Missing values surface as
    # ``data_unavailable`` with explicit blockers in the deterministic tool;
    # the runtime never invents a $1,000 account.
    account_equity: float | None = None
    buying_power: float | None = None
    fractional_trading_enabled: bool = True
    risk_budget: float | None = None
    symbols: list[str] = Field(default_factory=list)
    usable_symbols: list[str] = Field(default_factory=list)
    selected_symbol: str | None = None
    latest_price: float | None = None
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    expected_r: float | None = None
    predicted_expected_value_r: float | None = None
    spread_bps: float | None = None
    slippage_bps: float | None = None
    avg_dollar_volume: float | None = None
    dollar_volume: float | None = None
    volume: float | None = None
    market_session: str | None = None
    execution_mode: str = "plan_only"
    paper_trading_enabled: bool = True
    live_trading_enabled: bool = False
    broker_execution_enabled: bool = False
    allow_submit: bool = False
    planned_risk_dollars: float | None = None
    open_positions: int = 0
    day_trades_used: int = 0
    current_daily_loss: float = 0.0
    proof_status: str | None = None
    source_mode: str | None = None
    using_non_real_data: bool = False
    persistence_status: str | None = None
    # Owner risk policy uses **human percent values** at the boundary:
    # ``0.5`` means 0.5%, ``100`` means 100%. The deterministic sizing service
    # converts percent to a decimal fraction exactly once.
    max_risk_per_trade_pct: float = MAX_RISK_PER_TRADE_PCT
    max_risk_dollars: float | None = None
    max_daily_loss_pct: float = MAX_DAILY_LOSS_PCT
    max_position_notional_pct: float = MAX_POSITION_NOTIONAL_PCT
    max_position_notional: float | None = None
    max_open_positions: int = 1
    max_trades_per_day: int = 3
    min_order_notional: float = 1.0
    min_expected_r: float = 0.25
    max_liquidity_participation_pct: float = 0.05
    min_predicted_expected_value_r: float | None = None
    strategy_key: str | None = None
    setup_type: str | None = None
    candidate_source: str | None = None
    provider_name: str | None = None
    data_quality: str | None = None


class SmallAccountFeasibilityResponse(BaseModel):
    decision: Literal["pass", "degraded", "blocked", "data_unavailable"]
    account_feasibility_decision: Literal["feasible", "degraded", "blocked", "data_unavailable"]
    small_account_decision: Literal["feasible", "degraded", "blocked", "data_unavailable"]
    account_equity: float | None = None
    buying_power: float | None = None
    fractional_trading_enabled: bool
    fractional_feasible: bool
    position_size_shares: float | None = None
    position_size_notional: float | None = None
    risk_dollars: float
    risk_per_share: float | None = None
    max_loss_if_stopped: float | None = None
    expected_profit_dollars: float | None = None
    expected_value_dollars: float | None = None
    notional_usage_pct: float | None = None
    buying_power_usage_pct: float | None = None
    liquidity_participation_pct: float | None = None
    spread_cost_estimate: float | None = None
    slippage_cost_estimate: float | None = None
    expected_r_after_costs: float | None = None
    max_risk_dollars: float
    max_daily_loss_dollars: float
    max_position_notional: float
    feasible_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[str] = Field(default_factory=list)
    small_account_rejected_symbols: list[str] = Field(default_factory=list)
    sizing_notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    account_feasibility_blockers: list[str] = Field(default_factory=list)
    account_feasibility_warnings: list[str] = Field(default_factory=list)
    small_account_blockers: list[str] = Field(default_factory=list)
    small_account_warnings: list[str] = Field(default_factory=list)
    next_agent: str | None = None
    allow_submit: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    llm_used: bool = False


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def evaluate_small_account_feasibility(request: SmallAccountFeasibilityRequest) -> SmallAccountFeasibilityResponse:
    expected_r = float(request.expected_r if request.expected_r is not None else DEFAULT_EXPECTED_R)
    predicted_ev = request.predicted_expected_value_r

    inp = AccountFeasibilityInput(
        account_equity=request.account_equity,
        buying_power=request.buying_power,
        fractional_trading_enabled=request.fractional_trading_enabled,
        risk_budget=request.risk_budget,
        max_risk_pct=request.max_risk_per_trade_pct,
        max_risk_dollars=request.max_risk_dollars,
        max_daily_loss_pct=request.max_daily_loss_pct,
        max_position_notional_pct=request.max_position_notional_pct,
        max_position_notional=request.max_position_notional,
        symbols=list(request.symbols),
        usable_symbols=list(request.usable_symbols),
        selected_symbol=request.selected_symbol,
        entry=request.entry,
        stop=request.stop,
        target=request.target,
        latest_price=request.latest_price,
        expected_r=expected_r,
        predicted_expected_value_r=predicted_ev,
        spread_bps=request.spread_bps,
        slippage_bps=request.slippage_bps,
        volume=request.volume,
        dollar_volume=request.dollar_volume,
        avg_dollar_volume=request.avg_dollar_volume,
        market_session=request.market_session,
        execution_mode=request.execution_mode,
        paper_trading_enabled=request.paper_trading_enabled,
        live_trading_enabled=request.live_trading_enabled,
        broker_execution_enabled=request.broker_execution_enabled,
        allow_submit=request.allow_submit,
        planned_risk_dollars=request.planned_risk_dollars,
        open_positions=request.open_positions,
        day_trades_used=request.day_trades_used,
        current_daily_loss=request.current_daily_loss,
        max_open_positions=request.max_open_positions,
        max_trades_per_day=request.max_trades_per_day,
        proof_status=request.proof_status,
        using_non_real_data=request.using_non_real_data,
        persistence_status=request.persistence_status,
        min_expected_r_after_costs=float(request.min_expected_r),
        min_predicted_expected_value_r=request.min_predicted_expected_value_r,
        max_liquidity_participation_pct=float(request.max_liquidity_participation_pct),
        min_order_notional=float(request.min_order_notional),
        strategy_key=request.strategy_key,
        setup_type=request.setup_type,
    )

    out = evaluate_account_feasibility(inp)

    if out.account_feasibility_decision == "data_unavailable":
        decision: Literal["pass", "degraded", "blocked", "data_unavailable"] = "data_unavailable"
    elif out.account_feasibility_decision == "blocked":
        decision = "blocked"
    elif out.account_feasibility_decision == "degraded":
        decision = "degraded"
    else:
        decision = "pass"

    sizing_notes = [
        "Account feasibility is risk/notional/participation based, not share-price based.",
        "Fractional shares apply when fractional_trading_enabled=true.",
        "allow_submit remains false; no broker submit is performed.",
    ]
    if request.candidate_source:
        sizing_notes.append(f"candidate_source={request.candidate_source}")
    if request.data_quality:
        sizing_notes.append(f"data_quality={request.data_quality}")

    return SmallAccountFeasibilityResponse(
        decision=decision,
        account_feasibility_decision=out.account_feasibility_decision,
        small_account_decision=out.small_account_decision,
        account_equity=out.account_equity,
        buying_power=out.buying_power,
        fractional_trading_enabled=out.fractional_trading_enabled,
        fractional_feasible=out.fractional_feasible,
        position_size_shares=_round(out.position_size_shares, 6),
        position_size_notional=_round(out.position_size_notional, 2),
        risk_dollars=out.risk_dollars,
        risk_per_share=_round(out.risk_per_share, 6),
        max_loss_if_stopped=_round(out.max_loss_if_stopped, 2),
        expected_profit_dollars=_round(out.expected_profit_dollars, 2),
        expected_value_dollars=_round(out.expected_value_dollars, 2),
        notional_usage_pct=_round(out.notional_usage_pct, 6),
        buying_power_usage_pct=_round(out.buying_power_usage_pct, 6),
        liquidity_participation_pct=_round(out.liquidity_participation_pct, 6),
        spread_cost_estimate=_round(out.spread_cost_estimate, 4),
        slippage_cost_estimate=_round(out.slippage_cost_estimate, 4),
        expected_r_after_costs=_round(out.expected_r_after_costs, 6),
        max_risk_dollars=out.max_risk_dollars,
        max_daily_loss_dollars=out.max_daily_loss_dollars,
        max_position_notional=out.max_position_notional,
        feasible_symbols=out.feasible_symbols,
        rejected_symbols=out.rejected_symbols,
        small_account_rejected_symbols=out.rejected_symbols,
        sizing_notes=sizing_notes,
        blockers=out.blockers,
        warnings=out.warnings,
        account_feasibility_blockers=out.account_feasibility_blockers,
        account_feasibility_warnings=out.account_feasibility_warnings,
        small_account_blockers=out.blockers,
        small_account_warnings=out.warnings,
        next_agent=out.next_agent,
        allow_submit=False,
        submitted_order=False,
        broker_called=False,
        llm_used=False,
    )


def readiness_summary() -> dict[str, Any]:
    return {
        "enabled": True,
        "account_equity_source": "owner_account_state",
        "buying_power_source": "owner_account_state",
        "owner_policy_defaults": {
            "max_risk_per_trade_pct": MAX_RISK_PER_TRADE_PCT,
            "max_daily_loss_pct": MAX_DAILY_LOSS_PCT,
            "max_position_notional_pct": MAX_POSITION_NOTIONAL_PCT,
        },
        "fractional_trading_enabled": True,
        "status": "ready",
        "blockers": [],
        "warnings": ["account_equity_and_buying_power_must_be_supplied_by_owner_account_state"],
    }
