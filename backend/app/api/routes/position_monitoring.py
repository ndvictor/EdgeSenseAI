"""Stage 11 — Position Monitoring (AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.position_monitoring.models import PositionMonitoringEvaluateRequest
from app.services.position_monitoring.service import build_status, evaluate_position, get_latest_evaluation

router = APIRouter(prefix="/position-monitoring", tags=["position-monitoring"])


@router.get("/status")
def get_position_monitoring_status():
    return build_status().model_dump()


@router.post("/evaluate")
def post_position_monitoring_evaluate(request: PositionMonitoringEvaluateRequest):
    return evaluate_position(request)


@router.get("/latest")
def get_position_monitoring_latest():
    latest = get_latest_evaluation()
    if latest is None:
        return {"status": "not_found", "message": "No position monitoring evaluation found yet."}
    return {"status": "ok", "position_evaluation": latest.model_dump()}

