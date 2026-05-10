from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.services.market_session_service import get_market_session_state, scanner_mode_for_session
from app.services.session_router.models import SessionEvaluateRequest
from app.services.session_router.service import evaluate_session
from app.workers import market_scanner_worker


ET = ZoneInfo("America/New_York")


def test_market_session_service_regular_market():
    state = get_market_session_state(datetime(2026, 5, 11, 10, 0, tzinfo=ET), prefer_alpaca=False)

    assert state.market_session == "regular_market"
    assert state.clock_source == "fallback_timezone"
    assert state.is_trading_day is True
    assert state.is_market_open is True
    assert state.is_regular_market is True
    assert scanner_mode_for_session(state) == "regular_market"


def test_market_session_service_post_market():
    state = get_market_session_state(datetime(2026, 5, 11, 17, 0, tzinfo=ET), prefer_alpaca=False)

    assert state.market_session == "post_market"
    assert state.is_post_market is True
    assert state.is_market_open is False
    assert scanner_mode_for_session(state) == "post_market"


def test_market_session_service_weekend_closed():
    state = get_market_session_state(datetime(2026, 5, 10, 12, 0, tzinfo=ET), prefer_alpaca=False)

    assert state.market_session == "closed"
    assert state.is_trading_day is False
    assert scanner_mode_for_session(state) == "market_closed"


def test_session_router_uses_shared_market_session_service():
    response = evaluate_session(
        SessionEvaluateRequest(
            market="us_equities",
            timestamp="2026-05-11T10:00:00-04:00",
            timezone="America/New_York",
            use_current_time=False,
        )
    )

    assert response["status"] == "ok"
    assert response["market_session_state"]["market_session"] == "regular_market"
    assert response["market_session_state"]["clock_source"] == "fallback_timezone"
    assert response["session"]["session"] == "market_open"


def test_market_scanner_worker_skips_when_market_closed(monkeypatch):
    monkeypatch.setattr(market_scanner_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(market_scanner_worker, "get_worker_run_id", lambda _name: "scanner_test_closed")
    monkeypatch.setattr(
        market_scanner_worker,
        "get_market_session_state",
        lambda: get_market_session_state(datetime(2026, 5, 10, 12, 0, tzinfo=ET), prefer_alpaca=False),
    )
    called = {"scanner": False}

    def _should_not_scan(*args, **kwargs):
        called["scanner"] = True
        raise AssertionError("scanner should not run when market is closed")

    monkeypatch.setattr(market_scanner_worker, "build_scanner_diagnostics", _should_not_scan)
    result = market_scanner_worker.run()

    assert called["scanner"] is False
    assert result["status"] == "market_closed"
    assert result["scanner_mode"] == "market_closed"
    assert result["selected_symbols"] == []
    assert result["blockers"] == ["market_closed"]
    assert result["broker_called"] is False if "broker_called" in result else True


def test_market_scanner_worker_regular_market_uses_configured_symbols(monkeypatch):
    monkeypatch.setattr(market_scanner_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(market_scanner_worker, "get_worker_run_id", lambda _name: "scanner_test_regular")
    monkeypatch.setenv("SCANNER_SYMBOLS", "TSLA,PLTR")
    monkeypatch.setattr(
        market_scanner_worker,
        "get_market_session_state",
        lambda: get_market_session_state(datetime(2026, 5, 11, 10, 0, tzinfo=ET), prefer_alpaca=False),
    )

    def _scan(symbols, **kwargs):
        assert symbols == ["TSLA", "PLTR"]
        return {
            "status": "ok",
            "provider_name": "yfinance",
            "provider_priority": ["yfinance"],
            "provider_configured": True,
            "selected_candidates": [{"symbol": "TSLA", "provider_name": "yfinance", "price": 200.0, "candidate_source": "scanner"}],
            "rejected_candidates": [],
            "total_symbols_rejected": 1,
            "rejection_counts": {"did_not_pass_filter": 1},
        }

    monkeypatch.setattr(market_scanner_worker, "build_scanner_diagnostics", _scan)
    result = market_scanner_worker.run()

    assert result["status"] == "candidate_selected"
    assert result["scanner_mode"] == "regular_market"
    assert result["market_session"] == "regular_market"
    assert result["selected_symbols"] == ["TSLA"]
    assert result["candidate_source"] == "scanner"


def test_market_scanner_worker_post_market_mode(monkeypatch):
    monkeypatch.setattr(market_scanner_worker, "require_production_data_policy", lambda: None)
    monkeypatch.setattr(market_scanner_worker, "get_worker_run_id", lambda _name: "scanner_test_post")
    monkeypatch.setenv("SCANNER_SYMBOLS", "TSLA")
    monkeypatch.setattr(
        market_scanner_worker,
        "get_market_session_state",
        lambda: get_market_session_state(datetime(2026, 5, 11, 17, 0, tzinfo=ET), prefer_alpaca=False),
    )
    monkeypatch.setattr(
        market_scanner_worker,
        "build_scanner_diagnostics",
        lambda symbols, **kwargs: {
            "status": "ok",
            "provider_name": "yfinance",
            "selected_candidates": [],
            "rejected_candidates": [{"symbol": "TSLA"}],
            "total_symbols_rejected": 1,
            "rejection_counts": {"post_market_filter": 1},
        },
    )

    result = market_scanner_worker.run()

    assert result["scanner_mode"] == "post_market"
    assert result["market_session"] == "post_market"
    assert result["status"] == "no_qualified_setup"
    assert "no_scanner_candidates_passed_filters" in result["blockers"]
