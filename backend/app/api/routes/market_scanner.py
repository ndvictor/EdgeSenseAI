from fastapi import APIRouter, HTTPException

from app.orchestration.schedulers.edge_scheduler import run_scheduled_market_scan
from app.services.market_condition_scanner_service import MarketScannerRequest, MarketScannerResponse, run_market_condition_scan
from app.services.market_scan_run_service import MarketScanRun, get_latest_scan_run, get_scan_run, list_scan_runs

router = APIRouter()


@router.post("/market-scanner/scan", response_model=MarketScannerResponse)
def post_market_scanner_scan(request: MarketScannerRequest):
    return run_market_condition_scan(request)


@router.get("/market-scanner/runs", response_model=list[MarketScanRun])
def get_market_scanner_runs(limit: int = 25):
    return list_scan_runs(limit)


@router.get("/market-scanner/runs/latest", response_model=MarketScanRun | None)
def get_latest_market_scanner_run():
    return get_latest_scan_run()


@router.get("/market-scanner/runs/{run_id}", response_model=MarketScanRun)
def get_market_scanner_run(run_id: str):
    run = get_scan_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Market scan run not found")
    return run


@router.post("/market-scanner/run-scheduled-once")
def post_market_scanner_run_scheduled_once():
    return run_scheduled_market_scan()
