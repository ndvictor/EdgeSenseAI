from __future__ import annotations

import app.services.data_freshness_gate_service as freshness


def test_minimal_request_does_not_raise_unbound_error():
    result = freshness.run_data_freshness_check(freshness.DataFreshnessCheckRequest())

    assert result.status == "fail"
    assert isinstance(result.warnings, list)
    assert isinstance(result.blockers, list)
    assert "No symbols provided. Explicit symbols required." in result.blockers


def test_unavailable_provider_returns_structured_result(monkeypatch):
    def unavailable_snapshot(symbol: str, source: str = "auto"):
        return {
            "symbol": symbol,
            "provider": None,
            "price": None,
            "volume": None,
            "is_mock": False,
            "data_quality": "unavailable",
            "error": "No configured real provider returned market data",
        }

    monkeypatch.setattr(freshness._MARKET_DATA, "get_market_snapshot", unavailable_snapshot)

    result = freshness.run_data_freshness_check(freshness.DataFreshnessCheckRequest(symbols=["MSFT"], source="auto"))

    assert result.status == "fail"
    assert isinstance(result.warnings, list)
    assert isinstance(result.blockers, list)
    assert result.summary.unavailable_count == 1
    assert result.results[0].is_mock is False
    assert result.results[0].decision == "blocked"
    assert result.results[0].blockers


def test_mock_snapshot_is_blocked_without_creating_synthetic_data(monkeypatch):
    def mock_snapshot(symbol: str, source: str = "auto"):
        return {
            "symbol": symbol,
            "provider": "mock",
            "price": 100.0,
            "volume": 1000000,
            "bid": None,
            "ask": None,
            "is_mock": True,
            "data_quality": "mock",
        }

    monkeypatch.setattr(freshness._MARKET_DATA, "get_market_snapshot", mock_snapshot)

    result = freshness.run_data_freshness_check(freshness.DataFreshnessCheckRequest(symbols=["MSFT"], source="auto", allow_mock=False))

    assert result.status == "fail"
    assert result.results[0].is_mock is True
    assert result.results[0].decision == "blocked"
    assert "Mock data detected but allow_mock=false" in result.results[0].blockers
    assert isinstance(result.warnings, list)
    assert isinstance(result.blockers, list)
