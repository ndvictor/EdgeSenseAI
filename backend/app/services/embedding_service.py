import hashlib
import math
from pydantic import BaseModel, Field

from app.core.effective_runtime import effective_bool
from app.core.settings import settings


class EmbeddingResult(BaseModel):
    embedding: list[float]
    embedding_model: str
    provider: str
    data_source: str = "placeholder"
    warnings: list[str] = Field(default_factory=list)


def _placeholder_embedding(text: str, dimensions: int = 64) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    while len(values) < dimensions:
        digest = hashlib.sha256(digest).digest()
        values.extend(((byte / 255.0) * 2) - 1 for byte in digest)
    vector = values[:dimensions]
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / norm, 6) for value in vector]


def embed_text(text: str) -> EmbeddingResult:
    warnings: list[str] = []
    paid_embeddings = effective_bool("EMBEDDINGS_ENABLE_PAID_CALLS")
    if settings.embeddings_provider != "placeholder" and not paid_embeddings:
        warnings.append("Real embedding provider requested, but EMBEDDINGS_ENABLE_PAID_CALLS=false; using deterministic placeholder embedding.")
    if settings.embeddings_provider != "placeholder" and paid_embeddings:
        warnings.append("Paid embeddings are not wired in this pass; using deterministic placeholder embedding.")
    return EmbeddingResult(
        embedding=_placeholder_embedding(text or ""),
        embedding_model=settings.embeddings_model or "placeholder-hash-embedding",
        provider="placeholder",
        data_source="placeholder",
        warnings=warnings,
    )


def get_embedding_status() -> dict:
    return {
        "provider": settings.embeddings_provider,
        "embedding_model": settings.embeddings_model,
        "paid_calls_enabled": effective_bool("EMBEDDINGS_ENABLE_PAID_CALLS"),
        "status": "placeholder_deterministic",
        "data_source": "placeholder",
    }
