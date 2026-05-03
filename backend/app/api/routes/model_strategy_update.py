"""Model Strategy Update API routes."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.services.model_strategy_update_service import (
    ModelStrategyUpdateRequest,
    ModelStrategyUpdateResponse,
    get_latest_update_proposal,
    list_update_history,
    propose_model_strategy_updates,
)

router = APIRouter()


class ProposeUpdateRequest(BaseModel):
    """Request to propose model/strategy updates."""

    model_config = ConfigDict(protected_namespaces=())

    research_run_id: str | None = None
    drift_run_id: str | None = None
    strategy_key: str | None = None
    model_name: str | None = None
    dry_run: bool = True


@router.post("/model-strategy-update/propose", response_model=ModelStrategyUpdateResponse)
def post_model_strategy_update_propose(request: ProposeUpdateRequest):
    """Propose model and strategy weight updates based on research priorities.
    
    This does not actually change production weights (dry_run default true).
    Returns collect_more_data proposals when evidence is insufficient.
    No LLM calls.
    """
    internal_request = ModelStrategyUpdateRequest(
        research_run_id=request.research_run_id,
        drift_run_id=request.drift_run_id,
        strategy_key=request.strategy_key,
        model_name=request.model_name,
        dry_run=request.dry_run,
    )
    return propose_model_strategy_updates(internal_request)


@router.get("/model-strategy-update/latest", response_model=ModelStrategyUpdateResponse | dict)
def get_model_strategy_update_latest():
    """Get the latest model/strategy update proposal."""
    result = get_latest_update_proposal()
    if result is None:
        return {"status": "not_found", "message": "No update proposal found"}
    return result


@router.get("/model-strategy-update/history")
def get_model_strategy_update_history(limit: int = 20):
    """List recent model/strategy update proposals."""
    return list_update_history(limit)
