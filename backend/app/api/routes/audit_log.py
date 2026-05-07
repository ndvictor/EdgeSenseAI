from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.audit_log.models import AuditEventCreate
from app.services.audit_log.service import get_audit_log_status, get_event, list_events, write_event

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


@router.get("/status")
def get_status():
    return get_audit_log_status().model_dump()


@router.get("/events")
def get_events(limit: int = 50):
    return {"status": "ok", "events": [e.model_dump() for e in list_events(limit=limit)]}


@router.get("/events/{audit_id}")
def get_event_route(audit_id: str):
    e = get_event(audit_id)
    if e is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return {"status": "ok", "event": e.model_dump()}


@router.post("/events")
def post_event(body: AuditEventCreate):
    e = write_event(body)
    return {"status": "ok", "event": e.model_dump()}

