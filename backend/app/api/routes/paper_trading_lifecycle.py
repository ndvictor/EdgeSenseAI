from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.platform_workflows import PaperTrade, PaperTradeCreateRequest, create_paper_trade, list_paper_trades, update_paper_trade_status

router = APIRouter()


class PaperTradeStatusUpdate(BaseModel):
    status: str
    exit_price: float | None = None
    outcome_label: str | None = None


@router.get("/paper-trades", response_model=list[PaperTrade])
def get_paper_trades():
    return list_paper_trades()


@router.post("/paper-trades", response_model=PaperTrade)
def post_paper_trade(request: PaperTradeCreateRequest):
    return create_paper_trade(request)


@router.patch("/paper-trades/{trade_id}", response_model=PaperTrade)
def patch_paper_trade(trade_id: str, request: PaperTradeStatusUpdate):
    try:
        return update_paper_trade_status(trade_id, request.status, request.exit_price, request.outcome_label)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
