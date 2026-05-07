from __future__ import annotations

from fastapi import APIRouter

from app.services.workflow_governance.models import WorkflowGovernanceCheckRequest
from app.services.workflow_governance.service import check_governance, get_governance_status

router = APIRouter(prefix="/workflow-governance", tags=["workflow-governance"])


@router.get("/status")
def get_status():
    return get_governance_status().model_dump()


@router.post("/check")
def post_check(body: WorkflowGovernanceCheckRequest):
    return check_governance(body).model_dump()

