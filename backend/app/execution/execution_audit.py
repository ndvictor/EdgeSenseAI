"""Audit log, idempotency, pending approvals, learning-loop events."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from app.execution.schemas import ExecutionRequest, ExecutionResponse, PrecheckSummary

LearningEventType = Literal[
    "execution_submitted",
    "execution_blocked",
    "execution_rejected",
    "execution_filled",
    "execution_canceled",
    "poor_fill_quality",
    "risk_limit_triggered",
]


@dataclass
class ExecutionAuditRecord:
    audit_id: str
    org_slug: str
    user_id: str | None
    request_summary: dict[str, Any]
    execution_mode: str
    precheck: PrecheckSummary | None
    precheck_passed: bool | None
    blockers: list[str]
    warnings: list[str]
    order_id: str | None
    broker_order_id: str | None
    final_status: str
    created_at: datetime
    updated_at: datetime
    pending_request: ExecutionRequest | None = None
    idempotency_key: str | None = None


_AUDITS: dict[str, ExecutionAuditRecord] = {}
_IDEMPOTENCY: dict[str, str] = {}
_LAST_RESPONSES: dict[str, ExecutionResponse] = {}
_LEARNING: list[dict[str, Any]] = []
_MAX_AUDITS = 500


def _trim() -> None:
    if len(_AUDITS) <= _MAX_AUDITS:
        return
    # drop oldest by created_at
    sorted_ids = sorted(_AUDITS.keys(), key=lambda i: _AUDITS[i].created_at)
    for aid in sorted_ids[: len(sorted_ids) - _MAX_AUDITS]:
        rec = _AUDITS.pop(aid, None)
        if rec and rec.idempotency_key:
            _IDEMPOTENCY.pop(rec.idempotency_key, None)


def compute_idempotency_key(req: ExecutionRequest) -> str:
    if req.client_request_id:
        return f"client:{req.org_slug}:{req.client_request_id}"
    bucket = int(datetime.now(timezone.utc).timestamp() // 300)
    rid = req.recommendation_id or "none"
    qty = req.quantity or 0.0
    return f"auto:{req.org_slug}:{rid}:{req.symbol.upper()}:{req.side}:{qty}:{bucket}"


def get_idempotent_response(key: str) -> ExecutionResponse | None:
    aid = _IDEMPOTENCY.get(key)
    if not aid:
        return None
    return _LAST_RESPONSES.get(aid)


def register_idempotency(key: str, audit_id: str, response: ExecutionResponse | None) -> None:
    _IDEMPOTENCY[key] = audit_id
    if response is not None:
        _LAST_RESPONSES[audit_id] = response


def emit_learning_event(event: LearningEventType, payload: dict[str, Any]) -> None:
    _LEARNING.append(
        {
            "event": event,
            "payload": payload,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    if len(_LEARNING) > 2000:
        del _LEARNING[:1000]


def create_audit(
    req: ExecutionRequest,
    execution_mode: str,
    precheck: PrecheckSummary | None,
    *,
    idempotency_key: str | None = None,
    pending_request: ExecutionRequest | None = None,
) -> ExecutionAuditRecord:
    now = datetime.now(timezone.utc)
    aid = f"aud-{uuid4().hex[:14]}"
    summary = {
        "symbol": req.symbol,
        "side": req.side,
        "asset_class": req.asset_class,
        "quantity": req.quantity,
        "order_type": req.order_type,
        "source": req.source,
        "recommendation_id": req.recommendation_id,
        "strategy_id": req.strategy_id,
    }
    rec = ExecutionAuditRecord(
        audit_id=aid,
        org_slug=req.org_slug,
        user_id=req.user_id,
        request_summary=summary,
        execution_mode=execution_mode,
        precheck=precheck,
        precheck_passed=precheck.passed if precheck else None,
        blockers=list(precheck.blockers) if precheck else [],
        warnings=list(precheck.warnings) if precheck else [],
        order_id=None,
        broker_order_id=None,
        final_status="init",
        created_at=now,
        updated_at=now,
        pending_request=pending_request,
        idempotency_key=idempotency_key,
    )
    _AUDITS[aid] = rec
    _trim()
    return rec


def update_audit(
    audit_id: str,
    *,
    final_status: str | None = None,
    blockers: list[str] | None = None,
    warnings: list[str] | None = None,
    order_id: str | None = None,
    broker_order_id: str | None = None,
) -> None:
    rec = _AUDITS.get(audit_id)
    if not rec:
        return
    rec.updated_at = datetime.now(timezone.utc)
    if final_status is not None:
        rec.final_status = final_status
    if blockers is not None:
        rec.blockers = blockers
    if warnings is not None:
        rec.warnings = warnings
    if order_id is not None:
        rec.order_id = order_id
    if broker_order_id is not None:
        rec.broker_order_id = broker_order_id


def get_audit(audit_id: str) -> ExecutionAuditRecord | None:
    return _AUDITS.get(audit_id)


def list_audits(limit: int = 50) -> list[ExecutionAuditRecord]:
    rows = sorted(_AUDITS.values(), key=lambda r: r.created_at, reverse=True)
    return rows[:limit]


def list_learning_events(limit: int = 100) -> list[dict[str, Any]]:
    return list(reversed(_LEARNING[-limit:]))


def clear_execution_audit_for_tests() -> None:
    _AUDITS.clear()
    _IDEMPOTENCY.clear()
    _LAST_RESPONSES.clear()
    _LEARNING.clear()
