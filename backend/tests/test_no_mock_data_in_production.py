from __future__ import annotations

import pytest


def test_resolved_market_provider_mock_blocked_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "yfinance")
    from app.main import _resolved_market_provider

    assert _resolved_market_provider("mock") == "not_configured"


def test_edge_signals_empty_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.services.edge_signal_service import build_edge_signals

    assert build_edge_signals() == []
