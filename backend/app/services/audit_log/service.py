from __future__ import annotations

from datetime import datetime, timezone

from app.services.audit_log.models import AuditEventCreate, AuditEventOut, AuditLogStatusResponse, iso_utc_now, new_audit_id

_MEMORY: dict[str, AuditEventOut] = {}


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def get_audit_log_status() -> AuditLogStatusResponse:
    session = _db_session()
    persistence_mode = "memory"
    count = len(_MEMORY)
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import WorkflowAuditEventRecord

            count = int(session.execute(select(func.count()).select_from(WorkflowAuditEventRecord)).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    return AuditLogStatusResponse(updated_at=iso_utc_now(), summary={"persistence_mode": persistence_mode, "events_count": count})


def write_event(body: AuditEventCreate) -> AuditEventOut:
    audit_id = body.audit_id or new_audit_id()
    out = AuditEventOut(
        audit_id=audit_id,
        workflow_run_id=body.workflow_run_id,
        orchestrator_run_id=body.orchestrator_run_id,
        agent_run_id=body.agent_run_id,
        event_type=body.event_type,
        actor=body.actor,
        severity=body.severity,
        message=body.message,
        metadata=dict(body.metadata or {}),
        created_at=iso_utc_now(),
    )

    session = _db_session()
    if session is not None:
        try:
            from app.db.models import WorkflowAuditEventRecord as Row

            session.merge(
                Row(
                    audit_id=out.audit_id,
                    workflow_run_id=out.workflow_run_id,
                    orchestrator_run_id=out.orchestrator_run_id,
                    agent_run_id=out.agent_run_id,
                    event_type=out.event_type,
                    actor=out.actor,
                    severity=out.severity,
                    message=out.message,
                    metadata_json=out.metadata,
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
            _MEMORY[out.audit_id] = out
            return out
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    _MEMORY[out.audit_id] = out
    return out


def list_events(limit: int = 50) -> list[AuditEventOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import WorkflowAuditEventRecord as Row

            rows = session.execute(select(Row).order_by(Row.created_at.desc()).limit(limit)).scalars().all()
            out: list[AuditEventOut] = []
            for r in rows:
                out.append(
                    AuditEventOut(
                        audit_id=r.audit_id,
                        workflow_run_id=r.workflow_run_id,
                        orchestrator_run_id=r.orchestrator_run_id,
                        agent_run_id=r.agent_run_id,
                        event_type=r.event_type,
                        actor=r.actor,
                        severity=r.severity,
                        message=r.message,
                        metadata=r.metadata_json or {},
                        created_at=r.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
                        if r.created_at
                        else iso_utc_now(),
                    )
                )
            for e in out:
                _MEMORY[e.audit_id] = e
            return out
        except Exception:
            return list(_MEMORY.values())[:limit]
        finally:
            session.close()
    return list(_MEMORY.values())[:limit]


def get_event(audit_id: str) -> AuditEventOut | None:
    if audit_id in _MEMORY:
        return _MEMORY.get(audit_id)
    session = _db_session()
    if session is None:
        return None
    try:
        from sqlalchemy import select

        from app.db.models import WorkflowAuditEventRecord as Row

        r = session.execute(select(Row).where(Row.audit_id == audit_id)).scalar_one_or_none()
        if r is None:
            return None
        out = AuditEventOut(
            audit_id=r.audit_id,
            workflow_run_id=r.workflow_run_id,
            orchestrator_run_id=r.orchestrator_run_id,
            agent_run_id=r.agent_run_id,
            event_type=r.event_type,
            actor=r.actor,
            severity=r.severity,
            message=r.message,
            metadata=r.metadata_json or {},
            created_at=r.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if r.created_at else iso_utc_now(),
        )
        _MEMORY[out.audit_id] = out
        return out
    except Exception:
        return None
    finally:
        session.close()

