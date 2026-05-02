from fastapi import APIRouter

from app.services.market_condition_scanner_service import MarketScannerRequest, MarketScannerResponse, run_market_condition_scan

router = APIRouter()


@router.post("/market-scanner/scan", response_model=MarketScannerResponse)
def post_market_scanner_scan(request: MarketScannerRequest):
    return run_market_condition_scan(request)
