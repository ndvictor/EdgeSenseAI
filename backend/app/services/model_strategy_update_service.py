"""Model Strategy Update Service.

Turns research tasks and drift findings into model/strategy weight update recommendations.
This does not retrain real models yet - it prepares safe update proposals.

NO fake performance claims.
NO LLM calls.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.research_priority_service import (
    _LATEST_RESEARCH_PRIORITY,
)


class StrategyWeightUpdate(BaseModel):
    """A strategy weight update proposal."""

    model_config = ConfigDict(protected_namespaces=())

    strategy_key: str
    current_weight: float | None = None
    proposed_weight: float
    action: Literal["keep", "reduce", "increase", "pause", "collect_more_data"]
    reason: str
    evidence: list[str] = Field(default_factory=list)


class ModelWeightUpdate(BaseModel):
    """A model weight update proposal."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    current_weight: float | None = None
    proposed_weight: float
    action: Literal["keep", "reduce", "increase", "pause", "collect_more_data"]
    reason: str
    evidence: list[str] = Field(default_factory=list)


class RetrainingRequest(BaseModel):
    """A model retraining request."""

    model_config = ConfigDict(protected_namespaces=())

    model_name: str
    reason: str
    required_data_points: int
    current_data_points: int


class ModelStrategyUpdateRequest(BaseModel):
    """Request to generate model/strategy update proposals."""

    model_config = ConfigDict(protected_namespaces=())

    research_run_id: str | None = None
    drift_run_id: str | None = None
    strategy_key: str | None = None
    model_name: str | None = None
    dry_run: bool = True


class ModelStrategyUpdateResponse(BaseModel):
    """Response with model/strategy update proposals."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["proposed", "insufficient_data", "no_changes"]
    strategy_weight_updates: list[StrategyWeightUpdate]
    model_weight_updates: list[ModelWeightUpdate]
    paused_strategies: list[str] = Field(default_factory=list)
    retraining_requests: list[RetrainingRequest]
    evaluation_jobs: list[dict[str, Any]] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime


# In-memory storage
_LATEST_UPDATE: ModelStrategyUpdateResponse | None = None
_UPDATE_HISTORY: list[ModelStrategyUpdateResponse] = []


# Mock current weights (in real system these would come from meta-model)
_STRATEGY_WEIGHTS: dict[str, float] = {}
_MODEL_WEIGHTS: dict[str, float] = {}


def _get_current_strategy_weight(strategy_key: str) -> float | None:
    """Get current strategy weight."""
    return _STRATEGY_WEIGHTS.get(strategy_key)


def _get_current_model_weight(model_name: str) -> float | None:
    """Get current model weight."""
    return _MODEL_WEIGHTS.get(model_name)


def _propose_strategy_updates_from_research() -> list[StrategyWeightUpdate]:
    """Propose strategy updates from research tasks."""
    updates = []
    
    if _LATEST_RESEARCH_PRIORITY is None:
        return updates
    
    for task in _LATEST_RESEARCH_PRIORITY.tasks:
        if task.status != "open":
            continue
        
        strategy_key = task.linked_strategy_key
        if not strategy_key:
            continue
        
        current_weight = _get_current_strategy_weight(strategy_key)
        
        # Determine action from task type
        if task.task_type == "strategy_review":
            if "pause" in task.title.lower():
                action: Literal["keep", "reduce", "increase", "pause", "collect_more_data"] = "pause"
                proposed_weight = 0.0
            elif "reduce" in task.title.lower():
                action = "reduce"
                proposed_weight = (current_weight or 1.0) * 0.5  # Reduce by 50%
            else:
                action = "collect_more_data"
                proposed_weight = current_weight or 1.0
        elif task.task_type == "risk_filter_review":
            action = "collect_more_data"
            proposed_weight = current_weight or 1.0
        else:
            action = "keep"
            proposed_weight = current_weight or 1.0
        
        updates.append(StrategyWeightUpdate(
            strategy_key=strategy_key,
            current_weight=current_weight,
            proposed_weight=proposed_weight,
            action=action,
            reason=task.description,
            evidence=task.evidence,
        ))
    
    return updates


def _propose_model_updates_from_research() -> list[ModelWeightUpdate]:
    """Propose model updates from research tasks."""
    updates = []
    
    if _LATEST_RESEARCH_PRIORITY is None:
        return updates
    
    for task in _LATEST_RESEARCH_PRIORITY.tasks:
        if task.status != "open":
            continue
        
        model_name = task.linked_model
        if not model_name:
            continue
        
        current_weight = _get_current_model_weight(model_name)
        
        # Determine action from task type
        if task.task_type == "retraining_request":
            action: Literal["keep", "reduce", "increase", "pause", "collect_more_data"] = "collect_more_data"
            proposed_weight = current_weight or 1.0
        elif task.task_type == "model_evaluation":
            action = "reduce"
            proposed_weight = (current_weight or 1.0) * 0.7  # Reduce by 30%
        else:
            action = "keep"
            proposed_weight = current_weight or 1.0
        
        updates.append(ModelWeightUpdate(
            model_name=model_name,
            current_weight=current_weight,
            proposed_weight=proposed_weight,
            action=action,
            reason=task.description,
            evidence=task.evidence,
        ))
    
    return updates


def _generate_retraining_requests() -> list[RetrainingRequest]:
    """Generate retraining requests from research."""
    requests = []
    
    if _LATEST_RESEARCH_PRIORITY is None:
        return requests
    
    for task in _LATEST_RESEARCH_PRIORITY.tasks:
        if task.task_type != "retraining_request":
            continue
        
        model_name = task.linked_model
        if not model_name:
            continue
        
        requests.append(RetrainingRequest(
            model_name=model_name,
            reason=task.description,
            required_data_points=100,  # Minimum for reliable retraining
            current_data_points=0,  # Would come from actual data
        ))
    
    return requests


def propose_model_strategy_updates(request: ModelStrategyUpdateRequest) -> ModelStrategyUpdateResponse:
    """Propose model and strategy updates.
    
    Rules:
    - If insufficient data, action is collect_more_data
    - Do not actually change production weights (dry_run default true)
    - No fake performance claims
    - No LLM calls
    """
    run_id = f"update-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    
    # Check if we have research to work from
    if _LATEST_RESEARCH_PRIORITY is None:
        return ModelStrategyUpdateResponse(
            run_id=run_id,
            status="insufficient_data",
            strategy_weight_updates=[],
            model_weight_updates=[],
            paused_strategies=[],
            retraining_requests=[],
            evaluation_jobs=[],
            blockers=["No research priority data available"],
            warnings=["Run research-priority first"],
            created_at=created_at,
        )
    
    # Check if research found any issues
    if _LATEST_RESEARCH_PRIORITY.status == "insufficient_evidence":
        return ModelStrategyUpdateResponse(
            run_id=run_id,
            status="insufficient_data",
            strategy_weight_updates=[],
            model_weight_updates=[],
            paused_strategies=[],
            retraining_requests=[],
            evaluation_jobs=[],
            blockers=[],
            warnings=["Insufficient evidence - need more labeled outcomes"],
            created_at=created_at,
        )
    
    # Generate proposals
    strategy_updates = _propose_strategy_updates_from_research()
    model_updates = _propose_model_updates_from_research()
    retraining_requests = _generate_retraining_requests()
    
    # Determine paused strategies
    paused_strategies = [
        u.strategy_key for u in strategy_updates 
        if u.action == "pause"
    ]
    
    # Determine status
    if not strategy_updates and not model_updates and not retraining_requests:
        status: Literal["proposed", "insufficient_data", "no_changes"] = "no_changes"
    else:
        status = "proposed"
    
    response = ModelStrategyUpdateResponse(
        run_id=run_id,
        status=status,
        strategy_weight_updates=strategy_updates,
        model_weight_updates=model_updates,
        paused_strategies=paused_strategies,
        retraining_requests=retraining_requests,
        evaluation_jobs=[],
        blockers=[],
        warnings=[],
        created_at=created_at,
    )
    
    # Store
    global _LATEST_UPDATE, _UPDATE_HISTORY
    _LATEST_UPDATE = response
    _UPDATE_HISTORY.append(response)
    
    # Keep only last 100
    if len(_UPDATE_HISTORY) > 100:
        _UPDATE_HISTORY = _UPDATE_HISTORY[-100:]
    
    return response


def get_latest_update_proposal() -> ModelStrategyUpdateResponse | None:
    """Get the latest update proposal."""
    return _LATEST_UPDATE


def list_update_history(limit: int = 20) -> list[ModelStrategyUpdateResponse]:
    """List recent update proposals."""
    return _UPDATE_HISTORY[-limit:]
