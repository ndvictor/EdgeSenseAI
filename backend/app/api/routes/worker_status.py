from __future__ import annotations

from fastapi import APIRouter

from app.services.worker_output_store import get_latest_worker_output_summary

router = APIRouter(prefix="/worker-status", tags=["worker-status"])


@router.get("/latest")
def get_latest_worker_status():
    return {"status": "ok", **get_latest_worker_output_summary()}
