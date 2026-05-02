from fastapi import APIRouter

from app.services.platform_workflows import MarketRadarEvent, get_market_radar_events

router = APIRouter()


@router.get("/market-radar/events", response_model=list[MarketRadarEvent])
def get_events():
    return get_market_radar_events()
