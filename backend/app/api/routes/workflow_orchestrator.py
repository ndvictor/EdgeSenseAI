from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.service import (
    get_latest_orchestrator_run,
    get_orchestrator_run,
    get_orchestrator_status,
    list_orchestrator_runs,
    pause_workflow,
    resume_workflow,
    run_workflow,
    stop_workflow,
    trace_workflow,
)

router = APIRouter(prefix="/workflow-orchestrator", tags=["workflow-orchestrator"])


@router.post("/run")
def post_run(body: OrchestratorRunRequest):
    run = run_workflow(body)
    return {"status": "ok", "run": run.model_dump()}


@router.get("/status/{workflow_run_id}")
def get_status(workflow_run_id: str):
    # minimal: use trace + latest run if exists
    return {"status": "ok", "workflow_run_id": workflow_run_id, "trace": trace_workflow(workflow_run_id)}


@router.get("/latest")
def get_latest():
    run = get_latest_orchestrator_run()
    return {"status": "ok", "run": run.model_dump() if run else None}


@router.get("/runs")
def get_runs(limit: int = 20):
    return {"status": "ok", "runs": [r.model_dump() for r in list_orchestrator_runs(limit=limit)]}


@router.get("/trace/{workflow_run_id}")
def get_trace(workflow_run_id: str):
    return trace_workflow(workflow_run_id)


@router.post("/{workflow_run_id}/pause")
def post_pause(workflow_run_id: str):
    return pause_workflow(workflow_run_id)


@router.post("/{workflow_run_id}/resume")
def post_resume(workflow_run_id: str):
    return resume_workflow(workflow_run_id)


@router.post("/{workflow_run_id}/stop")
def post_stop(workflow_run_id: str):
    return stop_workflow(workflow_run_id)


@router.get("/health")
def get_health():
    return get_orchestrator_status().model_dump()

