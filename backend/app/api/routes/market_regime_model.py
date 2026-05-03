"""Market Regime Model API Routes."""

from fastapi import APIRouter

from app.services.market_regime_model_service import (
    MarketRegimeRequest,
    MarketRegimeResponse,
    get_latest_market_regime,
    list_market_regime_history,
    run_market_regime_model,
)

router = APIRouter()


@router.post("/market-regime/model/run", response_model=MarketRegimeResponse)
def post_market_regime_run(request: MarketRegimeRequest):
    """Run market regime detection.

    Classifies current market state using SPY/QQQ/VIX data.
    NO LLM calls - deterministic only.
    Returns unknown/warn if data unavailable - NO fake output.
    """
    return run_market_regime_model(request)


@router.get("/market-regime/model/latest", response_model=MarketRegimeResponse | dict)
def get_latest_market_regime_endpoint():
    """Get the most recent market regime detection."""
    latest = get_latest_market_regime()
    if not latest:
        return {"message": "No market regime detection available", "status": "not_found"}
    return latest
