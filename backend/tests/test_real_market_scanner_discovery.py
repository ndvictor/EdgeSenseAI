from __future__ import annotations

from pathlib import Path
from typing import Any

import app.services.market_condition_scanner_service as scanner
import app.workers.market_scanner_worker as market_scanner_worker
from app.services.market_condition_scanner_service import MarketScannerRequest, MarketScannerResponse, run_market_condition_scan


class _MarketData:
    def __init__(self, snapshots: dict[str, dict[str, Any]]):
        self.snapshots = snapshots

    def get_market_snapshot(self, symbol: str, source: str | None = None) -> dict[str, Any]:
        _ = source
        return dict(self.snapshots[symbol.upper()])


def _snapshot(**overrides: Any) -> dict[str, Any]:
    data = {
        "symbol": "ROWX",
        "price": 12.0,
        "volume": 2_000_000,
        "average_volume": 500_000,
        "relative_volume": 4.0,
        "change_percent": 5.0,
        "bid": 11.99,
        "ask": 12.01,
        "vwap": 11.8,
        "session_state": "regular",
        "provider": "provider_test",
        "data_quality": "real",
        "is_non_real": False,
    }
    data.update(overrides)
    return data


def test_real_market_scanner_selects_candidate_that_passes_criteria(monkeypatch):
    monkeypatch.setattr(scanner, "_MARKET_DATA", _MarketData({"ROWX": _snapshot()}))

    response = run_market_condition_scan(
        MarketScannerRequest(strategy_key="stock_day_trading", symbols=["ROWX"], data_source="provider_test", auto_run=False)
    )

    assert response.matched_signals
    assert response.matched_signals[0].symbol == "ROWX"
    assert response.matched_signals[0].metadata["relative_volume"] == 4.0
    assert response.matched_signals[0].metadata["dollar_volume"] == 24_000_000


def test_non_real_market_data_is_rejected_before_candidate_selection(monkeypatch):
    monkeypatch.setattr(scanner, "_MARKET_DATA", _MarketData({"ROWX": _snapshot(is_non_real=True)}))

    response = run_market_condition_scan(
        MarketScannerRequest(strategy_key="stock_day_trading", symbols=["ROWX"], data_source="provider_test", auto_run=False)
    )

    assert response.matched_signals == []
    assert any("non_real_market_data_rejected" in signal.reason for signal in response.skipped_signals)


def test_synthetic_market_data_is_rejected_before_candidate_selection(monkeypatch):
    monkeypatch.setattr(scanner, "_MARKET_DATA", _MarketData({"ROWX": _snapshot(spread_synthetic=True)}))

    response = run_market_condition_scan(
        MarketScannerRequest(strategy_key="stock_day_trading", symbols=["ROWX"], data_source="provider_test", auto_run=False)
    )

    assert response.matched_signals == []
    assert any("synthetic_market_data_rejected" in signal.reason for signal in response.skipped_signals)


def test_no_candidates_pass_returns_worker_no_qualified_setup(monkeypatch):
    response = MarketScannerResponse(
        run_id="scan-test",
        trigger_type="scheduled",
        strategy_key="stock_day_trading",
        symbols_scanned=["ROWX"],
        matched_signals=[],
        skipped_signals=[],
        should_trigger_workflow=False,
        recommended_workflow_key="none",
        required_agents=[],
        required_models=[],
        safety_state=scanner.get_auto_run_state(),
        next_action="No deterministic edge signal matched.",
        data_source="source_backed",
    )
    monkeypatch.setattr(market_scanner_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(market_scanner_worker, "list_candidates", lambda status=None: [])
    monkeypatch.setattr(market_scanner_worker, "get_latest_universe_selection", lambda: type("Latest", (), {"selected_watchlist": [type("C", (), {"symbol": "ROWX"})()], "ranked_candidates": []})())
    monkeypatch.setattr(market_scanner_worker, "run_market_condition_scan", lambda _request: response)
    monkeypatch.setattr(market_scanner_worker, "record_worker_status", lambda **_kwargs: {})
    monkeypatch.setattr(market_scanner_worker, "save_scanner_candidates", lambda **_kwargs: {})

    summary = market_scanner_worker.run()

    assert summary["recommendation_status"] == "no_qualified_setup"
    assert summary["filtered_candidate_count"] == 0
    assert summary["selected_symbols"] == []


def test_real_scanner_discovery_has_no_hardcoded_fallback_symbols():
    forbidden = {"TEST_STOCK_A", "TEST_STOCK_D", "TEST_STOCK_B", "TSLA", "SPY", "QQQ"}
    path = Path(__file__).resolve().parents[1] / "app" / "services" / "market_condition_scanner_service.py"
    source = path.read_text()

    for symbol in forbidden:
        assert symbol not in source
