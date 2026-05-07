from __future__ import annotations

from typing import Any

from app.services.candidate_universe_service import list_candidates


def build_watchlist(*, asset_class: str, horizon: str, max_symbols: int = 10) -> dict[str, Any]:
    """Build a workflow-ready watchlist from candidate universe (reuses existing service)."""
    candidates = list_candidates(status="active")
    filtered = [c for c in candidates if c.asset_class == asset_class and c.horizon in {horizon, "day_trade", "day_trading"}]
    filtered = sorted(filtered, key=lambda c: (-float(c.priority_score or 0), str(c.symbol)))
    symbols = [c.symbol for c in filtered[:max_symbols]]
    ranked_candidates = [{"symbol": c.symbol, "priority_score": c.priority_score, "source_type": c.source_type} for c in filtered[:max_symbols]]
    return {
        "symbols": symbols,
        "ranked_candidates": ranked_candidates,
        "source_breakdown": {"candidate_universe": len(symbols)},
        "selected_candidate": symbols[0] if symbols else None,
        "next_action": "Proceed to strategy selection." if symbols else "No candidates available. Run market scanner promotion or add manual candidates.",
    }

