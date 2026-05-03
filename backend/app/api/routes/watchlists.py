"""Watchlist API routes."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.candidate_universe_service import add_candidate
from app.services.platform_workflows import Watchlist, WatchlistCreateRequest, WatchlistItem, add_watchlist_item, create_watchlist, list_watchlists

router = APIRouter()


class PromoteWatchlistToCandidatesRequest(BaseModel):
    watchlist_id: str | None = None
    symbols: list[str] | None = None
    horizon: str = "swing"
    priority_score: float = 50.0


class PromoteWatchlistToCandidatesResponse(BaseModel):
    success: bool
    message: str
    added: list[dict[str, Any]]
    skipped: list[dict[str, Any]]
    total_added: int
    total_skipped: int


@router.get("/watchlists", response_model=list[Watchlist])
def get_watchlists():
    return list_watchlists()


@router.post("/watchlists", response_model=Watchlist)
def post_watchlist(request: WatchlistCreateRequest):
    return create_watchlist(request)


@router.post("/watchlists/{watchlist_id}/items", response_model=Watchlist)
def post_watchlist_item(watchlist_id: str, item: WatchlistItem):
    try:
        return add_watchlist_item(watchlist_id, item)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/watchlists/promote-to-candidates", response_model=PromoteWatchlistToCandidatesResponse)
def post_promote_watchlist_to_candidates(request: PromoteWatchlistToCandidatesRequest | None = None):
    """Promote symbols from watchlist or explicit list to candidate universe.

    If symbols provided, promote those symbols directly.
    If watchlist_id provided, promote symbols from that watchlist.
    If neither provided, returns no_symbols_selected.
    """
    req = request or PromoteWatchlistToCandidatesRequest()

    symbols_to_promote: list[str] = []
    source_detail = "Promoted from watchlist"

    if req.symbols:
        # Use explicitly provided symbols
        symbols_to_promote = [s.upper().strip() for s in req.symbols if s.strip()]
        source_detail = "Promoted from explicit symbol list"
    elif req.watchlist_id:
        # Get symbols from watchlist
        watchlists = list_watchlists()
        watchlist = next((w for w in watchlists if w.id == req.watchlist_id), None)
        if watchlist is None:
            return PromoteWatchlistToCandidatesResponse(
                success=False,
                message=f"Watchlist {req.watchlist_id} not found",
                added=[],
                skipped=[],
                total_added=0,
                total_skipped=0,
            )
        symbols_to_promote = [item.ticker.upper() for item in watchlist.items]
        source_detail = f"Promoted from watchlist: {watchlist.name}"
    else:
        # No symbols or watchlist provided
        return PromoteWatchlistToCandidatesResponse(
            success=False,
            message="No symbols or watchlist_id provided",
            added=[],
            skipped=[],
            total_added=0,
            total_skipped=0,
        )

    if not symbols_to_promote:
        return PromoteWatchlistToCandidatesResponse(
            success=False,
            message="No symbols to promote",
            added=[],
            skipped=[],
            total_skipped=0,
            total_added=0,
        )

    added = []
    skipped = []

    for symbol in symbols_to_promote:
        try:
            candidate = add_candidate(
                symbol=symbol,
                asset_class="stock",
                horizon=req.horizon,
                source_type="watchlist",
                source_detail=source_detail,
                priority_score=req.priority_score,
                notes=f"Added from watchlist promotion",
            )
            added.append({
                "symbol": symbol,
                "candidate_id": candidate.id,
            })
        except Exception as exc:
            skipped.append({"symbol": symbol, "reason": str(exc)})

    return PromoteWatchlistToCandidatesResponse(
        success=len(added) > 0,
        message=f"Promoted {len(added)} symbol(s) from watchlist to candidate universe" if added else "No symbols were promoted",
        added=added,
        skipped=skipped,
        total_added=len(added),
        total_skipped=len(skipped),
    )
