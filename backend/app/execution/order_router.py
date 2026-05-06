"""Route execution request to paper / simulated / live Alpaca."""

from __future__ import annotations

from typing import Any, Literal

from app.execution.paper_order_router import submit_paper_order
from app.execution.schemas import ExecutionRequest


def route_order(
    req: ExecutionRequest,
    effective_mode: str,
) -> tuple[Literal["submitted", "simulated", "failed"], dict[str, Any], str | None]:
    if effective_mode == "simulated":
        return "simulated", {"status": "simulated", "message": "No broker call (simulated mode)"}, None

    if effective_mode == "live":
        from app.execution.alpaca_order_router import submit_alpaca_order
        from app.execution.paper_order_router import execution_request_to_alpaca_payload

        payload = execution_request_to_alpaca_payload(req)
        code, body, rid = submit_alpaca_order(payload, mode="live")
        if code >= 200 and code < 300:
            return "submitted", body, rid
        return "failed", body, rid

    # paper (default path)
    ok, body, rid = submit_paper_order(req)
    if ok:
        return "submitted", body, rid
    return "failed", body, rid
