from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.audit_log.models import AuditEventCreate
from app.services.audit_log.service import write_event
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.service import run_workflow
from app.services.workflow_scheduler.models import ScheduleCreateRequest, ScheduleOut, SchedulerRunOnceRequest, SchedulerStatusResponse, iso_utc_now, new_schedule_id

_MEMORY: dict[str, ScheduleOut] = {}


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def get_status() -> SchedulerStatusResponse:
    session = _db_session()
    count = len(_MEMORY)
    persistence_mode = "memory"
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import WorkflowScheduleRecord

            count = int(session.execute(select(func.count()).select_from(WorkflowScheduleRecord)).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    return SchedulerStatusResponse(updated_at=iso_utc_now(), summary={"persistence_mode": persistence_mode, "schedules_count": count})


def _to_out(row: Any) -> ScheduleOut:
    def _iso(dt):
        if not dt:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return ScheduleOut(
        schedule_id=row.schedule_id,
        name=row.name,
        enabled=bool(row.enabled),
        schedule_type=row.schedule_type,
        cron_expression=row.cron_expression,
        interval_seconds=row.interval_seconds,
        workflow_request=row.workflow_request or {},
        max_runs_per_day=int(row.max_runs_per_day),
        last_run_at=_iso(row.last_run_at),
        next_run_at=_iso(row.next_run_at),
        created_at=_iso(row.created_at) or iso_utc_now(),
        updated_at=_iso(row.updated_at) or iso_utc_now(),
    )


def create_schedule(body: ScheduleCreateRequest) -> ScheduleOut:
    now = iso_utc_now()
    sid = body.schedule_id or new_schedule_id()
    out = ScheduleOut(
        schedule_id=sid,
        name=body.name,
        enabled=bool(body.enabled),
        schedule_type=body.schedule_type,
        cron_expression=body.cron_expression,
        interval_seconds=body.interval_seconds,
        workflow_request=dict(body.workflow_request or {}),
        max_runs_per_day=int(body.max_runs_per_day),
        last_run_at=None,
        next_run_at=None,
        created_at=now,
        updated_at=now,
    )

    session = _db_session()
    if session is not None:
        try:
            from app.db.models import WorkflowScheduleRecord as Row

            session.merge(
                Row(
                    schedule_id=out.schedule_id,
                    name=out.name,
                    enabled=out.enabled,
                    schedule_type=out.schedule_type,
                    cron_expression=out.cron_expression,
                    interval_seconds=out.interval_seconds,
                    workflow_request=out.workflow_request,
                    max_runs_per_day=out.max_runs_per_day,
                    last_run_at=None,
                    next_run_at=None,
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

    _MEMORY[out.schedule_id] = out
    write_event(AuditEventCreate(event_type="schedule_created", actor="system", severity="info", message="Schedule created", metadata={"schedule_id": out.schedule_id}))
    return out


def update_schedule(schedule_id: str, body: ScheduleCreateRequest) -> ScheduleOut | None:
    existing = get_schedule(schedule_id)
    if existing is None:
        return None
    data = existing.model_dump()
    data.update({k: v for k, v in body.model_dump().items() if v is not None and k != "schedule_id"})
    data["schedule_id"] = schedule_id
    data["updated_at"] = iso_utc_now()
    out = ScheduleOut(**data)
    _MEMORY[schedule_id] = out

    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import WorkflowScheduleRecord as Row

            row = session.execute(select(Row).where(Row.schedule_id == schedule_id)).scalar_one_or_none()
            if row:
                row.name = out.name
                row.enabled = out.enabled
                row.schedule_type = out.schedule_type
                row.cron_expression = out.cron_expression
                row.interval_seconds = out.interval_seconds
                row.workflow_request = out.workflow_request
                row.max_runs_per_day = out.max_runs_per_day
                row.updated_at = datetime.now(timezone.utc)
                session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()
    return out


def enable_schedule(schedule_id: str) -> ScheduleOut | None:
    sch = get_schedule(schedule_id)
    if sch is None:
        return None
    sch.enabled = True
    sch.updated_at = iso_utc_now()
    _MEMORY[schedule_id] = sch
    return sch


def disable_schedule(schedule_id: str) -> ScheduleOut | None:
    sch = get_schedule(schedule_id)
    if sch is None:
        return None
    sch.enabled = False
    sch.updated_at = iso_utc_now()
    _MEMORY[schedule_id] = sch
    return sch


def list_schedules(limit: int = 50) -> list[ScheduleOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import WorkflowScheduleRecord as Row

            rows = session.execute(select(Row).order_by(Row.created_at.desc()).limit(limit)).scalars().all()
            out = [_to_out(r) for r in rows]
            for s in out:
                _MEMORY[s.schedule_id] = s
            return out
        except Exception:
            return list(_MEMORY.values())[:limit]
        finally:
            session.close()
    return list(_MEMORY.values())[:limit]


def get_schedule(schedule_id: str) -> ScheduleOut | None:
    if schedule_id in _MEMORY:
        return _MEMORY.get(schedule_id)
    _ = list_schedules(limit=50)
    return _MEMORY.get(schedule_id)


def run_once(body: SchedulerRunOnceRequest) -> dict[str, Any]:
    write_event(AuditEventCreate(event_type="scheduled_run_started", actor="system", severity="info", message="Scheduled run started", metadata={}))
    req = OrchestratorRunRequest.model_validate({**(body.workflow_request or {}), "dry_run": True, "allow_submit": False})
    run = run_workflow(req)
    if run.status in {"blocked", "failed"}:
        write_event(AuditEventCreate(workflow_run_id=run.workflow_run_id or None, orchestrator_run_id=run.orchestrator_run_id, event_type="scheduled_run_blocked", actor="system", severity="warn", message="Scheduled run blocked", metadata=run.model_dump()))
    return {"status": "ok", "run": run.model_dump()}

