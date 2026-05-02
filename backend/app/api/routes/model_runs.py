from fastapi import APIRouter

from app.services.model_orchestrator_service import (
    ModelRunPlanRequest,
    ModelRunPlanResponse,
    ModelRunRequest,
    ModelRunResponse,
    get_model_registry,
    plan_model_runs,
    run_model_orchestrator,
)

router = APIRouter()


@router.get("/model-runs/registry")
def get_registry():
    return get_model_registry()


@router.post("/model-runs/plan", response_model=ModelRunPlanResponse)
def post_model_run_plan(request: ModelRunPlanRequest):
    return plan_model_runs(request)


@router.post("/model-runs/run", response_model=ModelRunResponse)
def post_model_run(request: ModelRunRequest):
    return run_model_orchestrator(request)
