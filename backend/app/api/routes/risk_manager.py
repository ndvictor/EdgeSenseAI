"""Risk Manager API routes."""

from fastapi import APIRouter

from app.services.risk_manager_service import (
    RiskReviewRequest,
    RiskReviewResponse,
    get_latest_risk_review,
    review_risk,
)

router = APIRouter()


@router.post("/risk-manager/review", response_model=RiskReviewResponse)
def post_risk_manager_review(request: RiskReviewRequest):
    """Review risk for a potential trade.

    Hard veto layer. Can approve, watch-only, paper-only, reduce-size, or block.
    Live trading always disabled.
    """
    return review_risk(request)


@router.get("/risk-manager/latest", response_model=RiskReviewResponse | dict)
def get_risk_manager_latest():
    """Get the latest risk review."""
    result = get_latest_risk_review()
    if result is None:
        return {"status": "not_found", "message": "No risk review found"}
    return result
