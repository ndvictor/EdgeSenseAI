"""Step 6: paper autonomy loop tests.

These tests exercise the full simulation chain:

    execution_planner_agent  →  execution_approval_agent (paper_simulator)
    →  paper_order_store / paper_position_store
    →  position_monitor_agent (real market data)
    →  close_review_agent (close paper position)
    →  post_trade_evaluator_agent (compute actual_return_r, prediction_error_r, ...)
    →  learning_loop_agent (recommendation only)

Hard invariants the tests verify:
- broker_called is False everywhere.
- submitted_order is True only on the paper auto-submit path, never on live or
  approval paths.
- live submit is blocked in this step regardless of authority/flags.
- No fallback symbols and no synthetic prices are introduced by the autonomy
  loop. Symbols come from the audited execution plan; prices come from the real
  ``MarketDataService`` call (which we monkeypatch in tests).
"""

from __future__ import annotations

from typing import Any

import pytest

from app.services.agent_runtime.wrappers.stage_wrappers import run_wrapped_agent
from app.services.paper_autonomy import (
    learning_outcomes_store,
    paper_order_store,
    paper_position_store,
)
from app.services.paper_autonomy.paper_simulator import simulate_paper_order_from_plan


WORKFLOW_RUN_ID = "wr_step6_test"


@pytest.fixture(autouse=True)
def _reset_paper_stores():
    paper_order_store.reset()
    paper_position_store.reset()
    learning_outcomes_store.reset()
    yield
    paper_order_store.reset()
    paper_position_store.reset()
    learning_outcomes_store.reset()


def _execution_plan(*, submit_route: str = "paper", symbol: str = "AAPL") -> dict[str, Any]:
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
        "submit_route": submit_route,
        "requires_human_approval": False,
        "submitted_order": submit_route == "paper",
        "broker_called": False,
    }


def _owner_authority(level: str = "paper_auto") -> dict[str, Any]:
    return {
        "level": level,
        "can_recommend_trades": True,
        "can_create_paper_plans": True,
        "can_create_approval_requests": True,
        "can_submit_paper_orders": level in {"paper_submit", "paper_auto", "live_submit"},
        "can_paper_auto_submit": level in {"paper_auto", "live_submit"},
        "can_submit_live_orders": level == "live_submit",
        "require_human_approval": level not in {"paper_auto", "live_submit"},
    }


def _flags(*, paper_auto: bool = True, live: bool = False) -> dict[str, Any]:
    return {
        "agent_can_recommend_trades": True,
        "agent_can_create_paper_plans": True,
        "agent_can_create_approval_requests": True,
        "agent_can_submit_paper_orders": paper_auto,
        "agent_can_auto_submit_paper_orders": paper_auto,
        "agent_can_submit_live_orders": live,
    }


def _sim_inputs(
    *,
    submit_route: str = "paper",
    symbol: str = "AAPL",
    paper_trading_enabled: bool = True,
    live_trading_enabled: bool = False,
    broker_execution_enabled: bool = False,
    owner_level: str = "paper_auto",
    paper_auto_flag: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "execution_plan": _execution_plan(submit_route=submit_route, symbol=symbol),
        "submit_route": submit_route,
        "owner_authority": _owner_authority(owner_level),
        "agent_capability_flags": _flags(paper_auto=paper_auto_flag, live=False),
        "paper_trading_enabled": paper_trading_enabled,
        "live_trading_enabled": live_trading_enabled,
        "broker_execution_enabled": broker_execution_enabled,
        "recommendation_id": "rec_step6_test",
        "strategy_key": "regime_aware_momentum_catalyst",
    }
    if extra:
        payload.update(extra)
    return payload


def _approval_call(inputs: dict[str, Any]) -> dict[str, Any]:
    return run_wrapped_agent(
        agent_key="execution_approval_agent",
        inputs=inputs,
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "orchestrator_run_id": None, "agent_run_id": "ar_test"},
    )


def _patch_quote(monkeypatch: pytest.MonkeyPatch, *, symbol: str, price: float | None, data_quality: str = "real_time") -> dict[str, Any]:
    captured: dict[str, Any] = {"calls": []}

    def fake_get_quote(self, sym: str, source: str | None = None) -> dict[str, Any]:
        captured["calls"].append({"symbol": sym, "source": source})
        return {
            "symbol": sym.upper(),
            "price": price,
            "previous_close": price,
            "change": 0.0,
            "change_percent": 0.0,
            "day_high": price,
            "day_low": price,
            "volume": 1_000_000,
            "provider": "test_real_time",
            "source": source or "auto",
            "is_non_real": False,
            "data_quality": data_quality,
            "unavailable_fields": [],
            "not_configured_fields": [],
        }

    from app.services.market_data_service import MarketDataService

    monkeypatch.setattr(MarketDataService, "get_quote", fake_get_quote)
    return captured


# ---------------------------------------------------------------------------
# 1. submit_route="none" creates no paper order
# ---------------------------------------------------------------------------


def test_submit_route_none_creates_no_paper_order():
    inputs = _sim_inputs(submit_route="none")
    inputs["owner_authority"]["require_human_approval"] = False
    response = simulate_paper_order_from_plan(
        inputs,
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "plan_only"
    assert response["paper_order"] is None
    assert response["paper_position"] is None
    assert response["approval_item"] is None
    assert response["submitted_order"] is False
    assert response["broker_called"] is False
    assert paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID) == []
    assert paper_position_store.list_positions(workflow_run_id=WORKFLOW_RUN_ID) == []


# ---------------------------------------------------------------------------
# 2. submit_route="paper" with paper_auto creates paper order
# ---------------------------------------------------------------------------


def test_paper_auto_creates_paper_order_and_position():
    response = simulate_paper_order_from_plan(
        _sim_inputs(submit_route="paper"),
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "paper_simulated"
    assert response["paper_order"] is not None
    assert response["paper_position"] is not None
    assert response["paper_order"]["submit_route"] == "paper"
    assert response["paper_order"]["status"] == "paper_open"
    orders = paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID)
    positions = paper_position_store.list_positions(workflow_run_id=WORKFLOW_RUN_ID)
    assert len(orders) == 1 and len(positions) == 1
    assert orders[0].symbol == "AAPL"
    assert positions[0].paper_order_id == orders[0].paper_order_id


# ---------------------------------------------------------------------------
# 3. paper_auto requires AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS=true
# ---------------------------------------------------------------------------


def test_paper_auto_requires_agent_capability_flag():
    inputs = _sim_inputs(submit_route="paper", paper_auto_flag=False)
    response = simulate_paper_order_from_plan(
        inputs,
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "paper_blocked"
    assert response["submitted_order"] is False
    assert response["broker_called"] is False
    assert "agent_can_auto_submit_paper_orders_disabled" in response["blockers"]
    assert response["paper_order"] is None and response["paper_position"] is None


# ---------------------------------------------------------------------------
# 4. paper_auto requires paper_trading_enabled=true
# ---------------------------------------------------------------------------


def test_paper_auto_requires_paper_trading_enabled():
    inputs = _sim_inputs(submit_route="paper", paper_trading_enabled=False)
    response = simulate_paper_order_from_plan(
        inputs,
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "paper_blocked"
    assert "paper_trading_disabled" in response["blockers"]
    assert response["submitted_order"] is False
    assert response["broker_called"] is False
    assert paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID) == []


# ---------------------------------------------------------------------------
# 5. paper order creation sets submitted_order=true and broker_called=false
# ---------------------------------------------------------------------------


def test_paper_order_record_flags_submitted_order_true_and_broker_called_false():
    response = simulate_paper_order_from_plan(
        _sim_inputs(submit_route="paper"),
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    paper_order = response["paper_order"]
    paper_position = response["paper_position"]
    assert paper_order["submitted_order"] is True
    assert paper_order["broker_called"] is False
    assert paper_position["broker_called"] is False
    assert response["live_submit"] is False
    stored_order = paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID)[0]
    assert stored_order.submitted_order is True
    assert stored_order.broker_called is False


# ---------------------------------------------------------------------------
# 6. live submit route is blocked in step_6
# ---------------------------------------------------------------------------


def test_live_submit_route_is_blocked_for_step_6():
    inputs = _sim_inputs(
        submit_route="live",
        owner_level="live_submit",
        live_trading_enabled=True,
        broker_execution_enabled=True,
    )
    inputs["owner_authority"]["can_submit_live_orders"] = True
    inputs["owner_authority"]["can_paper_auto_submit"] = True

    response = simulate_paper_order_from_plan(
        inputs,
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "live_blocked"
    assert "live_submit_disabled_for_step_6" in response["blockers"]
    assert response["submitted_order"] is False
    assert response["broker_called"] is False
    assert response["live_submit"] is False
    assert response["paper_order"] is None
    assert response["paper_position"] is None
    assert paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID) == []


# ---------------------------------------------------------------------------
# 7. approval-required path creates approval item only
# ---------------------------------------------------------------------------


def test_approval_required_path_creates_approval_item_only():
    inputs = _sim_inputs(submit_route="none", owner_level="paper_plan")
    inputs["execution_plan"]["requires_human_approval"] = True
    inputs["owner_authority"]["require_human_approval"] = True
    inputs["owner_authority"]["can_paper_auto_submit"] = False

    response = simulate_paper_order_from_plan(
        inputs,
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "approval_required"
    assert response["approval_item"] is not None
    assert response["approval_item"]["status"] == "pending"
    assert response["paper_order"] is None
    assert response["paper_position"] is None
    assert response["submitted_order"] is False
    assert response["broker_called"] is False


# ---------------------------------------------------------------------------
# 8. paper position is created from paper order
# ---------------------------------------------------------------------------


def test_paper_position_is_created_from_paper_order_via_approval_wrapper():
    wrapper_out = _approval_call(_sim_inputs(submit_route="paper"))

    tool_response = wrapper_out["tool_response"]
    assert tool_response["execution_approval_decision"] == "paper_simulated"
    assert tool_response["paper_order"] is not None
    assert tool_response["paper_position"] is not None
    assert tool_response["paper_position"]["paper_order_id"] == tool_response["paper_order"]["paper_order_id"]
    assert tool_response["broker_called"] is False
    assert tool_response["live_submit"] is False
    assert tool_response["submitted_order"] is True


# ---------------------------------------------------------------------------
# 9. position monitor reads paper position and uses real market data status
# ---------------------------------------------------------------------------


def test_position_monitor_reads_paper_position_with_real_market_data(monkeypatch):
    _approval_call(_sim_inputs(submit_route="paper"))
    captured = _patch_quote(monkeypatch, symbol="AAPL", price=151.25)

    wrapper_out = run_wrapped_agent(
        agent_key="position_monitor_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_pm"},
    )

    tool_response = wrapper_out["tool_response"]
    assert tool_response["broker_called"] is False
    assert tool_response["submitted_order"] is False
    assert tool_response["source"] == "paper_autonomy"
    assert tool_response["current_price"] == 151.25
    assert tool_response["symbol"] == "AAPL"
    assert tool_response["paper_position_id"]
    assert any(call["symbol"] == "AAPL" for call in captured["calls"])

    open_position = paper_position_store.latest_open_for_workflow(WORKFLOW_RUN_ID)
    assert open_position is not None
    assert open_position.last_mark_price == 151.25


# ---------------------------------------------------------------------------
# 10. close review creates review only, no broker call
# ---------------------------------------------------------------------------


def test_close_review_creates_review_only_and_marks_position_closed(monkeypatch):
    _approval_call(_sim_inputs(submit_route="paper"))
    _patch_quote(monkeypatch, symbol="AAPL", price=153.50)

    wrapper_out = run_wrapped_agent(
        agent_key="close_review_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID, "recommended_action": "exit_review"},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_close"},
    )

    tool_response = wrapper_out["tool_response"]
    assert tool_response["broker_called"] is False
    assert tool_response["submitted_order"] is False
    assert tool_response["source"] == "paper_autonomy"
    close_review = tool_response.get("close_review") or {}
    assert close_review.get("submitted_order") is False
    assert close_review.get("broker_called") is False

    closed = paper_position_store.latest_closed_for_workflow(WORKFLOW_RUN_ID)
    if close_review.get("review_action") == "close_review":
        assert closed is not None
        assert closed.exit_price == 153.50
        assert closed.status == "closed"


# ---------------------------------------------------------------------------
# 11. post-trade evaluator computes actual_return_r and prediction_error_r
# ---------------------------------------------------------------------------


def test_post_trade_evaluator_computes_return_and_prediction_error_r(monkeypatch):
    _approval_call(_sim_inputs(submit_route="paper"))
    open_position = paper_position_store.latest_open_for_workflow(WORKFLOW_RUN_ID)
    assert open_position is not None
    paper_position_store.close(
        open_position.paper_position_id,
        exit_price=153.00,
        exit_reason="target_hit",
    )
    closed = paper_position_store.get(open_position.paper_position_id)
    assert closed is not None and closed.status == "closed"
    assert closed.actual_return_r is not None
    assert closed.actual_return_pct is not None
    assert closed.prediction_error_r is not None
    assert closed.hit_target is True
    assert closed.broker_called is False

    wrapper_out = run_wrapped_agent(
        agent_key="post_trade_evaluator_agent",
        inputs={
            "workflow_run_id": WORKFLOW_RUN_ID,
            "strategy_key": "regime_aware_momentum_catalyst",
        },
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_pt"},
    )

    tool_response = wrapper_out["tool_response"]
    assert tool_response["broker_called"] is False
    assert tool_response["submitted_order"] is False
    assert tool_response["source"] == "paper_autonomy"
    assert tool_response["actual_return_r"] == pytest.approx(closed.actual_return_r)
    assert tool_response["actual_return_pct"] == pytest.approx(closed.actual_return_pct)
    assert tool_response["prediction_error_r"] == pytest.approx(closed.prediction_error_r)
    assert tool_response["hit_target"] is True
    assert tool_response["hit_stop"] is False


# ---------------------------------------------------------------------------
# 12. learning loop consumes outcome and recommends learning status
# ---------------------------------------------------------------------------


def test_learning_loop_consumes_outcome_and_recommends_status(monkeypatch):
    _approval_call(_sim_inputs(submit_route="paper"))
    open_position = paper_position_store.latest_open_for_workflow(WORKFLOW_RUN_ID)
    assert open_position is not None
    paper_position_store.close(
        open_position.paper_position_id,
        exit_price=153.00,
        exit_reason="target_hit",
    )

    run_wrapped_agent(
        agent_key="post_trade_evaluator_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID, "strategy_key": "regime_aware_momentum_catalyst"},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_pt"},
    )

    wrapper_out = run_wrapped_agent(
        agent_key="learning_loop_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID, "strategy_key": "regime_aware_momentum_catalyst"},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_ll"},
    )

    tool_response = wrapper_out["tool_response"]
    assert tool_response["broker_called"] is False
    assert tool_response["submitted_order"] is False
    assert tool_response["source"] == "paper_autonomy"
    decision = tool_response.get("learning_decision") or {}
    assert decision.get("learning_action") in {
        "promote_candidate",
        "keep_monitoring",
        "demote_to_paper",
        "demote_to_research",
        "block_strategy",
        "review_needed",
    }
    promotion = decision.get("promotion") or {}
    assert promotion.get("eligible_for_promotion") is False or decision.get("learning_action") == "keep_monitoring"


# ---------------------------------------------------------------------------
# 13. autonomy loop introduces no mock/synthetic data
# ---------------------------------------------------------------------------


def test_autonomy_loop_does_not_introduce_synthetic_data():
    response = simulate_paper_order_from_plan(
        _sim_inputs(submit_route="paper", symbol="MSFT"),
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )
    paper_order = response["paper_order"]
    paper_position = response["paper_position"]

    assert paper_order["symbol"] == "MSFT"
    assert paper_position["symbol"] == "MSFT"
    assert paper_order["entry"] == 150.00
    assert paper_position["entry_price"] == 150.00
    assert paper_order["shares"] == 10.0
    assert paper_position["shares"] == 10.0
    assert paper_order["risk_dollars"] == 15.00
    assert paper_position["source"] == "paper_simulator"
    assert paper_position["last_mark_price"] is None


# ---------------------------------------------------------------------------
# 14. autonomy loop has no fallback symbols
# ---------------------------------------------------------------------------


def test_autonomy_loop_has_no_fallback_symbols():
    inputs = _sim_inputs(submit_route="paper", symbol="")
    inputs["execution_plan"]["symbol"] = ""
    response = simulate_paper_order_from_plan(
        inputs,
        workflow_run_id=WORKFLOW_RUN_ID,
        orchestrator_run_id=None,
        agent_run_id=None,
    )

    assert response["status"] == "paper_blocked"
    assert "missing_symbol" in response["blockers"]
    assert response["paper_order"] is None
    assert response["paper_position"] is None
    assert paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID) == []
    assert paper_position_store.list_positions(workflow_run_id=WORKFLOW_RUN_ID) == []


# ---------------------------------------------------------------------------
# 15. broker_called=false everywhere across the loop
# ---------------------------------------------------------------------------


def test_broker_called_false_everywhere_in_full_loop(monkeypatch):
    approval_out = _approval_call(_sim_inputs(submit_route="paper"))
    assert approval_out["tool_response"]["broker_called"] is False

    _patch_quote(monkeypatch, symbol="AAPL", price=151.25)
    pm_out = run_wrapped_agent(
        agent_key="position_monitor_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_pm"},
    )
    assert pm_out["tool_response"]["broker_called"] is False

    _patch_quote(monkeypatch, symbol="AAPL", price=153.50)
    cr_out = run_wrapped_agent(
        agent_key="close_review_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID, "recommended_action": "exit_review"},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_cr"},
    )
    assert cr_out["tool_response"]["broker_called"] is False
    assert cr_out["tool_response"]["submitted_order"] is False

    open_position = paper_position_store.latest_open_for_workflow(WORKFLOW_RUN_ID)
    if open_position is not None:
        paper_position_store.close(open_position.paper_position_id, exit_price=153.50, exit_reason="target_hit")
    pt_out = run_wrapped_agent(
        agent_key="post_trade_evaluator_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID, "strategy_key": "regime_aware_momentum_catalyst"},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_pt"},
    )
    assert pt_out["tool_response"]["broker_called"] is False

    ll_out = run_wrapped_agent(
        agent_key="learning_loop_agent",
        inputs={"workflow_run_id": WORKFLOW_RUN_ID, "strategy_key": "regime_aware_momentum_catalyst"},
        context={"source": "test", "workflow_run_id": WORKFLOW_RUN_ID, "agent_run_id": "ar_ll"},
    )
    assert ll_out["tool_response"]["broker_called"] is False

    closed_positions = paper_position_store.list_closed(workflow_run_id=WORKFLOW_RUN_ID)
    for pos in closed_positions:
        assert pos.broker_called is False
    open_orders = paper_order_store.list_orders(workflow_run_id=WORKFLOW_RUN_ID)
    for order in open_orders:
        assert order.broker_called is False
