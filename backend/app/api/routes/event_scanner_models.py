"""Event Scanner Models API Routes."""

from fastapi import APIRouter

from app.services.event_scanner_models_service import (
    EventScannerRequest,
    EventScannerResponse,
    get_latest_event_scan,
    list_event_scan_runs,
    run_event_scanner,
)

router = APIRouter()


@router.post("/event-scanner/run", response_model=EventScannerResponse)
def post_event_scanner_run(request: EventScannerRequest):
    """Run cheap event scanner.

    Scans only active trigger rules or latest watchlist.
    Does NOT scan whole market.
    NO LLM. NO recommendation. NO default symbols.
    """
    return run_event_scanner(request)


@router.get("/event-scanner/runs/latest", response_model=EventScannerResponse | dict)
def get_latest_event_scan_endpoint():
    """Get the most recent event scanner run."""
    latest = get_latest_event_scan()
    if not latest:
        return {"message": "No event scanner run available", "status": "not_found"}
    return latest


@router.get("/event-scanner/runs")
def get_event_scan_runs(limit: int = 20):
    """List recent event scanner runs."""
    runs = list_event_scan_runs(limit)
    return {
        "runs": runs,
        "count": len(runs),
    }
