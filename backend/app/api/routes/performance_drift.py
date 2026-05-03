"""Performance Drift API routes."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.services.performance_drift_service import (
    PerformanceDriftRequest,
    PerformanceDriftResponse,
    get_latest_drift_check,
    list_drift_history,
    run_performance_drift_check,
)

router = APIRouter()


class RunDriftRequest(BaseModel):
    """Request to run performance drift check."""

    model_config = ConfigDict(protected_namespaces=())

    lookback_days: int = 30
    strategy_key: str | None = None
    model_name: str | None = None
    min_samples: int = 5
    source: str = "both"


@router.post("/performance-drift/run", response_model=PerformanceDriftResponse)
def post_performance_drift_run(request: RunDriftRequest):
    """Run performance drift analysis on journal and paper trade outcomes.
    
    Returns insufficient_data if sample count is below minimum.
    Does not invent performance metrics.
    """
    internal_request = PerformanceDriftRequest(
        lookback_days=request.lookback_days,
        strategy_key=request.strategy_key,
        model_name=request.model_name,
        min_samples=request.min_samples,
        source=request.source,  # type: ignore
    )
    return run_performance_drift_check(internal_request)


@router.get("/performance-drift/latest", response_model=PerformanceDriftResponse | dict)
def get_performance_drift_latest():
    """Get the latest performance drift check."""
    result = get_latest_drift_check()
    if result is None:
        return {"status": "not_found", "message": "No drift check found"}
    return result


@router.get("/performance-drift/history")
def get_performance_drift_history(limit: int = 20):
    """List recent performance drift checks."""
    return list_drift_history(limit)
