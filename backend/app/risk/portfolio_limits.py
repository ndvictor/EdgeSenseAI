"""Portfolio exposure limits (uses broker-reported positions when available)."""

from __future__ import annotations

from typing import Any


def symbol_exposure_pct(positions: list[dict[str, Any]], symbol: str, equity: float | None) -> float | None:
    if not equity or equity <= 0:
        return None
    sym = symbol.upper()
    for p in positions:
        if str(p.get("symbol", "")).upper() != sym:
            continue
        mv = p.get("market_value")
        if mv is None:
            qty = p.get("qty") or p.get("quantity")
            price = p.get("current_price")
            try:
                mv = float(qty or 0) * float(price or 0)
            except (TypeError, ValueError):
                mv = None
        if mv is not None:
            try:
                return (float(mv) / float(equity)) * 100.0
            except (TypeError, ValueError):
                return None
    return 0.0


def count_open_positions(positions: list[Any]) -> int:
    return len(positions or [])
