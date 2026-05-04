"""Memory Update Service.

Stores summaries of journal outcomes, workflow runs, research tasks, model evaluations, 
and lessons into existing memory/vector system.

Does not fake memory_id if not stored.
NO LLM calls.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.journal_outcome_service import (
    _JOURNAL_CREATE_REQUESTS,
    _JOURNAL_ENTRIES,
    get_latest_journal_entry,
)
from app.services.persistence_service import get_database_table_status
from app.services.research_priority_service import get_latest_research_priority
from app.services.vector_memory_service import create_memory_record


class MemoryUpdateRequest(BaseModel):
    """Request to store memory."""

    model_config = ConfigDict(protected_namespaces=())

    source_type: Literal[
        "journal_outcome", "workflow_summary", "research_task", 
        "model_evaluation", "paper_trade_outcome", "recommendation_summary"
    ]
    source_id: str | None = None
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


class MemoryUpdateResponse(BaseModel):
    """Response from memory update."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["stored", "skipped", "unavailable"]
    memory_id: str | None = None
    source_type: str
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    created_at: datetime


# In-memory storage
_LATEST_MEMORY_UPDATE: MemoryUpdateResponse | None = None
_MEMORY_UPDATE_HISTORY: list[MemoryUpdateResponse] = []


def _save_memory_update(response: MemoryUpdateResponse) -> MemoryUpdateResponse:
    global _LATEST_MEMORY_UPDATE
    _LATEST_MEMORY_UPDATE = response
    _MEMORY_UPDATE_HISTORY.append(response)
    if len(_MEMORY_UPDATE_HISTORY) > 100:
        del _MEMORY_UPDATE_HISTORY[:-100]
    return response


def store_memory(request: MemoryUpdateRequest) -> MemoryUpdateResponse:
    """Store a memory record.
    
    Rules:
    - Use existing vector memory service if available
    - If DB/pgvector unavailable, return unavailable
    - Do not fake memory_id if not stored
    - No LLM calls
    """
    run_id = f"memup-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)
    
    if request.dry_run:
        return _save_memory_update(MemoryUpdateResponse(
            run_id=run_id,
            status="skipped",
            memory_id=None,
            source_type=request.source_type,
            warnings=["Dry run - memory not stored"],
            blockers=[],
            created_at=created_at,
        ))
    
    # Try to store via vector memory service
    try:
        memory_type_map = {
            "journal_outcome": "journal_lesson",
            "workflow_summary": "workflow_summary",
            "research_task": "research_task",
            "model_evaluation": "model_evaluation",
            "paper_trade_outcome": "paper_trade_outcome",
            "recommendation_summary": "recommendation_summary",
        }
        
        memory_record = create_memory_record(
            memory_type=memory_type_map.get(request.source_type, "general"),
            title=request.title,
            content=request.content,
            source_type=request.source_type,
            source_id=request.source_id,
            symbol=request.metadata.get("symbol"),
            strategy_key=request.metadata.get("strategy_key"),
            horizon=request.metadata.get("horizon"),
            metadata=request.metadata,
            importance_score=request.metadata.get("importance_score", 0.5),
        )
        
        # Check if actually persisted
        if memory_record.data_source == "in_memory_fallback":
            return _save_memory_update(MemoryUpdateResponse(
                run_id=run_id,
                status="unavailable",
                memory_id=memory_record.memory_id,
                source_type=request.source_type,
                warnings=["Memory stored in fallback only - DB/pgvector unavailable"],
                blockers=[],
                created_at=created_at,
            ))
        
        return _save_memory_update(MemoryUpdateResponse(
            run_id=run_id,
            status="stored",
            memory_id=memory_record.memory_id,
            source_type=request.source_type,
            warnings=[],
            blockers=[],
            created_at=created_at,
        ))
    
    except Exception as e:
        return _save_memory_update(MemoryUpdateResponse(
            run_id=run_id,
            status="unavailable",
            memory_id=None,
            source_type=request.source_type,
            warnings=[str(e)],
            blockers=["Memory storage failed"],
            created_at=created_at,
        ))


def store_latest_journal_to_memory() -> MemoryUpdateResponse:
    """Store the latest journal entry as memory."""
    latest = get_latest_journal_entry()
    if latest is None:
        return MemoryUpdateResponse(
            run_id=f"memup-{uuid4().hex[:12]}",
            status="skipped",
            memory_id=None,
            source_type="journal_outcome",
            warnings=["No journal entries to store"],
            blockers=[],
            created_at=datetime.now(timezone.utc),
        )
    
    # Get original request for more context
    request = _JOURNAL_CREATE_REQUESTS.get(latest.id)
    
    title = f"Journal: {latest.symbol} - {latest.outcome_label}"
    content = (
        f"Outcome: {latest.outcome_label}\n"
        f"Realized R: {latest.realized_r}\n"
        f"MFE: {latest.mfe_percent}%, MAE: {latest.mae_percent}%\n"
        f"Lessons: {', '.join(latest.lessons) if latest.lessons else 'None'}\n"
        f"Notes: {request.notes if request else 'N/A'}"
    )
    
    metadata = {
        "symbol": latest.symbol,
        "outcome_label": latest.outcome_label,
        "realized_r": latest.realized_r,
        "source_entry_id": latest.id,
        "strategy_key": request.strategy_key if request else None,
        "importance_score": 0.7 if latest.outcome_label in ("win", "loss") else 0.5,
    }
    
    store_request = MemoryUpdateRequest(
        source_type="journal_outcome",
        source_id=latest.id,
        title=title,
        content=content,
        metadata=metadata,
        dry_run=False,
    )
    
    return store_memory(store_request)


def store_latest_research_to_memory() -> MemoryUpdateResponse:
    """Store the latest research priority run as memory."""
    latest = get_latest_research_priority()
    if latest is None:
        return MemoryUpdateResponse(
            run_id=f"memup-{uuid4().hex[:12]}",
            status="skipped",
            memory_id=None,
            source_type="research_task",
            warnings=["No research priority to store"],
            blockers=[],
            created_at=datetime.now(timezone.utc),
        )
    
    title = f"Research Priority: {latest.run_id}"
    content = (
        f"Status: {latest.status}\n"
        f"Tasks: {len(latest.tasks)}\n"
        + "\n".join([
            f"- {t.priority_rank}. {t.title} ({t.task_type}): {t.description[:100]}..."
            for t in latest.tasks[:5]
        ])
    )
    
    metadata = {
        "research_run_id": latest.run_id,
        "task_count": len(latest.tasks),
        "importance_score": 0.6,
    }
    
    store_request = MemoryUpdateRequest(
        source_type="research_task",
        source_id=latest.run_id,
        title=title,
        content=content,
        metadata=metadata,
        dry_run=False,
    )
    
    return store_memory(store_request)


def get_latest_memory_update() -> MemoryUpdateResponse | None:
    """Get the latest memory update."""
    return _LATEST_MEMORY_UPDATE


def list_memory_update_history(limit: int = 20) -> list[MemoryUpdateResponse]:
    """List recent memory updates."""
    return _MEMORY_UPDATE_HISTORY[-limit:]


def get_persistence_mode() -> str:
    """Return the current persistence mode for memory updates."""
    status = get_database_table_status()
    return "postgres" if status.get("connected", False) else "memory"
