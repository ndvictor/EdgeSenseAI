from fastapi import APIRouter

from app.schemas import AccountRiskProfile
from app.services.decision_workflow_service import (
    DecisionWorkflowRunRequest,
    DecisionWorkflowRunResponse,
    build_default_decision_workflow,
    get_latest_decision_workflow_run,
    list_decision_workflow_runs,
    run_decision_workflow,
)

router = APIRouter()


@router.get("/decision-workflows/runs/latest", response_model=DecisionWorkflowRunResponse | None)
def get_latest_decision_workflow_run_route():
    return get_latest_decision_workflow_run()


@router.get("/decision-workflows/runs", response_model=list[DecisionWorkflowRunResponse])
def list_decision_workflow_runs_route(limit: int = 20):
    return list_decision_workflow_runs(limit)


@router.post("/decision-workflows/run", response_model=DecisionWorkflowRunResponse)
def post_decision_workflow_run(request: DecisionWorkflowRunRequest):
    return run_decision_workflow(request, account_profile=AccountRiskProfile())


@router.post("/decision-workflows/run-default", response_model=DecisionWorkflowRunResponse)
def post_default_decision_workflow_run():
    return build_default_decision_workflow(account_profile=AccountRiskProfile())
