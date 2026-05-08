"""Stage 14 — Learning Loop (AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.learning_loop.models import LearningLoopEvaluateRequest
from app.services.learning_loop.service import build_status, evaluate_learning_loop, get_latest_decision

router = APIRouter(prefix="/learning-loop", tags=["learning-loop"])


@router.get("/status")
def get_learning_loop_status():
    return build_status().model_dump()


@router.post("/evaluate")
def post_learning_loop_evaluate(request: LearningLoopEvaluateRequest):
    return evaluate_learning_loop(request)


@router.get("/latest")
def get_learning_loop_latest():
    latest = get_latest_decision()
    if latest is None:
        return {"status": "not_found", "message": "No learning loop decision found yet."}
    payload = latest.model_dump()
    # Canonical contract: {status, result}. Preserve legacy keys temporarily.
    return {"status": "ok", "result": payload, "learning_decision": payload}

