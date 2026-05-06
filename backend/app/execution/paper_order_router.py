"""Paper order construction + Alpaca paper submit."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from app.execution.alpaca_order_router import submit_alpaca_order
from app.execution.execution_prechecks import normalize_asset_class
from app.execution.schemas import ExecutionRequest


def execution_request_to_alpaca_payload(req: ExecutionRequest) -> dict[str, Any]:
    client_id = req.client_request_id or f"edgesense-exec-{uuid4().hex[:18]}"
    payload: dict[str, Any] = {
        "symbol": req.symbol.upper().strip(),
        "side": req.side,
        "type": req.order_type,
        "time_in_force": req.time_in_force,
        "client_order_id": client_id,
    }
    if req.quantity is not None:
        payload["qty"] = str(req.quantity)
    if req.notional is not None:
        payload["notional"] = str(req.notional)
    if req.limit_price is not None:
        payload["limit_price"] = str(req.limit_price)
    if req.stop_price is not None:
        payload["stop_price"] = str(req.stop_price)
    return payload


def submit_paper_order(req: ExecutionRequest) -> tuple[bool, dict[str, Any], str | None]:
    """Submit to Alpaca paper. Returns ok, broker_body, request_id."""
    ac = normalize_asset_class(req.asset_class)
    if ac == "crypto" and req.time_in_force not in {"gtc", "ioc"}:
        return False, {"error": "crypto_requires_gtc_or_ioc"}, None
    if ac in {"stock", "etf"} and req.notional is not None:
        return False, {"error": "notional_not_supported_for_equity_here_use_qty"}, None

    payload = execution_request_to_alpaca_payload(req)
    code, body, rid = submit_alpaca_order(payload, mode="paper")
    if code == 0:
        return False, body, rid
    if code >= 400:
        return False, body, rid
    return True, body, rid
