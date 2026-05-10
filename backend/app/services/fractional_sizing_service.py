"""Account-size-agnostic feasibility: risk, notional, liquidity participation, and friction vs expected R."""

from __future__ import annotations

from math import floor
from typing import Literal

from pydantic import BaseModel, Field


# Owner risk policy uses **human percent values** at the input boundary:
#   max_risk_per_trade_pct = 0.5   means 0.5%
#   max_daily_loss_pct     = 1.5   means 1.5%
#   max_position_notional_pct = 100 means 100%
# Internally we convert the percent value to a decimal **fraction** exactly
# once via ``_percent_to_fraction`` and use the ``_fraction`` variables for
# multiplication. Never apply ``/100`` more than once.
MAX_RISK_PER_TRADE_PCT = 0.5
MAX_DAILY_LOSS_PCT = 1.5
MAX_POSITION_NOTIONAL_PCT = 100.0
DEFAULT_MAX_OPEN_POSITIONS = 1
DEFAULT_MAX_TRADES_PER_DAY = 3
DEFAULT_MIN_ORDER_NOTIONAL = 1.0
DEFAULT_MIN_EXPECTED_R_AFTER_COSTS = 0.25
DEFAULT_MAX_LIQUIDITY_PARTICIPATION_PCT = 0.05
DEFAULT_EXPECTED_R = 1.0


class AccountFeasibilityInput(BaseModel):
    account_equity: float | None = None
    buying_power: float | None = None
    fractional_trading_enabled: bool = True
    risk_budget: float | None = None
    # Owner risk policy: percent values (``0.5`` = 0.5%, ``100`` = 100%).
    # Converted to a decimal fraction internally exactly once.
    max_risk_pct: float | None = None
    max_daily_loss_pct: float | None = None
    max_risk_dollars: float | None = None
    max_risk_dollars_cap: float | None = None
    max_position_notional_pct: float | None = None
    max_position_notional: float | None = None
    max_position_notional_cap: float | None = None

    symbols: list[str] = Field(default_factory=list)
    usable_symbols: list[str] = Field(default_factory=list)
    selected_symbol: str | None = None

    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    latest_price: float | None = None
    expected_r: float | None = None
    predicted_expected_value_r: float | None = None

    spread_bps: float | None = None
    slippage_bps: float | None = None

    volume: float | None = None
    dollar_volume: float | None = None
    avg_dollar_volume: float | None = None

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
    max_open_positions: int = DEFAULT_MAX_OPEN_POSITIONS
    max_trades_per_day: int = DEFAULT_MAX_TRADES_PER_DAY

    proof_status: str | None = None
    using_non_real_data: bool = False
    persistence_status: str | None = None

    min_expected_r_after_costs: float = DEFAULT_MIN_EXPECTED_R_AFTER_COSTS
    min_predicted_expected_value_r: float | None = None
    max_liquidity_participation_pct: float = DEFAULT_MAX_LIQUIDITY_PARTICIPATION_PCT
    min_order_notional: float = DEFAULT_MIN_ORDER_NOTIONAL

    strategy_key: str | None = None
    setup_type: str | None = None


class AccountFeasibilityOutput(BaseModel):
    account_feasibility_decision: Literal["feasible", "degraded", "blocked", "data_unavailable"]
    small_account_decision: Literal["feasible", "degraded", "blocked", "data_unavailable"]
    fractional_feasible: bool
    fractional_trading_enabled: bool
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
    feasible_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    account_feasibility_blockers: list[str] = Field(default_factory=list)
    account_feasibility_warnings: list[str] = Field(default_factory=list)
    small_account_blockers: list[str] = Field(default_factory=list)
    small_account_warnings: list[str] = Field(default_factory=list)
    account_equity: float | None = None
    buying_power: float | None = None
    max_risk_dollars: float
    max_daily_loss_dollars: float
    max_position_notional: float
    next_agent: str | None = None
    allow_submit: bool = False
    submitted_order: bool = False
    broker_called: bool = False
    llm_used: bool = False


def _clean_symbols(values: list[str]) -> list[str]:
    return [str(symbol).strip().upper() for symbol in values if str(symbol).strip()]


def _percent_to_fraction(
    value_pct: float | None,
    *,
    default_pct: float,
    warnings: list[str],
    label: str,
) -> float:
    """Convert a human percent value (``0.5`` = 0.5%, ``100`` = 100%) into a decimal fraction.

    The service applies ``/ 100`` exactly once here. ``None`` quietly uses the
    configured default (no warning -- an unset value is the expected callsite).
    Explicitly-provided values must lie in ``(0, 100]``; anything else falls back
    to ``default_pct`` and emits a ``risk_policy_default_used`` warning so the
    auditor can flag the suspicious input.
    """
    if value_pct is None:
        return float(default_pct) / 100.0
    try:
        pct = float(value_pct)
    except (TypeError, ValueError):
        warnings.append(f"{label}_invalid_value")
        warnings.append("risk_policy_default_used")
        return float(default_pct) / 100.0
    if pct <= 0:
        warnings.append(f"{label}_non_positive_rejected")
        warnings.append("risk_policy_default_used")
        return float(default_pct) / 100.0
    if pct > 100.0:
        warnings.append(f"{label}_above_100_percent_rejected")
        warnings.append("risk_policy_default_used")
        return float(default_pct) / 100.0
    return pct / 100.0


def _round_f(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _regular_market_session(market_session: str | None) -> bool:
    s = str(market_session or "").strip().lower().replace("-", "_")
    return s in {"regular_market", "regular", "market_hours", "open", "rth"}


def _live_execution_spread_hard_block(inp: AccountFeasibilityInput) -> bool:
    return bool(inp.allow_submit) and bool(inp.live_trading_enabled) and _regular_market_session(inp.market_session)


def evaluate_account_feasibility(inp: AccountFeasibilityInput) -> AccountFeasibilityOutput:
    pct_warnings: list[str] = []
    # Convert owner policy percent values to decimal fractions exactly once.
    max_risk_per_trade_fraction = _percent_to_fraction(
        inp.max_risk_pct,
        default_pct=MAX_RISK_PER_TRADE_PCT,
        warnings=pct_warnings,
        label="max_risk_per_trade_pct",
    )
    max_daily_loss_fraction = _percent_to_fraction(
        inp.max_daily_loss_pct,
        default_pct=MAX_DAILY_LOSS_PCT,
        warnings=pct_warnings,
        label="max_daily_loss_pct",
    )
    max_position_notional_fraction = _percent_to_fraction(
        inp.max_position_notional_pct,
        default_pct=MAX_POSITION_NOTIONAL_PCT,
        warnings=pct_warnings,
        label="max_position_notional_pct",
    )

    blockers: list[str] = []
    warnings: list[str] = list(pct_warnings)
    account_equity = float(inp.account_equity) if inp.account_equity is not None and float(inp.account_equity) > 0 else None
    buying_power = float(inp.buying_power) if inp.buying_power is not None and float(inp.buying_power) >= 0 else None
    if account_equity is None:
        blockers.append("account_equity_unavailable")
    if buying_power is None:
        blockers.append("buying_power_unavailable")

    if account_equity is None or buying_power is None:
        blockers = sorted(set(blockers))
        warnings = sorted(set(warnings))
        return AccountFeasibilityOutput(
            account_feasibility_decision="data_unavailable",
            small_account_decision="data_unavailable",
            fractional_feasible=False,
            fractional_trading_enabled=bool(inp.fractional_trading_enabled),
            risk_dollars=0.0,
            feasible_symbols=[],
            rejected_symbols=_clean_symbols([inp.selected_symbol] if inp.selected_symbol else []),
            blockers=blockers,
            warnings=warnings,
            account_feasibility_blockers=blockers,
            account_feasibility_warnings=warnings,
            small_account_blockers=blockers,
            small_account_warnings=warnings,
            account_equity=account_equity,
            buying_power=buying_power,
            max_risk_dollars=0.0,
            max_daily_loss_dollars=0.0,
            max_position_notional=0.0,
            next_agent=None,
            allow_submit=False,
            submitted_order=False,
            broker_called=False,
            llm_used=False,
        )

    max_risk_dollars = round(account_equity * max_risk_per_trade_fraction, 2)
    if inp.max_risk_dollars is not None:
        max_risk_dollars = min(max_risk_dollars, float(inp.max_risk_dollars))
    if inp.max_risk_dollars_cap is not None:
        max_risk_dollars = min(max_risk_dollars, float(inp.max_risk_dollars_cap))
    max_daily_loss_dollars = round(account_equity * max_daily_loss_fraction, 2)
    max_position_notional = round(account_equity * max_position_notional_fraction, 2)
    if inp.max_position_notional is not None:
        max_position_notional = min(max_position_notional, float(inp.max_position_notional))
    if inp.max_position_notional_cap is not None:
        max_position_notional = min(max_position_notional, float(inp.max_position_notional_cap))

    symbols = _clean_symbols(inp.usable_symbols or inp.symbols)
    selected_symbol = str(inp.selected_symbol).strip().upper() if inp.selected_symbol else None
    rejected_symbols: list[str] = []
    feasible_symbols: list[str] = []

    if not selected_symbol:
        blockers.append("no_selected_symbol")
    elif selected_symbol not in symbols and symbols:
        warnings.append("selected_symbol_not_in_usable_symbols")

    mode = str(inp.execution_mode or "plan_only").strip().lower()
    if mode == "live":
        if not inp.live_trading_enabled:
            blockers.append("execution_mode_live_not_allowed")
        if not inp.broker_execution_enabled:
            blockers.append("execution_mode_live_broker_disabled")
    elif mode == "paper":
        if not inp.paper_trading_enabled:
            blockers.append("execution_mode_paper_not_allowed")

    entry = inp.entry if inp.entry is not None else inp.latest_price
    entry_f = float(entry) if entry is not None else None
    stop = float(inp.stop) if inp.stop is not None else None

    expected_r_base = float(inp.expected_r if inp.expected_r is not None else DEFAULT_EXPECTED_R)

    if inp.using_non_real_data:
        blockers.append("non_real_or_synthetic_data")

    if entry_f is None or entry_f <= 0:
        blockers.append("missing_entry")

    if inp.stop is None:
        blockers.append("missing_stop")

    risk_per_share: float | None = None
    if entry_f is not None and entry_f > 0 and stop is not None:
        risk_per_share = abs(entry_f - stop)
        if risk_per_share <= 0:
            blockers.append("risk_per_share_invalid")

    risk_dollars = float(inp.planned_risk_dollars) if inp.planned_risk_dollars is not None else max_risk_dollars
    if inp.risk_budget is not None and risk_dollars > float(inp.risk_budget):
        blockers.append("planned_risk_exceeds_risk_budget")
    if risk_dollars <= 0:
        blockers.append("risk_dollars_invalid")
    if risk_dollars > max_risk_dollars:
        blockers.append("planned_risk_exceeds_policy_limit")

    if int(inp.open_positions or 0) >= int(inp.max_open_positions):
        blockers.append("max_open_positions_reached")

    if int(inp.day_trades_used or 0) >= int(inp.max_trades_per_day):
        blockers.append("max_trades_per_day_reached")

    # Daily-loss accumulator: never block the first trade of the day, only
    # block when the proposed trade's risk would push cumulative loss past the
    # configured policy cap.
    current_daily_loss = max(0.0, float(inp.current_daily_loss or 0.0))
    if current_daily_loss + float(risk_dollars) > float(max_daily_loss_dollars):
        blockers.append("daily_loss_limit_would_be_exceeded")

    proof_status = str(inp.proof_status or "").strip().lower()
    if proof_status in {"", "backtest_required", "proof_required"}:
        warnings.append("proof_not_ready_for_promotion")

    if str(inp.persistence_status or "").lower() in {"memory_fallback", "unavailable"}:
        warnings.append("persistence_not_confirmed_for_account_feasibility")

    position_size_shares: float | None = None
    position_size_notional: float | None = None
    max_loss_if_stopped: float | None = None
    expected_profit_dollars: float | None = None
    expected_value_dollars: float | None = None
    notional_usage_pct: float | None = None
    buying_power_usage_pct: float | None = None
    liquidity_participation_pct: float | None = None
    spread_cost_estimate: float | None = None
    slippage_cost_estimate: float | None = None
    expected_r_after_costs: float | None = None
    fractional_feasible = False
    degraded_sizing = False

    dollar_vol = inp.dollar_volume if inp.dollar_volume is not None else inp.avg_dollar_volume
    dollar_vol_f = float(dollar_vol) if dollar_vol is not None else None
    volume_f = float(inp.volume) if inp.volume is not None else None

    live_spread_block = _live_execution_spread_hard_block(inp)
    spread_missing = inp.spread_bps is None

    if spread_missing:
        if live_spread_block:
            blockers.append("missing_spread_bps_for_cost_estimation")
        else:
            warnings.append("spread_bps_missing_for_cost_estimation")

    pre_blockers = list(blockers)

    can_size = (
        not pre_blockers
        and entry_f is not None
        and entry_f > 0
        and buying_power > 0
    )

    if can_size:
        if risk_per_share is not None and risk_per_share > 0:
            raw_shares = risk_dollars / risk_per_share
            shares = raw_shares if inp.fractional_trading_enabled else floor(raw_shares)
        else:
            degraded_sizing = True
            target_notional = min(max_position_notional, buying_power)
            raw_shares = target_notional / entry_f
            shares = raw_shares if inp.fractional_trading_enabled else floor(raw_shares)

        if shares <= 0:
            blockers.append("position_size_zero")
        else:
            position_size_shares = shares
            position_size_notional = shares * entry_f
            fractional_feasible = bool(inp.fractional_trading_enabled or shares >= 1)
            if risk_per_share is not None:
                max_loss_if_stopped = shares * risk_per_share
            expected_profit_dollars = risk_dollars * expected_r_base
            if inp.predicted_expected_value_r is not None:
                expected_value_dollars = risk_dollars * float(inp.predicted_expected_value_r)
            if account_equity > 0:
                notional_usage_pct = position_size_notional / account_equity
            buying_power_usage_pct = (position_size_notional / buying_power) if buying_power > 0 else None

            if dollar_vol_f is not None and dollar_vol_f > 0 and position_size_notional is not None:
                liquidity_participation_pct = position_size_notional / dollar_vol_f
            elif volume_f is not None and volume_f > 0 and position_size_shares is not None:
                liquidity_participation_pct = position_size_shares / volume_f
                warnings.append("liquidity_participation_used_share_volume_ratio")
            else:
                warnings.append("liquidity_participation_not_computable")

            if position_size_notional is not None:
                if position_size_notional < float(inp.min_order_notional):
                    blockers.append("position_notional_below_min_order_notional")
                if position_size_notional > buying_power:
                    blockers.append("position_notional_exceeds_buying_power")
                if position_size_notional > max_position_notional:
                    blockers.append("position_notional_exceeds_max_position_notional")

            if liquidity_participation_pct is not None and liquidity_participation_pct > float(inp.max_liquidity_participation_pct):
                blockers.append("liquidity_participation_too_high")

            friction_r = 0.0
            if inp.spread_bps is not None and position_size_notional is not None and risk_dollars > 0:
                sp = float(inp.spread_bps)
                spread_cost_estimate = position_size_notional * (sp / 10000.0) * 0.5
                slip_bps = float(inp.slippage_bps) if inp.slippage_bps is not None else sp * 0.25
                slippage_cost_estimate = position_size_notional * (slip_bps / 10000.0)
                total_cost = (spread_cost_estimate or 0.0) + (slippage_cost_estimate or 0.0)
                friction_r = total_cost / risk_dollars

            if risk_dollars > 0:
                expected_r_after_costs = expected_r_base - friction_r

            below_min = expected_r_after_costs is not None and expected_r_after_costs <= float(inp.min_expected_r_after_costs)
            intrinsic_shortfall = expected_r_base <= float(inp.min_expected_r_after_costs)
            if below_min:
                if intrinsic_shortfall:
                    blockers.append("expected_r_after_costs_below_minimum")
                elif friction_r > 0 and live_spread_block:
                    blockers.append("spread_slippage_destroys_expected_r")
                elif friction_r > 0 and not live_spread_block:
                    warnings.append("spread_too_wide_for_execution_now")
                else:
                    blockers.append("expected_r_after_costs_below_minimum")

            if inp.predicted_expected_value_r is not None and inp.min_predicted_expected_value_r is not None and risk_dollars > 0:
                ev_after = float(inp.predicted_expected_value_r) - friction_r
                if ev_after < float(inp.min_predicted_expected_value_r):
                    if friction_r > 0 and live_spread_block:
                        blockers.append("predicted_expected_value_after_costs_below_threshold")
                    elif friction_r > 0 and not live_spread_block:
                        warnings.append("predicted_ev_low_after_friction_advisory")
                    else:
                        blockers.append("predicted_expected_value_after_costs_below_threshold")

            if degraded_sizing:
                warnings.append("notional_sized_without_stop_risk_anchor")

    blockers = sorted(set(blockers))
    warnings = sorted(set(warnings))

    if selected_symbol:
        if blockers:
            rejected_symbols.append(selected_symbol)
        else:
            feasible_symbols.append(selected_symbol)

    if blockers:
        account_decision: Literal["feasible", "degraded", "blocked"] = "blocked"
        small_decision = "blocked"
        next_agent = None
    elif warnings:
        account_decision = "degraded"
        small_decision = "degraded"
        next_agent = "execution_planner_agent"
    else:
        account_decision = "feasible"
        small_decision = "feasible"
        next_agent = "execution_planner_agent"

    return AccountFeasibilityOutput(
        account_feasibility_decision=account_decision,
        small_account_decision=small_decision,
        fractional_feasible=bool(fractional_feasible and not blockers),
        fractional_trading_enabled=bool(inp.fractional_trading_enabled),
        position_size_shares=_round_f(position_size_shares, 6),
        position_size_notional=_round_f(position_size_notional, 2),
        risk_dollars=round(risk_dollars, 2),
        risk_per_share=_round_f(risk_per_share, 6),
        max_loss_if_stopped=_round_f(max_loss_if_stopped, 2),
        expected_profit_dollars=_round_f(expected_profit_dollars, 2),
        expected_value_dollars=_round_f(expected_value_dollars, 2),
        notional_usage_pct=_round_f(notional_usage_pct, 6),
        buying_power_usage_pct=_round_f(buying_power_usage_pct, 6),
        liquidity_participation_pct=_round_f(liquidity_participation_pct, 6),
        spread_cost_estimate=_round_f(spread_cost_estimate, 4),
        slippage_cost_estimate=_round_f(slippage_cost_estimate, 4),
        expected_r_after_costs=_round_f(expected_r_after_costs, 6),
        feasible_symbols=feasible_symbols,
        rejected_symbols=rejected_symbols,
        blockers=list(blockers),
        warnings=list(warnings),
        account_feasibility_blockers=list(blockers),
        account_feasibility_warnings=list(warnings),
        small_account_blockers=list(blockers),
        small_account_warnings=list(warnings),
        account_equity=round(account_equity, 2),
        buying_power=round(buying_power, 2),
        max_risk_dollars=max_risk_dollars,
        max_daily_loss_dollars=max_daily_loss_dollars,
        max_position_notional=max_position_notional,
        next_agent=next_agent,
        allow_submit=False,
        submitted_order=False,
        broker_called=False,
        llm_used=False,
    )
