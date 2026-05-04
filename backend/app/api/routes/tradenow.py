from fastapi import APIRouter

from app.services.alpaca_execution_service import (
    TradeNowConfig,
    TradeNowConfigUpdate,
    TradeNowOrderRequest,
    TradeNowOrderResponse,
    get_last_trade_now_order,
    get_trade_now_config,
    place_trade_now_order,
    update_trade_now_config,
)

router = APIRouter()


@router.get("/tradenow/config", response_model=TradeNowConfig)
def get_config():
    return get_trade_now_config()


@router.put("/tradenow/config", response_model=TradeNowConfig)
def update_config(update: TradeNowConfigUpdate):
    return update_trade_now_config(update)


@router.post("/tradenow/orders", response_model=TradeNowOrderResponse)
def place_order(request: TradeNowOrderRequest):
    return place_trade_now_order(request)


@router.get("/tradenow/orders/latest")
def get_latest_order():
    return get_last_trade_now_order()
