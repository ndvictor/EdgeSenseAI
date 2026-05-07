"""Stage 8 — Trigger Monitoring (AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.trigger_monitoring.models import TriggerMonitoringEvaluateRequest
from app.services.trigger_monitoring.service import build_status, evaluate_trigger, get_latest_evaluation

router = APIRouter(prefix="/trigger-monitoring", tags=["trigger-monitoring"])


@router.get("/status")
def get_trigger_monitoring_status():
    return build_status().model_dump()


@router.post("/evaluate")
def post_trigger_monitoring_evaluate(request: TriggerMonitoringEvaluateRequest):
    return evaluate_trigger(request)


@router.get("/latest")
def get_trigger_monitoring_latest():
    latest = get_latest_evaluation()
    if latest is None:
        return {"status": "not_found", "message": "No trigger monitoring evaluation found yet."}
    return {"status": "ok", "trigger_evaluation": latest.model_dump()}

