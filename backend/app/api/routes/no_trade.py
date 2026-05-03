"""No-Trade / Sit-Out Agent API routes."""

from fastapi import APIRouter

from app.services.no_trade_service import (
    NoTradeRequest,
    NoTradeResponse,
    evaluate_no_trade,
    get_latest_no_trade,
)

router = APIRouter()


@router.post("/no-trade/evaluate", response_model=NoTradeResponse)
def post_no_trade_evaluate(request: NoTradeRequest):
    """Evaluate whether to trade or sit out.

    Makes no-trade a first-class decision.
    """
    return evaluate_no_trade(request)


@router.get("/no-trade/latest", response_model=NoTradeResponse | dict)
def get_no_trade_latest():
    """Get the latest no-trade evaluation."""
    result = get_latest_no_trade()
    if result is None:
        return {"status": "not_found", "message": "No no-trade evaluation found"}
    return result
