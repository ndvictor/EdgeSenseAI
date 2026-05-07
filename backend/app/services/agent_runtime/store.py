from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.agent_runtime.models import AgentRunResult, WorkflowRunRecord


# In-memory storage (Phase 0/1)
_WORKFLOW_RUNS: dict[str, WorkflowRunRecord] = {}
_AGENT_RUNS: dict[str, AgentRunResult] = {}
_LATEST_AGENT_RUN_BY_KEY: dict[str, str] = {}  # agent_key -> run_id
_IDEMPOTENCY_INDEX: dict[str, str] = {}  # fingerprint -> run_id


def _parse_iso_utc(ts: str | None) -> datetime:
    """Best-effort ISO parse for agent runtime timestamps (always store as tz-aware UTC)."""
    if not ts:
        return datetime.now(timezone.utc)
    try:
        s = ts.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _db_session():
    """
    Best-effort DB session.
    Must never raise: if Postgres is unavailable, callers should fallback to memory.
    """
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        # Uses Base.metadata.create_all behind the scenes (no migration system).
        init_db()
        return open_session()
    except Exception:
        return None


def _db_ready_for_agent_runtime() -> bool:
    """
    True only when DB is reachable and agent-runtime tables can be used.
    Keep this conservative so we never break startup/tests.
    """
    session = _db_session()
    if session is None:
        return False
    try:
        # Touch the mapped tables. If they don't exist yet, init_db() should have created them.
        from sqlalchemy import text

        session.execute(text("SELECT 1 FROM agent_runs LIMIT 1"))
        return True
    except Exception:
        return False
    finally:
        try:
            session.close()
        except Exception:
            pass


def store_workflow_run(rec: WorkflowRunRecord) -> None:
    _WORKFLOW_RUNS[rec.workflow_run_id] = rec
    save_agent_workflow_run(rec)


def get_workflow_run(workflow_run_id: str) -> WorkflowRunRecord | None:
    db = get_agent_workflow_run(workflow_run_id)
    if db is not None:
        # keep memory warm for /latest snapshot speed within-process
        _WORKFLOW_RUNS[workflow_run_id] = db
        return db
    return _WORKFLOW_RUNS.get(workflow_run_id)


def list_workflow_runs() -> list[WorkflowRunRecord]:
    db = list_agent_workflow_runs(limit=500)
    if db:
        for r in db:
            _WORKFLOW_RUNS[r.workflow_run_id] = r
        return db
    return list(_WORKFLOW_RUNS.values())


def store_agent_run(result: AgentRunResult) -> None:
    _AGENT_RUNS[result.run_id] = result
    _LATEST_AGENT_RUN_BY_KEY[result.agent_key] = result.run_id
    save_agent_run(result)


def get_agent_run(run_id: str) -> AgentRunResult | None:
    db = get_agent_run_record(run_id)
    if db is not None:
        _AGENT_RUNS[run_id] = db
        _LATEST_AGENT_RUN_BY_KEY[db.agent_key] = db.run_id
        return db
    return _AGENT_RUNS.get(run_id)


def list_agent_runs() -> list[AgentRunResult]:
    # Used by /latest snapshot; prefer DB when available.
    if _db_ready_for_agent_runtime():
        # Keep scope bounded.
        session = _db_session()
        if session is None:
            return list(_AGENT_RUNS.values())
        try:
            from sqlalchemy import select

            from app.db.models import AgentRunRecord

            rows = (
                session.execute(select(AgentRunRecord).order_by(AgentRunRecord.created_at.desc()).limit(500))
                .scalars()
                .all()
            )
            out: list[AgentRunResult] = []
            for row in rows:
                out.append(_row_to_agent_run_result(row))
            for r in out:
                _AGENT_RUNS[r.run_id] = r
                _LATEST_AGENT_RUN_BY_KEY[r.agent_key] = r.run_id
            return out
        except Exception:
            return list(_AGENT_RUNS.values())
        finally:
            session.close()
    return list(_AGENT_RUNS.values())


def get_latest_agent_run_id(agent_key: str) -> str | None:
    # Prefer Postgres so /latest works across restarts.
    latest = get_latest_agent_run_by_key(agent_key)
    if latest is not None:
        _AGENT_RUNS[latest.run_id] = latest
        _LATEST_AGENT_RUN_BY_KEY[agent_key] = latest.run_id
        return latest.run_id
    return _LATEST_AGENT_RUN_BY_KEY.get(agent_key)


def index_idempotency(fingerprint: str, run_id: str) -> None:
    _IDEMPOTENCY_INDEX[fingerprint] = run_id
    try:
        from app.services.agent_runtime.redis_runtime import set_idempotency_cache

        set_idempotency_cache(fingerprint=fingerprint, run_id=run_id)
    except Exception:
        pass
    # Best-effort persistence: workflow_run_id/agent_key are looked up from memory if available.
    result = _AGENT_RUNS.get(run_id)
    if result is not None:
        save_agent_idempotency_fingerprint(
            fingerprint=fingerprint,
            run_id=run_id,
            workflow_run_id=result.workflow_run_id,
            agent_key=result.agent_key,
        )


def lookup_idempotency(fingerprint: str) -> str | None:
    try:
        from app.services.agent_runtime.redis_runtime import get_idempotency_cache

        cached = get_idempotency_cache(fingerprint)
        if cached:
            _IDEMPOTENCY_INDEX[fingerprint] = cached
            return cached
    except Exception:
        pass
    db = get_agent_run_id_by_idempotency_fingerprint(fingerprint)
    if db:
        _IDEMPOTENCY_INDEX[fingerprint] = db
        return db
    return _IDEMPOTENCY_INDEX.get(fingerprint)


def persistence_mode() -> str:
    return "postgres" if _db_ready_for_agent_runtime() else "memory"


# -----------------------------
# Postgres persistence (best-effort)
# -----------------------------
def _row_to_workflow_run_record(row: Any) -> WorkflowRunRecord:
    return WorkflowRunRecord.model_validate(
        {
            "workflow_run_id": row.workflow_run_id,
            "workflow_name": row.workflow_name or "",
            "asset_class": row.asset_class or "",
            "horizon": row.horizon or "",
            "mode": row.mode or "",
            "source": row.source or "",
            "status": row.status or "created",
            "current_stage": row.current_stage,
            "current_agent_key": row.current_agent_key,
            "stage_states": row.stage_states or {},
            "agent_run_ids": row.agent_run_ids or [],
            "blockers": row.blockers or [],
            "warnings": row.warnings or [],
            "metadata": row.metadata_json or {},
            "created_at": (row.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if row.created_at else ""),
            "updated_at": (row.updated_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if row.updated_at else ""),
        }
    )


def _row_to_agent_run_result(row: Any) -> AgentRunResult:
    return AgentRunResult.model_validate(
        {
            "run_id": row.run_id,
            "workflow_run_id": row.workflow_run_id,
            "agent_key": row.agent_key,
            "status": row.status or "recorded",
            "decision": row.decision or {},
            "blockers": row.blockers or [],
            "warnings": row.warnings or [],
            "next_action": row.next_action or "",
            "next_agent": row.next_agent,
            "artifacts": row.artifacts or {},
            "trace_id": row.trace_id or "",
            "trace": row.trace or [],
            "idempotency_key": row.idempotency_key or "",
            "inputs_hash": row.inputs_hash or "",
            "created_at": (row.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if row.created_at else ""),
        }
    )


def save_agent_workflow_run(rec: WorkflowRunRecord) -> None:
    session = _db_session()
    if session is None:
        return
    try:
        from app.db.models import AgentWorkflowRunRecord

        row = AgentWorkflowRunRecord(
            workflow_run_id=rec.workflow_run_id,
            workflow_name=rec.workflow_name,
            asset_class=rec.asset_class,
            horizon=rec.horizon,
            mode=rec.mode,
            source=rec.source,
            status=rec.status,
            current_stage=rec.current_stage,
            current_agent_key=rec.current_agent_key,
            stage_states=rec.stage_states,
            agent_run_ids=rec.agent_run_ids,
            blockers=rec.blockers,
            warnings=rec.warnings,
            metadata_json=rec.metadata,
            created_at=_parse_iso_utc(rec.created_at),
            updated_at=_parse_iso_utc(rec.updated_at),
        )
        session.merge(row)
        session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        session.close()


def get_agent_workflow_run(workflow_run_id: str) -> WorkflowRunRecord | None:
    session = _db_session()
    if session is None:
        return None
    try:
        from sqlalchemy import select

        from app.db.models import AgentWorkflowRunRecord

        row = session.execute(select(AgentWorkflowRunRecord).where(AgentWorkflowRunRecord.workflow_run_id == workflow_run_id)).scalar_one_or_none()
        if row is None:
            return None
        return _row_to_workflow_run_record(row)
    except Exception:
        return None
    finally:
        session.close()


def list_agent_workflow_runs(limit: int = 20) -> list[WorkflowRunRecord]:
    session = _db_session()
    if session is None:
        return []
    try:
        from sqlalchemy import select

        from app.db.models import AgentWorkflowRunRecord

        rows = session.execute(select(AgentWorkflowRunRecord).order_by(AgentWorkflowRunRecord.created_at.desc()).limit(limit)).scalars().all()
        return [_row_to_workflow_run_record(r) for r in rows]
    except Exception:
        return []
    finally:
        session.close()


def save_agent_run(result: AgentRunResult) -> None:
    session = _db_session()
    if session is None:
        return
    try:
        from app.db.models import AgentRunRecord

        row = AgentRunRecord(
            run_id=result.run_id,
            workflow_run_id=result.workflow_run_id,
            agent_key=result.agent_key,
            status=result.status,
            decision=result.decision,
            blockers=result.blockers,
            warnings=result.warnings,
            next_action=result.next_action,
            next_agent=result.next_agent,
            artifacts=result.artifacts,
            trace_id=result.trace_id,
            trace=result.trace,
            idempotency_key=result.idempotency_key,
            inputs_hash=result.inputs_hash,
            created_at=_parse_iso_utc(result.created_at),
        )
        session.merge(row)
        session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        session.close()


def get_agent_run_record(run_id: str) -> AgentRunResult | None:
    session = _db_session()
    if session is None:
        return None
    try:
        from sqlalchemy import select

        from app.db.models import AgentRunRecord

        row = session.execute(select(AgentRunRecord).where(AgentRunRecord.run_id == run_id)).scalar_one_or_none()
        if row is None:
            return None
        return _row_to_agent_run_result(row)
    except Exception:
        return None
    finally:
        session.close()


def get_latest_agent_run_by_key(agent_key: str) -> AgentRunResult | None:
    session = _db_session()
    if session is None:
        return None
    try:
        from sqlalchemy import select

        from app.db.models import AgentRunRecord

        row = (
            session.execute(
                select(AgentRunRecord)
                .where(AgentRunRecord.agent_key == agent_key)
                .order_by(AgentRunRecord.created_at.desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if row is None:
            return None
        return _row_to_agent_run_result(row)
    except Exception:
        return None
    finally:
        session.close()


def save_agent_idempotency_fingerprint(*, fingerprint: str, run_id: str, workflow_run_id: str, agent_key: str) -> None:
    session = _db_session()
    if session is None:
        return
    try:
        from app.db.models import AgentIdempotencyIndexRecord

        row = AgentIdempotencyIndexRecord(
            fingerprint=fingerprint,
            run_id=run_id,
            workflow_run_id=workflow_run_id,
            agent_key=agent_key,
            created_at=datetime.now(timezone.utc),
        )
        session.merge(row)
        session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        session.close()


def get_agent_run_id_by_idempotency_fingerprint(fingerprint: str) -> str | None:
    session = _db_session()
    if session is None:
        return None
    try:
        from sqlalchemy import select

        from app.db.models import AgentIdempotencyIndexRecord

        row = (
            session.execute(
                select(AgentIdempotencyIndexRecord).where(AgentIdempotencyIndexRecord.fingerprint == fingerprint)
            )
            .scalars()
            .first()
        )
        return row.run_id if row else None
    except Exception:
        return None
    finally:
        session.close()

