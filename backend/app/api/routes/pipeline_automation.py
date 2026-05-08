from __future__ import annotations

from fastapi import APIRouter

from app.services.pipeline_automation.models import PipelineAutomationRunRequest
from app.services.pipeline_automation.service import get_latest_pipeline_run, run_pipeline

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/run")
def post_run(body: PipelineAutomationRunRequest):
    run = run_pipeline(body)
    return {"status": "ok", "run": run.model_dump()}


@router.get("/latest")
def get_latest():
    run = get_latest_pipeline_run()
    return {"status": "ok", "run": run.model_dump() if run else None}

