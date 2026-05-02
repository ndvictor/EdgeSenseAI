from fastapi import APIRouter

from app.services.platform_workflows import RecommendationLifecycleItem, get_recommendation_lifecycle

router = APIRouter()


@router.get("/recommendations/lifecycle", response_model=list[RecommendationLifecycleItem])
def get_lifecycle():
    return get_recommendation_lifecycle()
