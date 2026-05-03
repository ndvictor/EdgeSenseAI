from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.vector_memory_service import (
    MemoryRecord,
    create_journal_lesson_memory,
    create_memory_record,
    create_strategy_playbook_memory,
    create_workflow_summary_memory,
    get_memory,
    list_recent_memories,
    search_memory,
)

router = APIRouter()


class MemoryCreateRequest(BaseModel):
    memory_type: str
    title: str
    content: str
    summary: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    symbol: str | None = None
    asset_class: str | None = None
    strategy_key: str | None = None
    horizon: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance_score: float = 0.5


class MemorySearchRequest(BaseModel):
    query: str
    memory_type: str | None = None
    symbol: str | None = None
    strategy_key: str | None = None
    limit: int = 10


@router.get("/memory/recent", response_model=list[MemoryRecord])
def get_recent_memory(limit: int = 25):
    return list_recent_memories(limit)


@router.get("/memory/{memory_id}", response_model=MemoryRecord)
def get_memory_route(memory_id: str):
    memory = get_memory(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory


@router.post("/memory/search")
def post_memory_search(request: MemorySearchRequest):
    return search_memory(request.query, memory_type=request.memory_type, symbol=request.symbol, strategy_key=request.strategy_key, limit=request.limit)


@router.post("/memory", response_model=MemoryRecord)
def post_memory(request: MemoryCreateRequest):
    return create_memory_record(**request.model_dump())


@router.post("/memory/strategy-playbook", response_model=MemoryRecord)
def post_strategy_playbook_memory(request: MemoryCreateRequest):
    payload = request.model_dump()
    payload.pop("memory_type", None)
    return create_strategy_playbook_memory(**payload)


@router.post("/memory/workflow-summary", response_model=MemoryRecord)
def post_workflow_summary_memory(request: MemoryCreateRequest):
    payload = request.model_dump()
    payload.pop("memory_type", None)
    return create_workflow_summary_memory(**payload)


@router.post("/memory/journal-lesson", response_model=MemoryRecord)
def post_journal_lesson_memory(request: MemoryCreateRequest):
    payload = request.model_dump()
    payload.pop("memory_type", None)
    return create_journal_lesson_memory(**payload)
