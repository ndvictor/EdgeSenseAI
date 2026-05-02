from fastapi import APIRouter, HTTPException

from app.services.platform_workflows import Watchlist, WatchlistCreateRequest, WatchlistItem, add_watchlist_item, create_watchlist, list_watchlists

router = APIRouter()


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
