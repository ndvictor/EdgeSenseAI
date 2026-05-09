from __future__ import annotations

from typing import Any

from app.services.small_account_feasibility.service import SmallAccountFeasibilityRequest, evaluate_small_account_feasibility


def evaluate_small_account_inputs(inputs: dict[str, Any]) -> dict[str, Any]:
    """Adapter contract for the autonomous small-account feasibility stage."""
    req = SmallAccountFeasibilityRequest(
        account_equity=float(inputs.get("account_equity") or 1000.0),
        symbols=[str(x) for x in (inputs.get("symbols") or []) if x],
        usable_symbols=[str(x) for x in (inputs.get("usable_symbols") or []) if x],
        selected_symbol=str(inputs.get("selected_symbol") or inputs.get("symbol") or "").upper() or None,
        latest_price=float(inputs["latest_price"]) if inputs.get("latest_price") is not None else None,
        spread_bps=float(inputs["spread_bps"]) if inputs.get("spread_bps") is not None else None,
        avg_dollar_volume=float(inputs["avg_dollar_volume"]) if inputs.get("avg_dollar_volume") is not None else None,
        planned_risk_dollars=float(inputs["planned_risk_dollars"]) if inputs.get("planned_risk_dollars") is not None else None,
        open_positions=int(inputs.get("open_positions") or 0),
        day_trades_used=int(inputs.get("day_trades_used") or 0),
        proof_status=str(inputs.get("proof_status")) if inputs.get("proof_status") is not None else None,
        source_mode=str(inputs.get("source_mode")) if inputs.get("source_mode") is not None else None,
        using_mock_data=bool(inputs.get("using_mock_data", False)),
        persistence_status=str(inputs.get("persistence_status")) if inputs.get("persistence_status") is not None else None,
        max_risk_per_trade_pct=float(inputs.get("max_risk_per_trade_percent") or inputs.get("max_risk_per_trade_pct") or 0.005),
        max_daily_loss_pct=float(inputs.get("max_daily_loss_percent") or inputs.get("max_daily_loss_pct") or 0.015),
        max_open_positions=int(inputs.get("max_open_positions") or 1),
        max_trades_per_day=int(inputs.get("max_trades_per_day") or 3),
    )
    return evaluate_small_account_feasibility(req).model_dump()
