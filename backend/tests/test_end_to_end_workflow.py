"""Phase 6 end-to-end platform completion and safety contracts."""

from __future__ import annotations

import os

from unittest.mock import patch

from app.core.effective_runtime import effective_bool as core_effective_bool
from app.main import app
from fastapi.testclient import TestClient

from app.services.approval_queue.models import ApprovalItemCreate
from app.services.approval_queue.service import create_item
from app.services.platform_readiness.final_report import build_final_readiness_status
from app.services.workflow_governance.models import WorkflowGovernanceCheckRequest
from app.services.workflow_governance.service import check_governance
from app.services.workflow_scheduler.models import SchedulerRunOnceRequest
from app.services.workflow_scheduler.service import run_once as scheduler_run_once
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.service import run_workflow

client = TestClient(app)

_CORE_LAB_NAMES = [
    "Agent Runtime Foundation",
    "Agent Wrapper Runtime",
    "Glue Agent Runtime",
    "Data Readiness Agent",
    "Market Condition Agent",
    "Watchlist Builder Agent",
    "Strategy Selection Agent",
    "Model Selection Agent",
    "Backtest Validation Agent",
    "Qlib Research Agent",
    "Qlib Integration Adapter",
    "Qlib Signal Score Adapter",
    "Proof Registry",
    "Model Evidence Registry",
    "Strategy Evidence Registry",
    "WorkflowOrchestratorAgent",
    "Workflow Run Backend",
    "Approval Queue Backend",
    "Audit Log Backend",
    "Workflow Scheduler Backend",
    "Workflow Governance Backend",
    "Platform Readiness Backend",
    "UI Workflow Dashboard",
]


def _flat_lab_units():
    r = client.get("/api/lab/inventory")
    assert r.status_code == 200
    inv = r.json()
    out = []
    for st in inv.get("stages", []) or []:
        for u in st.get("units", []) or []:
            out.append(u)
    return out


def test_final_readiness_payload_shape():
    payload = build_final_readiness_status()
    assert payload["status"] in ("ok", "warning", "blocked")
    assert "platform_completion" in payload
    pc = payload["platform_completion"]
    for k in (
        "agent_runtime_complete",
        "stage_agent_wrappers_complete",
        "glue_agents_complete",
        "qlib_adapter_complete",
        "orchestrator_complete",
        "approval_queue_complete",
        "audit_log_complete",
        "scheduler_complete",
        "governance_complete",
        "frontend_operations_complete",
        "platform_readiness_complete",
    ):
        assert k in pc
    assert "safety" in payload
    for k in ("no_default_broker_submit", "no_default_live_trading", "human_approval_required", "no_llm_decisioning", "qlib_safe_when_unavailable"):
        assert k in payload["safety"]
    assert "storage" in payload
    assert "endpoints" in payload
    assert "frontend_routes" in payload
    assert "missing_core_units" in payload
    assert "warnings" in payload
    assert "blockers" in payload
    assert payload["next_action"]


def test_final_readiness_http_contract():
    r = client.get("/api/final-readiness/status")
    assert r.status_code == 200
    body = r.json()
    assert body["data_mode"] == "final_readiness_v1"
    assert isinstance(body.get("endpoints"), list)


def test_platform_readiness_status_has_major_systems():
    r = client.get("/api/platform-readiness/status")
    assert r.status_code == 200
    body = r.json()
    assert body.get("status") == "ok"
    systems = body.get("systems") or {}
    for key in (
        "database",
        "agent_runtime",
        "workflow_orchestrator",
        "approval_queue",
        "audit_log",
        "workflow_scheduler",
        "governance",
        "qlib_integration",
        "proof_registry",
        "model_evidence",
        "strategy_evidence",
        "execution_gates",
    ):
        assert key in systems, f"missing systems.{key}"


def test_lab_inventory_core_platform_units_present():
    units = {u["name"]: u for u in _flat_lab_units()}
    for name in _CORE_LAB_NAMES:
        assert name in units, f"missing inventory unit {name}"
        u = units[name]
        assert u.get("backend_status") == "present", name
        assert u.get("status") not in ("need_to_build", "need_to_build_clarify", "unclear"), name


def test_workflow_orchestrator_run_safety_flags():
    r = client.post(
        "/api/workflow-orchestrator/run",
        json={
            "asset_class": "stock",
            "horizon": "day_trading",
            "mode": "paper_first",
            "source": "manual",
            "symbols": ["AMD"],
            "dry_run": True,
            "stop_at_stage": 11,
            "allow_submit": False,
            "require_human_approval": True,
        },
    )
    assert r.status_code == 200
    run = r.json()["run"]
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False


def test_workflow_orchestrator_creates_approval_at_execution_boundary_when_required():
    def _eff(key: str) -> bool:
        if key in ("BROKER_EXECUTION_ENABLED", "LIVE_TRADING_ENABLED"):
            return False
        return core_effective_bool(key)

    with patch("app.services.workflow_governance.service.effective_bool", side_effect=_eff):
        run = run_workflow(
            OrchestratorRunRequest(
                asset_class="stock",
                horizon="day_trading",
                mode="paper_first",
                source="manual",
                symbols=["AMD"],
                dry_run=True,
                stop_at_stage=20,
                allow_submit=False,
                require_human_approval=True,
            )
        )
    assert run.execution_boundary_reached is True
    assert run.approval_id
    assert run.submitted_order is False
    assert run.broker_called is False
    assert run.llm_used is False


def test_governance_blocks_non_stock_asset_class():
    req = WorkflowGovernanceCheckRequest(asset_class="crypto", horizon="day_trading", symbols=["BTC"], allow_submit=False, dry_run=True)
    out = check_governance(req)
    assert out.decision == "blocked"
    assert "asset_class_not_supported_v1" in out.blockers


def test_governance_blocks_allow_submit():
    req = WorkflowGovernanceCheckRequest(allow_submit=True, dry_run=True, symbols=["AMD"])
    out = check_governance(req)
    assert out.decision == "blocked"
    assert "allow_submit_blocked_v1" in out.blockers


def test_governance_blocks_when_live_trading_enabled():
    def _eff(key: str) -> bool:
        if key == "LIVE_TRADING_ENABLED":
            return True
        return core_effective_bool(key)

    with patch("app.services.workflow_governance.service.effective_bool", side_effect=_eff):
        req = WorkflowGovernanceCheckRequest(symbols=["AMD"], allow_submit=False, dry_run=True)
        out = check_governance(req)
    assert out.decision == "blocked"
    assert "live_trading_blocked_v1" in out.blockers


def test_scheduler_run_once_forces_safe_execution_flags():
    r = scheduler_run_once(
        SchedulerRunOnceRequest(workflow_request={"allow_submit": True, "dry_run": False, "symbols": ["AMD"], "stop_at_stage": 2})
    )
    run = r["run"]
    assert run["submitted_order"] is False
    assert run["broker_called"] is False
    assert run["llm_used"] is False


def test_approval_action_writes_audit_event():
    item = create_item(
        ApprovalItemCreate(
            workflow_run_id="wr_smoke_audit",
            orchestrator_run_id="orc_smoke_audit",
            approval_type="execution_boundary",
            status="pending",
            requested_action={"test": True},
        )
    )
    n0 = len(client.get("/api/audit-log/events?limit=200").json().get("events", []))
    client.post(f"/api/approval-queue/items/{item.approval_id}/approve", json={"actor": "phase6_test", "reason": "test"})
    events = client.get("/api/audit-log/events?limit=200").json().get("events", [])
    assert len(events) >= n0
    assert any(e.get("event_type") == "approval_approved" and e.get("metadata", {}).get("approval_id") == item.approval_id for e in events)


def test_qlib_status_safe_when_unavailable():
    r = client.get("/api/qlib/status")
    assert r.status_code == 200
    body = r.json()
    assert "qlib_available" in body
    assert isinstance(body["qlib_available"], bool)


def test_evidence_endpoints_status_ok():
    for path in ("/api/proof-registry/status", "/api/model-evidence/status", "/api/strategy-evidence/status"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.json().get("status") == "ok"


def test_agent_runtime_ready_agent_registry_superset():
    r = client.get("/api/agent-runtime/agents")
    assert r.status_code == 200
    keys = {a["agent_key"] for a in r.json().get("agents", [])}
    expected = {
        "session_router_agent",
        "workflow_router_agent",
        "strategy_eligibility_agent",
        "trigger_monitor_agent",
        "execution_planner_agent",
        "data_readiness_agent",
        "market_condition_agent",
        "watchlist_builder_agent",
        "strategy_selection_agent",
        "model_selection_agent",
        "backtest_validation_agent",
        "qlib_research_agent",
        "workflow_orchestrator_agent",
    }
    missing = expected - keys
    assert not missing, missing
    for a in r.json().get("agents", []):
        if a["agent_key"] in expected:
            assert a["status"] == "ready"


def test_agent_runtime_trace_includes_tool_and_decision_events():
    wf = client.post(
        "/api/agent-runtime/workflow-runs",
        json={"workflow_name": "t", "asset_class": "stock", "horizon": "day_trading", "mode": "paper_first", "source": "manual"},
    )
    wr_id = wf.json()["workflow_run"]["workflow_run_id"]
    body = {
        "workflow_run_id": wr_id,
        "agent_key": "session_router_agent",
        "inputs": {"timestamp": "2026-05-07T09:35:00-05:00"},
        "context": {"source": "e2e_test"},
        "dry_run": True,
        "idempotency_key": f"e2e_trace_{os.urandom(4).hex()}",
    }
    r = client.post("/api/agent-runtime/agent-runs", json=body)
    assert r.status_code == 200
    trace = r.json()["agent_run"]["trace"]
    kinds = {ev["event"] for ev in trace}
    assert "tool_called" in kinds
    assert "decision_recorded" in kinds


def test_no_execution_submit_in_this_module():
    src = open(__file__, encoding="utf-8").read()
    needle = "/api/execution" + "/submit"
    assert needle not in src
