"""Stage 12 — Close Position (review/preview only; AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.close_position.models import ClosePositionReviewRequest
from app.services.close_position.service import build_status, get_latest_review, review_close_position

router = APIRouter(prefix="/close-position", tags=["close-position"])


@router.get("/status")
def get_close_position_status():
    return build_status().model_dump()


@router.post("/review")
def post_close_position_review(request: ClosePositionReviewRequest):
    return review_close_position(request)


@router.get("/latest")
def get_close_position_latest():
    latest = get_latest_review()
    if latest is None:
        return {"status": "not_found", "message": "No close position review found yet."}
    payload = latest.model_dump()
    # Canonical contract: {status, result}. Preserve legacy keys temporarily.
    return {"status": "ok", "result": payload, "close_review": payload}

