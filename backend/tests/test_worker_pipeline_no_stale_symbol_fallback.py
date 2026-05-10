from __future__ import annotations

from app.services.worker_output_store import clear_worker_output_memory, get_latest_worker_output_summary, save_feature_rows, save_market_snapshots, save_scanner_candidates
from app.workers import data_ingestion_worker, feature_pipeline_worker
from app.services.agent_runtime.wrappers.watchlist_adapter import build_watchlist


def test_ingestion_worker_does_not_fall_back_without_scanner_candidates(monkeypatch):
    clear_worker_output_memory()
    monkeypatch.delenv("WORKER_SYMBOLS", raising=False)
    monkeypatch.setattr(data_ingestion_worker, "get_latest_scanner_candidates", lambda _limit: [])

    result = data_ingestion_worker.run()

    assert result["status"] == "no_symbols_to_ingest"
    assert result["attempted_symbols"] == []
    assert result["snapshot_count"] == 0
    assert "no_scanner_candidates" in result["blockers"]


def test_feature_worker_does_not_fall_back_without_ingested_scanner_snapshots(monkeypatch):
    clear_worker_output_memory()
    monkeypatch.delenv("WORKER_SYMBOLS", raising=False)
    monkeypatch.setattr(feature_pipeline_worker, "get_latest_market_snapshots", lambda _limit, **_kwargs: [])

    result = feature_pipeline_worker.run()

    assert result["status"] == "missing_features"
    assert result["symbols"] == []
    assert result["feature_row_count"] == 0
    assert result["feature_rows"] == []
    assert "no_ingested_scanner_snapshots" in result["blockers"]


def test_watchlist_orchestrator_does_not_use_candidate_or_universe_fallback(monkeypatch):
    clear_worker_output_memory()
    monkeypatch.setattr("app.services.agent_runtime.wrappers.watchlist_adapter.get_latest_scanner_candidates", lambda _max_pick: [])
    monkeypatch.setattr("app.services.agent_runtime.wrappers.watchlist_adapter.get_latest_feature_rows_for_production_discovery", lambda _max_pick: [])

    result = build_watchlist(asset_class="stock", horizon="day_trade", orchestrator_mode=True, max_symbols=5)

    assert result["recommendation"]["status"] == "no_qualified_setup"
    assert result["symbols"] == []
    assert result["usable_symbols"] == []
    assert result["selected_candidate"] is None
    assert result["candidate_source"] == "none"
    assert "no_scanner_candidates_passed_filters" in result["blockers"]


def test_worker_output_summary_uses_latest_counts_not_historical_rows():
    clear_worker_output_memory()
    save_scanner_candidates(
        worker_run_id="scanner-empty",
        provider_name="yfinance",
        candidates=[],
        status="no_scanner_candidates",
        blockers=["no_scanner_candidates"],
    )
    save_market_snapshots(
        worker_run_id="ingestion-empty",
        provider_name="yfinance",
        snapshots=[],
        status="no_symbols_to_ingest",
        blockers=["no_scanner_candidates"],
    )
    save_feature_rows(
        worker_run_id="features-empty",
        provider_name="yfinance",
        feature_rows=[],
        status="missing_features",
        blockers=["no_ingested_scanner_snapshots"],
    )

    summary = get_latest_worker_output_summary()

    assert summary["candidate_count"] == 0
    assert summary["snapshot_count"] == 0
    assert summary["feature_row_count"] == 0
    assert summary["scanner_worker"]["status"] == "no_scanner_candidates"
    assert summary["ingestion_worker"]["status"] == "no_symbols_to_ingest"
    assert summary["feature_worker"]["status"] == "missing_features"
