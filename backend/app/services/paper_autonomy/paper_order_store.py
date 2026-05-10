"""In-memory store for simulated paper orders.

This is a process-local ledger. It does not persist to a broker, does not write
to Postgres in this step, and never flips ``broker_called`` to True.
"""

from __future__ import annotations

from typing import Any

from app.services.paper_autonomy.models import PaperOrderRecord


_MEMORY: dict[str, PaperOrderRecord] = {}


def reset() -> None:
    """Test helper: clear the in-memory ledger."""
    _MEMORY.clear()


def create(order: PaperOrderRecord) -> PaperOrderRecord:
    if order.broker_called:
        raise ValueError("paper_order_store: broker_called must be False")
    _MEMORY[order.paper_order_id] = order
    return order


def get(paper_order_id: str) -> PaperOrderRecord | None:
    return _MEMORY.get(paper_order_id)


def list_orders(*, workflow_run_id: str | None = None) -> list[PaperOrderRecord]:
    items = list(_MEMORY.values())
    if workflow_run_id:
        items = [o for o in items if o.workflow_run_id == workflow_run_id]
    return items


def list_open(*, workflow_run_id: str | None = None) -> list[PaperOrderRecord]:
    items = [
        o for o in _MEMORY.values()
        if o.status in {"paper_submitted", "paper_open", "paper_filled"}
    ]
    if workflow_run_id:
        items = [o for o in items if o.workflow_run_id == workflow_run_id]
    return items


def update_status(paper_order_id: str, *, status: str, warnings: list[str] | None = None) -> PaperOrderRecord | None:
    rec = _MEMORY.get(paper_order_id)
    if rec is None:
        return None
    data: dict[str, Any] = rec.model_dump()
    data["status"] = status
    if warnings:
        merged = list(rec.warnings) + [w for w in warnings if w]
        data["warnings"] = sorted(set(merged))
    updated = PaperOrderRecord.model_validate(data)
    _MEMORY[paper_order_id] = updated
    return updated
