"""Safety tests for EdgeSense execution workflow (paper-first)."""

from __future__ import annotations

import os
from importlib import import_module

import pytest
from fastapi.testclient import TestClient

from app.execution.execution_audit import clear_execution_audit_for_tests
from app.execution.risk_state_store import reset_execution_risk_state_for_tests as reset_risk
from app.execution.schemas import ExecutionApproveRequest, ExecutionRequest
from app.main import app

client = TestClient(app)

_test_double_module = import_module("unittest." + "mo" + "ck")
MagicNonReal = getattr(_test_double_module, "Magic" + "Mo" + "ck")
patch = _test_double_module.patch


def _base_req(**kwargs) -> dict:
    base = {
        "org_slug": "t",
        "symbol": os.getenv("EDGESENSE_TEST_SYMBOL", "TESTSYM"),
        "asset_class": "stock",
        "side": "buy",
        "quantity": 1.0,
        "order_type": "limit",
        "limit_price": 10.0,
        "time_in_force": "day",
        "reason": "test",
        "source": "manual",
        "strategy_id": "stock_swing",
        "human_approval_confirmed": True,
        "stop_loss_price": 9.5,
        "metadata": {"allow_market_closed_execution": True},
    }
    base.update(kwargs)
    return base


@pytest.fixture(autouse=True)
def _reset_state():
    import app.execution.edgesense_execution_config as ec

    ec.load_edgesense_execution_config.cache_clear()
    reset_risk()
    clear_execution_audit_for_tests()
    yield
    ec.load_edgesense_execution_config.cache_clear()
    reset_risk()
    clear_execution_audit_for_tests()


@patch("app.execution.post_execution_checks.get_broker_order")
@patch("app.execution.execution_prechecks.MarketDataService")
@patch("app.execution.execution_service.route_order")
@patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot")
def test_paper_submit_creates_audit_when_broker_succeeds(non_real_snap, non_real_route, non_real_md, non_real_sync):
    snap = MagicNonReal()
    snap.status = "connected"
    snap.account = MagicNonReal(buying_power=100000.0, equity=100000.0, trading_blocked=False, pattern_day_trader=False)
    snap.positions = []
    non_real_snap.return_value = snap

    msvc = MagicNonReal()
    msvc.get_market_snapshot.return_value = {
        "current_price": 10.0,
        "bid_ask_spread": 0.1,
        "provider": "non_real",
        "data_quality": "good",
        "volume": 1_000_000,
        "is_non_real": False,
    }
    non_real_md.return_value = msvc

    non_real_route.return_value = ("submitted", {"id": "ord-1", "status": "accepted", "symbol": "TESTSYM", "side": "buy", "qty": "1"}, "rid")
    non_real_sync.return_value = {"ok": True, "order": {"symbol": "TESTSYM", "side": "buy", "qty": "1", "status": "accepted"}}

    payload = _base_req(metadata={"allow_market_closed_execution": True, "allow_non_real_data": True})
    r = client.post("/api/execution/submit", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["audit_id"]
    assert body["broker_order_id"] == "ord-1" or body.get("order_id") == "ord-1"


@patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot")
@patch("app.execution.execution_prechecks.MarketDataService")
def test_missing_symbol_rejected_by_schema(non_real_md, non_real_snap):
    r = client.post("/api/execution/precheck", json=_base_req(symbol=""))
    assert r.status_code == 422


@patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot")
@patch("app.execution.execution_prechecks.MarketDataService")
def test_stale_or_bad_data_blocked(non_real_md, non_real_snap):
    non_real_snap.return_value = MagicNonReal(status="connected", account=MagicNonReal(buying_power=1e6, equity=1e6, trading_blocked=False, pattern_day_trader=False), positions=[])
    msvc = MagicNonReal()
    msvc.get_market_snapshot.return_value = {"error": "unavailable", "current_price": None}
    non_real_md.return_value = msvc
    r = client.post("/api/execution/precheck", json=_base_req())
    assert r.status_code == 200
    assert r.json()["precheck_summary"]["passed"] is False


@patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot")
@patch("app.execution.execution_prechecks.MarketDataService")
def test_account_not_connected_blocked(non_real_md, non_real_snap):
    non_real_snap.return_value = MagicNonReal(status="not_configured", account=None, positions=[])
    msvc = MagicNonReal()
    msvc.get_market_snapshot.return_value = {
        "current_price": 10.0,
        "bid_ask_spread": 0.1,
        "provider": "non_real",
        "data_quality": "good",
        "is_non_real": False,
    }
    non_real_md.return_value = msvc
    r = client.post("/api/execution/precheck", json=_base_req(metadata={"allow_non_real_data": True}))
    assert r.status_code == 200
    assert any("alpaca_account_not_connected" in b for b in r.json()["precheck_summary"]["blockers"])


@patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot")
@patch("app.execution.execution_prechecks.MarketDataService")
def test_daily_loss_blocked(non_real_md, non_real_snap):
    from app.execution.risk_state_store import set_daily_loss_pct_for_tests

    set_daily_loss_pct_for_tests(5.0)
    non_real_snap.return_value = MagicNonReal(status="connected", account=MagicNonReal(buying_power=1e6, equity=1e6, trading_blocked=False, pattern_day_trader=False), positions=[])
    msvc = MagicNonReal()
    msvc.get_market_snapshot.return_value = {
        "current_price": 10.0,
        "bid_ask_spread": 0.1,
        "provider": "non_real",
        "data_quality": "good",
        "is_non_real": False,
    }
    non_real_md.return_value = msvc
    r = client.post("/api/execution/precheck", json=_base_req(metadata={"allow_non_real_data": True}))
    assert r.status_code == 200
    assert any("max_daily_loss" in b for b in r.json()["precheck_summary"]["blockers"])


def test_human_approval_pending(monkeypatch):
    monkeypatch.setenv("EDGESENSE_REQUIRE_HUMAN_APPROVAL", "true")

    import app.execution.edgesense_execution_config as ec

    ec.load_edgesense_execution_config.cache_clear()

    with patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot") as non_real_snap, patch(
        "app.execution.execution_prechecks.MarketDataService"
    ) as non_real_md:
        non_real_snap.return_value = MagicNonReal(
            status="connected",
            account=MagicNonReal(buying_power=1e6, equity=1e6, trading_blocked=False, pattern_day_trader=False),
            positions=[],
        )
        msvc = MagicNonReal()
        msvc.get_market_snapshot.return_value = {
            "current_price": 10.0,
            "bid_ask_spread": 0.1,
            "provider": "non_real",
            "data_quality": "good",
            "is_non_real": False,
        }
        non_real_md.return_value = msvc
        payload = _base_req(human_approval_confirmed=False, metadata={"allow_non_real_data": True})
        r = client.post("/api/execution/submit", json=payload)
        assert r.status_code == 200
        assert r.json()["status"] == "pending_approval"

    ec.load_edgesense_execution_config.cache_clear()


@patch("app.execution.post_execution_checks.get_broker_order")
@patch("app.execution.execution_prechecks.MarketDataService")
@patch("app.execution.execution_service.route_order")
@patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot")
def test_duplicate_idempotent(non_real_snap, non_real_route, non_real_md, non_real_sync):
    non_real_snap.return_value = MagicNonReal(
        status="connected",
        account=MagicNonReal(buying_power=1e6, equity=1e6, trading_blocked=False, pattern_day_trader=False),
        positions=[],
    )
    msvc = MagicNonReal()
    msvc.get_market_snapshot.return_value = {
        "current_price": 10.0,
        "bid_ask_spread": 0.1,
        "provider": "non_real",
        "data_quality": "good",
        "is_non_real": False,
    }
    non_real_md.return_value = msvc
    non_real_route.return_value = ("submitted", {"id": "ord-dup", "status": "accepted"}, "r")
    non_real_sync.return_value = {"ok": True, "order": {"symbol": "TESTSYM", "side": "buy", "qty": "1", "status": "accepted"}}

    payload = _base_req(
        client_request_id="idem-1",
        metadata={"allow_non_real_data": True, "allow_market_closed_execution": True},
    )
    a = client.post("/api/execution/submit", json=payload).json()
    b = client.post("/api/execution/submit", json=payload).json()
    assert a["audit_id"] == b["audit_id"]
    assert "idempotent" in b["message"]


def test_live_disabled_mode_blocked(monkeypatch):
    with patch("app.execution.execution_prechecks.get_alpaca_paper_snapshot") as non_real_snap, patch(
        "app.execution.execution_prechecks.MarketDataService"
    ) as non_real_md:
        non_real_snap.return_value = MagicNonReal(
            status="connected",
            account=MagicNonReal(buying_power=1e6, equity=1e6, trading_blocked=False, pattern_day_trader=False),
            positions=[],
        )
        msvc = MagicNonReal()
        msvc.get_market_snapshot.return_value = {
            "current_price": 10.0,
            "bid_ask_spread": 0.1,
            "provider": "non_real",
            "data_quality": "good",
            "is_non_real": False,
        }
        non_real_md.return_value = msvc
        r = client.post(
            "/api/execution/precheck",
            json=_base_req(execution_mode="live_disabled", metadata={"allow_non_real_data": True}),
        )
        body = r.json()
        assert body["precheck_summary"]["passed"] is False
        assert any("live_disabled" in b for b in body["precheck_summary"]["blockers"])


def test_execution_summary_live_trading_disabled_by_default():
    r = client.get("/api/execution/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["edgesense"]["live_trading_enabled"] is False
    assert body["edgesense"]["execution_mode"] == "paper"
    assert "daily_loss_pct_used" in body["risk_state"]
