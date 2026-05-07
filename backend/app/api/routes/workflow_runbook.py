"""Workflow Runbook (read-only; no LLM) API routes."""

from fastapi import APIRouter

from app.services.workflow_runbook.service import build_latest, build_stages, build_status

router = APIRouter(prefix="/workflow-runbook", tags=["workflow-runbook"])


@router.get("/status")
def get_workflow_runbook_status():
    return build_status().model_dump()


@router.get("/stages")
def get_workflow_runbook_stages():
    return build_stages().model_dump()


@router.get("/latest")
def get_workflow_runbook_latest():
    return build_latest().model_dump()

