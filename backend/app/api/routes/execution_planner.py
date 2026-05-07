"""Stage 9 — Execution Planner (AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.execution_planner.models import ExecutionPlannerPlanRequest
from app.services.execution_planner.service import build_status, get_latest_plan, plan_execution

router = APIRouter(prefix="/execution-planner", tags=["execution-planner"])


@router.get("/status")
def get_execution_planner_status():
    return build_status().model_dump()


@router.post("/plan")
def post_execution_planner_plan(request: ExecutionPlannerPlanRequest):
    return plan_execution(request)


@router.get("/latest")
def get_execution_planner_latest():
    latest = get_latest_plan()
    if latest is None:
        return {"status": "not_found", "message": "No execution planner plan found yet."}
    return {"status": "ok", "execution_plan": latest.model_dump()}

