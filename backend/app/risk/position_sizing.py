"""Volatility-aware position sizing helpers (deterministic, no fake account values)."""

from __future__ import annotations


def max_shares_for_risk_dollars(
    entry_price: float,
    stop_price: float,
    max_risk_dollars: float,
    side: str,
) -> float | None:
    if entry_price <= 0 or max_risk_dollars <= 0:
        return None
    risk_per_share = abs(entry_price - stop_price)
    if risk_per_share <= 0:
        return None
    return max_risk_dollars / risk_per_share


def order_notional(quantity: float | None, price: float | None, notional: float | None) -> float | None:
    if notional is not None and notional > 0:
        return notional
    if quantity is not None and price is not None and quantity > 0 and price > 0:
        return quantity * price
    return None
