from __future__ import annotations

from datetime import datetime, timezone

from app.services.approval_queue.models import ApprovalActionRequest, ApprovalItemCreate, ApprovalItemOut, ApprovalQueueStatusResponse, iso_utc_now, new_approval_id
from app.services.audit_log.models import AuditEventCreate
from app.services.audit_log.service import write_event

_MEMORY: dict[str, ApprovalItemOut] = {}


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def get_status() -> ApprovalQueueStatusResponse:
    session = _db_session()
    persistence_mode = "memory"
    count = len(_MEMORY)
    pending = len([i for i in _MEMORY.values() if i.status == "pending"])
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import WorkflowApprovalItemRecord

            count = int(session.execute(select(func.count()).select_from(WorkflowApprovalItemRecord)).scalar() or 0)
            pending = int(session.execute(select(func.count()).select_from(WorkflowApprovalItemRecord).where(WorkflowApprovalItemRecord.status == "pending")).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    return ApprovalQueueStatusResponse(updated_at=iso_utc_now(), summary={"persistence_mode": persistence_mode, "items_count": count, "pending_count": pending})


def create_item(body: ApprovalItemCreate) -> ApprovalItemOut:
    now = iso_utc_now()
    approval_id = body.approval_id or new_approval_id()
    out = ApprovalItemOut(
        approval_id=approval_id,
        workflow_run_id=body.workflow_run_id,
        orchestrator_run_id=body.orchestrator_run_id,
        agent_run_id=body.agent_run_id,
        approval_type=body.approval_type,
        status=body.status,
        requested_action=dict(body.requested_action or {}),
        risk_summary=dict(body.risk_summary or {}),
        required_approver=body.required_approver,
        approved_by=None,
        rejected_by=None,
        approval_reason=body.approval_reason,
        expires_at=body.expires_at,
        created_at=now,
        updated_at=now,
    )

    session = _db_session()
    if session is not None:
        try:
            from app.db.models import WorkflowApprovalItemRecord as Row

            session.merge(
                Row(
                    approval_id=out.approval_id,
                    workflow_run_id=out.workflow_run_id,
                    orchestrator_run_id=out.orchestrator_run_id,
                    agent_run_id=out.agent_run_id,
                    approval_type=out.approval_type,
                    status=out.status,
                    requested_action=out.requested_action,
                    risk_summary=out.risk_summary,
                    required_approver=out.required_approver,
                    approved_by=None,
                    rejected_by=None,
                    approval_reason=out.approval_reason,
                    expires_at=None,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    _MEMORY[out.approval_id] = out
    write_event(AuditEventCreate(workflow_run_id=out.workflow_run_id, orchestrator_run_id=out.orchestrator_run_id, agent_run_id=out.agent_run_id, event_type="approval_requested", actor="system", severity="info", message="Approval requested", metadata={"approval_id": out.approval_id, "approval_type": out.approval_type}))
    return out


def list_items(limit: int = 50, status: str | None = None) -> list[ApprovalItemOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import WorkflowApprovalItemRecord as Row

            q = select(Row)
            if status:
                q = q.where(Row.status == status)
            rows = session.execute(q.order_by(Row.updated_at.desc()).limit(limit)).scalars().all()
            out: list[ApprovalItemOut] = []
            for r in rows:
                out.append(
                    ApprovalItemOut(
                        approval_id=r.approval_id,
                        workflow_run_id=r.workflow_run_id,
                        orchestrator_run_id=r.orchestrator_run_id,
                        agent_run_id=r.agent_run_id,
                        approval_type=r.approval_type,
                        status=r.status,
                        requested_action=r.requested_action or {},
                        risk_summary=r.risk_summary or {},
                        required_approver=r.required_approver,
                        approved_by=r.approved_by,
                        rejected_by=r.rejected_by,
                        approval_reason=r.approval_reason,
                        expires_at=r.expires_at.isoformat() if r.expires_at else None,
                        created_at=r.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if r.created_at else iso_utc_now(),
                        updated_at=r.updated_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if r.updated_at else iso_utc_now(),
                    )
                )
            for i in out:
                _MEMORY[i.approval_id] = i
            return out
        except Exception:
            pass
        finally:
            session.close()
    items = list(_MEMORY.values())
    if status:
        items = [i for i in items if i.status == status]
    return items[:limit]


def get_item(approval_id: str) -> ApprovalItemOut | None:
    if approval_id in _MEMORY:
        return _MEMORY.get(approval_id)
    rows = list_items(limit=50)
    _ = rows
    return _MEMORY.get(approval_id)


def _update_status(approval_id: str, *, new_status: str, actor_field: str | None = None, actor: str | None = None, reason: str | None = None) -> ApprovalItemOut | None:
    item = get_item(approval_id)
    if item is None:
        return None
    now = iso_utc_now()
    data = item.model_dump()
    data["status"] = new_status
    data["updated_at"] = now
    if actor_field and actor:
        data[actor_field] = actor
    if reason:
        data["approval_reason"] = reason
    updated = ApprovalItemOut(**data)
    _MEMORY[approval_id] = updated

    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import WorkflowApprovalItemRecord as Row

            row = session.execute(select(Row).where(Row.approval_id == approval_id)).scalar_one_or_none()
            if row:
                row.status = new_status
                if actor_field == "approved_by":
                    row.approved_by = actor
                if actor_field == "rejected_by":
                    row.rejected_by = actor
                row.approval_reason = updated.approval_reason
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    return updated


def approve_item(approval_id: str, body: ApprovalActionRequest) -> ApprovalItemOut | None:
    updated = _update_status(approval_id, new_status="approved", actor_field="approved_by", actor=body.actor, reason=body.reason)
    if updated:
        write_event(AuditEventCreate(workflow_run_id=updated.workflow_run_id, orchestrator_run_id=updated.orchestrator_run_id, agent_run_id=updated.agent_run_id, event_type="approval_approved", actor=body.actor, severity="info", message="Approval approved", metadata={"approval_id": approval_id}))
    return updated


def reject_item(approval_id: str, body: ApprovalActionRequest) -> ApprovalItemOut | None:
    updated = _update_status(approval_id, new_status="rejected", actor_field="rejected_by", actor=body.actor, reason=body.reason)
    if updated:
        write_event(AuditEventCreate(workflow_run_id=updated.workflow_run_id, orchestrator_run_id=updated.orchestrator_run_id, agent_run_id=updated.agent_run_id, event_type="approval_rejected", actor=body.actor, severity="warn", message="Approval rejected", metadata={"approval_id": approval_id}))
    return updated


def cancel_item(approval_id: str, body: ApprovalActionRequest) -> ApprovalItemOut | None:
    updated = _update_status(approval_id, new_status="cancelled", actor_field=None, actor=None, reason=body.reason)
    if updated:
        write_event(AuditEventCreate(workflow_run_id=updated.workflow_run_id, orchestrator_run_id=updated.orchestrator_run_id, agent_run_id=updated.agent_run_id, event_type="approval_cancelled", actor=body.actor, severity="info", message="Approval cancelled", metadata={"approval_id": approval_id}))
    return updated

