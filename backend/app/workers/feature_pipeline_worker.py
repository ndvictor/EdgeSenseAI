from __future__ import annotations

import os
from typing import Any

from app.services.feature_store_service import FeatureStoreRunRequest, get_feature_row_persistence_status, run_feature_store_pipeline
from app.services.worker_output_store import get_latest_market_snapshots, record_worker_status, save_feature_rows
from app.workers.common import clean_symbols, get_worker_run_id, print_summary, require_production_data_policy, setup_worker_logging


def _symbols(limit: int) -> list[str]:
    return clean_symbols([row.get("symbol") for row in get_latest_market_snapshots(limit, production_scanner_chain_only=True)])


def _spread_bps(snapshot: dict[str, Any]) -> float | None:
    if snapshot.get("spread_bps") is not None:
        return float(snapshot["spread_bps"])
    if snapshot.get("bid_ask_spread") is not None:
        return float(snapshot["bid_ask_spread"]) * 100.0
    if snapshot.get("spread_percent") is not None:
        return float(snapshot["spread_percent"]) * 100.0
    price = snapshot.get("price")
    bid = snapshot.get("bid")
    ask = snapshot.get("ask")
    if price is None or bid is None or ask is None:
        return None
    try:
        return ((float(ask) - float(bid)) / float(price)) * 10_000.0
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _relative_volume(snapshot: dict[str, Any]) -> float | None:
    if snapshot.get("relative_volume") is not None:
        return float(snapshot["relative_volume"])
    volume = snapshot.get("volume")
    average = snapshot.get("average_volume") or snapshot.get("avg_volume")
    if volume is None or average is None:
        return None
    try:
        return float(volume) / float(average)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _alpha_feature_row(symbol: str, snapshot: dict[str, Any], response_row: Any | None = None) -> dict[str, Any]:
    price = snapshot.get("price") or snapshot.get("last_price") or snapshot.get("close")
    vwap = snapshot.get("vwap")
    price_above_vwap = None
    if price is not None and vwap is not None:
        try:
            price_above_vwap = float(price) > float(vwap)
        except (TypeError, ValueError):
            price_above_vwap = None
    return {
        "symbol": symbol,
        "last_price": price,
        "volume": snapshot.get("volume"),
        "avg_volume": snapshot.get("average_volume") or snapshot.get("avg_volume"),
        "relative_volume": _relative_volume(snapshot),
        "day_change_pct": snapshot.get("change_percent") or snapshot.get("day_change_pct"),
        "spread_bps": _spread_bps(snapshot),
        "vwap": vwap,
        "price_above_vwap": price_above_vwap,
        "high_of_day": snapshot.get("day_high") or snapshot.get("high_of_day"),
        "low_of_day": snapshot.get("day_low") or snapshot.get("low_of_day"),
        "trend_score": getattr(response_row, "momentum_score", None),
        "liquidity_score": getattr(response_row, "liquidity_score", None),
        "volatility_score": getattr(response_row, "volatility_score", None),
        "session_state": snapshot.get("session_state"),
        "source": "feature_store",
        "provider_name": snapshot.get("provider"),
        "data_quality": snapshot.get("data_quality"),
        "non_real": bool(snapshot.get("is_non_real")),
        "synthetic": bool(snapshot.get("synthetic") or snapshot.get("spread_synthetic")),
    }


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
            "status": "missing_features",
            "recommendation_status": "missing_features",
            "symbols": [],
            "feature_rows": [],
            "feature_row_count": 0,
            "missing_features": ["no_ingested_scanner_snapshots"],
            "persistence_status": "unavailable",
            "blockers": ["no_ingested_scanner_snapshots"],
            "warnings": [],
        }
        record_worker_status(
            worker="feature-pipeline-worker",
            status="missing_features",
            worker_run_id=worker_run_id,
            provider=provider,
            symbols=[],
            feature_rows=[],
            feature_row_count=0,
            missing_features=["no_ingested_scanner_snapshots"],
            warnings=[],
            blockers=["no_ingested_scanner_snapshots"],
        )
        print_summary(summary)
        return summary

    latest_snapshots = {str(row.get("symbol", "")).upper(): row for row in get_latest_market_snapshots(limit, production_scanner_chain_only=True)}
    feature_row_count = 0
    missing_features: list[str] = []
    persistence_statuses: list[str] = []
    blockers: list[str] = []
    warnings: list[str] = []
    alpha_feature_rows: list[dict[str, Any]] = []
    for symbol in symbols:
        snapshot = latest_snapshots.get(symbol) or {}
        if snapshot.get("price") is None or snapshot.get("is_non_real") or snapshot.get("data_quality") in {"unavailable", "not_configured"}:
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
            alpha_feature_rows.append(_alpha_feature_row(symbol, snapshot, response.row))
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
    save_feature_rows(
        worker_run_id=worker_run_id,
        provider_name=provider,
        feature_rows=alpha_feature_rows,
        status="features_available" if feature_row_count else "missing_features",
        warnings=sorted(set(warnings)),
        blockers=sorted(set(blockers)),
    )
    print_summary(summary)
    return summary


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
