from typing import Any, Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.services.market_data_service import MarketDataService

router = APIRouter()
market_data_service = MarketDataService()


class MarketSnapshot(BaseModel):
    symbol: str
    price: Optional[float] = None
    previous_close: Optional[float] = None
    change: Optional[float] = None
    change_percent: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[float] = None
    average_volume: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    bid_ask_spread: Optional[float] = None
    market_cap: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    provider: Optional[str] = None
    source: Optional[str] = None
    is_mock: bool = False
    data_quality: Optional[str] = None
    source_fields_used: Optional[Dict[str, Any]] = None
    unavailable_fields: list[str] = []
    not_configured_fields: list[str] = []
    provider_statuses: Optional[list[dict]] = None
    error: Optional[str] = None


class PriceHistory(BaseModel):
    symbol: str
    period: str
    interval: str
    data: list
    provider: Optional[str] = None
    is_mock: bool = False
    data_quality: Optional[str] = None
    error: Optional[str] = None


@router.get("/market-data/quote/{symbol}", response_model=Dict[str, Any])
def get_quote(symbol: str):
    return market_data_service.get_quote(symbol)


@router.get("/market-data/snapshot/{symbol}", response_model=MarketSnapshot)
def get_market_snapshot(symbol: str):
    return MarketSnapshot(**market_data_service.get_market_snapshot(symbol))


@router.get("/market-data/history/{symbol}", response_model=PriceHistory)
def get_price_history(symbol: str, period: str = Query("6mo"), interval: str = Query("1d")):
    return PriceHistory(**market_data_service.get_price_history(symbol, period, interval))
