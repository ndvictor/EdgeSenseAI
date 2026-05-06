"""Post-submission verification, fill quality, position sync (broker-sourced only)."""

from __future__ import annotations

from typing import Any

from app.execution.order_status_service import get_broker_order
from app.execution.schemas import ExecutionRequest, PostcheckSummary
from app.execution.edgesense_execution_config import load_edgesense_execution_config
from app.services.alpaca_paper_account_service import get_alpaca_paper_snapshot


def run_post_execution_checks(
    req: ExecutionRequest,
    *,
    broker_body: dict[str, Any],
    paper: bool = True,
    expected_limit: float | None = None,
) -> PostcheckSummary:
    cfg = load_edgesense_execution_config()
    blockers: list[str] = []
    warnings: list[str] = []
    details: dict[str, Any] = {"broker_response_keys": list(broker_body.keys())}

    oid = broker_body.get("id")
    if not oid:
        blockers.append("missing_broker_order_id_in_response")
        return PostcheckSummary(submission_ok=False, blockers=blockers, warnings=warnings, details=details)

    st = broker_body.get("status")
    details["initial_status"] = st
    if st in {"rejected"}:
        blockers.append("broker_rejected_immediately")

    synced = get_broker_order(str(oid), paper=paper)
    details["sync"] = synced
    if not synced.get("ok"):
        warnings.append("order_status_sync_failed")
    else:
        order = synced.get("order") or {}
        details["synced_status"] = order.get("status")
        sym = order.get("symbol")
        if sym and sym.upper() != req.symbol.upper():
            blockers.append("broker_symbol_mismatch")
        side = order.get("side")
        if side and side != req.side:
            blockers.append("broker_side_mismatch")
        try:
            sub_qty = float(order.get("qty") or order.get("filled_qty") or 0)
            if req.quantity is not None and sub_qty > 0 and abs(sub_qty - float(req.quantity)) > 1e-6:
                warnings.append("submitted_quantity_differs_from_request")
        except (TypeError, ValueError):
            warnings.append("quantity_parse_failed")

    fill_px = broker_body.get("filled_avg_price") or broker_body.get("limit_price")
    slippage = None
    if expected_limit and fill_px:
        try:
            fp = float(fill_px)
            el = float(expected_limit)
            if el > 0:
                slippage = abs(fp - el) / el * 100.0
                if slippage > cfg.max_slippage_pct:
                    warnings.append(f"poor_fill_slippage_pct_{slippage:.3f}")
        except (TypeError, ValueError):
            pass

    pos_ok = None
    snap = get_alpaca_paper_snapshot()
    if snap.status == "connected":
        sym = req.symbol.upper()
        for p in snap.positions:
            if getattr(p, "symbol", "").upper() == sym:
                pos_ok = True
                break
        if st in {"filled", "partially_filled"} and pos_ok is None:
            warnings.append("position_not_yet_visible_may_be_eventual_consistency")

    submission_ok = bool(oid) and broker_body.get("status") not in {"rejected"}

    return PostcheckSummary(
        submission_ok=submission_ok,
        fill_quality_ok=None if slippage is None else slippage <= cfg.max_slippage_pct,
        slippage_pct=slippage,
        position_sync_ok=pos_ok,
        risk_state_updated=False,
        journal_entry_id=None,
        blockers=blockers,
        warnings=warnings,
        details=details,
    )
