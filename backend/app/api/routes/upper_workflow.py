"""Upper Workflow API Routes."""

from fastapi import APIRouter

from app.services.upper_workflow_service import (
    UpperWorkflowRequest,
    UpperWorkflowResponse,
    get_latest_upper_workflow,
    list_upper_workflow_history,
    run_upper_workflow,
)

router = APIRouter()


@router.post("/upper-workflow/run", response_model=UpperWorkflowResponse)
def post_upper_workflow_run(request: UpperWorkflowRequest):
    """Run the complete upper workflow.

    Approved workflow sequence:
    1. Runtime cadence
    2. Data freshness check
    3. Market regime model
    4. Strategy debate
    5. Strategy ranking
    6. Model selection for top strategy
    7. Universe selection/watchlist builder
    8. Optional promotion to candidate universe

    Explicit symbols required - NO defaults.
    NO LLM calls.
    Live trading disabled, human approval required.
    """
    return run_upper_workflow(request)


@router.get("/upper-workflow/latest", response_model=UpperWorkflowResponse | dict)
def get_latest_upper_workflow_endpoint():
    """Get the most recent upper workflow run."""
    latest = get_latest_upper_workflow()
    if not latest:
        return {"message": "No upper workflow run available", "status": "not_found"}
    return latest


@router.get("/upper-workflow/history")
def get_upper_workflow_history(limit: int = 20):
    """List recent upper workflow runs."""
    return {
        "runs": list_upper_workflow_history(limit),
        "count": len(list_upper_workflow_history(limit)),
    }
