from __future__ import annotations

import pytest


def test_allow_mock_false_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("APP_ENV", "production")
    from app.core.production_safety import allow_mock_market_data

    assert allow_mock_market_data() is False


def test_allow_mock_requires_flag_in_non_prod(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "dev")
    monkeypatch.delenv("ALLOW_MOCK_MARKET_DATA", raising=False)
    from app.core.production_safety import allow_mock_market_data

    assert allow_mock_market_data() is False


def test_data_providers_mock_unknown_symbol_not_amd(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_MOCK_MARKET_DATA", "true")
    from app.data_providers.mock_provider import MockMarketDataProvider

    snap = MockMarketDataProvider().get_snapshot("ZZUNKNOWN", "stock")
    assert snap.symbol == "ZZUNKNOWN"
    assert snap.data_mode == "source_unavailable"


def test_services_mock_unknown_symbol_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_MOCK_MARKET_DATA", "true")
    from app.services.market_data_providers.mock_provider import MockMarketDataProvider

    row = MockMarketDataProvider().get_snapshot("NOTFOUND")
    assert row["data_quality"] == "unavailable"
    assert row.get("error") == "unknown_symbol"


def test_services_mock_disabled_returns_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ALLOW_MOCK_MARKET_DATA", "false")
    from app.services.market_data_providers.mock_provider import MockMarketDataProvider

    row = MockMarketDataProvider().get_snapshot("AMD")
    assert row["data_quality"] == "unavailable"
    assert row.get("error") == "mock_market_data_disabled"


def test_resolved_market_provider_mock_blocked_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("MARKET_DATA_PROVIDER", "yfinance")
    from app.main import _resolved_market_provider

    assert _resolved_market_provider("mock") == "yfinance"


def test_edge_signals_empty_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    from app.services.edge_signal_service import build_edge_signals

    assert build_edge_signals() == []
