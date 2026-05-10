"""In-memory store for simulated paper positions.

Mark-to-market and close routines compute MFE/MAE, hit_target/hit_stop, R-multiple,
prediction_error_r purely from real quote prices vs. the position's audited
entry/stop/target. No fake/synthetic numbers are introduced here.
"""

from __future__ import annotations

from typing import Any

from app.services.paper_autonomy.models import PaperPositionRecord, iso_utc_now


_MEMORY: dict[str, PaperPositionRecord] = {}


def reset() -> None:
    """Test helper: clear the in-memory ledger."""
    _MEMORY.clear()


def create(position: PaperPositionRecord) -> PaperPositionRecord:
    if position.broker_called:
        raise ValueError("paper_position_store: broker_called must be False")
    _MEMORY[position.paper_position_id] = position
    return position


def get(paper_position_id: str) -> PaperPositionRecord | None:
    return _MEMORY.get(paper_position_id)


def list_positions(*, workflow_run_id: str | None = None) -> list[PaperPositionRecord]:
    items = list(_MEMORY.values())
    if workflow_run_id:
        items = [p for p in items if p.workflow_run_id == workflow_run_id]
    return items


def list_open(*, workflow_run_id: str | None = None) -> list[PaperPositionRecord]:
    items = [p for p in _MEMORY.values() if p.status == "open"]
    if workflow_run_id:
        items = [p for p in items if p.workflow_run_id == workflow_run_id]
    return items


def list_closed(*, workflow_run_id: str | None = None) -> list[PaperPositionRecord]:
    items = [p for p in _MEMORY.values() if p.status == "closed"]
    if workflow_run_id:
        items = [p for p in items if p.workflow_run_id == workflow_run_id]
    return items


def latest_open_for_workflow(workflow_run_id: str) -> PaperPositionRecord | None:
    open_items = list_open(workflow_run_id=workflow_run_id)
    if not open_items:
        return None
    open_items.sort(key=lambda p: p.opened_at, reverse=True)
    return open_items[0]


def latest_closed_for_workflow(workflow_run_id: str) -> PaperPositionRecord | None:
    closed_items = list_closed(workflow_run_id=workflow_run_id)
    if not closed_items:
        return None
    closed_items.sort(key=lambda p: p.closed_at or "", reverse=True)
    return closed_items[0]


def mark_to_market(paper_position_id: str, current_price: float) -> PaperPositionRecord | None:
    rec = _MEMORY.get(paper_position_id)
    if rec is None or rec.status != "open":
        return None
    if not isinstance(current_price, (int, float)):
        return rec
    price = float(current_price)
    new_mfe = max(rec.mfe, price - rec.entry_price)
    new_mae = min(rec.mae, price - rec.entry_price)
    data: dict[str, Any] = rec.model_dump()
    data["last_mark_price"] = price
    data["last_marked_at"] = iso_utc_now()
    data["mfe"] = new_mfe
    data["mae"] = new_mae
    updated = PaperPositionRecord.model_validate(data)
    _MEMORY[paper_position_id] = updated
    return updated


def close(
    paper_position_id: str,
    *,
    exit_price: float,
    exit_reason: str,
) -> PaperPositionRecord | None:
    """Close a paper position and compute outcome metrics.

    Computes:
    - actual_return_pct
    - actual_return_r (vs risk_per_share = entry - stop)
    - hit_target / hit_stop
    - prediction_error_r (planned target_r - actual_return_r)
    """
    rec = _MEMORY.get(paper_position_id)
    if rec is None or rec.status != "open":
        return None
    if not isinstance(exit_price, (int, float)):
        raise ValueError("paper_position_store.close: exit_price must be numeric")

    exit_p = float(exit_price)
    entry_p = rec.entry_price
    stop_p = rec.stop_price
    target_p = rec.target_price

    risk_per_share = entry_p - stop_p
    planned_reward_per_share = target_p - entry_p

    actual_return_pct = ((exit_p - entry_p) / entry_p) * 100.0 if entry_p else 0.0
    actual_return_r = ((exit_p - entry_p) / risk_per_share) if risk_per_share > 0 else 0.0
    planned_target_r = (planned_reward_per_share / risk_per_share) if risk_per_share > 0 else 0.0
    prediction_error_r = planned_target_r - actual_return_r

    hit_target = exit_p >= target_p
    hit_stop = exit_p <= stop_p

    new_mfe = max(rec.mfe, exit_p - entry_p)
    new_mae = min(rec.mae, exit_p - entry_p)

    data: dict[str, Any] = rec.model_dump()
    data.update(
        {
            "status": "closed",
            "closed_at": iso_utc_now(),
            "exit_price": exit_p,
            "exit_reason": exit_reason,
            "actual_return_pct": actual_return_pct,
            "actual_return_r": actual_return_r,
            "hit_target": hit_target,
            "hit_stop": hit_stop,
            "prediction_error_r": prediction_error_r,
            "mfe": new_mfe,
            "mae": new_mae,
        }
    )
    updated = PaperPositionRecord.model_validate(data)
    _MEMORY[paper_position_id] = updated
    return updated
