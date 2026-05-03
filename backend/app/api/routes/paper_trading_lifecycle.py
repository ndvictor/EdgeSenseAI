from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.persistence_service import (
    close_paper_trade_outcome,
    create_paper_trade_outcome_from_recommendation,
    list_paper_trade_outcomes,
)
from app.services.platform_workflows import PaperTrade, PaperTradeCreateRequest, create_paper_trade, list_paper_trades, update_paper_trade_status

router = APIRouter()


class PaperTradeStatusUpdate(BaseModel):
    status: str
    exit_price: float | None = None
    outcome_label: str | None = None


class CreatePaperTradeFromRecommendation(BaseModel):
    recommendation_id: str
    symbol: str
    entry_price: float
    stop_loss: float
    target_price: float
    quantity: float = 1.0
    action: str = "long"


class ClosePaperTradeOutcome(BaseModel):
    exit_price: float
    notes: str | None = None


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


# Paper Trade Outcomes endpoints (DB-backed)
@router.get("/paper-trading/outcomes")
def get_paper_trade_outcomes(status: str | None = None, symbol: str | None = None, limit: int = 100):
    """List paper trade outcomes from database storage."""
    return list_paper_trade_outcomes(status=status, symbol=symbol, limit=limit)


@router.post("/paper-trading/outcomes/create-from-recommendation")
def post_create_paper_trade_outcome_from_recommendation(request: CreatePaperTradeFromRecommendation):
    """Create a new paper trade outcome from an approved recommendation."""
    result = create_paper_trade_outcome_from_recommendation(
        recommendation_id=request.recommendation_id,
        symbol=request.symbol,
        entry_price=request.entry_price,
        stop_loss=request.stop_loss,
        target_price=request.target_price,
        quantity=request.quantity,
        action=request.action,
    )
    if not result.get("persisted") and not result.get("id"):
        raise HTTPException(status_code=503, detail="Database unavailable and memory fallback not created")
    return {"success": True, "trade_id": result.get("id"), "persisted": result.get("persisted", False)}


@router.post("/paper-trading/outcomes/close")
def post_close_paper_trade_outcome(trade_id: str, request: ClosePaperTradeOutcome):
    """Close a paper trade outcome and compute PnL. Creates training example if recommendation linked."""
    result = close_paper_trade_outcome(
        trade_id=trade_id,
        exit_price=request.exit_price,
        notes=request.notes,
    )
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("error", "Failed to close trade"))
    return result
