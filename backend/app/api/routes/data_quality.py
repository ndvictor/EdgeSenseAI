from fastapi import APIRouter, Query

from app.services.data_quality_service import DataQualityReport, check_market_data_quality

router = APIRouter()


@router.get("/data-quality/{symbol}", response_model=DataQualityReport)
def get_data_quality(symbol: str, asset_class: str = Query("stock"), source: str = Query("auto")):
    return check_market_data_quality(symbol, asset_class=asset_class, source=source)
