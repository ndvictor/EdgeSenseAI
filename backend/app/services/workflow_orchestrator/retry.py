from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def record_retry_event(
    *,
    workflow_run_id: str,
    orchestrator_run_id: str | None,
    agent_key: str | None,
    attempt: int,
    status: str,
    reason: str,
    next_retry_at: datetime | None = None,
    metadata: dict[str, Any] | None = None,
) -> str:
    retry_id = f"retry_{uuid4().hex[:12]}"
    session = _db_session()
    if session is None:
        return retry_id
    try:
        from app.db.models import WorkflowRetryEventRecord

        session.merge(
            WorkflowRetryEventRecord(
                retry_id=retry_id,
                workflow_run_id=workflow_run_id,
                orchestrator_run_id=orchestrator_run_id,
                agent_key=agent_key,
                attempt=attempt,
                status=status,
                reason=reason,
                next_retry_at=next_retry_at,
                metadata_json=metadata or {},
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
        return retry_id
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        return retry_id
    finally:
        session.close()


def next_backoff_seconds(*, attempt: int, base: int = 2, cap: int = 60) -> int:
    # Deterministic exponential backoff with cap.
    return min(cap, max(1, int(base ** max(0, attempt - 1))))

