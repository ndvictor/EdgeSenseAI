"""Agent Runtime Foundation (Phase 0/1 only; no LLM) API routes."""

from fastapi import APIRouter, HTTPException

from app.services.agent_runtime.models import AgentRunRequest, WorkflowRunCreateRequest
from app.services.agent_runtime.registry import list_agents
from app.services.agent_runtime.service import (
    build_status,
    create_agent_run,
    create_workflow_run,
    get_agent_run,
    get_latest_snapshot,
    get_workflow_run,
)

router = APIRouter(prefix="/agent-runtime", tags=["agent-runtime"])


@router.get("/status")
def get_agent_runtime_status():
    return build_status().model_dump()


@router.get("/agents")
def get_agent_runtime_agents():
    return {"status": "ok", "agents": [a.model_dump() for a in list_agents()]}


@router.post("/workflow-runs")
def post_agent_runtime_workflow_runs(request: WorkflowRunCreateRequest):
    rec = create_workflow_run(request)
    return {"status": "ok", "workflow_run": rec.model_dump()}


@router.get("/workflow-runs/{workflow_run_id}")
def get_agent_runtime_workflow_run(workflow_run_id: str):
    rec = get_workflow_run(workflow_run_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return {"status": "ok", "workflow_run": rec.model_dump()}


@router.post("/agent-runs")
def post_agent_runtime_agent_runs(request: AgentRunRequest):
    try:
        result = create_agent_run(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {"status": "ok", "agent_run": result.model_dump()}


@router.get("/agent-runs/{run_id}")
def get_agent_runtime_agent_run(run_id: str):
    res = get_agent_run(run_id)
    if res is None:
        raise HTTPException(status_code=404, detail="Agent run not found")
    return {"status": "ok", "agent_run": res.model_dump()}


@router.get("/latest")
def get_agent_runtime_latest():
    return get_latest_snapshot()

