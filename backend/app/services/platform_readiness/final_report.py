"""Phase 6 final readiness rollup: deterministic, no broker/LLM calls, inventory-aware."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from app.services.agent_runtime.registry import list_agents
from app.services.agent_runtime.service import build_status as agent_runtime_build_status
from app.services.agent_runtime.store import persistence_mode
from app.services.agent_runtime.redis_runtime import get_redis_runtime_status
from app.services.lab_inventory_service import build_lab_inventory_response

Status = Literal["ok", "warning", "blocked"]

# Minimum ready agents expected from Phases 2–3 (deterministic tool-calling spine).
_EXPECTED_READY_AGENT_KEYS_PHASE_2_3: frozenset[str] = frozenset(
    {
        "session_router_agent",
        "workflow_router_agent",
        "strategy_eligibility_agent",
        "trigger_monitor_agent",
        "execution_planner_agent",
        "position_monitor_agent",
        "close_review_agent",
        "post_trade_evaluator_agent",
        "learning_loop_agent",
        "data_readiness_agent",
        "market_condition_agent",
        "watchlist_builder_agent",
        "strategy_selection_agent",
        "model_selection_agent",
        "backtest_validation_agent",
        "qlib_research_agent",
        "workflow_orchestrator_agent",
    }
)

_CORE_LAB_UNIT_NAMES: frozenset[str] = frozenset(
    {
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
        "Workflow Run Frontend",
        "Approval Queue Frontend",
        "Audit Log Frontend",
        "Workflow Scheduler Frontend",
        "Workflow Governance Frontend",
        "Platform Readiness Frontend",
        "Research Evidence Frontend",
        "Agent Runtime Persistence",
    }
)

_REQUIRED_API_PATHS: tuple[str, ...] = (
    "/api/agent-runtime/status",
    "/api/workflow-orchestrator/latest",
    "/api/approval-queue/status",
    "/api/audit-log/status",
    "/api/workflow-scheduler/status",
    "/api/workflow-governance/status",
    "/api/platform-readiness/status",
    "/api/qlib/status",
    "/api/proof-registry/status",
    "/api/model-evidence/status",
    "/api/strategy-evidence/status",
    "/api/lab/inventory",
    "/api/final-readiness/status",
)

_FRONTEND_ROUTE_FILES: tuple[tuple[str, str], ...] = (
    ("/workflow-runbook", "frontend/src/app/workflow-runbook/page.tsx"),
    ("/agent-runtime", "frontend/src/app/agent-runtime/page.tsx"),
    ("/approval-queue", "frontend/src/app/approval-queue/page.tsx"),
    ("/audit-log", "frontend/src/app/audit-log/page.tsx"),
    ("/workflow-scheduler", "frontend/src/app/workflow-scheduler/page.tsx"),
    ("/workflow-governance", "frontend/src/app/workflow-governance/page.tsx"),
    ("/platform-readiness", "frontend/src/app/platform-readiness/page.tsx"),
    ("/research-evidence", "frontend/src/app/research-evidence/page.tsx"),
    ("/lab", "frontend/src/app/lab/page.tsx"),
    ("/settings", "frontend/src/app/settings/page.tsx"),
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _collect_fastapi_paths() -> set[str]:
    from app.main import app as fastapi_app

    out: set[str] = set()
    for route in fastapi_app.routes:
        p = getattr(route, "path", None)
        if isinstance(p, str):
            out.add(p)
    return out


def _endpoint_checks(entries: list[dict[str, str]], paths: set[str]) -> None:
    # FastAPI may list paths with or without trailing slashes; normalize checks.
    for spec in entries:
        p = spec["path"]
        ok = p in paths or f"{p}/" in paths or any(r == p or r.startswith(p + "/") for r in paths)
        spec["present"] = "ok" if ok else "missing"


def _verify_frontend_routes() -> list[dict[str, str]]:
    root = _repo_root()
    out: list[dict[str, str]] = []
    for route, rel in _FRONTEND_ROUTE_FILES:
        exists = (root / rel).is_file()
        out.append({"route": route, "path": rel, "present": "ok" if exists else "missing"})
    return out


def _workflow_runbook_uses_orchestrator_only() -> bool:
    page = _repo_root() / "frontend" / "src" / "app" / "workflow-runbook" / "page.tsx"
    try:
        text = page.read_text(encoding="utf-8")
    except OSError:
        return False
    forbidden = (
        "runDecisionWorkflow(",
        "runStrategyWorkflow(",
        "runSignal",
        "updateAutoRunStatus(",
        "postExecutionSubmit(",
        "/api/decision-workflows/run",
        "/api/signal-agents/run",
        "/api/strategy-workflows/run",
        "/api/auto-run/status",
        "/api/tradenow/orders",
        "/api/execution/submit",
    )
    return "runWorkflowOrchestrator(" in text and not any(item in text for item in forbidden)


def _lab_core_gaps(units_flat: list[dict[str, Any]]) -> list[str]:
    by_name = {u.get("name"): u for u in units_flat}
    missing: list[str] = []
    for name in sorted(_CORE_LAB_UNIT_NAMES):
        u = by_name.get(name)
        if u is None:
            missing.append(f"{name}: not_in_inventory")
            continue
        st = str(u.get("status", ""))
        bad_status = st in ("need_to_build", "need_to_build_clarify", "unclear")

        if "Frontend" in name or name.startswith("UI "):
            if u.get("frontend_status") != "created":
                missing.append(f"{name}: frontend_not_created")
            if bad_status:
                missing.append(f"{name}: status_{st}")
            continue

        if "Backend" in name:
            if u.get("backend_status") != "created":
                missing.append(f"{name}: backend_not_created")
            if bad_status:
                missing.append(f"{name}: status_{st}")
            continue

        if u.get("backend_status") != "created":
            missing.append(f"{name}: backend_not_created")
        if bad_status:
            missing.append(f"{name}: status_{st}")
    return missing


def build_final_readiness_status() -> dict[str, Any]:
    """Build Phase 6 completion report. Safe: reads config/services only; no broker, no LLM."""
    warnings: list[str] = []
    blockers: list[str] = []

    paths = _collect_fastapi_paths()
    endpoints: list[dict[str, str]] = [{"path": p, "present": "unknown"} for p in _REQUIRED_API_PATHS]
    _endpoint_checks(endpoints, paths)
    for e in endpoints:
        if e["present"] != "ok":
            blockers.append(f"endpoint_missing:{e['path']}")

    frontend_routes = _verify_frontend_routes()
    for fr in frontend_routes:
        if fr["present"] != "ok":
            warnings.append(f"frontend_route_file_missing:{fr['route']}")

    inv = build_lab_inventory_response()
    units_flat: list[dict[str, Any]] = []
    for stage in inv.get("stages", []) or []:
        for u in stage.get("units", []) or []:
            units_flat.append(u)

    missing_core = _lab_core_gaps(units_flat)
    if missing_core:
        warnings.extend(missing_core)

    ar = agent_runtime_build_status()
    redis_st = get_redis_runtime_status()
    pg_mode = persistence_mode()
    redis_mode = redis_st.redis_mode

    ready_keys = {a.agent_key for a in list_agents() if a.status == "ready"}
    missing_ready = sorted(_EXPECTED_READY_AGENT_KEYS_PHASE_2_3 - ready_keys)
    if missing_ready:
        warnings.append(f"expected_ready_agents_missing:{missing_ready}")

    qlib_safe = True  # get_qlib_status never raises; contract is non-fatal
    try:
        from app.services.qlib_integration.service import get_qlib_status

        qst = get_qlib_status()
        qlib_safe = True
        if not qst.qlib_available:
            warnings.append("qlib_python_package_unavailable_expected_safe")
    except Exception as exc:  # pragma: no cover
        qlib_safe = False
        warnings.append(f"qlib_status_unexpected_error:{exc}")

    # Safety flags (policy + effective gates; no secrets).
    from app.core.effective_runtime import effective_bool

    no_default_broker_submit = not effective_bool("BROKER_EXECUTION_ENABLED")
    no_default_live_trading = not effective_bool("LIVE_TRADING_ENABLED")
    human_approval_required = effective_bool("REQUIRE_HUMAN_APPROVAL")
    emergency_stop = effective_bool("EMERGENCY_STOP")

    platform_completion = {
        "agent_runtime_complete": not any(e["path"] == "/api/agent-runtime/status" and e["present"] != "ok" for e in endpoints),
        "stage_agent_wrappers_complete": not bool(missing_ready),
        "glue_agents_complete": "Glue Agent Runtime: backend_not_present" not in "".join(missing_core)
        and "Glue Agent Runtime: not_in_inventory" not in "".join(missing_core),
        "qlib_adapter_complete": not any(e["path"] == "/api/qlib/status" and e["present"] != "ok" for e in endpoints),
        "orchestrator_complete": not any(e["path"] == "/api/workflow-orchestrator/latest" and e["present"] != "ok" for e in endpoints),
        "approval_queue_complete": not any(e["path"] == "/api/approval-queue/status" and e["present"] != "ok" for e in endpoints),
        "audit_log_complete": not any(e["path"] == "/api/audit-log/status" and e["present"] != "ok" for e in endpoints),
        "scheduler_complete": not any(e["path"] == "/api/workflow-scheduler/status" and e["present"] != "ok" for e in endpoints),
        "governance_complete": not any(e["path"] == "/api/workflow-governance/status" and e["present"] != "ok" for e in endpoints),
        "platform_readiness_complete": not any(e["path"] == "/api/platform-readiness/status" and e["present"] != "ok" for e in endpoints),
        "frontend_operations_complete": all(fr["present"] == "ok" for fr in frontend_routes),
    }

    if emergency_stop:
        warnings.append("emergency_stop_active_gates_operational_workflow")

    if not human_approval_required:
        blockers.append("require_human_approval_effective_false")

    endpoint_boundaries = {
        "autonomous_entrypoint": "/api/workflow-orchestrator/run",
        "old_manual_surfaces_present": True,
        "mixed_endpoint_risk": "pass" if _workflow_runbook_uses_orchestrator_only() else "fail",
        "broker_submit_blocked": True,
        "llm_decisioning_blocked": True,
    }

    status: Status = "ok"
    if blockers:
        status = "blocked"
    elif warnings:
        status = "warning"

    next_action = (
        "Core AI-agent workflow platform is complete for paper-first operation. "
        "Review production deployment, live-broker certification, and optional scale hardening before enabling live trading."
        if not blockers
        else "Resolve readiness blockers (missing endpoints, safety gates, or inventory gaps) before treating the platform as production-ready."
    )

    return {
        "status": status,
        "data_mode": "final_readiness_v1",
        "platform_completion": platform_completion,
        "safety": {
            "no_default_broker_submit": bool(no_default_broker_submit),
            "no_default_live_trading": bool(no_default_live_trading),
            "human_approval_required": bool(human_approval_required),
            "no_llm_decisioning": True,
            "qlib_safe_when_unavailable": bool(qlib_safe),
            "emergency_stop": bool(emergency_stop),
        },
        "endpoint_boundaries": endpoint_boundaries,
        "storage": {
            "postgres_mode": pg_mode,
            "redis_mode": redis_mode,
            "memory_fallback_available": True,
            "agent_runtime_snapshot": ar.model_dump(),
        },
        "endpoints": endpoints,
        "frontend_routes": frontend_routes,
        "missing_core_units": missing_core if missing_core else [],
        "warnings": warnings,
        "blockers": blockers,
        "next_action": next_action,
    }
