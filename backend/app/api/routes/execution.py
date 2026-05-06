"""Paper-first execution workflow API."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.execution.execution_service import (
    approve_execution,
    cancel_execution_order,
    get_execution_order,
    list_execution_orders,
    reject_execution,
    run_precheck_only,
    submit_execution,
    sync_execution_order,
)
from app.execution.edgesense_execution_config import edgesense_config_summary
from app.execution.risk_state_store import get_daily_loss_pct_used, is_risk_lockout
from app.execution.schemas import (
    ExecutionApproveRequest,
    ExecutionRejectRequest,
    ExecutionRequest,
    ExecutionResponse,
)

router = APIRouter()


class TestPaperOrderBody(BaseModel):
    """Body for test paper order — symbol must be supplied by caller (no hardcoded tickers)."""

    symbol: str = Field(min_length=1)
    quantity: float = Field(gt=0, default=1.0)
    limit_price: float | None = None
    side: Literal["buy", "sell"] = "buy"
    org_slug: str = "default"


@router.get("/execution/summary")
def get_execution_summary() -> dict[str, Any]:
    """Env-backed EdgeSense execution config + in-process risk usage (not a persisted ledger)."""
    return {
        "edgesense": edgesense_config_summary(),
        "risk_state": {
            "daily_loss_pct_used": get_daily_loss_pct_used(),
            "risk_lockout_active": is_risk_lockout(),
        },
        "persistence": "process_memory",
    }


@router.post("/execution/precheck", response_model=ExecutionResponse)
def post_execution_precheck(request: ExecutionRequest):
    return run_precheck_only(request)


@router.post("/execution/submit", response_model=ExecutionResponse)
def post_execution_submit(request: ExecutionRequest):
    return submit_execution(request)


@router.get("/execution/orders")
def get_execution_orders(limit: int = 50) -> dict[str, Any]:
    return {"orders": list_execution_orders(limit)}


@router.get("/execution/orders/{order_id}")
def get_execution_order_route(order_id: str) -> dict[str, Any]:
    return get_execution_order(order_id)


@router.post("/execution/orders/{order_id}/cancel")
def post_execution_order_cancel(order_id: str) -> dict[str, Any]:
    return cancel_execution_order(order_id)


@router.post("/execution/orders/{order_id}/sync")
def post_execution_order_sync(order_id: str) -> dict[str, Any]:
    return sync_execution_order(order_id)


@router.post("/execution/approve", response_model=ExecutionResponse)
def post_execution_approve(request: ExecutionApproveRequest):
    return approve_execution(request)


@router.post("/execution/reject", response_model=ExecutionResponse)
def post_execution_reject(request: ExecutionRejectRequest):
    return reject_execution(request)


@router.post("/execution/test-paper-order", response_model=ExecutionResponse)
def post_execution_test_paper_order(body: TestPaperOrderBody):
    """Runs submit path with caller-provided symbol; still subject to all env and precheck gates."""
    req = ExecutionRequest(
        org_slug=body.org_slug,
        symbol=body.symbol.strip(),
        asset_class="stock",
        side=body.side,  # type: ignore[arg-type]
        quantity=body.quantity,
        order_type="limit" if body.limit_price else "market",
        limit_price=body.limit_price,
        time_in_force="day",
        source="model_lab",
        reason="test_paper_order",
        human_approval_confirmed=True,
        metadata={"allow_market_closed_execution": True},
        stop_loss_price=body.limit_price * 0.99 if body.limit_price else None,
    )
    if body.limit_price is None:
        req.metadata["exempt_stop_loss"] = True
    return submit_execution(req)
