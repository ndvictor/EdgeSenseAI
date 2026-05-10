from __future__ import annotations

from math import floor
from typing import Any, Literal

from pydantic import BaseModel, Field


DEFAULT_ACCOUNT_EQUITY = 1000.0
DEFAULT_BUYING_POWER = 1000.0
DEFAULT_MAX_RISK_PER_TRADE_PCT = 0.005
DEFAULT_MAX_DAILY_LOSS_PCT = 0.015
DEFAULT_MAX_POSITION_NOTIONAL_PCT = 1.0
DEFAULT_MAX_OPEN_POSITIONS = 1
DEFAULT_MAX_TRADES_PER_DAY = 3
DEFAULT_MIN_AVG_DOLLAR_VOLUME = 1_000_000.0
DEFAULT_MAX_SPREAD_BPS = 35.0
DEFAULT_MIN_ORDER_NOTIONAL = 1.0
DEFAULT_MIN_EXPECTED_R = 0.25
DEFAULT_EXPECTED_R = 1.0


class SmallAccountFeasibilityRequest(BaseModel):
    account_equity: float = DEFAULT_ACCOUNT_EQUITY
    buying_power: float | None = None
    fractional_trading_enabled: bool = True
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
    avg_dollar_volume: float | None = None
    planned_risk_dollars: float | None = None
    open_positions: int = 0
    day_trades_used: int = 0
    proof_status: str | None = None
    source_mode: str | None = None
    using_non_real_data: bool = False
    persistence_status: str | None = None
    max_risk_per_trade_pct: float = DEFAULT_MAX_RISK_PER_TRADE_PCT
    max_daily_loss_pct: float = DEFAULT_MAX_DAILY_LOSS_PCT
    max_position_notional_pct: float = DEFAULT_MAX_POSITION_NOTIONAL_PCT
    max_open_positions: int = DEFAULT_MAX_OPEN_POSITIONS
    max_trades_per_day: int = DEFAULT_MAX_TRADES_PER_DAY
    min_avg_dollar_volume: float = DEFAULT_MIN_AVG_DOLLAR_VOLUME
    max_spread_bps: float = DEFAULT_MAX_SPREAD_BPS
    min_order_notional: float = DEFAULT_MIN_ORDER_NOTIONAL
    min_expected_r: float = DEFAULT_MIN_EXPECTED_R


class SmallAccountFeasibilityResponse(BaseModel):
    decision: Literal["pass", "degraded", "blocked"]
    small_account_decision: Literal["feasible", "degraded", "blocked"]
    account_equity: float
    buying_power: float
    fractional_trading_enabled: bool
    fractional_feasible: bool
    position_size_shares: float | None = None
    position_size_notional: float | None = None
    risk_dollars: float
    risk_per_share: float | None = None
    max_loss_if_stopped: float | None = None
    expected_profit_dollars: float | None = None
    notional_usage_pct: float | None = None
    max_risk_dollars: float
    max_daily_loss_dollars: float
    max_position_notional: float
    feasible_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[str] = Field(default_factory=list)
    small_account_rejected_symbols: list[str] = Field(default_factory=list)
    sizing_notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    small_account_blockers: list[str] = Field(default_factory=list)
    small_account_warnings: list[str] = Field(default_factory=list)
    next_agent: str | None = None
    allow_submit: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    llm_used: bool = False


def _clean_symbols(values: list[str]) -> list[str]:
    return [str(symbol).strip().upper() for symbol in values if str(symbol).strip()]


def _pct_to_fraction(value: float, *, default: float) -> float:
    """Accept either decimal fractions (0.005) or percent values (0.5)."""
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return default
    if pct <= 0:
        return default
    return pct / 100.0 if pct > 0.05 else pct


def _round(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def evaluate_small_account_feasibility(request: SmallAccountFeasibilityRequest) -> SmallAccountFeasibilityResponse:
    account_equity = float(request.account_equity or DEFAULT_ACCOUNT_EQUITY)
    buying_power = float(request.buying_power if request.buying_power is not None else account_equity if account_equity > 0 else DEFAULT_BUYING_POWER)
    max_risk_pct = _pct_to_fraction(request.max_risk_per_trade_pct, default=DEFAULT_MAX_RISK_PER_TRADE_PCT)
    max_daily_loss_pct = _pct_to_fraction(request.max_daily_loss_pct, default=DEFAULT_MAX_DAILY_LOSS_PCT)
    max_position_notional_pct = _pct_to_fraction(request.max_position_notional_pct, default=DEFAULT_MAX_POSITION_NOTIONAL_PCT)
    max_risk_dollars = round(account_equity * max_risk_pct, 2)
    max_daily_loss_dollars = round(account_equity * max_daily_loss_pct, 2)
    max_position_notional = round(account_equity * max_position_notional_pct, 2)

    blockers: list[str] = []
    warnings: list[str] = []
    sizing_notes: list[str] = [
        "Small-account feasibility is risk/notional based, not absolute stock-price based.",
        "Fractional shares are allowed when fractional_trading_enabled=true.",
        "allow_submit remains false; no broker submit is performed.",
    ]

    symbols = _clean_symbols(request.usable_symbols or request.symbols)
    selected_symbol = str(request.selected_symbol).strip().upper() if request.selected_symbol else None
    rejected_symbols: list[str] = []
    feasible_symbols: list[str] = []

    entry = float(request.entry or request.latest_price or 0.0) if (request.entry is not None or request.latest_price is not None) else None
    stop = float(request.stop) if request.stop is not None else None
    target = float(request.target) if request.target is not None else None
    expected_r = float(request.predicted_expected_value_r if request.predicted_expected_value_r is not None else request.expected_r if request.expected_r is not None else DEFAULT_EXPECTED_R)

    if not selected_symbol:
        blockers.append("no_selected_symbol")
    elif selected_symbol not in symbols and symbols:
        warnings.append("selected_symbol_not_in_usable_symbols")

    if entry is None or entry <= 0:
        blockers.append("missing_entry")

    risk_per_share: float | None = None
    if entry is not None and entry > 0 and stop is not None:
        risk_per_share = abs(entry - stop)
        if risk_per_share <= 0:
            blockers.append("risk_per_share_invalid")
    elif stop is None:
        warnings.append("missing_stop_using_notional_budget_only")

    risk_dollars = float(request.planned_risk_dollars) if request.planned_risk_dollars is not None else max_risk_dollars
    if risk_dollars <= 0:
        blockers.append("risk_dollars_invalid")
    if risk_dollars > max_risk_dollars:
        blockers.append("planned_risk_exceeds_small_account_limit")

    if expected_r < float(request.min_expected_r):
        blockers.append("expected_r_below_minimum")

    position_size_shares: float | None = None
    position_size_notional: float | None = None
    max_loss_if_stopped: float | None = None
    expected_profit_dollars: float | None = None
    notional_usage_pct: float | None = None
    fractional_feasible = False

    if entry is not None and entry > 0:
        if risk_per_share is not None and risk_per_share > 0:
            raw_shares = risk_dollars / risk_per_share
            shares = raw_shares if request.fractional_trading_enabled else floor(raw_shares)
        else:
            target_notional = min(max_position_notional, buying_power)
            raw_shares = target_notional / entry
            shares = raw_shares if request.fractional_trading_enabled else floor(raw_shares)
        if shares <= 0:
            blockers.append("position_size_zero")
        else:
            position_size_shares = shares
            position_size_notional = shares * entry
            fractional_feasible = bool(request.fractional_trading_enabled or shares >= 1)
            if risk_per_share is not None:
                max_loss_if_stopped = shares * risk_per_share
            expected_profit_dollars = risk_dollars * expected_r
            notional_usage_pct = (position_size_notional / buying_power) if buying_power > 0 else None

    if position_size_notional is not None:
        if position_size_notional < float(request.min_order_notional):
            blockers.append("position_notional_below_min_order_notional")
        if position_size_notional > buying_power:
            blockers.append("position_notional_exceeds_buying_power")
        if position_size_notional > max_position_notional:
            blockers.append("position_notional_exceeds_max_position_notional")

    if request.spread_bps is not None and float(request.spread_bps) > request.max_spread_bps:
        if expected_r <= 1.0:
            blockers.append("spread_slippage_destroys_expected_r")
        else:
            warnings.append("spread_wide_but_expected_r_may_absorb_cost")

    if request.avg_dollar_volume is not None and float(request.avg_dollar_volume) < request.min_avg_dollar_volume:
        blockers.append("avg_dollar_volume_below_small_account_minimum")

    if int(request.open_positions or 0) >= int(request.max_open_positions):
        blockers.append("max_open_positions_reached")

    if int(request.day_trades_used or 0) >= int(request.max_trades_per_day):
        blockers.append("max_trades_per_day_reached")

    proof_status = str(request.proof_status or "").strip().lower()
    if proof_status in {"", "backtest_required", "proof_required"}:
        warnings.append("proof_not_ready_for_small_account")

    if request.using_non_real_data:
        blockers.append("non_real_data_used_for_small_account_feasibility")

    if str(request.persistence_status or "").lower() in {"memory_fallback", "unavailable"}:
        warnings.append("persistence_not_confirmed_for_small_account_feasibility")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))

    if selected_symbol:
        if blockers:
            rejected_symbols.append(selected_symbol)
        else:
            feasible_symbols.append(selected_symbol)

    if blockers:
        decision: Literal["pass", "degraded", "blocked"] = "blocked"
        small_account_decision: Literal["feasible", "degraded", "blocked"] = "blocked"
        next_agent = None
    elif warnings:
        decision = "degraded"
        small_account_decision = "degraded"
        next_agent = "execution_planner_agent"
    else:
        decision = "pass"
        small_account_decision = "feasible"
        next_agent = "execution_planner_agent"

    return SmallAccountFeasibilityResponse(
        decision=decision,
        small_account_decision=small_account_decision,
        account_equity=round(account_equity, 2),
        buying_power=round(buying_power, 2),
        fractional_trading_enabled=bool(request.fractional_trading_enabled),
        fractional_feasible=bool(fractional_feasible and not blockers),
        position_size_shares=_round(position_size_shares, 6),
        position_size_notional=_round(position_size_notional, 2),
        risk_dollars=round(risk_dollars, 2),
        risk_per_share=_round(risk_per_share, 6),
        max_loss_if_stopped=_round(max_loss_if_stopped, 2),
        expected_profit_dollars=_round(expected_profit_dollars, 2),
        notional_usage_pct=_round(notional_usage_pct, 6),
        max_risk_dollars=max_risk_dollars,
        max_daily_loss_dollars=max_daily_loss_dollars,
        max_position_notional=max_position_notional,
        feasible_symbols=feasible_symbols,
        rejected_symbols=rejected_symbols,
        small_account_rejected_symbols=rejected_symbols,
        sizing_notes=sizing_notes,
        blockers=blockers,
        warnings=warnings,
        small_account_blockers=blockers,
        small_account_warnings=warnings,
        next_agent=next_agent,
        allow_submit=False,
        submitted_order=False,
        broker_called=False,
        llm_used=False,
    )


def readiness_summary() -> dict[str, Any]:
    return {
        "enabled": True,
        "account_equity_default": int(DEFAULT_ACCOUNT_EQUITY),
        "max_risk_per_trade_pct": 0.5,
        "max_daily_loss_pct": 1.5,
        "fractional_trading_enabled": True,
        "status": "ready",
        "blockers": [],
        "warnings": [],
    }
