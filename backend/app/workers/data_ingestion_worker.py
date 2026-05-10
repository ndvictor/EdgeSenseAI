from __future__ import annotations

import os
from typing import Any

from app.services.candidate_universe_service import list_candidates
from app.services.market_data_service import MarketDataService
from app.services.universe_selection_service import get_latest_universe_selection
from app.workers.common import clean_symbols, get_worker_run_id, print_summary, require_production_data_policy, setup_worker_logging


def _env_symbols() -> list[str]:
    return clean_symbols((os.environ.get("WORKER_SYMBOLS") or "").split(","))


def _candidate_symbols(limit: int) -> list[str]:
    return clean_symbols([c.symbol for c in list_candidates(status="active")[:limit]])


def _latest_watchlist_symbols(limit: int) -> list[str]:
    latest = get_latest_universe_selection()
    if latest is None:
        return []
    return clean_symbols([c.symbol for c in (latest.selected_watchlist or latest.ranked_candidates or [])[:limit]])


def _symbols_to_ingest(limit: int) -> list[str]:
    symbols = _env_symbols()
    if symbols:
        return symbols[:limit]
    symbols = _candidate_symbols(limit)
    if symbols:
        return symbols
    return _latest_watchlist_symbols(limit)


def run() -> dict[str, Any]:
    setup_worker_logging()
    require_production_data_policy()
    worker_run_id = get_worker_run_id("data-ingestion-worker")
    limit = max(1, int(os.environ.get("WORKER_MAX_CANDIDATES") or "25"))
    provider = os.environ.get("MARKET_DATA_PROVIDER", "yfinance")
    symbols = _symbols_to_ingest(limit)
    if not symbols:
        summary = {
            "worker": "data-ingestion-worker",
            "worker_run_id": worker_run_id,
            "recommendation_status": "no_symbols_to_ingest",
            "attempted_symbols": [],
            "successful_symbols": [],
            "failed_symbols": [],
            "provider_status": {},
            "persistence_status": "no_snapshot_persistence_service_available",
            "missing_fields": {},
            "blockers": [],
            "warnings": [],
        }
        print_summary(summary)
        return summary

    service = MarketDataService()
    successful: list[str] = []
    failed: list[str] = []
    provider_status: dict[str, Any] = {}
    missing_fields: dict[str, list[str]] = {}
    for symbol in symbols:
        snapshot = service.get_market_snapshot(symbol, source=provider)
        provider_status[symbol] = {
            "provider": snapshot.get("provider"),
            "data_quality": snapshot.get("data_quality"),
            "error": snapshot.get("error"),
        }
        missing = list(snapshot.get("unavailable_fields") or snapshot.get("not_configured_fields") or [])
        if missing:
            missing_fields[symbol] = missing
        if snapshot.get("price") is not None and not snapshot.get("is_mock") and snapshot.get("data_quality") not in {"unavailable", "not_configured"}:
            successful.append(symbol)
        else:
            failed.append(symbol)

    summary = {
        "worker": "data-ingestion-worker",
        "worker_run_id": worker_run_id,
        "recommendation_status": "data_available" if successful else "data_unavailable",
        "attempted_symbols": symbols,
        "successful_symbols": successful,
        "failed_symbols": failed,
        "provider_status": provider_status,
        "persistence_status": "no_snapshot_persistence_service_available",
        "missing_fields": missing_fields,
        "blockers": [] if successful else ["provider_data_unavailable"],
        "warnings": [],
    }
    print_summary(summary)
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
