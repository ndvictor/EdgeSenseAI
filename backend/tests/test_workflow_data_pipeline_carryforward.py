from __future__ import annotations

from typing import Any

import pytest

import app.services.agent_runtime.wrappers.glue_agents as glue_agents
import app.services.workflow_orchestrator.service as orchestrator_service
from app.services.agent_runtime.models import AgentRunRequest, AgentRunResult, WorkflowRunCreateRequest, WorkflowRunRecord, iso_utc_now
from app.services.workflow_orchestrator.pipeline_carryforward import apply_stage_carryforward
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def _agent_result(agent_key: str, result: dict[str, Any], *, blockers: list[str] | None = None, warnings: list[str] | None = None) -> AgentRunResult:
    now = iso_utc_now()
    return AgentRunResult(
        run_id=f"ar_{agent_key}",
        workflow_run_id="wr_data_pipeline",
        agent_key=agent_key,
        status="blocked" if blockers else "completed",
        decision={"phase": "test", "agent_key": agent_key, "tool": f"test.{agent_key}", "result": result},
        blockers=blockers or [],
        warnings=warnings or [],
        next_action="ok",
        next_agent=None,
        artifacts={"llm_used": False, "broker_called": False, "submitted_order": False},
        trace_id=f"tr_{agent_key}",
        trace=[],
        idempotency_key=f"idempotency:{agent_key}",
        inputs_hash=f"hash:{agent_key}",
        created_at=now,
        persistence_mode="memory",
    )


def test_data_pipeline_fields_carry_forward_to_state():
    state = WorkflowCarryForwardState(symbols=["AMD", "MSFT"], source="runtime")
    result = {
        "decision": "degraded",
        "provider_status": {"AMD": {"status": "usable"}, "MSFT": {"status": "blocked"}},
        "provider_name": "yfinance",
        "source_mode": "runtime",
        "using_mock_data": False,
        "usable_symbols": ["AMD"],
        "rejected_symbols": ["MSFT"],
        "latest_snapshot_count": 1,
        "feature_row_count": 1,
        "persistence_status": "memory_fallback",
        "freshness_status": "fresh",
        "kafka_status": "configured_optional_not_active",
        "warnings": ["provider partially throttled"],
        "blockers": [],
    }

    apply_stage_carryforward(agent_key="data_readiness_agent", agent_result=_agent_result("data_readiness_agent", result), state=state)

    assert state.source_mode == "runtime"
    assert state.using_mock_data is False
    assert state.usable_symbols == ["AMD"]
    assert state.rejected_symbols == ["MSFT"]
    assert state.symbols == ["AMD"]
    assert state.selected_symbol == "AMD"
    assert state.kafka_status == "configured_optional_not_active"
    assert state.feature_row_count == 1


def test_watchlist_builder_receives_usable_symbols_from_carry_forward(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_build_watchlist(**kwargs):
        captured.update(kwargs)
        return {"symbols": kwargs["seed_symbols"], "selected_candidate": kwargs["seed_symbols"][0], "ranked_candidates": [], "next_action": "ok"}

    monkeypatch.setattr(glue_agents, "build_watchlist", fake_build_watchlist)

    out = glue_agents.run_glue_agent(
        agent_key="watchlist_builder_agent",
        inputs={"symbols": ["MSFT"], "usable_symbols": ["AMD"], "source": "runtime"},
        context={"source": "workflow_orchestrator"},
        safety=type("Safety", (), {"sanitized_inputs": {"symbols": ["MSFT"], "usable_symbols": ["AMD"], "source": "runtime", "asset_class": "stock", "horizon": "day_trading"}, "blockers": [], "warnings": []})(),
    )

    assert captured["seed_symbols"] == ["AMD"]
    assert out["tool_response"]["symbols"] == ["AMD"]


@pytest.fixture()
def _orchestrator_memory(monkeypatch):
    import app.services.workflow_governance.service as governance_service

    monkeypatch.setattr(orchestrator_service, "_db_session", lambda: None)
    monkeypatch.setattr(orchestrator_service, "write_event", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(orchestrator_service, "default_stage_plan", lambda **_kwargs: ["data_readiness_agent", "watchlist_builder_agent"])
    monkeypatch.setattr(orchestrator_service, "orchestrator_pipeline_agent_count", lambda: 2)
    monkeypatch.setattr(governance_service, "get_active_workflow_state", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(governance_service, "effective_bool", lambda key: key in {"PAPER_TRADING_ENABLED", "REQUIRE_HUMAN_APPROVAL", "WORKFLOW_ENABLED"})

    def fake_create_workflow_run(req: WorkflowRunCreateRequest) -> WorkflowRunRecord:
        now = iso_utc_now()
        return WorkflowRunRecord(
            workflow_run_id="wr_data_pipeline",
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
        if req.agent_key == "data_readiness_agent":
            return _agent_result(
                "data_readiness_agent",
                {
                    "decision": "data_ready",
                    "provider_status": {"AMD": {"status": "usable"}},
                    "provider_name": "yfinance",
                    "source_mode": req.inputs["source"],
                    "using_mock_data": False,
                    "usable_symbols": ["AMD"],
                    "rejected_symbols": [],
                    "latest_snapshot_count": 1,
                    "feature_row_count": 1,
                    "persistence_status": "memory_fallback",
                    "freshness_status": "fresh",
                    "kafka_status": "configured_optional_not_active",
                    "warnings": ["kafka_optional_not_active"],
                    "blockers": [],
                },
                warnings=["kafka_optional_not_active"],
            )
        assert req.inputs["usable_symbols"] == ["AMD"]
        return _agent_result("watchlist_builder_agent", {"symbols": ["AMD"], "selected_candidate": "AMD"})

    monkeypatch.setattr(orchestrator_service, "create_workflow_run", fake_create_workflow_run)
    monkeypatch.setattr(orchestrator_service, "create_agent_run", fake_create_agent_run)


def test_orchestrator_dry_run_response_includes_data_pipeline_fields(_orchestrator_memory):
    run = orchestrator_service.run_workflow(
        orchestrator_service.OrchestratorRunRequest(dry_run=True, source="runtime", symbols=["AMD"], allow_submit=False, stop_at_stage=2)
    )

    assert run.source_mode == "runtime"
    assert run.using_mock_data is False
    assert run.usable_symbols == ["AMD"]
    assert run.latest_snapshot_count == 1
    assert run.feature_row_count == 1
    assert run.persistence_status == "memory_fallback"
    assert run.freshness_status == "fresh"
    assert run.kafka_status == "configured_optional_not_active"
    timeline = {row["agent_key"]: row for row in run.stage_timeline}
    assert timeline["watchlist_builder_agent"]["pipeline_inputs_snapshot"]["usable_symbols"] == ["AMD"]
