from __future__ import annotations

from fastapi import APIRouter

from app.services.qlib_integration.models import QlibBacktestRecordCreate, QlibModelArtifactRegisterCreate, QlibSignalScoreCreate
from app.services.qlib_integration.service import (
    automation_backtest,
    automation_score,
    get_qlib_automation_status,
    get_latest_signal_scores,
    get_qlib_status,
    get_qlib_job,
    list_qlib_jobs,
    list_artifacts,
    record_backtest_artifact,
    register_model_artifact,
    save_signal_scores,
)

router = APIRouter(prefix="/qlib", tags=["qlib"])


@router.get("/status")
def get_status():
    return get_qlib_status().model_dump()


@router.get("/artifacts")
def get_artifacts(limit: int = 50):
    return {"status": "ok", "artifacts": [a.model_dump() for a in list_artifacts(limit=limit)]}


@router.get("/signals/latest")
def get_signals_latest():
    a = get_latest_signal_scores()
    return {"status": "ok", "artifact": a.model_dump() if a else None}


@router.post("/signals/score")
def post_signal_score(body: QlibSignalScoreCreate):
    a = save_signal_scores(body)
    return {"status": "ok", "artifact": a.model_dump()}


@router.post("/backtests/record")
def post_backtest_record(body: QlibBacktestRecordCreate):
    a = record_backtest_artifact(body)
    return {"status": "ok", "artifact": a.model_dump(), "proof_record": a.metadata.get("proof_record") if isinstance(a.metadata, dict) else None}


@router.post("/models/register-artifact")
def post_register_model_artifact(body: QlibModelArtifactRegisterCreate):
    a = register_model_artifact(body)
    return {"status": "ok", "artifact": a.model_dump()}


@router.get("/automation/status")
def get_automation_status():
    return get_qlib_automation_status()


@router.get("/automation/jobs")
def get_automation_jobs(limit: int = 50):
    return {"status": "ok", "jobs": list_qlib_jobs(limit=limit)}


@router.get("/automation/jobs/{job_id}")
def get_automation_job(job_id: str):
    job = get_qlib_job(job_id)
    return {"status": "ok" if job else "not_found", "job": job}


@router.post("/automation/backtest")
def post_automation_backtest(payload: dict):
    return automation_backtest(payload=payload)


@router.post("/automation/score")
def post_automation_score(payload: dict):
    return automation_score(payload=payload)

