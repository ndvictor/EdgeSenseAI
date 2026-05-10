from __future__ import annotations

import inspect
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.services.workflow_orchestrator.service as orchestrator_service
from app.services.agent_runtime.models import AgentRunRequest, AgentRunResult, WorkflowRunCreateRequest, WorkflowRunRecord, iso_utc_now


client = TestClient(app)
_RUN_CACHE: dict[tuple[tuple[str, str], ...], dict[str, Any]] = {}


@pytest.fixture(autouse=True)
def _force_memory_persistence(monkeypatch):
    import app.services.workflow_governance.service as governance_service

    _RUN_CACHE.clear()
    monkeypatch.setattr(orchestrator_service, "_db_session", lambda: None)
    monkeypatch.setattr(orchestrator_service, "write_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        orchestrator_service,
        "default_stage_plan",
        lambda **_kwargs: [
            "account_owner_policy_agent",
            "watchlist_builder_agent",
            "strategy_selection_agent",
            "qlib_research_agent",
            "small_account_feasibility_agent",
            "strategy_eligibility_agent",
            "execution_planner_agent",
        ],
    )
    monkeypatch.setattr(governance_service, "get_active_workflow_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(orchestrator_service, "orchestrator_pipeline_agent_count", lambda: 7)
    monkeypatch.setattr(governance_service, "effective_bool", lambda key: key in {"BROKER_EXECUTION_ENABLED", "LIVE_TRADING_ENABLED", "PAPER_TRADING_ENABLED", "REQUIRE_HUMAN_APPROVAL", "WORKFLOW_ENABLED"})

    def fake_create_workflow_run(req: WorkflowRunCreateRequest) -> WorkflowRunRecord:
        now = iso_utc_now()
        return WorkflowRunRecord(
            workflow_run_id="wr_test_autonomous_boundaries",
            workflow_name=req.workflow_name,
            asset_class=req.asset_class,
            horizon=req.horizon,
            mode=req.mode,
            source=req.source,
            created_at=now,
            updated_at=now,
            metadata=req.metadata,
        )

    def fake_create_agent_run(req: AgentRunRequest) -> AgentRunResult:
        inputs = dict(req.inputs or {})
        agent_key = req.agent_key
        symbol = str(inputs.get("symbol") or inputs.get("selected_symbol") or (inputs.get("symbols") or ["TEST_STOCK_A"])[0]).upper()
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
        elif agent_key == "small_account_feasibility_agent":
            result.update(
                {
                    "decision": "pass",
                    "account_equity": inputs.get("account_equity", 1000.0),
                    "max_risk_dollars": 5.0,
                    "max_daily_loss_dollars": 15.0,
                    "feasible_symbols": [symbol],
                    "rejected_symbols": [],
                    "blockers": [],
                    "warnings": [],
                }
            )
        elif agent_key == "execution_approval_agent":
            result.update({"approval": {"approval_id": "ap_test_preview"}})
        elif agent_key == "narrative_review_agent":
            result.update({"narrative": None, "warnings": ["narrative_review_deferred_by_policy"]})
        elif agent_key == "execution_planner_agent":
            result.update({"execution_plan": {"account_state": {"account_equity": inputs.get("account_equity")}}})
        now = iso_utc_now()
        return AgentRunResult(
            run_id=f"ar_test_{agent_key}",
            workflow_run_id=req.workflow_run_id or "wr_test_autonomous_boundaries",
            agent_key=agent_key,
            status="completed",
            decision={"phase": "test", "agent_key": agent_key, "tool": f"test.{agent_key}", "result": result},
            blockers=[],
            warnings=list(result.get("warnings") or []),
            next_action="ok",
            next_agent=None,
            artifacts={"llm_used": False, "broker_called": False, "submitted_order": False},
            trace_id=f"tr_test_{agent_key}",
            trace=[],
            idempotency_key=req.idempotency_key or f"test:{agent_key}",
            inputs_hash=f"hash:{agent_key}",
            created_at=now,
            persistence_mode="memory",
        )

    monkeypatch.setattr(orchestrator_service, "create_workflow_run", fake_create_workflow_run)
    monkeypatch.setattr(orchestrator_service, "create_agent_run", fake_create_agent_run)


def _run_orchestrator(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = {
        "dry_run": True,
        "allow_submit": False,
        "symbols": ["TEST_STOCK_A"],
        "source": "manual",
        "stop_at_stage": 100,
    }
    body.update(payload or {})
    cache_key = tuple(sorted((key, repr(value)) for key, value in body.items()))
    if cache_key in _RUN_CACHE:
        return _RUN_CACHE[cache_key]
    response = client.post("/api/workflow-orchestrator/run", json=body)
    assert response.status_code == 200
    run = response.json()["run"]
    _RUN_CACHE[cache_key] = run
    return run


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

    assert run["allow_submit"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False
    assert run["workflow_run_id"]
    assert run["orchestrator_run_id"]


def test_orchestrator_stage_timeline_uses_default_stage_plan():
    run = _run_orchestrator()

    keys = [row["agent_key"] for row in run["stage_timeline"]]
    for key in ["account_owner_policy_agent", "watchlist_builder_agent", "strategy_selection_agent", "small_account_feasibility_agent", "execution_planner_agent"]:
        assert key in keys


def test_selected_symbol_carries_from_watchlist_into_downstream_snapshots():
    run = _run_orchestrator({"symbols": ["TEST_STOCK_A"]})
    timeline = _timeline_by_agent(run)

    watchlist_snapshot = timeline["watchlist_builder_agent"]["pipeline_inputs_snapshot"]
    downstream_snapshot = timeline["strategy_selection_agent"]["pipeline_inputs_snapshot"]

    assert watchlist_snapshot["selected_symbol"] == "TEST_STOCK_A"
    assert downstream_snapshot["selected_symbol"] == "TEST_STOCK_A"
    assert downstream_snapshot["symbol"] == "TEST_STOCK_A"


def test_execution_planner_uses_small_account_default_in_orchestrator_context():
    run = _run_orchestrator()
    timeline = _timeline_by_agent(run)
    snapshot = timeline["execution_planner_agent"]["pipeline_inputs_snapshot"]

    assert snapshot["account_equity"] <= 1000.0
    assert snapshot["max_risk_dollars"] == 5.0
    assert snapshot["max_daily_loss_dollars"] == 15.0


def test_small_account_stage_in_plan_before_strategy_eligibility():
    from app.services.workflow_orchestrator.stage_plan import default_stage_plan

    plan = default_stage_plan()

    assert "small_account_feasibility_agent" in plan
    assert plan.index("small_account_feasibility_agent") < plan.index("strategy_eligibility_agent")


def test_orchestrator_snapshots_include_small_account_fields():
    run = _run_orchestrator()
    timeline = _timeline_by_agent(run)
    snapshot = timeline["strategy_eligibility_agent"]["pipeline_inputs_snapshot"]

    assert snapshot["small_account_decision"] == "feasible"
    assert snapshot["max_risk_dollars"] == 5.0
    assert snapshot["max_daily_loss_dollars"] == 15.0
    assert snapshot["feasible_symbols"] == ["TEST_STOCK_A"]


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


def test_qlib_unavailable_does_not_fail_orchestrator(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "default_stage_plan", lambda **_kwargs: ["account_owner_policy_agent", "qlib_research_agent"])
    run = _run_orchestrator()
    keys = [row["agent_key"] for row in run["stage_timeline"]]

    assert "qlib_research_agent" in keys
    assert run["status"] != "failed"


def test_approval_queue_creation_does_not_submit_broker_order(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "default_stage_plan", lambda **_kwargs: ["account_owner_policy_agent", "execution_approval_agent"])
    run = _run_orchestrator()

    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["execution_boundary_reached"] is True


def test_narrative_review_does_not_call_llm_by_default(monkeypatch):
    monkeypatch.setattr(orchestrator_service, "default_stage_plan", lambda **_kwargs: ["account_owner_policy_agent", "narrative_review_agent"])
    run = _run_orchestrator()
    keys = [row["agent_key"] for row in run["stage_timeline"]]

    assert "narrative_review_agent" in keys
    assert run["llm_used"] is False


def test_dry_run_governance_blockers_continue_with_trace():
    run = _run_orchestrator({"dry_run": True, "source": "runtime", "stop_at_stage": 3})

    assert run["stage_timeline"]
    assert "broker_execution_blocked_v1" in run["governance_blockers"]
    assert "live_trading_blocked_v1" in run["governance_blockers"]
    assert run["preview_continued_despite_governance_blockers"] is True
    assert run["source_mode"] == "runtime"
    assert run["using_non_real_data"] is False
    assert run["allow_submit"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False


def test_non_dry_run_governance_blockers_stop_before_stages():
    run = _run_orchestrator({"dry_run": False, "source": "runtime", "stop_at_stage": 3})

    assert run["status"] == "blocked"
    assert run["stage_timeline"] == []
    assert "broker_execution_blocked_v1" in run["governance_blockers"]
    assert "live_trading_blocked_v1" in run["governance_blockers"]
    assert run["preview_continued_despite_governance_blockers"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False


# ---------- DeepAgents advisory layer must not cross broker / submit boundaries ----------


def test_orchestrator_run_remains_non_submitting_with_reasoning_enabled(monkeypatch):
    """Even when AGENT_REASONING_ENABLED=true, orchestrator must not submit or call broker."""
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "true")
    run = _run_orchestrator()

    assert run["allow_submit"] is False
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False


def test_agent_runtime_status_surfaces_capability_flags():
    response = client.get("/api/agent-runtime/status")
    assert response.status_code == 200
    payload = response.json()

    summary = payload.get("summary") or {}
    safety = payload.get("safety") or {}
    flags = summary.get("agent_capability_flags") or safety.get("agent_capability_flags")

    assert isinstance(flags, dict)
    for required in (
        "agent_reasoning_enabled",
        "agent_can_recommend_trades",
        "agent_can_create_paper_plans",
        "agent_can_create_approval_requests",
        "agent_can_submit_paper_orders",
        "agent_can_submit_live_orders",
    ):
        assert required in flags
    # Live submission is hard-gated regardless of the flag value.
    assert flags["agent_can_submit_live_orders"] is False
    assert safety["no_broker_calls"] is True
    assert safety["no_execution_submit"] is True
    assert safety["no_llm_for_trade_decision"] is True
