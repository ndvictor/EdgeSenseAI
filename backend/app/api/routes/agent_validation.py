"""Agent Validation API routes."""

from fastapi import APIRouter

from app.services.agent_validation_service import (
    AgentValidationRequest,
    AgentValidationResponse,
    get_latest_agent_validation,
    run_agent_validation,
)

router = APIRouter()


@router.post("/agent-validation/run", response_model=AgentValidationResponse)
def post_agent_validation_run(request: AgentValidationRequest):
    """Run deterministic agent validation on an ensemble signal.

    No paid LLM calls. Specialist agents vote deterministically.
    """
    return run_agent_validation(request)


@router.get("/agent-validation/latest", response_model=AgentValidationResponse | dict)
def get_agent_validation_latest():
    """Get the latest agent validation result."""
    result = get_latest_agent_validation()
    if result is None:
        return {"status": "not_found", "message": "No agent validation found"}
    return result
