"""Stage 7 — Strategy Requirements & Eligibility Checker (AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.strategy_eligibility.models import StrategyEligibilityCheckRequest
from app.services.strategy_eligibility.service import build_status, check_strategy_eligibility, get_latest_check

router = APIRouter(prefix="/strategy-eligibility", tags=["strategy-eligibility"])


@router.get("/status")
def get_strategy_eligibility_status():
    return build_status().model_dump()


@router.post("/check")
def post_strategy_eligibility_check(request: StrategyEligibilityCheckRequest):
    return check_strategy_eligibility(request)


@router.get("/latest")
def get_strategy_eligibility_latest():
    latest = get_latest_check()
    if latest is None:
        return {"status": "not_found", "message": "No strategy eligibility check found yet."}
    return {"status": "ok", "eligibility": latest.model_dump()}

