from __future__ import annotations

from typing import Any

import pytest

import app.services.agent_runtime.wrappers.watchlist_adapter as watchlist_adapter
import app.services.worker_output_store as worker_output_store
import app.workers.data_ingestion_worker as data_ingestion_worker
import app.workers.feature_pipeline_worker as feature_pipeline_worker


STALE_SYMBOLS = ["AMD", "MSFT"]


@pytest.fixture(autouse=True)
def _isolated_worker_store(monkeypatch):
    worker_output_store.clear_worker_output_memory()
    monkeypatch.setattr(worker_output_store, "save_market_scan_run", lambda *_args, **_kwargs: {"persisted": False, "warning": None})
    monkeypatch.setattr(worker_output_store, "save_feature_store_row", lambda *_args, **_kwargs: {"persisted": False, "warning": None})
    monkeypatch.setattr(worker_output_store, "list_market_scan_runs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(worker_output_store, "list_feature_store_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(data_ingestion_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(feature_pipeline_worker, "require_production_data_policy", lambda: None)
    yield
    worker_output_store.clear_worker_output_memory()


def _old_snapshot(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "price": 10.0,
        "volume": 1_000_000,
        "provider": "alpaca",
        "data_quality": "real",
        "is_non_real": False,
    }


def _old_feature(symbol: str) -> dict[str, Any]:
    return {
        "symbol": symbol,
        "last_price": 10.0,
        "volume": 1_000_000,
        "relative_volume": 2.0,
        "spread_bps": 10.0,
        "source": "feature_store",
        "provider_name": "alpaca",
        "data_quality": "real",
    }


def _record_zero_scanner_run() -> None:
    worker_output_store.record_worker_status(
        worker="market-scanner-worker",
        status="no_qualified_setup",
        worker_run_id="scanner-latest-zero",
        provider="alpaca",
        scanner_candidates=[],
        selected_symbols=[],
        raw_candidate_count=0,
        filtered_candidate_count=0,
        blockers=["no_real_discovery_universe_configured"],
        candidate_source="scanner",
    )


def _record_zero_ingestion_run() -> None:
    worker_output_store.record_worker_status(
        worker="data-ingestion-worker",
        status="no_symbols_to_ingest",
        worker_run_id="ingestion-latest-zero",
        provider="alpaca",
        snapshots=[],
        attempted_symbols=[],
        successful_symbols=[],
        snapshot_count=0,
        blockers=["no_scanner_candidates"],
        candidate_source="scanner",
    )


def _record_zero_feature_run() -> None:
    worker_output_store.record_worker_status(
        worker="feature-pipeline-worker",
        status="missing_features",
        worker_run_id="feature-latest-zero",
        provider="alpaca",
        feature_rows=[],
        feature_row_count=0,
        symbols=[],
        blockers=["no_ingested_scanner_snapshots"],
        candidate_source="scanner",
    )


def test_data_ingestion_ignores_stale_symbols_when_latest_scanner_has_zero_candidates(monkeypatch):
    worker_output_store.save_scanner_candidates(
        worker_run_id="scanner-old",
        provider_name="alpaca",
        candidates=[{"symbol": symbol, "source": "scanner", "candidate_source": "scanner"} for symbol in STALE_SYMBOLS],
    )
    _record_zero_scanner_run()

    class _NoMarketData:
        def get_market_snapshot(self, *_args, **_kwargs):
            raise AssertionError("data ingestion must not call provider without latest scanner candidates")

    monkeypatch.setattr(data_ingestion_worker, "MarketDataService", lambda: _NoMarketData())

    result = data_ingestion_worker.run()

    assert result["status"] == "no_symbols_to_ingest"
    assert result["attempted_symbols"] == []
    assert result["snapshot_count"] == 0
    assert result["blockers"] == ["no_scanner_candidates"]
    assert worker_output_store.get_latest_scanner_candidates() == []
    assert worker_output_store.get_latest_market_snapshots() == []


def test_feature_pipeline_ignores_stale_snapshots_when_latest_ingestion_has_zero_snapshots(monkeypatch):
    worker_output_store.save_market_snapshots(
        worker_run_id="ingestion-old",
        provider_name="alpaca",
        snapshots=[_old_snapshot(symbol) for symbol in STALE_SYMBOLS],
    )
    _record_zero_ingestion_run()
    monkeypatch.setattr(
        feature_pipeline_worker,
        "run_feature_store_pipeline",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("feature pipeline must not process stale snapshots")),
    )

    result = feature_pipeline_worker.run()

    assert result["status"] == "missing_features"
    assert result["symbols"] == []
    assert result["feature_rows"] == []
    assert result["feature_row_count"] == 0
    assert result["blockers"] == ["no_ingested_scanner_snapshots"]
    assert worker_output_store.get_latest_market_snapshots() == []
    assert worker_output_store.get_latest_feature_rows() == []


def test_worker_status_latest_counts_ignore_historical_rows():
    worker_output_store.save_scanner_candidates(
        worker_run_id="scanner-old",
        provider_name="alpaca",
        candidates=[{"symbol": symbol, "source": "scanner", "candidate_source": "scanner"} for symbol in STALE_SYMBOLS],
    )
    worker_output_store.save_market_snapshots(
        worker_run_id="ingestion-old",
        provider_name="alpaca",
        snapshots=[_old_snapshot(symbol) for symbol in STALE_SYMBOLS],
    )
    worker_output_store.save_feature_rows(
        worker_run_id="feature-old",
        provider_name="alpaca",
        feature_rows=[_old_feature(symbol) for symbol in STALE_SYMBOLS],
    )

    _record_zero_scanner_run()
    _record_zero_ingestion_run()
    _record_zero_feature_run()

    summary = worker_output_store.get_latest_worker_output_summary()

    assert summary["candidate_count"] == 0
    assert summary["snapshot_count"] == 0
    assert summary["feature_row_count"] == 0
    assert summary["scanner_status"] == "no_qualified_setup"


def test_watchlist_with_empty_symbols_cannot_use_candidate_universe_or_old_worker_rows(monkeypatch):
    worker_output_store.save_feature_rows(
        worker_run_id="feature-old",
        provider_name="alpaca",
        feature_rows=[_old_feature(symbol) for symbol in STALE_SYMBOLS],
    )
    _record_zero_scanner_run()
    _record_zero_feature_run()
    monkeypatch.setattr(watchlist_adapter, "list_candidates", lambda status=None: [object()])
    monkeypatch.setattr(watchlist_adapter, "get_latest_universe_selection", lambda: object())

    result = watchlist_adapter.build_watchlist(
        asset_class="stock",
        horizon="day_trading",
        orchestrator_mode=True,
        seed_symbols=[],
    )

    assert result["recommendation"]["status"] == "no_qualified_setup"
    assert result["usable_symbols"] == []
    assert result["selected_candidate"] is None
    assert result["candidate_source"] == "none"
    assert result["raw_candidate_count"] == 0
    assert result["filtered_candidate_count"] == 0
