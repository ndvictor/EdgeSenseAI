from __future__ import annotations

import os
from typing import Any

from app.services.market_data_service import MarketDataService
from app.services.worker_output_store import get_latest_scanner_candidates, record_worker_status, save_market_snapshots
from app.workers.common import clean_symbols, get_worker_run_id, print_summary, require_production_data_policy, setup_worker_logging


def _symbols_to_ingest(limit: int) -> list[str]:
    return clean_symbols([row.get("symbol") for row in get_latest_scanner_candidates(limit)])


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
            "status": "no_symbols_to_ingest",
            "recommendation_status": "no_symbols_to_ingest",
            "symbols": [],
            "attempted_symbols": [],
            "successful_symbols": [],
            "failed_symbols": [],
            "snapshot_count": 0,
            "provider_status": {},
            "persistence_status": "no_snapshot_persistence_service_available",
            "missing_fields": {},
            "blockers": ["no_scanner_candidates"],
            "warnings": [],
        }
        record_worker_status(
            worker="data-ingestion-worker",
            status="no_symbols_to_ingest",
            worker_run_id=worker_run_id,
            provider=provider,
            symbols=[],
            attempted_symbols=[],
            successful_symbols=[],
            failed_symbols=[],
            snapshot_count=0,
            warnings=[],
            blockers=["no_scanner_candidates"],
        )
        print_summary(summary)
        return summary

    service = MarketDataService()
    successful: list[str] = []
    failed: list[str] = []
    provider_status: dict[str, Any] = {}
    missing_fields: dict[str, list[str]] = {}
    persisted_snapshots: list[dict[str, Any]] = []
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
        if snapshot.get("price") is not None and not snapshot.get("is_non_real") and snapshot.get("data_quality") not in {"unavailable", "not_configured"}:
            successful.append(symbol)
            persisted_snapshots.append({**snapshot, "symbol": symbol})
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
    status = "data_available" if successful else "data_unavailable"
    save_market_snapshots(
        worker_run_id=worker_run_id,
        provider_name=provider,
        snapshots=persisted_snapshots,
        status=status,
        warnings=[],
        blockers=[] if successful else ["provider_data_unavailable"],
    )
    summary["persistence_status"] = "postgres_or_memory_worker_output_store"
    print_summary(summary)
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
