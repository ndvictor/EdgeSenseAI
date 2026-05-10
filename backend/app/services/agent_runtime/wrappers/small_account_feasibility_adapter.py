from __future__ import annotations

from typing import Any

from app.services.fractional_sizing_service import (
    MAX_DAILY_LOSS_PCT,
    MAX_POSITION_NOTIONAL_PCT,
    MAX_RISK_PER_TRADE_PCT,
)
from app.services.small_account_feasibility.service import SmallAccountFeasibilityRequest, evaluate_small_account_feasibility


def _percent_or_none(value: Any) -> float | None:
    """Pass through a human percent value (``0.5`` = 0.5%, ``100`` = 100%).

    The deterministic fractional sizing service converts percent to a decimal
    fraction exactly once. Adapters must not pre-divide by 100.
    """
    if value is None:
        return None
    try:
        pct = float(value)
    except (TypeError, ValueError):
        return None
    if pct <= 0:
        return None
    return pct


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _first_row_for_symbol(rows: Any, symbol: str) -> dict[str, Any]:
    if not isinstance(rows, list) or not symbol:
        return {}
    u = symbol.strip().upper()
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
        if sym == u:
            return row
    return {}


def merge_small_account_feasibility_context(inputs: dict[str, Any]) -> dict[str, Any]:
    """Prefer Alpha recommendation + feature row liquidity; never rewrite Alpha into watchlist seeds."""
    merged: dict[str, Any] = dict(inputs)
    ar = merged.get("alpha_recommendation")
    if not isinstance(ar, dict):
        ar = {}

    sym = (
        str(
            merged.get("alpha_selected_symbol")
            or merged.get("selected_symbol")
            or merged.get("symbol")
            or ar.get("symbol")
            or ""
        )
        .strip()
        .upper()
        or None
    )
    if sym:
        merged["selected_symbol"] = sym

    ep = ar.get("entry_plan")
    ep_dict = ep if isinstance(ep, dict) else {}

    if ep_dict.get("entry") is not None:
        merged["entry"] = merged.get("entry") if merged.get("entry") is not None else _float_or_none(ep_dict.get("entry"))
    if ep_dict.get("stop") is not None:
        merged["stop"] = merged.get("stop") if merged.get("stop") is not None else _float_or_none(ep_dict.get("stop"))
    if ep_dict.get("target") is not None:
        merged["target"] = merged.get("target") if merged.get("target") is not None else _float_or_none(ep_dict.get("target"))
    if ep_dict.get("expected_r") is not None:
        merged["expected_r"] = merged.get("expected_r") if merged.get("expected_r") is not None else _float_or_none(ep_dict.get("expected_r"))
    if merged.get("expected_r") is None and ar.get("predicted_return_r") is not None:
        merged["expected_r"] = _float_or_none(ar.get("predicted_return_r"))
    if ep_dict.get("risk_per_share") is not None and merged.get("risk_per_share") is None:
        merged["risk_per_share"] = _float_or_none(ep_dict.get("risk_per_share"))

    if merged.get("latest_price") is None:
        merged["latest_price"] = _float_or_none(ar.get("latest_price")) or _float_or_none(ep_dict.get("entry"))

    for key in (
        "predicted_return_r",
        "predicted_expected_value_r",
        "predicted_win_probability",
        "final_score",
        "confidence",
        "setup_type",
        "strategy_key",
        "provider_name",
        "data_quality",
        "candidate_source",
        "market_session",
    ):
        if ar.get(key) is not None and merged.get(key) is None:
            merged[key] = ar.get(key)

    for key in ("spread_bps", "dollar_volume", "volume", "avg_volume", "relative_volume", "avg_dollar_volume"):
        if ar.get(key) is not None and merged.get(key) is None:
            merged[key] = ar.get(key)

    fr = _first_row_for_symbol(merged.get("feature_rows"), sym or "")
    if not fr:
        fr = _first_row_for_symbol(merged.get("scanner_candidates"), sym or "")

    if fr:
        if merged.get("spread_bps") is None:
            merged["spread_bps"] = _float_or_none(fr.get("spread_bps"))
        if merged.get("volume") is None:
            merged["volume"] = _float_or_none(fr.get("volume"))
        if merged.get("avg_volume") is None:
            merged["avg_volume"] = _float_or_none(fr.get("avg_volume") or fr.get("average_volume"))
        if merged.get("relative_volume") is None:
            merged["relative_volume"] = _float_or_none(fr.get("relative_volume"))
        if merged.get("dollar_volume") is None:
            merged["dollar_volume"] = _float_or_none(fr.get("dollar_volume"))
        if merged.get("avg_dollar_volume") is None and merged.get("dollar_volume") is not None:
            merged["avg_dollar_volume"] = merged.get("dollar_volume")
        elif merged.get("avg_dollar_volume") is None:
            lp = _float_or_none(fr.get("last_price") or fr.get("price"))
            vol = _float_or_none(fr.get("volume"))
            if lp is not None and vol is not None:
                merged["avg_dollar_volume"] = round(lp * vol, 2)
        if merged.get("market_session") is None:
            merged["market_session"] = fr.get("session_state") or fr.get("market_session")
        if merged.get("provider_name") is None:
            merged["provider_name"] = fr.get("provider_name") or fr.get("provider")
        if merged.get("data_quality") is None:
            merged["data_quality"] = fr.get("data_quality")
    if merged.get("candidate_source") is None and inputs.get("candidate_source"):
        merged["candidate_source"] = inputs.get("candidate_source")

    mode = str(merged.get("mode", "") or "").lower()
    if merged.get("execution_mode") in (None, "", "plan_only") and mode == "paper_first":
        merged["execution_mode"] = "paper"

    gates = inputs.get("account_owner_gates")
    if isinstance(gates, dict):
        if inputs.get("paper_trading_enabled") is None and "paper_trading_enabled" in gates:
            merged["paper_trading_enabled"] = bool(gates["paper_trading_enabled"])
        if inputs.get("live_trading_enabled") is None and "live_trading_enabled" in gates:
            merged["live_trading_enabled"] = bool(gates["live_trading_enabled"])
        if inputs.get("broker_execution_enabled") is None and "broker_execution_enabled" in gates:
            merged["broker_execution_enabled"] = bool(gates["broker_execution_enabled"])

    return merged


def evaluate_small_account_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Adapter contract for the autonomous small-account feasibility stage."""
    merged = merge_small_account_feasibility_context(inputs)
    m = merged

    def _bool(key: str, default: bool) -> bool:
        if m.get(key) is None:
            return default
        return bool(m[key])

    req = SmallAccountFeasibilityRequest(
        # Real account state must come from the workflow input. We never
        # default account_equity / buying_power: missing values surface as
        # ``data_unavailable`` in the deterministic tool.
        account_equity=_float_or_none(m.get("account_equity")),
        buying_power=_float_or_none(m.get("buying_power")),
        fractional_trading_enabled=_bool("fractional_trading_enabled", True),
        risk_budget=_float_or_none(m.get("risk_budget")),
        symbols=[str(x) for x in (m.get("symbols") or []) if x],
        usable_symbols=[str(x) for x in (m.get("usable_symbols") or []) if x],
        selected_symbol=str(m.get("selected_symbol") or m.get("symbol") or "").upper() or None,
        entry=_float_or_none(m.get("entry")),
        stop=_float_or_none(m.get("stop")),
        target=_float_or_none(m.get("target")),
        latest_price=_float_or_none(m.get("latest_price")),
        expected_r=_float_or_none(m.get("expected_r")),
        predicted_expected_value_r=_float_or_none(m.get("predicted_expected_value_r")),
        spread_bps=_float_or_none(m.get("spread_bps")),
        slippage_bps=_float_or_none(m.get("slippage_bps")),
        avg_dollar_volume=_float_or_none(m.get("avg_dollar_volume")),
        dollar_volume=_float_or_none(m.get("dollar_volume")),
        volume=_float_or_none(m.get("volume")),
        market_session=str(m.get("market_session")) if m.get("market_session") is not None else None,
        execution_mode=str(m.get("execution_mode") or "plan_only"),
        paper_trading_enabled=_bool("paper_trading_enabled", True),
        live_trading_enabled=_bool("live_trading_enabled", False),
        broker_execution_enabled=_bool("broker_execution_enabled", False),
        allow_submit=_bool("allow_submit", False),
        planned_risk_dollars=_float_or_none(m.get("planned_risk_dollars")),
        open_positions=int(m.get("open_positions") or 0),
        day_trades_used=int(m.get("day_trades_used") or 0),
        current_daily_loss=float(m.get("current_daily_loss") or 0.0),
        proof_status=str(m.get("proof_status")) if m.get("proof_status") is not None else None,
        source_mode=str(m.get("source_mode")) if m.get("source_mode") is not None else None,
        using_non_real_data=bool(m.get("using_non_real_data", False)),
        persistence_status=str(m.get("persistence_status")) if m.get("persistence_status") is not None else None,
        # Owner risk policy uses **human percent values** end-to-end at the
        # boundary (``0.5`` = 0.5%, ``100`` = 100%). The deterministic sizing
        # service converts percent to a decimal fraction exactly once. Both
        # ``_pct`` and ``_percent`` keys are passed through unchanged.
        max_risk_per_trade_pct=(
            _percent_or_none(m.get("max_risk_per_trade_pct"))
            or _percent_or_none(m.get("max_risk_per_trade_percent"))
            or MAX_RISK_PER_TRADE_PCT
        ),
        max_risk_dollars=_float_or_none(m.get("max_risk_dollars")),
        max_daily_loss_pct=(
            _percent_or_none(m.get("max_daily_loss_pct"))
            or _percent_or_none(m.get("max_daily_loss_percent"))
            or MAX_DAILY_LOSS_PCT
        ),
        max_position_notional_pct=(
            _percent_or_none(m.get("max_position_notional_pct"))
            or _percent_or_none(m.get("max_position_notional_percent"))
            or MAX_POSITION_NOTIONAL_PCT
        ),
        max_position_notional=_float_or_none(m.get("max_position_notional")),
        max_open_positions=int(m.get("max_open_positions") or 1),
        max_trades_per_day=int(m.get("max_trades_per_day") or 3),
        min_order_notional=float(m.get("min_order_notional") or 1.0),
        min_expected_r=float(m.get("min_expected_r_after_costs") or m.get("min_expected_r") or 0.25),
        max_liquidity_participation_pct=float(m.get("max_liquidity_participation_pct") or 0.05),
        min_predicted_expected_value_r=_float_or_none(m.get("min_predicted_expected_value_r")),
        strategy_key=str(m.get("strategy_key")) if m.get("strategy_key") is not None else None,
        setup_type=str(m.get("setup_type")) if m.get("setup_type") is not None else None,
        candidate_source=str(m.get("candidate_source")) if m.get("candidate_source") is not None else None,
        provider_name=str(m.get("provider_name")) if m.get("provider_name") is not None else None,
        data_quality=str(m.get("data_quality")) if m.get("data_quality") is not None else None,
    )
    result = evaluate_small_account_feasibility(req).model_dump()
    if isinstance(m.get("alpha_recommendation"), dict):
        result["alpha_recommendation"] = dict(m["alpha_recommendation"])
    if m.get("alpha_selected_symbol") is not None:
        result["alpha_selected_symbol"] = str(m.get("alpha_selected_symbol")).upper()
    if m.get("alpha_strategy_key") is not None:
        result["alpha_strategy_key"] = m.get("alpha_strategy_key")
    result["selected_symbol"] = req.selected_symbol
    result["symbol"] = req.selected_symbol
    return result
