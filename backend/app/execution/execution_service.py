"""Orchestrates prechecks, approval gate, routing, post-checks, audit, journal, learning events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.execution.execution_audit import (
    compute_idempotency_key,
    create_audit,
    emit_learning_event,
    get_audit,
    get_idempotent_response,
    list_audits,
    register_idempotency,
    update_audit,
)
from app.execution.execution_prechecks import run_all_prechecks
from app.execution.edgesense_execution_config import load_edgesense_execution_config
from app.execution.order_router import route_order
from app.execution.post_execution_checks import run_post_execution_checks
from app.execution.schemas import (
    ExecutionApproveRequest,
    ExecutionRejectRequest,
    ExecutionRequest,
    ExecutionResponse,
    PostcheckSummary,
    PrecheckSummary,
)
from app.execution.order_status_service import cancel_broker_order, get_broker_order
from app.services.journal_outcome_service import JournalEntryCreateRequest, create_journal_entry


def _precheck_only_response(req: ExecutionRequest, summary: PrecheckSummary, eff: str, audit_id: str) -> ExecutionResponse:
    msg = "precheck_failed" if not summary.passed else "precheck_passed_no_submit"
    extra = ["precheck_only_endpoint_did_not_submit_order"] if summary.passed else []
    return ExecutionResponse(
        status="blocked",
        execution_mode=eff,
        symbol=req.symbol,
        side=req.side,
        requested_quantity=req.quantity,
        submitted_quantity=None,
        requested_price=req.limit_price,
        submitted_price=None,
        precheck_summary=summary,
        postcheck_summary=None,
        blockers=list(summary.blockers),
        warnings=list(summary.warnings) + extra,
        audit_id=audit_id,
        message=msg,
        created_at=datetime.now(timezone.utc),
    )


def run_precheck_only(req: ExecutionRequest, *, data_source: str = "auto") -> ExecutionResponse:
    summary, eff, _ref = run_all_prechecks(req, data_source=data_source)
    audit = create_audit(req, eff, summary, idempotency_key=None)
    update_audit(audit.audit_id, final_status="precheck_complete")
    return _precheck_only_response(req, summary, eff, audit.audit_id)


def submit_execution(req: ExecutionRequest, *, data_source: str = "auto") -> ExecutionResponse:
    cfg = load_edgesense_execution_config()
    idem = compute_idempotency_key(req)
    cached = get_idempotent_response(idem)
    if cached is not None:
        return cached.model_copy(update={"message": "idempotent_repeat"})

    summary, eff, ref = run_all_prechecks(req, data_source=data_source)
    pending = (
        req
        if summary.passed and cfg.require_human_approval and not req.human_approval_confirmed
        else None
    )
    audit = create_audit(req, eff, summary, idempotency_key=idem, pending_request=pending)

    if not summary.passed:
        update_audit(audit.audit_id, final_status="blocked", blockers=summary.blockers)
        emit_learning_event("execution_blocked", {"audit_id": audit.audit_id, "blockers": summary.blockers})
        resp = ExecutionResponse(
            status="blocked",
            execution_mode=eff,
            symbol=req.symbol,
            side=req.side,
            requested_quantity=req.quantity,
            precheck_summary=summary,
            blockers=summary.blockers,
            warnings=summary.warnings,
            audit_id=audit.audit_id,
            message="precheck_failed",
            created_at=datetime.now(timezone.utc),
        )
        register_idempotency(idem, audit.audit_id, resp)
        _journal_execution(req, audit.audit_id, resp, None)
        return resp

    if cfg.require_human_approval and not req.human_approval_confirmed:
        update_audit(audit.audit_id, final_status="pending_approval")
        emit_learning_event("execution_blocked", {"audit_id": audit.audit_id, "reason": "pending_human_approval"})
        resp = ExecutionResponse(
            status="pending_approval",
            execution_mode=eff,
            symbol=req.symbol,
            side=req.side,
            requested_quantity=req.quantity,
            precheck_summary=summary,
            blockers=[],
            warnings=summary.warnings + ["human_approval_required"],
            audit_id=audit.audit_id,
            message="awaiting_approval",
            created_at=datetime.now(timezone.utc),
        )
        register_idempotency(idem, audit.audit_id, resp)
        return resp

    return _execute_after_gates(req, summary, eff, audit.audit_id, idem, ref, data_source)


def _execute_after_gates(
    req: ExecutionRequest,
    summary: PrecheckSummary,
    eff: str,
    audit_id: str,
    idem: str,
    ref: float | None,
    data_source: str,
) -> ExecutionResponse:
    route_status, broker_body, rid = route_order(req, eff)
    post: PostcheckSummary | None = None
    broker_oid = broker_body.get("id") if isinstance(broker_body, dict) else None

    if route_status == "simulated":
        update_audit(audit_id, final_status="submitted", broker_order_id=broker_oid)
        emit_learning_event("execution_submitted", {"audit_id": audit_id, "mode": "simulated"})
        resp = ExecutionResponse(
            status="submitted",
            execution_mode=eff,
            broker_order_id=broker_oid,
            symbol=req.symbol,
            side=req.side,
            requested_quantity=req.quantity,
            submitted_quantity=req.quantity,
            requested_price=req.limit_price,
            submitted_price=req.limit_price,
            precheck_summary=summary,
            postcheck_summary=PostcheckSummary(warnings=["simulated_no_broker"]),
            warnings=summary.warnings,
            audit_id=audit_id,
            message="simulated_execution",
            created_at=datetime.now(timezone.utc),
        )
        register_idempotency(idem, audit_id, resp)
        _journal_execution(req, audit_id, resp, post)
        return resp

    if route_status == "failed":
        update_audit(audit_id, final_status="rejected", blockers=[str(broker_body)[:200]])
        emit_learning_event("execution_rejected", {"audit_id": audit_id, "broker": broker_body})
        resp = ExecutionResponse(
            status="rejected",
            execution_mode=eff,
            broker_order_id=broker_oid,
            symbol=req.symbol,
            side=req.side,
            requested_quantity=req.quantity,
            precheck_summary=summary,
            blockers=[json.dumps(broker_body)[:300]],
            warnings=summary.warnings,
            audit_id=audit_id,
            message="broker_rejected",
            created_at=datetime.now(timezone.utc),
        )
        register_idempotency(idem, audit_id, resp)
        _journal_execution(req, audit_id, resp, post)
        return resp

    post = run_post_execution_checks(req, broker_body=broker_body, paper=True, expected_limit=req.limit_price or ref)
    bstatus = broker_body.get("status") if isinstance(broker_body, dict) else None
    estatus: Any = "submitted"
    if bstatus == "filled":
        estatus = "filled"
    elif bstatus == "partially_filled":
        estatus = "partially_filled"
    elif bstatus in {"canceled", "cancelled"}:
        estatus = "canceled"

    update_audit(
        audit_id,
        final_status=str(estatus),
        order_id=str(broker_oid) if broker_oid else None,
        broker_order_id=str(broker_oid) if broker_oid else None,
        warnings=post.warnings,
        blockers=post.blockers,
    )
    emit_learning_event("execution_submitted", {"audit_id": audit_id, "broker_order_id": broker_oid})

    if post.warnings and any("poor_fill" in w for w in post.warnings):
        emit_learning_event("poor_fill_quality", {"audit_id": audit_id})

    resp = ExecutionResponse(
        status=estatus,
        execution_mode=eff,
        order_id=str(broker_oid) if broker_oid else None,
        broker_order_id=str(broker_oid) if broker_oid else None,
        symbol=req.symbol,
        side=req.side,
        requested_quantity=req.quantity,
        submitted_quantity=req.quantity,
        requested_price=req.limit_price,
        submitted_price=broker_body.get("limit_price") if isinstance(broker_body, dict) else None,
        precheck_summary=summary,
        postcheck_summary=post,
        blockers=post.blockers,
        warnings=summary.warnings + post.warnings,
        audit_id=audit_id,
        message="order_routed",
        created_at=datetime.now(timezone.utc),
    )
    register_idempotency(idem, audit_id, resp)
    _journal_execution(req, audit_id, resp, post)
    return resp


def _journal_execution(req: ExecutionRequest, audit_id: str, resp: ExecutionResponse, post: PostcheckSummary | None) -> None:
    fill_px = None
    if resp.postcheck_summary and resp.postcheck_summary.details:
        fill_px = resp.postcheck_summary.details.get("initial_status")
    notes = json.dumps(
        {
            "audit_id": audit_id,
            "status": resp.status,
            "broker_order_id": resp.broker_order_id,
            "precheck_blockers": resp.precheck_summary.blockers,
            "post_warnings": (post.warnings if post else []),
        },
        default=str,
    )[:8000]
    try:
        entry = create_journal_entry(
            JournalEntryCreateRequest(
                source_type="manual_observation",
                source_id=audit_id,
                symbol=req.symbol,
                strategy_key=req.strategy_id,
                notes=notes,
            )
        )
        if resp.postcheck_summary:
            resp.postcheck_summary.journal_entry_id = entry.id
    except Exception:
        pass


def approve_execution(body: ExecutionApproveRequest) -> ExecutionResponse:
    rec = get_audit(body.audit_id)
    if not rec or not rec.pending_request:
        return ExecutionResponse(
            status="error",
            execution_mode="paper",
            symbol="UNKNOWN",
            side="buy",
            precheck_summary=PrecheckSummary(passed=False, steps=[], blockers=["pending_request_not_found"], warnings=[]),
            blockers=["pending_request_not_found"],
            audit_id=body.audit_id,
            message="approve_failed",
            created_at=datetime.now(timezone.utc),
        )
    req = rec.pending_request
    req.human_approval_confirmed = True
    # Re-run from gates (prechecks may have aged — product choice: full re-run)
    idem = compute_idempotency_key(req)
    summary, eff, ref = run_all_prechecks(req)
    if not summary.passed:
        return ExecutionResponse(
            status="blocked",
            execution_mode=eff,
            symbol=req.symbol,
            side=req.side,
            precheck_summary=summary,
            blockers=summary.blockers,
            audit_id=body.audit_id,
            message="stale_precheck_failed_on_approve",
            created_at=datetime.now(timezone.utc),
        )
    return _execute_after_gates(req, summary, eff, body.audit_id, idem, ref, "auto")


def reject_execution(body: ExecutionRejectRequest) -> ExecutionResponse:
    rec = get_audit(body.audit_id)
    update_audit(body.audit_id, final_status="rejected", blockers=[body.reason or "rejected_by_operator"])
    emit_learning_event("execution_rejected", {"audit_id": body.audit_id, "reason": body.reason})
    sym = rec.pending_request.symbol if rec and rec.pending_request else "UNKNOWN"
    side = rec.pending_request.side if rec and rec.pending_request else "buy"
    return ExecutionResponse(
        status="rejected",
        execution_mode="paper",
        symbol=sym,
        side=side,
        precheck_summary=PrecheckSummary(passed=False, steps=[], blockers=[body.reason or "rejected"], warnings=[]),
        audit_id=body.audit_id,
        message="rejected",
        created_at=datetime.now(timezone.utc),
    )


def list_execution_orders(limit: int = 50) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in list_audits(limit):
        out.append(
            {
                "audit_id": a.audit_id,
                "final_status": a.final_status,
                "broker_order_id": a.broker_order_id,
                "created_at": a.created_at.isoformat(),
                "request_summary": a.request_summary,
                "blockers": a.blockers,
            }
        )
    return out


def get_execution_order(order_id: str) -> dict[str, Any]:
    if order_id.startswith("aud-"):
        rec = get_audit(order_id)
        if not rec:
            return {"not_configured": True, "error": "audit_not_found"}
        return {
            "audit_id": rec.audit_id,
            "org_slug": rec.org_slug,
            "final_status": rec.final_status,
            "broker_order_id": rec.broker_order_id,
            "blockers": rec.blockers,
            "warnings": rec.warnings,
            "request_summary": rec.request_summary,
            "precheck": rec.precheck.model_dump() if rec.precheck else None,
            "created_at": rec.created_at.isoformat(),
            "updated_at": rec.updated_at.isoformat(),
        }
    sync = get_broker_order(order_id, paper=True)
    return sync


def cancel_execution_order(order_id: str) -> dict[str, Any]:
    if order_id.startswith("aud-"):
        return {"not_configured": True, "error": "use_broker_order_id_for_cancel"}
    return cancel_broker_order(order_id, paper=True)


def sync_execution_order(order_id: str) -> dict[str, Any]:
    return get_broker_order(order_id, paper=True)
