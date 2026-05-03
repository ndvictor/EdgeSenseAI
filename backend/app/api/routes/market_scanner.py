"""Market scanner API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException

from app.orchestration.schedulers.edge_scheduler import run_scheduled_market_scan
from app.services.candidate_universe_service import add_candidate
from app.services.market_condition_scanner_service import MarketScannerRequest, MarketScannerResponse, run_market_condition_scan
from app.services.market_scan_run_service import MarketScanRun, get_latest_scan_run, get_scan_run, list_scan_runs
from pydantic import BaseModel

router = APIRouter()


class PromoteScannerToCandidatesRequest(BaseModel):
    min_score: float = 60.0
    max_candidates: int = 25
    horizon: str = "swing"
    source: str = "scanner"


class PromoteScannerToCandidatesResponse(BaseModel):
    success: bool
    message: str
    added: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    total_added: int
    total_skipped: int


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


@router.post("/market-scanner/promote-to-candidates", response_model=PromoteScannerToCandidatesResponse)
def post_promote_scanner_to_candidates(request: PromoteScannerToCandidatesRequest | None = None):
    """Promote matched signals from latest scanner run to candidate universe.

    If no latest scanner run exists, returns no_scanner_results.
    Only promotes matched signals with confidence >= min_score.
    """
    req = request or PromoteScannerToCandidatesRequest()

    latest_run = get_latest_scan_run()
    if latest_run is None:
        return PromoteScannerToCandidatesResponse(
            success=False,
            message="No scanner results available. Run a market scan first.",
            added=[],
            skipped=[],
            total_added=0,
            total_skipped=0,
        )

    added = []
    skipped = []

    # Get unique symbols from matched signals
    seen_symbols: set[str] = set()
    for signal in latest_run.matched_signals:
        symbol = signal.symbol.upper()
        if symbol in seen_symbols:
            continue
        seen_symbols.add(symbol)

        if len(added) >= req.max_candidates:
            skipped.append({"symbol": symbol, "reason": "max_candidates limit reached"})
            continue

        if signal.confidence < req.min_score:
            skipped.append({"symbol": symbol, "reason": f"confidence {signal.confidence} below min_score {req.min_score}"})
            continue

        # Add to candidate universe
        candidate = add_candidate(
            symbol=symbol,
            asset_class="stock",  # Default to stock, could be derived from signal
            horizon=req.horizon,
            source_type="scanner",
            source_detail=f"Promoted from market scanner (signal: {signal.signal_key}, run: {latest_run.run_id})",
            priority_score=signal.confidence * 100,  # Scale confidence to 0-100
            notes=f"Scanner confidence: {signal.confidence}, data_source: {signal.data_source}, reason: {signal.reason}",
        )
        added.append({
            "symbol": symbol,
            "candidate_id": candidate.id,
            "signal_key": signal.signal_key,
            "confidence": signal.confidence,
        })

    return PromoteScannerToCandidatesResponse(
        success=len(added) > 0,
        message=f"Promoted {len(added)} symbol(s) from scanner to candidate universe" if added else "No symbols met criteria for promotion",
        added=added,
        skipped=skipped,
        total_added=len(added),
        total_skipped=len(skipped),
    )
