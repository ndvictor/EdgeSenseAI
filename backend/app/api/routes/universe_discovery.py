"""Universe Discovery API Routes.

POST /api/universe/discover
Deterministic discovery/watchlist intake. Does not enable execution.
"""

from fastapi import APIRouter

from app.services.universe_discovery_service import UniverseDiscoverRequest, UniverseDiscoverResponse, discover_universe

router = APIRouter()


@router.post("/universe/discover", response_model=UniverseDiscoverResponse)
def post_universe_discover(request: UniverseDiscoverRequest):
    return discover_universe(request)

