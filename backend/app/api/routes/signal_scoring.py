"""Signal Scoring API Routes."""

from fastapi import APIRouter

from app.services.signal_scoring_service import (
    SignalScoringRequest,
    SignalScoringResponse,
    get_latest_signal_scoring,
    list_signal_scoring_runs,
    run_signal_scoring,
)

router = APIRouter()


@router.post("/signal-scoring/run", response_model=SignalScoringResponse)
def post_signal_scoring_run(request: SignalScoringRequest):
    """Run signal scoring on matched events.

    Uses available models (weighted ranker, XGBoost if trained,
    historical similarity if available).

    NO fake unavailable outputs.
    NO LLM.
    NO recommendation.
    """
    return run_signal_scoring(request)


@router.get("/signal-scoring/runs/latest", response_model=SignalScoringResponse | dict)
def get_latest_signal_scoring_endpoint():
    """Get the most recent signal scoring run."""
    latest = get_latest_signal_scoring()
    if not latest:
        return {"message": "No signal scoring run available", "status": "not_found"}
    return latest


@router.get("/signal-scoring/runs")
def get_signal_scoring_runs(limit: int = 20):
    """List recent signal scoring runs."""
    runs = list_signal_scoring_runs(limit)
    return {
        "runs": runs,
        "count": len(runs),
    }
