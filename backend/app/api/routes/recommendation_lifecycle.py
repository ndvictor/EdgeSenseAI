"""Recommendation lifecycle API routes."""

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.services.recommendation_lifecycle_service import (
    RecommendationLifecycleRecord,
    approve_recommendation,
    expire_recommendation,
    get_recommendation,
    get_recommendation_summary,
    list_recommendations,
    reject_recommendation,
)

router = APIRouter()


class UpdateStatusRequest(BaseModel):
    id: str


class UpdateStatusResponse(BaseModel):
    success: bool
    recommendation: RecommendationLifecycleRecord | None = None
    message: str


@router.get("/recommendation-lifecycle", response_model=list[RecommendationLifecycleRecord])
def get_recommendation_lifecycle_list(status: str | None = None, symbol: str | None = None, limit: int = 100):
    """List recommendation lifecycle records with optional filtering."""
    return list_recommendations(status=status, symbol=symbol, limit=limit)


@router.get("/recommendation-lifecycle/summary", response_model=dict[str, Any])
def get_recommendation_lifecycle_summary():
    """Get summary statistics for recommendations."""
    return get_recommendation_summary()


@router.post("/recommendation-lifecycle/approve", response_model=UpdateStatusResponse)
def post_approve_recommendation(request: UpdateStatusRequest):
    """Approve a recommendation for paper trading."""
    record = approve_recommendation(request.id)
    if record is None:
        return UpdateStatusResponse(success=False, recommendation=None, message=f"Recommendation {request.id} not found")
    return UpdateStatusResponse(success=True, recommendation=record, message=f"Recommendation {request.id} approved")


@router.post("/recommendation-lifecycle/reject", response_model=UpdateStatusResponse)
def post_reject_recommendation(request: UpdateStatusRequest):
    """Reject a recommendation."""
    record = reject_recommendation(request.id)
    if record is None:
        return UpdateStatusResponse(success=False, recommendation=None, message=f"Recommendation {request.id} not found")
    return UpdateStatusResponse(success=True, recommendation=record, message=f"Recommendation {request.id} rejected")


@router.post("/recommendation-lifecycle/expire", response_model=UpdateStatusResponse)
def post_expire_recommendation(request: UpdateStatusRequest):
    """Mark a recommendation as expired."""
    record = expire_recommendation(request.id)
    if record is None:
        return UpdateStatusResponse(success=False, recommendation=None, message=f"Recommendation {request.id} not found")
    return UpdateStatusResponse(success=True, recommendation=record, message=f"Recommendation {request.id} expired")
