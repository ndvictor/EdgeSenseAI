"""Data Freshness API Routes."""

from fastapi import APIRouter

from app.services.data_freshness_gate_service import (
    DataFreshnessCheckRequest,
    DataFreshnessCheckResponse,
    get_latest_data_freshness_check,
    list_data_freshness_checks,
    run_data_freshness_check,
)

router = APIRouter()


@router.post("/data-freshness/check", response_model=DataFreshnessCheckResponse)
def post_data_freshness_check(request: DataFreshnessCheckRequest):
    """Run data freshness check on provided symbols.

    Gates every workflow before data is trusted.
    Checks quote freshness, bar freshness, bid/ask, volume.
    NO fake values - blocks on unavailable data.
    """
    return run_data_freshness_check(request)


@router.get("/data-freshness/latest", response_model=DataFreshnessCheckResponse | dict)
def get_latest_data_freshness():
    """Get the most recent data freshness check."""
    latest = get_latest_data_freshness_check()
    if not latest:
        return {"message": "No data freshness check available", "status": "not_found"}
    return latest
