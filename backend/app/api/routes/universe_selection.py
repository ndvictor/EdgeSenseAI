"""Universe Selection API Routes.

Endpoints for running universe selection and managing watchlist candidates.
"""

from fastapi import APIRouter

from app.services.universe_selection_service import (
    UniverseSelectionRequest,
    UniverseSelectionResponse,
    get_latest_universe_selection,
    list_universe_selection_runs,
    promote_latest_universe_selection_to_candidates,
    run_universe_selection,
)

router = APIRouter()


@router.post("/universe-selection/run", response_model=UniverseSelectionResponse)
def post_universe_selection_run(request: UniverseSelectionRequest):
    """Run universe selection on provided symbols.

    Symbols must be explicitly provided. No hardcoded defaults.
    Uses deterministic weighted scoring (no LLMs).

    Returns ranked candidates and selected watchlist.
    """
    return run_universe_selection(request)


@router.get("/universe-selection/runs/latest", response_model=UniverseSelectionResponse | dict)
def get_latest_universe_selection_run():
    """Get the most recent universe selection run."""
    latest = get_latest_universe_selection()
    if not latest:
        return {"message": "No universe selection run available", "status": "not_found"}
    return latest


@router.get("/universe-selection/runs")
def get_universe_selection_runs(limit: int = 20):
    """List recent universe selection runs.

    Returns up to 100 most recent runs.
    """
    runs = list_universe_selection_runs(limit)
    return {
        "runs": runs,
        "count": len(runs),
        "total_available": len(runs),
    }


@router.post("/universe-selection/promote-latest-to-candidates")
def post_promote_latest_to_candidates():
    """Promote the latest selected watchlist to Candidate Universe.

    This connects Universe Selection (upstream) to Candidate Universe (downstream).
    Only selected watchlist symbols are promoted.
    """
    return promote_latest_universe_selection_to_candidates()
