"""Memory Update API routes."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from typing import Any

from app.services.memory_update_service import (
    MemoryUpdateRequest,
    MemoryUpdateResponse,
    get_latest_memory_update,
    list_memory_update_history,
    store_latest_journal_to_memory,
    store_latest_research_to_memory,
    store_memory,
)

router = APIRouter()


class StoreMemoryRequest(BaseModel):
    """Request to store memory."""

    model_config = ConfigDict(protected_namespaces=())

    source_type: str
    source_id: str | None = None
    title: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = False


@router.post("/memory-update/store", response_model=MemoryUpdateResponse)
def post_memory_update_store(request: StoreMemoryRequest):
    """Store a memory record.
    
    Uses existing memory/vector service if available.
    Returns unavailable if DB/pgvector not accessible.
    Does not fake memory_id.
    """
    internal_request = MemoryUpdateRequest(
        source_type=request.source_type,  # type: ignore
        source_id=request.source_id,
        title=request.title,
        content=request.content,
        metadata=request.metadata,
        dry_run=request.dry_run,
    )
    return store_memory(internal_request)


@router.post("/memory-update/from-journal-latest")
def post_memory_update_from_journal_latest():
    """Store the latest journal entry to memory."""
    return store_latest_journal_to_memory()


@router.post("/memory-update/from-research-latest")
def post_memory_update_from_research_latest():
    """Store the latest research priority run to memory."""
    return store_latest_research_to_memory()


@router.get("/memory-update/latest", response_model=MemoryUpdateResponse | dict)
def get_memory_update_latest():
    """Get the latest memory update."""
    result = get_latest_memory_update()
    if result is None:
        return {"status": "not_found", "message": "No memory update found"}
    return result
