from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DEFAULT_ACCOUNT_EQUITY = 1000.0
DEFAULT_MAX_RISK_PER_TRADE_PCT = 0.005
DEFAULT_MAX_DAILY_LOSS_PCT = 0.015
DEFAULT_MAX_OPEN_POSITIONS = 1
DEFAULT_MAX_TRADES_PER_DAY = 3
DEFAULT_MIN_AVG_DOLLAR_VOLUME = 20_000_000.0
DEFAULT_MAX_SPREAD_BPS = 20.0
DEFAULT_MIN_PRICE = 2.0
DEFAULT_MAX_PRICE = 75.0


class SmallAccountFeasibilityRequest(BaseModel):
    account_equity: float = DEFAULT_ACCOUNT_EQUITY
    symbols: list[str] = Field(default_factory=list)
    usable_symbols: list[str] = Field(default_factory=list)
    selected_symbol: str | None = None
    latest_price: float | None = None
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
    max_open_positions: int = DEFAULT_MAX_OPEN_POSITIONS
    max_trades_per_day: int = DEFAULT_MAX_TRADES_PER_DAY
    min_avg_dollar_volume: float = DEFAULT_MIN_AVG_DOLLAR_VOLUME
    max_spread_bps: float = DEFAULT_MAX_SPREAD_BPS
    min_price: float = DEFAULT_MIN_PRICE
    max_price: float = DEFAULT_MAX_PRICE


class SmallAccountFeasibilityResponse(BaseModel):
    decision: Literal["pass", "degraded", "blocked"]
    account_equity: float
    max_risk_dollars: float
    max_daily_loss_dollars: float
    feasible_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[str] = Field(default_factory=list)
    sizing_notes: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
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


def evaluate_small_account_feasibility(request: SmallAccountFeasibilityRequest) -> SmallAccountFeasibilityResponse:
    account_equity = float(request.account_equity or DEFAULT_ACCOUNT_EQUITY)
    max_risk_pct = _pct_to_fraction(request.max_risk_per_trade_pct, default=DEFAULT_MAX_RISK_PER_TRADE_PCT)
    max_daily_loss_pct = _pct_to_fraction(request.max_daily_loss_pct, default=DEFAULT_MAX_DAILY_LOSS_PCT)
    max_risk_dollars = round(account_equity * max_risk_pct, 2)
    max_daily_loss_dollars = round(account_equity * max_daily_loss_pct, 2)

    blockers: list[str] = []
    warnings: list[str] = []
    sizing_notes: list[str] = [
        "Small-account feasibility is evaluated before strategy eligibility and execution planning.",
        "Risk is capped before any approval or execution boundary; allow_submit remains false.",
    ]

    symbols = _clean_symbols(request.usable_symbols or request.symbols)
    selected_symbol = str(request.selected_symbol).strip().upper() if request.selected_symbol else None
    rejected_symbols: list[str] = []
    feasible_symbols: list[str] = []

    if not selected_symbol:
        blockers.append("no_selected_symbol")
    elif selected_symbol not in symbols and symbols:
        warnings.append("selected_symbol_not_in_usable_symbols")

    if request.latest_price is None:
        blockers.append("missing_latest_price")
    elif request.latest_price < request.min_price:
        blockers.append("latest_price_below_minimum")
    elif request.latest_price > request.max_price:
        warnings.append("latest_price_above_small_account_preferred_max")

    if request.planned_risk_dollars is not None and float(request.planned_risk_dollars) > max_risk_dollars:
        blockers.append("planned_risk_exceeds_small_account_limit")

    if request.spread_bps is not None and float(request.spread_bps) > request.max_spread_bps:
        blockers.append("spread_too_wide_for_small_account")

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
        warnings.append("non_real_data_used_for_small_account_feasibility")

    if str(request.persistence_status or "").lower() in {"memory_fallback", "unavailable"}:
        warnings.append("persistence_not_confirmed_for_small_account_feasibility")

    if selected_symbol:
        if blockers:
            rejected_symbols.append(selected_symbol)
        else:
            feasible_symbols.append(selected_symbol)

    if blockers:
        decision: Literal["pass", "degraded", "blocked"] = "blocked"
        next_agent = None
    elif warnings:
        decision = "degraded"
        next_agent = "strategy_eligibility_agent"
    else:
        decision = "pass"
        next_agent = "strategy_eligibility_agent"

    return SmallAccountFeasibilityResponse(
        decision=decision,
        account_equity=round(account_equity, 2),
        max_risk_dollars=max_risk_dollars,
        max_daily_loss_dollars=max_daily_loss_dollars,
        feasible_symbols=feasible_symbols,
        rejected_symbols=rejected_symbols,
        sizing_notes=sizing_notes,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
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
        "status": "ready",
        "blockers": [],
        "warnings": [],
    }
