"""Historical Similarity Search API Routes."""

from fastapi import APIRouter

from app.services.historical_similarity_service import (
    HistoricalSimilarityRequest,
    HistoricalSimilarityResponse,
    get_latest_historical_similarity,
    run_historical_similarity_search,
)

router = APIRouter()


@router.post("/historical-similarity/search", response_model=HistoricalSimilarityResponse)
def post_historical_similarity_search(request: HistoricalSimilarityRequest):
    """Search for similar historical setups for a symbol.

    Uses vector memory service when available. Returns degraded status
    with warnings if DB unavailable - NEVER invents fake matches.
    """
    return run_historical_similarity_search(request)


@router.get("/historical-similarity/latest", response_model=HistoricalSimilarityResponse | dict)
def get_latest_historical_similarity_endpoint():
    """Get the most recent historical similarity search."""
    latest = get_latest_historical_similarity()
    if not latest:
        return {"message": "No historical similarity search available", "status": "not_found"}
    return latest
