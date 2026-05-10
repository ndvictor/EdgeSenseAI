from __future__ import annotations

from typing import Any

from app.services.feature_store_service import FeatureStoreRunRequest, get_feature_row_persistence_status, run_feature_store_pipeline


def _provider_source_for(source_mode: str) -> str:
    source = (source_mode or "auto").lower().strip()
    if source == "mock":
        return "mock"
    if source in {"runtime", "manual", "candidate", "auto"}:
        return "auto"
    return source


def _feature_row_from_response(resp: Any, *, source_mode: str) -> dict[str, Any]:
    row = resp.row
    snap = resp.normalized_snapshot
    spread_bps = None
    if snap.spread_percent is not None:
        spread_bps = float(snap.spread_percent) * 100
    return {
        "symbol": row.ticker,
        "timestamp": snap.timestamp.isoformat(),
        "last_price": snap.price,
        "volume": snap.volume,
        "day_change_pct": snap.change_percent,
        "relative_volume": snap.relative_volume,
        "spread_bps": spread_bps,
        "source_mode": source_mode,
        "provider_name": snap.provider or "unknown",
        "feature_row_id": row.id,
        "data_quality": row.data_quality,
    }


def _status_from_persistence(resp: Any) -> str:
    persisted = get_feature_row_persistence_status(resp.row.id)
    if persisted.get("persisted"):
        return "persisted"
    if persisted.get("data_source") == "in_memory_fallback" or resp.storage_mode == "in_memory":
        return "memory_fallback"
    return "unavailable"


def _provider_warnings(symbol: str, statuses: list[dict[str, Any]]) -> list[str]:
    warnings: list[str] = []
    if len(statuses) > 1:
        failed = [s for s in statuses[:-1] if s.get("data_quality") in {"unavailable", "not_configured"} or s.get("error")]
        if failed:
            warnings.append(f"{symbol}: provider fallback used after {', '.join(str(s.get('provider')) for s in failed)} issue")
    for status in statuses:
        if status.get("error"):
            warnings.append(f"{symbol}: provider {status.get('provider')} warning: {status.get('error')}")
    return warnings


def evaluate_data_readiness(*, symbols: list[str], asset_class: str, horizon: str, source: str = "auto") -> dict[str, Any]:
    """Best-effort deterministic data readiness check.

    Uses existing feature-store pipeline (which itself is source-backed or mock-backed).
    Never triggers execution/broker calls; safe for v1.
    """
    source_mode = (source or "auto").lower().strip()
    provider_source = _provider_source_for(source_mode)
    blockers: list[str] = []
    warnings: list[str] = []
    provider_status: dict[str, Any] = {}
    feature_rows: list[dict[str, Any]] = []
    latest_snapshots: list[dict[str, Any]] = []
    usable_symbols: list[str] = []
    rejected_symbols: list[str] = []
    persistence_statuses: list[str] = []
    freshness_statuses: list[str] = []

    if not symbols:
        return {
            "decision": "discovery",
            "discovery_mode": True,
            "provider_status": {},
            "provider_name": "unknown",
            "source_mode": source_mode,
            "using_mock_data": False,
            "symbols": [],
            "usable_symbols": [],
            "rejected_symbols": [],
            "symbol_count": 0,
            "latest_snapshot_status": "missing",
            "latest_snapshot_count": 0,
            "feature_store_status": "unavailable",
            "feature_row_count": 0,
            "persistence_status": "unavailable",
            "freshness_status": "unknown",
            "kafka_status": "configured_optional_not_active",
            "blockers": [],
            "warnings": ["no_manual_symbols_using_scanner_discovery"],
            "artifacts": {"provider_status": {}, "feature_rows": [], "latest_snapshots": [], "kafka_status": "configured_optional_not_active"},
            "next_agent": "watchlist_builder_agent",
            "next_action": "No manual symbols supplied; continue with provider-backed scanner/candidate discovery.",
        }

    clean_symbols = [str(sym).strip().upper() for sym in symbols[:5] if str(sym).strip()]
    if source_mode == "mock":
        warnings.append("mock_source_enabled_for_dry_run")
    elif source_mode != provider_source:
        warnings.append(f"source_mode_preserved:{source_mode}; provider_source={provider_source}")

    for sym in clean_symbols:
        try:
            resp = run_feature_store_pipeline(FeatureStoreRunRequest(symbol=sym, asset_class=asset_class, horizon=horizon, source=provider_source))
        except Exception as exc:
            rejected_symbols.append(sym)
            warnings.append(f"{sym}: provider pipeline error: {exc}")
            provider_status[sym] = {"provider": "unknown", "status": "error", "error": str(exc), "attempts": []}
            continue

        snap = resp.normalized_snapshot
        q = resp.quality_report
        warnings.extend(resp.warnings or [])
        attempts = resp.provider_statuses or [{"provider": snap.provider or "unknown", "data_quality": snap.data_quality, "error": None}]
        warnings.extend(_provider_warnings(sym, attempts))
        symbol_status = "usable" if q.quality_status in {"pass", "warn"} and snap.price is not None else "blocked"
        provider_status[sym.upper()] = {
            "provider": snap.provider or "unknown",
            "status": symbol_status,
            "is_mock": bool(snap.is_mock),
            "quality_status": q.quality_status,
            "freshness_status": q.freshness_status,
            "blockers": q.blockers or [],
            "warnings": q.warnings or [],
            "attempts": attempts,
        }
        freshness_statuses.append(q.freshness_status)
        if symbol_status == "usable":
            usable_symbols.append(sym)
            feature_rows.append(_feature_row_from_response(resp, source_mode=source_mode))
            latest_snapshots.append(
                {
                    "symbol": sym,
                    "timestamp": snap.timestamp.isoformat(),
                    "price": snap.price,
                    "last": snap.price,
                    "close": snap.price,
                    "volume": snap.volume,
                    "provider_name": snap.provider or "unknown",
                    "source_mode": source_mode,
                    "using_mock_data": bool(snap.is_mock),
                }
            )
            persistence_statuses.append(_status_from_persistence(resp))
            if q.quality_status == "warn":
                warnings.extend(q.warnings or [])
        else:
            rejected_symbols.append(sym)
            warnings.extend(q.warnings or [])
            provider_blockers = q.blockers or ["no_price_snapshot_data"]
            warnings.append(f"{sym}: rejected by data readiness: {'; '.join(provider_blockers)}")

    if not usable_symbols:
        blockers.append("no_usable_symbols")
    if source_mode != "mock" and any(v.get("is_mock") for v in provider_status.values()):
        blockers.append("unexpected_mock_data_for_non_mock_source")

    if blockers:
        decision = "blocked"
    elif rejected_symbols or warnings:
        decision = "degraded"
    else:
        decision = "data_ready"

    provider_names = sorted({str(v.get("provider") or "unknown") for v in provider_status.values()})
    provider_name = provider_names[0] if len(provider_names) == 1 else ",".join(provider_names) if provider_names else "unknown"
    latest_snapshot_status = "available" if latest_snapshots else "missing"
    feature_store_status = "persisted" if persistence_statuses and all(x == "persisted" for x in persistence_statuses) else "memory_fallback" if feature_rows else "unavailable"
    persistence_status = "persisted" if "persisted" in persistence_statuses else "memory_fallback" if "memory_fallback" in persistence_statuses else "unavailable"
    freshness_status = "fresh" if freshness_statuses and all(x == "fresh" for x in freshness_statuses) else "stale" if "stale" in freshness_statuses else "unknown"
    kafka_status = "configured_optional_not_active"
    if kafka_status not in warnings:
        warnings.append("kafka_optional_not_active")

    return {
        "decision": decision,
        "provider_status": provider_status,
        "provider_name": provider_name,
        "source_mode": source_mode,
        "using_mock_data": source_mode == "mock" or any(bool(v.get("is_mock")) for v in provider_status.values()),
        "symbols": clean_symbols,
        "usable_symbols": usable_symbols,
        "rejected_symbols": rejected_symbols,
        "symbol_count": len(clean_symbols),
        "latest_snapshot_status": latest_snapshot_status,
        "latest_snapshot_count": len(latest_snapshots),
        "feature_store_status": feature_store_status,
        "feature_row_count": len(feature_rows),
        "persistence_status": persistence_status,
        "freshness_status": freshness_status,
        "kafka_status": kafka_status,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "artifacts": {
            "provider_status": provider_status,
            "source_mode": source_mode,
            "provider_source": provider_source,
            "feature_rows": feature_rows,
            "latest_snapshots": latest_snapshots,
            "kafka_status": kafka_status,
            "qlib_status": "optional_not_checked",
        },
        "next_agent": "market_condition_agent" if decision != "blocked" else None,
        "next_action": "Proceed to market condition scan." if decision != "blocked" else "Resolve hard data blockers before running the workflow.",
    }

