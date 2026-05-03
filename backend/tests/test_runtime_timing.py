from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.main import app
from app.services.timing_cadence_service import build_cadence_plan, detect_market_phase

client = TestClient(app)


def test_detect_market_phase_pre_market():
    status = detect_market_phase(datetime(2026, 5, 4, 8, 0, tzinfo=ZoneInfo("America/New_York")))
    assert status.market_phase == "pre_market"
    assert status.active_loop == "pre_market_planning_loop"
    assert status.is_regular_session is False


def test_detect_market_phase_first_30_minutes():
    status = detect_market_phase(datetime(2026, 5, 4, 9, 45, tzinfo=ZoneInfo("America/New_York")))
    assert status.market_phase == "market_open_first_30_min"
    assert status.active_loop == "fast_scanning_loop"
    assert status.is_regular_session is True


def test_detect_market_phase_after_hours():
    status = detect_market_phase(datetime(2026, 5, 4, 17, 0, tzinfo=ZoneInfo("America/New_York")))
    assert status.market_phase == "after_hours"
    assert status.active_loop == "after_hours_learning_loop"
    assert status.is_regular_session is False


def test_cadence_plan_never_allows_live_trading():
    plan = build_cadence_plan("market_open_first_30_min")
    assert plan.live_trading_allowed is False
    assert plan.human_approval_required is True
    assert plan.top_watchlist_scan_seconds >= 5
    assert plan.llm_validation_policy


def test_runtime_phase_endpoint_contract():
    response = client.get("/api/runtime/phase")
    assert response.status_code == 200
    payload = response.json()
    assert payload["market_phase"] in {
        "market_closed",
        "pre_market",
        "market_open_first_30_min",
        "market_open",
        "midday",
        "power_hour",
        "after_hours",
    }
    assert payload["active_loop"]
    assert payload["data_source"] == "deterministic_clock"


def test_runtime_cadence_endpoint_contract():
    response = client.get("/api/runtime/cadence")
    assert response.status_code == 200
    payload = response.json()
    assert payload["live_trading_allowed"] is False
    assert payload["paper_trading_allowed"] is True
    assert payload["human_approval_required"] is True
    assert payload["top_watchlist_scan_seconds"] > 0
    assert payload["secondary_watchlist_scan_seconds"] >= payload["top_watchlist_scan_seconds"]


def test_runtime_cadence_simulation_endpoint_contract():
    response = client.post(
        "/api/runtime/cadence/simulate",
        json={"market_phase": "midday", "volatility_state": "high", "strategy_key": "stock_day_trading"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["market_phase"] == "midday"
    assert payload["active_loop"] == "selective_monitoring_loop"
    assert payload["live_trading_allowed"] is False


def test_ai_ops_summary_includes_runtime_timing():
    response = client.get("/api/ai-ops/summary")
    assert response.status_code == 200
    payload = response.json()
    assert "market_phase" in payload
    assert "cadence_plan" in payload
    assert payload["cadence_plan"]["live_trading_allowed"] is False
    assert payload["active_loop"] == payload["cadence_plan"]["active_loop"]
    assert payload["scan_mode"] == payload["cadence_plan"]["scan_mode"]
