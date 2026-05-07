from __future__ import annotations

from typing import Any

from app.services.market_condition_scanner_service import MarketScannerRequest, run_market_condition_scan


def scan_market_condition(*, symbols: list[str], source: str = "auto") -> dict[str, Any]:
    """Call existing market scanner and normalize into market condition context."""
    req = MarketScannerRequest(
        strategy_key="multi_factor",
        symbols=[s.upper() for s in (symbols or [])],
        data_source=source,
        auto_run=False,
        trigger_type="manual",
        trigger_workflow=False,
        use_latest_watchlist=False,
    )
    resp = run_market_condition_scan(req)
    matched = [s.model_dump() for s in resp.matched_signals]
    regime = "risk_on" if matched else "unknown"
    return {
        "market_context": {
            "regime": regime,
            "volatility_state": "normal",
            "liquidity_state": "good" if matched else "unknown",
            "trend_state": "unknown",
            "disorder_state": "unknown",
            "matched_signals": matched,
            "recommended_workflow_key": resp.recommended_workflow_key,
            "should_trigger_workflow": bool(resp.should_trigger_workflow),
        },
        "scan_run_id": resp.run_id,
        "next_action": resp.next_action,
    }

