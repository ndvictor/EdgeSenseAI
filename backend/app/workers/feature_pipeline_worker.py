from __future__ import annotations

import os
from typing import Any

from app.services.candidate_universe_service import list_candidates
from app.services.feature_store_service import FeatureStoreRunRequest, get_feature_row_persistence_status, run_feature_store_pipeline
from app.services.market_data_service import MarketDataService
from app.services.universe_selection_service import get_latest_universe_selection
from app.workers.common import clean_symbols, get_worker_run_id, print_summary, require_production_data_policy, setup_worker_logging


def _symbols(limit: int) -> list[str]:
    env_symbols = clean_symbols((os.environ.get("WORKER_SYMBOLS") or "").split(","))
    if env_symbols:
        return env_symbols[:limit]
    candidate_symbols = clean_symbols([c.symbol for c in list_candidates(status="active")[:limit]])
    if candidate_symbols:
        return candidate_symbols
    latest = get_latest_universe_selection()
    if latest is None:
        return []
    return clean_symbols([c.symbol for c in (latest.selected_watchlist or latest.ranked_candidates or [])[:limit]])


def run() -> dict[str, Any]:
    setup_worker_logging()
    require_production_data_policy()
    worker_run_id = get_worker_run_id("feature-pipeline-worker")
    limit = max(1, int(os.environ.get("WORKER_MAX_CANDIDATES") or "25"))
    provider = os.environ.get("MARKET_DATA_PROVIDER", "yfinance")
    symbols = _symbols(limit)
    if not symbols:
        summary = {
            "worker": "feature-pipeline-worker",
            "worker_run_id": worker_run_id,
            "recommendation_status": "missing_features",
            "feature_row_count": 0,
            "missing_features": ["no_symbols_available"],
            "persistence_status": "unavailable",
            "blockers": [],
            "warnings": [],
        }
        print_summary(summary)
        return summary

    market_data = MarketDataService()
    feature_row_count = 0
    missing_features: list[str] = []
    persistence_statuses: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    for symbol in symbols:
        snapshot = market_data.get_market_snapshot(symbol, source=provider)
        if snapshot.get("price") is None or snapshot.get("is_mock") or snapshot.get("data_quality") in {"unavailable", "not_configured"}:
            missing_features.append(symbol)
            continue
        try:
            response = run_feature_store_pipeline(
                FeatureStoreRunRequest(symbol=symbol, asset_class="stock", horizon="day_trade", source=provider)
            )
        except Exception as exc:
            missing_features.append(symbol)
            warnings.append(f"{symbol}:feature_pipeline_failed:{exc}")
            continue
        if response.quality_report.quality_status in {"pass", "warn"}:
            feature_row_count += 1
            persisted = get_feature_row_persistence_status(response.row.id)
            persistence_statuses.append("persisted" if persisted.get("persisted") else str(persisted.get("data_source") or response.storage_mode))
            warnings.extend(response.warnings or [])
        else:
            missing_features.append(symbol)
            blockers.extend(response.quality_report.blockers or [])
            warnings.extend(response.quality_report.warnings or [])

    summary = {
        "worker": "feature-pipeline-worker",
        "worker_run_id": worker_run_id,
        "recommendation_status": "features_available" if feature_row_count else "missing_features",
        "feature_row_count": feature_row_count,
        "missing_features": missing_features,
        "persistence_status": "persisted" if "persisted" in persistence_statuses else (persistence_statuses[0] if persistence_statuses else "unavailable"),
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
    }
    print_summary(summary)
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
