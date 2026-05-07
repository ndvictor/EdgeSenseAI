from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.agent_runtime.idempotency import fingerprint
from app.services.agent_runtime.models import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntimeStatusResponse,
    WorkflowRunCreateRequest,
    WorkflowRunRecord,
    iso_utc_now,
)
from app.services.agent_runtime.registry import list_agents, require_agent
from app.services.agent_runtime.store import (
    get_agent_run as _get_agent_run,
    get_latest_agent_run_id,
    get_workflow_run as _get_workflow_run,
    index_idempotency,
    list_agent_runs,
    list_workflow_runs,
    lookup_idempotency,
    persistence_mode,
    store_agent_run,
    store_workflow_run,
)
from app.services.agent_runtime.redis_runtime import (
    acquire_agent_lock,
    get_redis_runtime_status,
    release_agent_lock,
    set_active_workflow_state,
)


def build_status() -> AgentRuntimeStatusResponse:
    updated_at = iso_utc_now()
    redis_status = get_redis_runtime_status()
    return AgentRuntimeStatusResponse(
        updated_at=updated_at,
        summary={
            "registered_agents_count": len(list_agents()),
            "workflow_runs_count": len(list_workflow_runs()),
            "agent_runs_count": len(list_agent_runs()),
            "persistence_mode": persistence_mode(),
            "redis_mode": redis_status.redis_mode,
            "llm_required": False,
            "broker_submission_enabled": False,
            "next_action": "Phase 2 wrappers available for Stage 3/5/7/8/9/11/12/13/14 agents. Orchestrator comes later.",
        },
        safety={
            "no_broker_calls": True,
            "no_execution_submit": True,
            "no_llm_calls": True,
            "dry_run_default": True,
        },
    )


def _workflow_run_id_for_idempotency(req: AgentRunRequest) -> str:
    # Avoid coupling dedupe to auto-generated workflow_run_id.
    # If a workflow_run_id is supplied, include it; otherwise use a stable placeholder.
    return req.workflow_run_id or "auto"


def _ensure_workflow_run(req: AgentRunRequest) -> WorkflowRunRecord:
    if req.workflow_run_id:
        wr = get_workflow_run(req.workflow_run_id)
        if wr is not None:
            return wr
        return create_workflow_run(WorkflowRunCreateRequest())
    return create_workflow_run(WorkflowRunCreateRequest())


def create_workflow_run(req: WorkflowRunCreateRequest) -> WorkflowRunRecord:
    now = iso_utc_now()
    workflow_run_id = f"wr_{now.replace('-', '').replace(':', '')}"
    rec = WorkflowRunRecord(
        workflow_run_id=workflow_run_id,
        workflow_name=req.workflow_name,
        asset_class=req.asset_class,
        horizon=req.horizon,
        mode=req.mode,
        source=req.source,
        status="created",
        current_stage=None,
        current_agent_key=None,
        stage_states={},
        agent_run_ids=[],
        blockers=[],
        warnings=[],
        created_at=now,
        updated_at=now,
        metadata=req.metadata,
    )
    store_workflow_run(rec)
    return rec


def get_workflow_run(workflow_run_id: str) -> WorkflowRunRecord | None:
    return _get_workflow_run(workflow_run_id)


def get_agent_run(run_id: str) -> AgentRunResult | None:
    return _get_agent_run(run_id)


def _trace_event(event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"event": event, "details": details or {}, "at": iso_utc_now()}


def create_agent_run(req: AgentRunRequest) -> AgentRunResult:
    descriptor = require_agent(req.agent_key)
    if descriptor is None:
        raise ValueError(f"Unknown agent_key '{req.agent_key}'")

    # Idempotency
    fp = fingerprint(
        agent_key=req.agent_key,
        workflow_run_id=_workflow_run_id_for_idempotency(req),
        inputs=req.inputs,
        context=req.context,
        requested_stage=req.requested_stage,
        idempotency_key=req.idempotency_key,
    )
    existing_run_id = lookup_idempotency(fp)
    if existing_run_id:
        existing = get_agent_run(existing_run_id)
        if existing:
            # Return existing run with duplicate status (do not mutate persisted record).
            dup = existing.model_dump()
            dup["status"] = "duplicate"
            return AgentRunResult(**dup)

    # Create workflow run after idempotency check (so dedupe works even without workflow_run_id)
    wr = _ensure_workflow_run(req)

    now = iso_utc_now()
    run_id = f"ar_{uuid4().hex[:12]}_{now.replace('-', '').replace(':', '')}"
    trace_id = f"tr_{uuid4().hex[:10]}"

    stage_num = req.requested_stage or descriptor.stage_number

    lock_acquired = acquire_agent_lock(workflow_run_id=wr.workflow_run_id, agent_key=req.agent_key, ttl_seconds=60)

    # Phase 2 dispatch
    from app.services.agent_runtime.wrappers import WRAPPED_AGENT_KEYS, run_wrapped_agent

    is_wrapped = req.agent_key in WRAPPED_AGENT_KEYS and descriptor.status == "ready"
    try:
        if is_wrapped:
            wrapper_out = run_wrapped_agent(agent_key=req.agent_key, inputs=req.inputs or {}, context=req.context or {})
            tool_name = wrapper_out["tool_name"]
            tool_req = wrapper_out["tool_request"]
            tool_resp = wrapper_out["tool_response"]
            next_agent = wrapper_out.get("next_agent")
            safety = wrapper_out.get("safety")

            decision_payload, blockers, warnings, next_action, next_agent, artifacts = wrapper_outcome_to_result(
                agent_key=req.agent_key,
                tool_name=tool_name,
                tool_request=tool_req,
                tool_response=tool_resp,
                safety=safety,
                next_agent=next_agent,
            )
            status = "completed" if not blockers and tool_resp.get("status") != "blocked" else "blocked"
            decision = {
                "phase": "phase_2_wrapped",
                "agent_key": req.agent_key,
                "tool": tool_name,
                "result": decision_payload,
            }
        else:
            status = "blocked"
            blockers = ["agent_wrapper_not_implemented"]
            warnings = []
            next_agent = None
            artifacts = {"llm_used": False, "broker_called": False, "submitted_order": False}
            decision = {
                "implementation_status": "not_implemented",
                "message": "Agent is registered but wrapper is not implemented in Phase 2.",
                "agent_status": descriptor.status,
            }
            next_action = "Implement Phase 2 wrapper for this agent or mark it ready when available."
    finally:
        if lock_acquired:
            release_agent_lock(workflow_run_id=wr.workflow_run_id, agent_key=req.agent_key)

    trace = [
        _trace_event("agent_started", {"agent_key": req.agent_key, "dry_run": bool(req.dry_run)}),
        _trace_event(
            "safety_boundary_checked",
            {
                "no_broker_calls": True,
                "no_execution_submit": True,
                "no_llm_calls": True,
                "dry_run_default": True,
            },
        ),
        _trace_event("tool_selected", {"wrapped": bool(is_wrapped)}),
        _trace_event("tool_called", {"tool": decision.get("tool") if isinstance(decision, dict) else None}),
        _trace_event("tool_result_received", {"status": status}),
        _trace_event("idempotency_checked", {"fingerprint": fp, "idempotency_key": req.idempotency_key}),
        _trace_event("decision_recorded", {"agent_key": req.agent_key}),
        _trace_event(
            "persisted_to_postgres_or_memory",
            {"persistence_mode": persistence_mode(), "redis_mode": get_redis_runtime_status().redis_mode},
        ),
    ]

    result = AgentRunResult(
        run_id=run_id,
        workflow_run_id=wr.workflow_run_id,
        agent_key=req.agent_key,
        status=status,  # type: ignore[arg-type]
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        next_action=next_action,
        next_agent=next_agent,
        artifacts=artifacts,
        trace_id=trace_id,
        trace=trace,
        idempotency_key=req.idempotency_key or fp,
        inputs_hash=fp,
        created_at=now,
        persistence_mode=persistence_mode(),
        storage_metadata={"redis_lock_acquired": bool(lock_acquired)},
    )

    store_agent_run(result)
    index_idempotency(fp, run_id)
    set_active_workflow_state(
        workflow_run_id=wr.workflow_run_id,
        state={"workflow_run_id": wr.workflow_run_id, "current_agent_key": req.agent_key, "current_stage": stage_num, "updated_at": now},
    )

    # Update workflow run record (in-place update and persist back)
    wr.agent_run_ids.append(run_id)
    wr.current_agent_key = req.agent_key
    wr.current_stage = stage_num
    wr.stage_states[req.agent_key] = {
        "run_id": run_id,
        "status": result.status,
        "stage": stage_num,
        "created_at": now,
    }
    wr.updated_at = now
    wr.persistence_mode = persistence_mode()
    store_workflow_run(wr)

    return result


def wrapper_outcome_to_result(
    *,
    agent_key: str,
    tool_name: str,
    tool_request: dict[str, Any],
    tool_response: dict[str, Any],
    safety: Any,
    next_agent: str | None,
) -> tuple[dict[str, Any], list[str], list[str], str, str | None, dict[str, Any]]:
    from app.services.agent_runtime.wrappers.stage_wrappers import _wrap_result

    return _wrap_result(
        agent_key=agent_key,
        tool_name=tool_name,
        tool_request=tool_request,
        tool_response=tool_response,
        safety=safety,
        next_agent=next_agent,
    )


def get_latest_snapshot() -> dict[str, Any]:
    runs = list_workflow_runs()
    latest_wr = sorted(runs, key=lambda r: r.updated_at)[-1].model_dump() if runs else None

    latest_by_key: dict[str, Any] = {}
    for a in list_agents():
        rid = get_latest_agent_run_id(a.agent_key)
        latest_by_key[a.agent_key] = _get_agent_run(rid).model_dump() if rid and _get_agent_run(rid) else None

    return {
        "status": "ok",
        "data_mode": "agent_runtime_latest_v1",
        "updated_at": iso_utc_now(),
        "registered_agents_count": len(list_agents()),
        "persistence_mode": persistence_mode(),
        "redis_mode": get_redis_runtime_status().redis_mode,
        "latest_workflow_run": latest_wr,
        "latest_agent_runs_by_key": latest_by_key,
        "message": "Agent runtime latest snapshot (best-effort Postgres persistence; falls back to memory when unavailable).",
    }

