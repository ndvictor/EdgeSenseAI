from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.services.persistence_service import (
    get_persistence_status,
    list_feature_store_rows,
    list_market_scan_runs,
    save_feature_store_row,
    save_market_scan_run,
)


_MEMORY: dict[str, list[dict[str, Any]]] = {
    "statuses": [],
    "scanner_candidates": [],
    "market_snapshots": [],
    "feature_rows": [],
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean_symbol(value: Any) -> str | None:
    symbol = str(value or "").strip().upper()
    return symbol or None


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_mock_or_synthetic(row: dict[str, Any]) -> bool:
    return bool(row.get("mock") or row.get("is_mock") or row.get("using_mock_data") or row.get("synthetic") or row.get("synthetic_data_used") or row.get("spread_synthetic"))


def _worker_status_payload(*, worker: str, status: str, worker_run_id: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    now = _utc_now()
    return {
        "worker": worker,
        "worker_run_id": worker_run_id,
        "status": status,
        "created_at": now,
        "updated_at": now,
        **payload,
    }


def record_worker_status(*, worker: str, status: str, worker_run_id: str | None = None, **payload: Any) -> dict[str, Any]:
    record = _worker_status_payload(worker=worker, status=status, worker_run_id=worker_run_id, payload=payload)
    persisted = save_market_scan_run(
        {
            "run_id": worker_run_id or f"worker-status-{uuid4().hex[:12]}",
            "trigger_type": "scheduled",
            "strategy_key": f"worker_status:{worker}",
            "symbols": payload.get("symbols") or payload.get("selected_symbols") or payload.get("attempted_symbols") or [],
            "status": status,
            "data_source": payload.get("provider") or payload.get("data_source") or payload.get("source"),
            "matched_signals": payload.get("scanner_candidates") or [],
            "skipped_signals": payload.get("rejected_candidates") or [],
            "warnings": payload.get("warnings") or [],
            "errors": payload.get("blockers") or [],
            "worker": worker,
            "worker_status": status,
            **record,
        }
    )
    record["persistence_status"] = "postgres" if persisted.get("persisted") else "memory"
    record["persistence_warning"] = persisted.get("warning")
    _MEMORY["statuses"].append(record)
    return record


def save_scanner_candidates(*, worker_run_id: str, provider_name: str | None, candidates: list[dict[str, Any]], rejected_candidates: list[dict[str, Any]] | None = None, status: str = "candidate_selected", warnings: list[str] | None = None, blockers: list[str] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        symbol = _clean_symbol(candidate.get("symbol"))
        if not symbol or _is_mock_or_synthetic(candidate):
            continue
        row = {
            "symbol": symbol,
            "source": "scanner",
            "provider_name": candidate.get("provider_name") or candidate.get("provider") or provider_name,
            "last_price": _float_or_none(candidate.get("last_price") or candidate.get("price") or candidate.get("close")),
            "volume": _float_or_none(candidate.get("volume")),
            "avg_volume": _float_or_none(candidate.get("avg_volume") or candidate.get("average_volume")),
            "relative_volume": _float_or_none(candidate.get("relative_volume")),
            "spread_bps": _float_or_none(candidate.get("spread_bps")),
            "vwap": _float_or_none(candidate.get("vwap")),
            "price_above_vwap": candidate.get("price_above_vwap") if isinstance(candidate.get("price_above_vwap"), bool) else None,
            "session_state": candidate.get("session_state"),
            "score": _float_or_none(candidate.get("score") or candidate.get("confidence") or candidate.get("priority_score")),
            "rejection_reasons": list(candidate.get("rejection_reasons") or []),
            "worker_run_id": worker_run_id,
            "created_at": _utc_now(),
        }
        rows.append({k: v for k, v in row.items() if v is not None})
    _MEMORY["scanner_candidates"] = rows
    return record_worker_status(
        worker="market-scanner-worker",
        status=status,
        worker_run_id=worker_run_id,
        provider=provider_name,
        scanner_candidates=rows,
        rejected_candidates=rejected_candidates or [],
        selected_symbols=[row["symbol"] for row in rows],
        raw_candidate_count=len(candidates),
        filtered_candidate_count=len(rows),
        warnings=warnings or [],
        blockers=blockers or [],
    )


def save_market_snapshots(*, worker_run_id: str, provider_name: str | None, snapshots: list[dict[str, Any]], status: str = "data_available", warnings: list[str] | None = None, blockers: list[str] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for snapshot in snapshots:
        symbol = _clean_symbol(snapshot.get("symbol"))
        if not symbol or _is_mock_or_synthetic(snapshot):
            continue
        row = {**snapshot, "symbol": symbol, "ticker": symbol, "kind": "worker_market_snapshot", "source": "provider", "provider_name": snapshot.get("provider") or provider_name, "worker_run_id": worker_run_id, "created_at": _utc_now()}
        rows.append(row)
        save_feature_store_row(
            {
                "id": f"worker-snapshot-{worker_run_id}-{symbol}",
                "ticker": symbol,
                "asset_class": "stock",
                "horizon": "worker_snapshot",
                "data_quality": snapshot.get("data_quality") or status,
                "data_source": snapshot.get("provider") or provider_name or "provider",
                **row,
            }
        )
    _MEMORY["market_snapshots"] = rows
    return record_worker_status(
        worker="data-ingestion-worker",
        status=status,
        worker_run_id=worker_run_id,
        provider=provider_name,
        snapshots=rows,
        attempted_symbols=[_clean_symbol(s.get("symbol")) for s in snapshots if _clean_symbol(s.get("symbol"))],
        successful_symbols=[row["symbol"] for row in rows],
        snapshot_count=len(rows),
        warnings=warnings or [],
        blockers=blockers or [],
    )


def save_feature_rows(*, worker_run_id: str, provider_name: str | None, feature_rows: list[dict[str, Any]], status: str = "features_available", warnings: list[str] | None = None, blockers: list[str] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for feature in feature_rows:
        symbol = _clean_symbol(feature.get("symbol") or feature.get("ticker"))
        if not symbol or _is_mock_or_synthetic(feature):
            continue
        row = {**feature, "symbol": symbol, "ticker": symbol, "kind": "worker_feature_row", "source": feature.get("source") or "feature_store", "provider_name": feature.get("provider_name") or feature.get("provider") or provider_name, "worker_run_id": worker_run_id, "created_at": _utc_now()}
        rows.append(row)
        save_feature_store_row(
            {
                "id": f"worker-feature-{worker_run_id}-{symbol}",
                "ticker": symbol,
                "asset_class": "stock",
                "horizon": "worker_feature",
                "data_quality": feature.get("data_quality") or status,
                "data_source": row.get("provider_name") or "provider",
                **row,
            }
        )
    _MEMORY["feature_rows"] = rows
    return record_worker_status(
        worker="feature-pipeline-worker",
        status=status,
        worker_run_id=worker_run_id,
        provider=provider_name,
        feature_rows=rows,
        feature_row_count=len(rows),
        symbols=[row["symbol"] for row in rows],
        warnings=warnings or [],
        blockers=blockers or [],
    )


def _latest_worker_status_from_db(worker: str) -> dict[str, Any] | None:
    for row in list_market_scan_runs(100):
        metadata = row.get("metadata") or row.get("metadata_json") or {}
        if isinstance(metadata, dict) and metadata.get("worker") == worker:
            return metadata
    return None


def get_latest_worker_status(worker: str) -> dict[str, Any] | None:
    db_status = _latest_worker_status_from_db(worker)
    if db_status:
        return db_status
    for row in reversed(_MEMORY["statuses"]):
        if row.get("worker") == worker:
            return row
    return None


def get_latest_scanner_candidates(limit: int = 25) -> list[dict[str, Any]]:
    latest = get_latest_worker_status("market-scanner-worker")
    rows = latest.get("scanner_candidates") if isinstance(latest, dict) else None
    if isinstance(rows, list) and rows:
        return [dict(row) for row in rows if isinstance(row, dict) and not _is_mock_or_synthetic(row)][:limit]
    return [dict(row) for row in _MEMORY["scanner_candidates"] if not _is_mock_or_synthetic(row)][:limit]


def _latest_feature_rows_from_db(*, kind: str, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in list_feature_store_rows(100):
        values = record.get("feature_values") or record.get("metadata") or record.get("metadata_json") or {}
        if not isinstance(values, dict) or values.get("kind") != kind:
            continue
        if _is_mock_or_synthetic(values):
            continue
        rows.append(dict(values))
        if len(rows) >= limit:
            break
    return rows


def get_latest_market_snapshots(limit: int = 25) -> list[dict[str, Any]]:
    rows = _latest_feature_rows_from_db(kind="worker_market_snapshot", limit=limit)
    return rows or [dict(row) for row in _MEMORY["market_snapshots"] if not _is_mock_or_synthetic(row)][:limit]


def get_latest_feature_rows(limit: int = 25) -> list[dict[str, Any]]:
    rows = _latest_feature_rows_from_db(kind="worker_feature_row", limit=limit)
    return rows or [dict(row) for row in _MEMORY["feature_rows"] if not _is_mock_or_synthetic(row)][:limit]


def get_latest_worker_output_summary() -> dict[str, Any]:
    scanner_status = get_latest_worker_status("market-scanner-worker") or {}
    ingestion_status = get_latest_worker_status("data-ingestion-worker") or {}
    feature_status = get_latest_worker_status("feature-pipeline-worker") or {}
    candidates = get_latest_scanner_candidates()
    snapshots = get_latest_market_snapshots()
    feature_rows = get_latest_feature_rows()
    embedded = (
        scanner_status.get("persistence_status")
        or ingestion_status.get("persistence_status")
        or feature_status.get("persistence_status")
    )
    if embedded in {"postgres", "memory"}:
        persistence_mode = embedded
    else:
        health = get_persistence_status()
        persistence_mode = "postgres" if health.get("postgres_persistence_status") == "connected" else "memory"
    return {
        "scanner_worker": scanner_status,
        "ingestion_worker": ingestion_status,
        "feature_worker": feature_status,
        "candidate_count": len(candidates),
        "snapshot_count": len(snapshots),
        "feature_row_count": len(feature_rows),
        "persistence_mode": persistence_mode,
    }


def clear_worker_output_memory() -> None:
    for values in _MEMORY.values():
        values.clear()
