"""Research Priority API routes."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.services.research_priority_service import (
    ResearchPriorityRequest,
    ResearchPriorityResponse,
    ResearchTask,
    generate_research_priorities,
    get_latest_research_priority,
    get_open_tasks,
    list_research_history,
    update_task_status,
)

router = APIRouter()


class RunResearchRequest(BaseModel):
    """Request to run research priority generation."""

    model_config = ConfigDict(protected_namespaces=())

    lookback_days: int = 30
    include_drift: bool = True
    include_journal: bool = True
    include_no_trade: bool = True
    include_recommendation_rejects: bool = True
    max_tasks: int = 20


class UpdateTaskRequest(BaseModel):
    """Request to update task status."""

    model_config = ConfigDict(protected_namespaces=())

    status: str


@router.post("/research-priority/run", response_model=ResearchPriorityResponse)
def post_research_priority_run(request: RunResearchRequest):
    """Generate research priorities from journal outcomes and drift checks.
    
    Returns collect-more-data tasks when evidence is insufficient.
    No LLM calls - deterministic scoring.
    """
    internal_request = ResearchPriorityRequest(
        lookback_days=request.lookback_days,
        include_drift=request.include_drift,
        include_journal=request.include_journal,
        include_no_trade=request.include_no_trade,
        include_recommendation_rejects=request.include_recommendation_rejects,
        max_tasks=request.max_tasks,
    )
    return generate_research_priorities(internal_request)


@router.get("/research-priority/latest", response_model=ResearchPriorityResponse | dict)
def get_research_priority_latest():
    """Get the latest research priority run."""
    result = get_latest_research_priority()
    if result is None:
        return {"status": "not_found", "message": "No research priority run found"}
    return result


@router.get("/research-priority/tasks")
def get_research_priority_tasks(status: str | None = None):
    """List research tasks."""
    tasks = get_open_tasks() if status == "open" else []
    if not tasks and status is None:
        # Return all tasks from latest
        latest = get_latest_research_priority()
        if latest:
            tasks = latest.tasks
    return tasks


@router.post("/research-priority/tasks/{task_id}/update")
def post_research_task_update(task_id: str, request: UpdateTaskRequest):
    """Update research task status."""
    task = update_task_status(task_id, request.status)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"success": True, "task": task}
