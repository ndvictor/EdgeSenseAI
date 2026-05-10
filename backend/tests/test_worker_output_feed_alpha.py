from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.agent_runtime.wrappers.alpha_engine_adapter import run_alpha_engine_selection
from app.services.agent_runtime.wrappers.watchlist_adapter import build_watchlist
import app.services.agent_runtime.wrappers.watchlist_adapter as watchlist_adapter
import app.services.worker_output_store as worker_output_store


client = TestClient(app)


@pytest.fixture(autouse=True)
def _isolated_worker_output_store(monkeypatch):
    worker_output_store.clear_worker_output_memory()
    monkeypatch.setattr(worker_output_store, "save_market_scan_run", lambda *_args, **_kwargs: {"persisted": False, "data_source": "in_memory_fallback", "warning": None})
    monkeypatch.setattr(worker_output_store, "save_feature_store_row", lambda *_args, **_kwargs: {"persisted": False, "data_source": "in_memory_fallback", "warning": None})
    monkeypatch.setattr(worker_output_store, "list_market_scan_runs", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(worker_output_store, "list_feature_store_rows", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(watchlist_adapter, "list_candidates", lambda status=None: [])
    monkeypatch.setattr(watchlist_adapter, "get_latest_feature_rows", lambda: [])
    monkeypatch.setattr(watchlist_adapter, "get_latest_universe_selection", lambda: None)
    yield
    worker_output_store.clear_worker_output_memory()


def _real_feature_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "symbol": "ROWX",
        "last_price": 10.0,
        "volume": 5_000_000,
        "avg_volume": 1_000_000,
        "relative_volume": 5.0,
        "day_change_pct": 8.0,
        "spread_bps": 8.0,
        "vwap": 9.7,
        "price_above_vwap": True,
        "trend_score": 80.0,
        "liquidity_score": 85.0,
        "source": "feature_store",
        "provider_name": "provider_test",
        "data_quality": "real",
    }
    row.update(overrides)
    return row


def test_persisted_scanner_candidate_becomes_usable_symbols_in_watchlist():
    worker_output_store.save_scanner_candidates(
        worker_run_id="scanner-test-1",
        provider_name="provider_test",
        candidates=[{"symbol": "ROWX", "source": "scanner", "relative_volume": 2.0}],
    )

    out = build_watchlist(asset_class="stock", horizon="day_trading", orchestrator_mode=True, seed_symbols=[])

    assert out["candidate_source"] == "scanner"
    assert out["usable_symbols"] == ["ROWX"]
    assert out["raw_candidate_count"] == 1
    assert out["filtered_candidate_count"] == 1


def test_persisted_feature_row_reaches_alpha_engine():
    worker_output_store.save_feature_rows(
        worker_run_id="feature-test-1",
        provider_name="provider_test",
        feature_rows=[_real_feature_row()],
    )
    watchlist = build_watchlist(asset_class="stock", horizon="day_trading", orchestrator_mode=True, seed_symbols=[])

    out = run_alpha_engine_selection(watchlist, {"workflow_run_id": "wr_worker_alpha"})

    assert watchlist["feature_rows"][0]["symbol"] == "ROWX"
    assert out["alpha_status"] == "candidate_selected"
    assert out["alpha_selected_symbol"] == "ROWX"


def test_alpha_selects_high_quality_real_candidate_from_worker_feature_row():
    worker_output_store.save_feature_rows(
        worker_run_id="feature-test-2",
        provider_name="provider_test",
        feature_rows=[_real_feature_row(symbol="ROWY")],
    )

    watchlist = build_watchlist(asset_class="stock", horizon="day_trading", orchestrator_mode=True, seed_symbols=[])
    out = run_alpha_engine_selection(watchlist, {"workflow_run_id": "wr_worker_alpha_select"})

    assert out["alpha_status"] == "candidate_selected"
    assert out["alpha_selected_symbol"] == "ROWY"
    assert out["alpha_strategy_key"] == "relative_volume_momentum_breakout_v1"


def test_no_candidates_still_returns_no_qualified_setup():
    watchlist = build_watchlist(asset_class="stock", horizon="day_trading", orchestrator_mode=True, seed_symbols=[])
    out = run_alpha_engine_selection(watchlist, {"workflow_run_id": "wr_worker_alpha_empty"})

    assert watchlist["recommendation"]["status"] == "no_qualified_setup"
    assert out["alpha_status"] == "no_qualified_setup"
    assert out["alpha_selected_symbol"] is None


def test_non_real_and_synthetic_candidates_are_rejected():
    worker_output_store.save_feature_rows(
        worker_run_id="feature-test-3",
        provider_name="provider_test",
        feature_rows=[_real_feature_row(symbol="NON_REALX", non_real=True), _real_feature_row(symbol="SYNX", synthetic=True)],
    )

    watchlist = build_watchlist(asset_class="stock", horizon="day_trading", orchestrator_mode=True, seed_symbols=[])
    out = run_alpha_engine_selection(watchlist, {"workflow_run_id": "wr_worker_alpha_reject"})

    assert watchlist["recommendation"]["status"] == "no_qualified_setup"
    assert out["alpha_status"] == "no_qualified_setup"
    assert out["alpha_selected_symbol"] is None


def test_no_hardcoded_fallback_symbols_in_worker_feed_path():
    forbidden = {"TEST_STOCK_A", "TEST_STOCK_D", "TEST_STOCK_B", "TSLA", "SPY", "QQQ"}
    root = Path(__file__).resolve().parents[1] / "app" / "services"
    files = [
        root / "worker_output_store.py",
        root / "agent_runtime" / "wrappers" / "watchlist_adapter.py",
        root / "agent_runtime" / "wrappers" / "alpha_engine_adapter.py",
    ]
    source = "\n".join(path.read_text() for path in files)
    for symbol in forbidden:
        assert symbol not in source


def test_worker_feed_alpha_keeps_execution_flags_false():
    out = run_alpha_engine_selection({"feature_rows": [_real_feature_row()]}, {"workflow_run_id": "wr_worker_alpha_flags"})

    assert out["submitted_order"] is False
    assert out["broker_called"] is False
    assert out["llm_used"] is False
    assert out["alpha_recommendation"]["submitted_order"] is False
    assert out["alpha_recommendation"]["broker_called"] is False
    assert out["alpha_recommendation"]["llm_used_for_trade_decision"] is False


def test_worker_status_latest_endpoint_reports_counts():
    worker_output_store.save_scanner_candidates(
        worker_run_id="scanner-test-2",
        provider_name="provider_test",
        candidates=[{"symbol": "ROWX", "source": "scanner"}],
    )
    worker_output_store.save_market_snapshots(
        worker_run_id="ingest-test-1",
        provider_name="provider_test",
        snapshots=[{"symbol": "ROWX", "price": 10.0, "provider": "provider_test", "data_quality": "real", "is_non_real": False}],
    )
    worker_output_store.save_feature_rows(
        worker_run_id="feature-test-4",
        provider_name="provider_test",
        feature_rows=[_real_feature_row()],
    )

    response = client.get("/api/worker-status/latest")

    assert response.status_code == 200
    data = response.json()
    assert data["candidate_count"] == 1
    assert data["snapshot_count"] == 1
    assert data["feature_row_count"] == 1
