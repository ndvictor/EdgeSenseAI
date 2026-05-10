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
            "is_non_real": False,
            "data_quality": "unavailable",
            "error": "No configured real provider returned market data",
        }

    monkeypatch.setattr(freshness._MARKET_DATA, "get_market_snapshot", unavailable_snapshot)

    result = freshness.run_data_freshness_check(freshness.DataFreshnessCheckRequest(symbols=["TEST_STOCK_B"], source="auto"))

    assert result.status == "fail"
    assert isinstance(result.warnings, list)
    assert isinstance(result.blockers, list)
    assert result.summary.unavailable_count == 1
    assert result.results[0].is_non_real is False
    assert result.results[0].decision == "blocked"
    assert result.results[0].blockers


def test_non_real_snapshot_is_blocked_without_creating_synthetic_data(monkeypatch):
    def non_real_snapshot(symbol: str, source: str = "auto"):
        return {
            "symbol": symbol,
            "provider": "non_real",
            "price": 100.0,
            "volume": 1000000,
            "bid": None,
            "ask": None,
            "is_non_real": True,
            "data_quality": "non_real",
        }

    monkeypatch.setattr(freshness._MARKET_DATA, "get_market_snapshot", non_real_snapshot)

    result = freshness.run_data_freshness_check(freshness.DataFreshnessCheckRequest(symbols=["TEST_STOCK_B"], source="auto", allow_non_real=False))

    assert result.status == "fail"
    assert result.results[0].is_non_real is True
    assert result.results[0].decision == "blocked"
    assert "Non-real market data detected" in result.results[0].blockers
    assert isinstance(result.warnings, list)
    assert isinstance(result.blockers, list)
