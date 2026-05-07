from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.workflow_scheduler.models import ScheduleCreateRequest, SchedulerRunOnceRequest
from app.services.workflow_scheduler.service import (
    create_schedule,
    disable_schedule,
    enable_schedule,
    get_schedule,
    get_status,
    list_schedules,
    run_once,
    update_schedule,
)

router = APIRouter(prefix="/workflow-scheduler", tags=["workflow-scheduler"])


@router.get("/status")
def get_scheduler_status():
    return get_status().model_dump()


@router.get("/schedules")
def get_schedules(limit: int = 50):
    return {"status": "ok", "schedules": [s.model_dump() for s in list_schedules(limit=limit)]}


@router.get("/schedules/{schedule_id}")
def get_schedule_route(schedule_id: str):
    sch = get_schedule(schedule_id)
    if sch is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "ok", "schedule": sch.model_dump()}


@router.post("/schedules")
def post_schedule(body: ScheduleCreateRequest):
    sch = create_schedule(body)
    return {"status": "ok", "schedule": sch.model_dump()}


@router.put("/schedules/{schedule_id}")
def put_schedule(schedule_id: str, body: ScheduleCreateRequest):
    sch = update_schedule(schedule_id, body)
    if sch is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "ok", "schedule": sch.model_dump()}


@router.post("/schedules/{schedule_id}/enable")
def post_enable(schedule_id: str):
    sch = enable_schedule(schedule_id)
    if sch is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "ok", "schedule": sch.model_dump()}


@router.post("/schedules/{schedule_id}/disable")
def post_disable(schedule_id: str):
    sch = disable_schedule(schedule_id)
    if sch is None:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"status": "ok", "schedule": sch.model_dump()}


@router.post("/run-once")
def post_run_once(body: SchedulerRunOnceRequest):
    return run_once(body)

