from fastapi import APIRouter

from app.services.platform_workflows import TradeQualityReview, get_trade_quality_reviews

router = APIRouter()


@router.get("/trade-quality/reviews", response_model=list[TradeQualityReview])
def get_reviews():
    return get_trade_quality_reviews()
