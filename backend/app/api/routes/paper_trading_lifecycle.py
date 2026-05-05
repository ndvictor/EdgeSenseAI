from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Literal

from app.services.persistence_service import (
    close_paper_trade_outcome,
    create_paper_trade_outcome_from_recommendation,
    list_paper_trade_outcomes,
)
from app.services.alpaca_paper_account_service import AlpacaPaperSnapshot, get_alpaca_paper_snapshot
from app.services.alpaca_execution_service import (
    TradeNowOrderRequest,
    place_trade_now_order,
    TradeNowOrderResponse,
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


class PaperOrderRequest(BaseModel):
    """Paper trading order request - simplified for manual order entry."""
    symbol: str
    side: Literal["buy", "sell"]
    qty: float
    type: Literal["market", "limit", "stop", "stop_limit"] = "market"
    time_in_force: Literal["day", "gtc", "ioc"] = "day"
    limit_price: float | None = None
    stop_price: float | None = None
    asset_class: Literal["stock", "etf", "crypto", "option"] = "stock"
    human_approval_confirmed: bool = False
    dry_run: bool = True  # Default to dry_run for safety


@router.get("/paper-trades", response_model=list[PaperTrade])
def get_paper_trades():
    return list_paper_trades()


@router.get("/paper-trading/alpaca", response_model=AlpacaPaperSnapshot)
def get_paper_trading_alpaca():
    return get_alpaca_paper_snapshot()


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


@router.post("/paper-trading/order", response_model=TradeNowOrderResponse)
def post_paper_trading_order(request: PaperOrderRequest):
    """Place a paper trading order with Alpaca.
    
    Safety features:
    - Requires human_approval_confirmed=True to submit to broker
    - dry_run=True by default (set to False to actually submit)
    - Validates all order parameters before submission
    """
    order_request = TradeNowOrderRequest(
        symbol=request.symbol.upper().strip(),
        asset_class=request.asset_class,
        side=request.side,
        qty=request.qty,
        type=request.type,
        time_in_force=request.time_in_force,
        limit_price=request.limit_price,
        stop_price=request.stop_price,
        dry_run=request.dry_run,
        human_approval_confirmed=request.human_approval_confirmed,
        approval_source="human",
    )
    
    result = place_trade_now_order(order_request)
    return result
