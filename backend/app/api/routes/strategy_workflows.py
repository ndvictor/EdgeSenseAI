from fastapi import APIRouter, HTTPException

from app.services.strategy_workflow_run_service import (
    StrategyWorkflowRunRequest,
    StrategyWorkflowRunResult,
    get_latest_strategy_workflow_run,
    get_strategy_workflow_run,
    list_strategy_workflow_runs,
    run_strategy_workflow_from_signal,
)

router = APIRouter()


@router.get("/strategy-workflows/runs", response_model=list[StrategyWorkflowRunResult])
def get_strategy_workflow_runs(limit: int = 25):
    return list_strategy_workflow_runs(limit)


@router.get("/strategy-workflows/runs/latest", response_model=StrategyWorkflowRunResult | None)
def get_latest_strategy_workflow_run_route():
    return get_latest_strategy_workflow_run()


@router.get("/strategy-workflows/runs/{workflow_run_id}", response_model=StrategyWorkflowRunResult)
def get_strategy_workflow_run_route(workflow_run_id: str):
    run = get_strategy_workflow_run(workflow_run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Strategy workflow run not found")
    return run


@router.post("/strategy-workflows/run", response_model=StrategyWorkflowRunResult)
def post_strategy_workflow_run(request: StrategyWorkflowRunRequest):
    return run_strategy_workflow_from_signal(request)
