from fastapi import APIRouter

from app.services.auto_run_control_service import AutoRunControlState, AutoRunControlUpdate, get_auto_run_state, update_auto_run_state

# This route is a manual/tool surface. It is not the autonomous workflow entrypoint.
# Autonomous workflow execution must go through /api/workflow-orchestrator/run.

router = APIRouter()


@router.get("/auto-run/status", response_model=AutoRunControlState)
def get_auto_run_status():
    return get_auto_run_state()


@router.put("/auto-run/status", response_model=AutoRunControlState)
def put_auto_run_status(update: AutoRunControlUpdate):
    return update_auto_run_state(update)
