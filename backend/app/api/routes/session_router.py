"""Stage 3 — Session Router (AI-Agent, no LLM) API routes.

Deterministic session evaluator for US equities basic trading sessions (v1).
No external calendar APIs. No broker calls. No paid APIs.
"""

from fastapi import APIRouter

from app.services.session_router.models import SessionEvaluateRequest
from app.services.session_router.service import build_status, evaluate_session, get_latest_session

router = APIRouter(prefix="/session-router", tags=["session-router"])


@router.get("/status")
def get_session_router_status():
    return build_status().model_dump()


@router.post("/evaluate")
def post_session_router_evaluate(request: SessionEvaluateRequest):
    return evaluate_session(request)


@router.get("/latest")
def get_session_router_latest():
    latest = get_latest_session()
    if latest is None:
        return {"status": "not_found", "message": "No session router evaluation found yet."}
    payload = latest.model_dump()
    # Canonical contract: {status, result}. Preserve legacy keys temporarily.
    return {"status": "ok", "result": payload, "evaluation": payload, "session": payload}

