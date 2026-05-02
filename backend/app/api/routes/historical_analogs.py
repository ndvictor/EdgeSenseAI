from fastapi import APIRouter

from app.services.platform_workflows import HistoricalAnalog, get_historical_analogs

router = APIRouter()


@router.get("/historical-analogs/{ticker}", response_model=list[HistoricalAnalog])
def get_analogs(ticker: str):
    return get_historical_analogs(ticker)
