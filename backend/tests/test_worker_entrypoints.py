from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import app.workers.common as common


WORKER_MODULES = [
    "app.workers.market_scanner_worker",
    "app.workers.data_ingestion_worker",
    "app.workers.feature_pipeline_worker",
]


def _set_safe_policy(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("MARKET_DATA_MODE", "provider")
    monkeypatch.setenv("ALLOW_MOCK_MARKET_DATA", "false")
    monkeypatch.setenv("ALLOW_SYNTHETIC_MARKET_DATA", "false")
    monkeypatch.setenv("LIVE_TRADING_ENABLED", "false")
    monkeypatch.setenv("BROKER_EXECUTION_ENABLED", "false")


def test_worker_modules_import():
    for module in WORKER_MODULES:
        assert importlib.import_module(module)


def test_production_data_policy_rejects_mock_enabled(monkeypatch):
    _set_safe_policy(monkeypatch)
    monkeypatch.setenv("ALLOW_MOCK_MARKET_DATA", "true")
    with pytest.raises(RuntimeError, match="mock_market_data_enabled"):
        common.require_production_data_policy()


def test_production_data_policy_rejects_synthetic_enabled(monkeypatch):
    _set_safe_policy(monkeypatch)
    monkeypatch.setenv("ALLOW_SYNTHETIC_MARKET_DATA", "true")
    with pytest.raises(RuntimeError, match="synthetic_market_data_enabled"):
        common.require_production_data_policy()


def test_workers_contain_no_hardcoded_fallback_ticker_lists():
    forbidden = {"AMD", "AAPL", "MSFT", "TSLA", "SPY", "QQQ"}
    worker_dir = Path(__file__).resolve().parents[1] / "app" / "workers"
    text = "\n".join(path.read_text() for path in worker_dir.glob("*.py"))
    for symbol in forbidden:
        assert symbol not in text


def test_workers_do_not_import_broker_submit_modules():
    forbidden = {
        "alpaca_order_router",
        "alpaca_execution_service",
        "execution.submit",
        "submit_alpaca_order",
        "place_trade_now_order",
    }
    worker_dir = Path(__file__).resolve().parents[1] / "app" / "workers"
    text = "\n".join(path.read_text() for path in worker_dir.glob("*.py"))
    for token in forbidden:
        assert token not in text


def test_worker_no_data_outcomes_exit_cleanly(monkeypatch):
    _set_safe_policy(monkeypatch)
    monkeypatch.delenv("WORKER_SYMBOLS", raising=False)

    market_worker = importlib.import_module("app.workers.market_scanner_worker")
    ingestion_worker = importlib.import_module("app.workers.data_ingestion_worker")
    feature_worker = importlib.import_module("app.workers.feature_pipeline_worker")

    monkeypatch.setattr(market_worker, "list_candidates", lambda status=None: [])
    monkeypatch.setattr(market_worker, "get_latest_universe_selection", lambda: None)
    monkeypatch.setattr(ingestion_worker, "list_candidates", lambda status=None: [])
    monkeypatch.setattr(ingestion_worker, "get_latest_universe_selection", lambda: None)
    monkeypatch.setattr(feature_worker, "list_candidates", lambda status=None: [])
    monkeypatch.setattr(feature_worker, "get_latest_universe_selection", lambda: None)

    assert market_worker.run()["recommendation_status"] == "no_qualified_setup"
    assert ingestion_worker.run()["recommendation_status"] == "no_symbols_to_ingest"
    assert feature_worker.run()["recommendation_status"] == "missing_features"
