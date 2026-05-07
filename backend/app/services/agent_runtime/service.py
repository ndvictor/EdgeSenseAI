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


def build_status() -> AgentRuntimeStatusResponse:
    updated_at = iso_utc_now()
    return AgentRuntimeStatusResponse(
        updated_at=updated_at,
        summary={
            "registered_agents_count": len(list_agents()),
            "workflow_runs_count": len(list_workflow_runs()),
            "agent_runs_count": len(list_agent_runs()),
            "persistence_mode": persistence_mode(),
            "llm_required": False,
            "broker_submission_enabled": False,
            "next_action": "Phase 0/1 foundation only. Implement Phase 2 wrappers to execute tools safely.",
        },
        safety={
            "no_broker_calls": True,
            "no_execution_submit": True,
            "no_llm_calls": True,
            "dry_run_default": True,
        },
    )


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

    # Create workflow run if absent
    if req.workflow_run_id:
        wr = get_workflow_run(req.workflow_run_id)
        if wr is None:
            # Auto-create if caller references missing run id (foundation convenience)
            wr = create_workflow_run(WorkflowRunCreateRequest())
    else:
        wr = create_workflow_run(WorkflowRunCreateRequest())

    assert wr is not None

    # Idempotency
    fp = fingerprint(
        agent_key=req.agent_key,
        workflow_run_id=wr.workflow_run_id,
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

    now = iso_utc_now()
    run_id = f"ar_{uuid4().hex[:12]}_{now.replace('-', '').replace(':', '')}"
    trace_id = f"tr_{uuid4().hex[:10]}"

    stage_num = req.requested_stage or descriptor.stage_number

    decision = {
        "phase": "foundation_only",
        "message": "Agent runtime recorded this run. Real tool execution starts in Phase 2 wrappers.",
    }

    trace = [
        _trace_event("request_received", {"agent_key": req.agent_key, "dry_run": bool(req.dry_run)}),
        _trace_event(
            "safety_boundary_checked",
            {
                "no_broker_calls": True,
                "no_execution_submit": True,
                "no_llm_calls": True,
                "dry_run_default": True,
            },
        ),
        _trace_event("idempotency_checked", {"fingerprint": fp, "idempotency_key": req.idempotency_key}),
        _trace_event("result_recorded", {"status": "recorded"}),
    ]

    result = AgentRunResult(
        run_id=run_id,
        workflow_run_id=wr.workflow_run_id,
        agent_key=req.agent_key,
        status="recorded",
        decision=decision,
        blockers=[],
        warnings=[],
        next_action="Phase 0/1 recorded. Implement Phase 2 agent wrapper to execute deterministically.",
        next_agent=None,
        artifacts={},
        trace_id=trace_id,
        trace=trace,
        idempotency_key=req.idempotency_key or fp,
        inputs_hash=fp,
        created_at=now,
    )

    store_agent_run(result)
    index_idempotency(fp, run_id)

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
    store_workflow_run(wr)

    return result


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
        "latest_workflow_run": latest_wr,
        "latest_agent_runs_by_key": latest_by_key,
        "message": "Phase 0/1 foundation only. Agent runs are recorded, not executed.",
    }

