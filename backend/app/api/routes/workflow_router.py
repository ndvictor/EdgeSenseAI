"""Stage 5 — Workflow Router (AI-Agent, no LLM) API routes.

Deterministic router that chooses which workflow route should run next.
No external calls. No paid APIs. No broker orders.
"""

from fastapi import APIRouter

from app.services.workflow_router.models import WorkflowRouteRequest
from app.services.workflow_router.service import build_status, get_latest_decision, route_next_workflow

router = APIRouter(prefix="/workflow-router", tags=["workflow-router"])


@router.get("/status")
def get_workflow_router_status():
    return build_status().model_dump()


@router.post("/route")
def post_workflow_router_route(request: WorkflowRouteRequest):
    return route_next_workflow(request)


@router.get("/latest")
def get_workflow_router_latest():
    latest = get_latest_decision()
    if latest is None:
        return {"status": "not_found", "message": "No workflow router decision found yet."}
    return {"status": "ok", "decision": latest.model_dump()}

