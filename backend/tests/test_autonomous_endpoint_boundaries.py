from __future__ import annotations

import inspect
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.workflow_orchestrator.stage_plan import default_stage_plan
import app.services.workflow_orchestrator.service as orchestrator_service


client = TestClient(app)


@pytest.fixture(autouse=True)
def _force_memory_persistence(monkeypatch):
    import app.services.agent_runtime.store as agent_store
    import app.services.agent_runtime.wrappers as wrappers
    import app.services.approval_queue.service as approval_service
    import app.services.audit_log.service as audit_service
    from app.services.agent_runtime.wrappers.safety import SafetyResult

    monkeypatch.setattr(orchestrator_service, "_db_session", lambda: None)
    monkeypatch.setattr(agent_store, "_db_session", lambda: None)
    monkeypatch.setattr(approval_service, "_db_session", lambda: None)
    monkeypatch.setattr(audit_service, "_db_session", lambda: None)

    def fake_wrapped_agent(*, agent_key: str, inputs: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        symbol = str(inputs.get("symbol") or inputs.get("selected_symbol") or (inputs.get("symbols") or ["AMD"])[0]).upper()
        safety = SafetyResult(sanitized_inputs=dict(inputs), blockers=[], warnings=[])
        result: dict[str, Any] = {"status": "ok", "warnings": [], "blockers": []}
        if agent_key == "market_condition_agent":
            result["market_context"] = {"regime": "risk_on", "volatility_state": "normal", "liquidity_state": "good"}
        elif agent_key == "watchlist_builder_agent":
            result.update({"symbols": [symbol], "selected_candidate": symbol})
        elif agent_key == "strategy_selection_agent":
            result.update({"selected_strategy_key": "small_account_momentum", "proof_status": "unknown"})
        elif agent_key == "model_selection_agent":
            result.update({"selected_model_key": "rules_v1", "selected_model_keys": ["rules_v1"]})
        elif agent_key == "backtest_validation_agent":
            result.update({"proof_status": "backtest_required", "proof_id": "proof_preview"})
        elif agent_key == "qlib_research_agent":
            result.update({"qlib_available": False, "warnings": ["qlib_unavailable"]})
        elif agent_key == "execution_approval_agent":
            result.update({"approval": {"approval_id": "ap_test_preview"}})
        elif agent_key == "narrative_review_agent":
            result.update({"narrative": None, "warnings": ["narrative_review_deferred_by_policy"]})
        elif agent_key == "execution_planner_agent":
            result.update({"execution_plan": {"account_state": {"account_equity": inputs.get("account_equity")}}})
        return {
            "tool_name": f"test.{agent_key}",
            "tool_request": dict(inputs),
            "tool_response": result,
            "next_agent": None,
            "safety": safety,
        }

    monkeypatch.setattr(wrappers, "run_wrapped_agent", fake_wrapped_agent)


def _run_orchestrator(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "dry_run": True,
        "allow_submit": False,
        "symbols": ["AMD"],
        "source": "manual",
        "stop_at_stage": 100,
    }
    body.update(payload or {})
    response = client.post("/api/workflow-orchestrator/run", json=body)
    assert response.status_code == 200
    return response.json()["run"]


def _walk_values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_values(item)
    else:
        yield value


def _timeline_by_agent(run: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(row.get("agent_key")): row for row in run.get("stage_timeline", [])}


def test_canonical_orchestrator_endpoint_is_non_submitting():
    run = _run_orchestrator()

    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert run["workflow_run_id"]
    assert run["orchestrator_run_id"]


def test_orchestrator_stage_timeline_uses_default_stage_plan():
    run = _run_orchestrator()

    keys = [row["agent_key"] for row in run["stage_timeline"]]
    for key in default_stage_plan():
        assert key in keys


def test_selected_symbol_carries_from_watchlist_into_downstream_snapshots():
    run = _run_orchestrator({"symbols": ["AMD"]})
    timeline = _timeline_by_agent(run)

    watchlist_snapshot = timeline["watchlist_builder_agent"]["pipeline_inputs_snapshot"]
    downstream_snapshot = timeline["strategy_selection_agent"]["pipeline_inputs_snapshot"]

    assert watchlist_snapshot["selected_symbol"] == "AMD"
    assert downstream_snapshot["selected_symbol"] == "AMD"
    assert downstream_snapshot["symbol"] == "AMD"


def test_execution_planner_uses_small_account_default_in_orchestrator_context():
    run = _run_orchestrator()
    timeline = _timeline_by_agent(run)
    snapshot = timeline["execution_planner_agent"]["pipeline_inputs_snapshot"]

    assert snapshot["account_equity"] <= 1000.0


def test_orchestrator_response_does_not_leak_legacy_10000_account_default():
    run = _run_orchestrator()

    assert 10000 not in list(_walk_values(run))
    assert 10000.0 not in list(_walk_values(run))


def test_orchestrator_service_does_not_call_old_autonomous_controller_surfaces():
    source = inspect.getsource(orchestrator_service)
    forbidden = (
        "run_decision_workflow",
        "run_signal_agents",
        "run_strategy_workflow_from_signal",
        "update_auto_run_state",
        "place_trade_now_order",
        "place_autonomous_trade_order",
        "submit_execution",
    )

    for name in forbidden:
        assert name not in source


def test_qlib_unavailable_does_not_fail_orchestrator():
    run = _run_orchestrator()
    keys = [row["agent_key"] for row in run["stage_timeline"]]

    assert "qlib_research_agent" in keys
    assert run["status"] != "failed"


def test_approval_queue_creation_does_not_submit_broker_order():
    run = _run_orchestrator({"stop_at_stage": 14})

    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["execution_boundary_reached"] is True


def test_narrative_review_does_not_call_llm_by_default():
    run = _run_orchestrator({"stop_at_stage": 15})
    keys = [row["agent_key"] for row in run["stage_timeline"]]

    assert "narrative_review_agent" in keys
    assert run["llm_used"] is False
