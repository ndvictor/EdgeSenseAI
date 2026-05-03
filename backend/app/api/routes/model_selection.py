"""Model Selection API Routes."""

from fastapi import APIRouter

from app.services.model_selection_service import (
    ModelSelectionRequest,
    ModelSelectionResponse,
    get_latest_model_selection,
    get_model_registry,
    list_model_selection_history,
    run_model_selection,
)

router = APIRouter()


@router.post("/model-selection/run", response_model=ModelSelectionResponse)
def post_model_selection_run(request: ModelSelectionRequest):
    """Run model selection for a strategy.

    Selects scanner models, scoring models, validation models, and meta-model weights.
    Based on strategy, market phase, regime, data availability, cost budget.
    NO paid LLM calls - deterministic selection only.
    """
    return run_model_selection(request)


@router.get("/model-selection/latest", response_model=ModelSelectionResponse | dict)
def get_latest_model_selection_endpoint():
    """Get the most recent model selection."""
    latest = get_latest_model_selection()
    if not latest:
        return {"message": "No model selection available", "status": "not_found"}
    return latest


@router.get("/model-selection/registry")
def get_model_selection_registry():
    """Get the model registry for reference."""
    return get_model_registry()
