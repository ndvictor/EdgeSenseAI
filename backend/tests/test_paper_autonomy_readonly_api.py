"""Step 7: read-only Paper Autonomy Control Tower API tests.

These tests verify that the new ``/api/v1/daytrading/paper-autonomy/*`` surface is:

- read-only (only GET handlers exist),
- safe on empty stores (no 500s),
- consistent: ``broker_called`` and ``live_submit_enabled`` are False everywhere
  in the response shape, and per-record ``broker_called`` is False on every
  returned paper order/position,
- aggregating real autonomy-loop data when records exist.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.paper_autonomy import (
    learning_outcomes_store,
    paper_order_store,
    paper_position_store,
)
from app.services.paper_autonomy.paper_simulator import simulate_paper_order_from_plan


client = TestClient(app)
WORKFLOW_RUN_ID = "wr_step7_test"


@pytest.fixture(autouse=True)
def _reset_paper_stores() -> None:
    paper_order_store.reset()
    paper_position_store.reset()
    learning_outcomes_store.reset()
    yield
    paper_order_store.reset()
    paper_position_store.reset()
    learning_outcomes_store.reset()


def _execution_plan(symbol: str = "AAPL") -> dict[str, Any]:
    return {
        "symbol": symbol,
        "side": "buy",
        "order_type": "limit",
        "time_in_force": "day",
        "entry": 150.00,
        "limit_price": 150.00,
        "stop_price": 148.50,
        "take_profit": 153.00,
        "position_size_shares": 10.0,
        "position_size_notional": 1500.00,
        "risk_dollars": 15.00,
        "expected_profit_dollars": 30.00,
        "expected_r_after_costs": 1.8,
        "submit_route": "paper",
        "requires_human_approval": False,
        "submitted_order": True,
        "broker_called": False,
    }


def _seed_one_paper_position(symbol: str = "AAPL") -> dict[str, Any]:
    return simulate_paper_order_from_plan(
        {
            "execution_plan": _execution_plan(symbol=symbol),
            "submit_route": "paper",
            "owner_authority": {
                "level": "paper_auto",
                "can_recommend_trades": True,
                "can_create_paper_plans": True,
                "can_create_approval_requests": True,
                "can_submit_paper_orders": True,
                "can_paper_auto_submit": True,
                "can_submit_live_orders": False,
                "require_human_approval": False,
            },
            "agent_capability_flags": {
                "agent_can_auto_submit_paper_orders": True,
                "agent_can_submit_paper_orders": True,
            },
            "paper_trading_enabled": True,
            "live_trading_enabled": False,
            "broker_execution_enabled": False,
            "strategy_key": "regime_aware_momentum_catalyst",
        },
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )


# ---------------------------------------------------------------------------
# 1. status endpoint returns ok on empty stores
# ---------------------------------------------------------------------------


def test_status_endpoint_returns_ok_on_empty_stores() -> None:
    response = client.get("/api/v1/daytrading/paper-autonomy/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["mode"] == "paper_autonomy"
    assert payload["broker_called"] is False
    assert payload["live_submit_enabled"] is False
    assert isinstance(payload.get("agent_capability_flags"), dict)
    assert "agent_can_submit_live_orders" in payload["agent_capability_flags"]


# ---------------------------------------------------------------------------
# 2. orders endpoint read-only and returns broker_called=false
# ---------------------------------------------------------------------------


def test_orders_endpoint_is_read_only_and_marks_broker_called_false() -> None:
    _seed_one_paper_position()
    response = client.get("/api/v1/daytrading/paper-autonomy/orders", params={"workflow_run_id": WORKFLOW_RUN_ID})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["broker_called"] is False
    assert payload["live_submit_enabled"] is False
    assert payload["count"] == 1
    item = payload["items"][0]
    assert item["broker_called"] is False
    assert item["submit_route"] == "paper"
    assert item["symbol"] == "AAPL"

    write_response = client.post("/api/v1/daytrading/paper-autonomy/orders", json={"symbol": "AAPL"})
    assert write_response.status_code == 405


# ---------------------------------------------------------------------------
# 3. open positions endpoint read-only
# ---------------------------------------------------------------------------


def test_open_positions_endpoint_read_only_with_broker_called_false() -> None:
    _seed_one_paper_position()
    response = client.get(
        "/api/v1/daytrading/paper-autonomy/positions/open",
        params={"workflow_run_id": WORKFLOW_RUN_ID},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["broker_called"] is False
    assert payload["count"] == 1
    pos = payload["items"][0]
    assert pos["broker_called"] is False
    assert pos["status"] == "open"
    assert pos["symbol"] == "AAPL"
    assert pos["source"] == "paper_simulator"

    write_response = client.post("/api/v1/daytrading/paper-autonomy/positions/open", json={"symbol": "AAPL"})
    assert write_response.status_code == 405


# ---------------------------------------------------------------------------
# 4. closed positions endpoint read-only
# ---------------------------------------------------------------------------


def test_closed_positions_endpoint_read_only_with_broker_called_false() -> None:
    _seed_one_paper_position()
    open_position = paper_position_store.latest_open_for_workflow(WORKFLOW_RUN_ID)
    assert open_position is not None
    paper_position_store.close(open_position.paper_position_id, exit_price=153.00, exit_reason="target_hit")

    response = client.get(
        "/api/v1/daytrading/paper-autonomy/positions/closed",
        params={"workflow_run_id": WORKFLOW_RUN_ID},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["broker_called"] is False
    assert payload["count"] == 1
    closed = payload["items"][0]
    assert closed["broker_called"] is False
    assert closed["status"] == "closed"
    assert closed["hit_target"] is True
    assert closed["actual_return_r"] is not None
    assert closed["prediction_error_r"] is not None

    write_response = client.post("/api/v1/daytrading/paper-autonomy/positions/closed", json={})
    assert write_response.status_code == 405


# ---------------------------------------------------------------------------
# 5. control tower aggregates counts
# ---------------------------------------------------------------------------


def test_control_tower_aggregates_counts_and_chain() -> None:
    _seed_one_paper_position(symbol="MSFT")
    open_position = paper_position_store.latest_open_for_workflow(WORKFLOW_RUN_ID)
    assert open_position is not None

    response = client.get(
        "/api/v1/daytrading/paper-autonomy/control-tower",
        params={"workflow_run_id": WORKFLOW_RUN_ID},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["status"] == "ok"
    assert payload["mode"] == "paper_autonomy"
    assert payload["broker_called"] is False
    assert payload["live_submit_enabled"] is False
    assert isinstance(payload["agent_capability_flags"], dict)

    summary = payload["summary"]
    assert summary["paper_orders"] == 1
    assert summary["open_positions"] == 1
    assert summary["closed_positions"] == 0
    assert summary["learning_outcomes"] == 0

    assert isinstance(payload["agent_chain"], list) and len(payload["agent_chain"]) == 9
    chain_keys = [entry["agent"] for entry in payload["agent_chain"]]
    assert chain_keys == [
        "watchlist_builder_agent",
        "alpha_engine_agent",
        "small_account_feasibility_agent",
        "execution_planner_agent",
        "execution_approval_agent",
        "position_monitor_agent",
        "close_review_agent",
        "post_trade_evaluator_agent",
        "learning_loop_agent",
    ]

    for order in payload["orders"]:
        assert order["broker_called"] is False
    for pos in payload["open_positions"]:
        assert pos["broker_called"] is False


# ---------------------------------------------------------------------------
# 6. no POST submit endpoint exists
# ---------------------------------------------------------------------------


def test_no_post_submit_endpoint_exists_for_paper_autonomy() -> None:
    routes = [r for r in app.router.routes if hasattr(r, "path")]
    paper_autonomy_routes = [r for r in routes if str(getattr(r, "path", "")).startswith("/api/v1/daytrading/paper-autonomy")]
    assert paper_autonomy_routes, "Expected paper-autonomy routes to be registered"
    for route in paper_autonomy_routes:
        methods = set(getattr(route, "methods", set()) or set())
        assert methods == {"GET"} or methods.issubset({"GET", "HEAD"}), (
            f"Paper autonomy route {route.path} is not read-only: methods={methods}"
        )


# ---------------------------------------------------------------------------
# 7. no broker/order call originates from these endpoints
# ---------------------------------------------------------------------------


def test_endpoints_do_not_create_orders_or_call_broker() -> None:
    pre_orders = paper_order_store.list_orders()
    pre_positions = paper_position_store.list_positions()

    paths = (
        "/api/v1/daytrading/paper-autonomy/status",
        "/api/v1/daytrading/paper-autonomy/orders",
        "/api/v1/daytrading/paper-autonomy/positions/open",
        "/api/v1/daytrading/paper-autonomy/positions/closed",
        "/api/v1/daytrading/paper-autonomy/learning/outcomes",
        "/api/v1/daytrading/paper-autonomy/control-tower",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        payload = response.json()
        assert payload.get("broker_called") is False
        if "live_submit_enabled" in payload:
            assert payload["live_submit_enabled"] is False

    assert paper_order_store.list_orders() == pre_orders
    assert paper_position_store.list_positions() == pre_positions
    for order in paper_order_store.list_orders():
        assert order.broker_called is False
    for pos in paper_position_store.list_positions():
        assert pos.broker_called is False


# ---------------------------------------------------------------------------
# 8. empty stores do not 500
# ---------------------------------------------------------------------------


def test_empty_stores_do_not_500() -> None:
    paths = (
        "/api/v1/daytrading/paper-autonomy/status",
        "/api/v1/daytrading/paper-autonomy/orders",
        "/api/v1/daytrading/paper-autonomy/positions/open",
        "/api/v1/daytrading/paper-autonomy/positions/closed",
        "/api/v1/daytrading/paper-autonomy/learning/outcomes",
        "/api/v1/daytrading/paper-autonomy/control-tower",
    )
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, f"{path} returned {response.status_code}"
        payload = response.json()
        assert payload.get("status") == "ok"
        if "items" in payload:
            assert payload["items"] == []
            assert payload["count"] == 0
        if path.endswith("/control-tower"):
            assert payload["summary"]["paper_orders"] == 0
            assert payload["summary"]["open_positions"] == 0
            assert payload["summary"]["closed_positions"] == 0
            assert any(alert.get("code") == "loop_empty" for alert in payload["alerts"])


# ---------------------------------------------------------------------------
# 9. learning outcomes endpoint returns recent outcomes across strategies
# ---------------------------------------------------------------------------


def test_learning_outcomes_endpoint_returns_recent_outcomes() -> None:
    from app.services.paper_autonomy.models import PaperLearningOutcome

    learning_outcomes_store.append(
        PaperLearningOutcome(
            trade_id="t1",
            paper_position_id="pp_test1",
            workflow_run_id=WORKFLOW_RUN_ID,
            strategy_key="regime_aware_momentum_catalyst",
            symbol="AAPL",
            outcome_label="target_hit",
            outcome_status="positive",
            realized_pnl=30.0,
            actual_return_r=2.0,
            slippage_status="pass",
            rule_compliant=True,
        )
    )

    response = client.get("/api/v1/daytrading/paper-autonomy/learning/outcomes")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["broker_called"] is False
    assert payload["count"] == 1
    assert payload["items"][0]["outcome_label"] == "target_hit"

    response_filtered = client.get(
        "/api/v1/daytrading/paper-autonomy/learning/outcomes",
        params={"strategy_key": "regime_aware_momentum_catalyst"},
    )
    assert response_filtered.status_code == 200
    assert response_filtered.json()["count"] == 1
    response_other = client.get(
        "/api/v1/daytrading/paper-autonomy/learning/outcomes",
        params={"strategy_key": "no_such_strategy"},
    )
    assert response_other.status_code == 200
    assert response_other.json()["count"] == 0
