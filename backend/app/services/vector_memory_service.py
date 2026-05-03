import math
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.settings import settings
from app.db.init_db import init_db
from app.db.models import VectorMemoryRecord
from app.db.session import check_database_health, open_session
from app.services.embedding_service import embed_text, get_embedding_status


class MemoryRecord(BaseModel):
    memory_id: str = Field(default_factory=lambda: f"mem-{uuid4().hex[:12]}")
    memory_type: str
    source_type: str | None = None
    source_id: str | None = None
    symbol: str | None = None
    asset_class: str | None = None
    strategy_key: str | None = None
    horizon: str | None = None
    title: str
    content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)
    embedding_model: str = "placeholder-hash-embedding"
    importance_score: float = 0.5
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_source: str = "in_memory_fallback"
    similarity_score: float | None = None


_MEMORIES: list[MemoryRecord] = []


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    size = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(size))
    norm_a = math.sqrt(sum(value * value for value in a[:size])) or 1.0
    norm_b = math.sqrt(sum(value * value for value in b[:size])) or 1.0
    return dot / (norm_a * norm_b)


def _persist_memory(memory: MemoryRecord) -> str:
    if not settings.vector_memory_enabled:
        return "in_memory_fallback"
    init_db()
    session = open_session()
    if session is None:
        return "in_memory_fallback"
    try:
        session.add(
            VectorMemoryRecord(
                memory_id=memory.memory_id,
                memory_type=memory.memory_type,
                source_type=memory.source_type,
                source_id=memory.source_id,
                symbol=memory.symbol,
                asset_class=memory.asset_class,
                strategy_key=memory.strategy_key,
                horizon=memory.horizon,
                title=memory.title,
                content=memory.content,
                summary=memory.summary,
                tags=memory.tags,
                metadata_json=memory.metadata,
                embedding=memory.embedding,
                embedding_model=memory.embedding_model,
                importance_score=memory.importance_score,
            )
        )
        session.commit()
        health = check_database_health()
        return "postgres_pgvector" if health.get("pgvector_status") == "enabled" else "postgres_keyword_fallback"
    except Exception:
        session.rollback()
        return "in_memory_fallback"
    finally:
        session.close()


def create_memory_record(
    *,
    memory_type: str,
    title: str,
    content: str,
    summary: str | None = None,
    source_type: str | None = None,
    source_id: str | None = None,
    symbol: str | None = None,
    asset_class: str | None = None,
    strategy_key: str | None = None,
    horizon: str | None = None,
    tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
    importance_score: float = 0.5,
) -> MemoryRecord:
    embedding = embed_text(f"{title}\n{summary or ''}\n{content}")
    memory = MemoryRecord(
        memory_type=memory_type,
        source_type=source_type,
        source_id=source_id,
        symbol=symbol.upper() if symbol else None,
        asset_class=asset_class,
        strategy_key=strategy_key,
        horizon=horizon,
        title=title,
        content=content,
        summary=summary,
        tags=tags or [],
        metadata={**(metadata or {}), "embedding_warnings": embedding.warnings},
        embedding=embedding.embedding,
        embedding_model=embedding.embedding_model,
        importance_score=importance_score,
    )
    memory.data_source = _persist_memory(memory)
    _MEMORIES.insert(0, memory)
    del _MEMORIES[500:]
    return memory


def list_recent_memories(limit: int = 25) -> list[MemoryRecord]:
    return _MEMORIES[: max(1, min(limit, 100))]


def get_memory(memory_id: str) -> MemoryRecord | None:
    return next((memory for memory in _MEMORIES if memory.memory_id == memory_id), None)


def search_memory(query: str, memory_type: str | None = None, symbol: str | None = None, strategy_key: str | None = None, limit: int = 10) -> dict[str, Any]:
    query_embedding = embed_text(query).embedding
    rows = _MEMORIES
    if memory_type:
        rows = [row for row in rows if row.memory_type == memory_type]
    if symbol:
        rows = [row for row in rows if row.symbol == symbol.upper()]
    if strategy_key:
        rows = [row for row in rows if row.strategy_key == strategy_key]
    keywords = {word.lower() for word in query.split() if len(word) > 2}
    scored = []
    for row in rows:
        semantic = _cosine(query_embedding, row.embedding)
        text = f"{row.title} {row.summary or ''} {row.content}".lower()
        keyword_score = sum(1 for word in keywords if word in text) / max(1, len(keywords))
        item = row.model_copy()
        item.similarity_score = round(max(semantic, keyword_score), 4)
        scored.append(item)
    scored.sort(key=lambda item: item.similarity_score or 0, reverse=True)
    health = check_database_health()
    data_source = "postgres_pgvector" if health.get("pgvector_status") == "enabled" and health.get("connected") else "postgres_keyword_fallback" if health.get("connected") else "in_memory_fallback"
    return {"data_source": data_source, "embedding_model": settings.embeddings_model, "results": scored[: max(1, min(limit, 50))]}


def create_strategy_playbook_memory(**kwargs: Any) -> MemoryRecord:
    return create_memory_record(memory_type="strategy_playbook", **kwargs)


def create_workflow_summary_memory(**kwargs: Any) -> MemoryRecord:
    return create_memory_record(memory_type="workflow_summary", **kwargs)


def create_journal_lesson_memory(**kwargs: Any) -> MemoryRecord:
    return create_memory_record(memory_type="journal_lesson", **kwargs)


def create_recommendation_memory(**kwargs: Any) -> MemoryRecord:
    return create_memory_record(memory_type="recommendation_summary", **kwargs)


def get_vector_memory_status() -> dict[str, Any]:
    health = check_database_health()
    return {
        "vector_memory_status": "configured" if settings.vector_memory_enabled else "disabled",
        "pgvector_status": health.get("pgvector_status", "unknown"),
        "recent_memory_count": len(_MEMORIES),
        "embedding": get_embedding_status(),
        "data_source": "postgres_pgvector" if health.get("connected") and health.get("pgvector_status") == "enabled" else "in_memory_fallback",
    }
