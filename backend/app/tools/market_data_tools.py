from typing import Any

from app.services.market_data_service import MarketDataService


_MARKET_DATA = MarketDataService()


def classify_market_data_source(snapshot: dict[str, Any]) -> str:
    if snapshot.get("is_non_real"):
        return "source_blocked"
    if snapshot.get("data_quality") in {"real", "delayed", "partial"} and snapshot.get("provider"):
        return "source_backed"
    return "source_unavailable"


def get_safe_market_snapshot(symbol: str, source: str = "auto") -> dict[str, Any]:
    snapshot = _MARKET_DATA.get_market_snapshot(symbol.upper(), source=source)
    snapshot["data_source"] = classify_market_data_source(snapshot)
    return snapshot


def get_safe_market_snapshots(symbols: list[str], source: str = "auto") -> dict[str, Any]:
    snapshots = [get_safe_market_snapshot(symbol, source=source) for symbol in symbols]
    sources = {snapshot.get("data_source", "source_unavailable") for snapshot in snapshots}
    if "source_backed" in sources:
        data_source = "source_backed"
    elif "source_blocked" in sources:
        data_source = "source_blocked"
    else:
        data_source = "source_unavailable"
    warnings = [
        f"{snapshot.get('symbol')}: {snapshot.get('error')}"
        for snapshot in snapshots
        if snapshot.get("error")
    ]
    return {
        "symbols": [symbol.upper() for symbol in symbols],
        "snapshots": snapshots,
        "data_source": data_source,
        "warnings": warnings,
    }


def summarize_market_inputs(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    usable = [
        snapshot
        for snapshot in snapshots
        if snapshot.get("price") is not None and snapshot.get("data_quality") not in {"unavailable", "not_configured"}
    ]
    return {
        "symbols_requested": [snapshot.get("symbol") for snapshot in snapshots],
        "usable_symbols": [snapshot.get("symbol") for snapshot in usable],
        "unavailable_symbols": [
            snapshot.get("symbol")
            for snapshot in snapshots
            if snapshot.get("data_quality") in {"unavailable", "not_configured"}
        ],
        "providers": sorted({str(snapshot.get("provider")) for snapshot in usable if snapshot.get("provider")}),
    }
