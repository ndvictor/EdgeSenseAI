"""Historical Similarity Search Service.

Retrieves similar historical setups using existing memory/vector service when available,
with safe deterministic fallback when vector memory is unavailable.

NO fake matches.
NO LLM.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.vector_memory_service import search_memory


class HistoricalSimilarityMatch(BaseModel):
    """A single historical match from vector memory search."""

    model_config = ConfigDict(protected_namespaces=())

    memory_id: str
    title: str
    memory_type: str
    strategy_key: str | None = None
    regime: str | None = None
    similarity_score: float = Field(..., ge=0, le=1)
    outcome_label: str | None = None  # "win", "loss", "scratch", "unknown"
    realized_r: float | None = None
    lesson: str | None = None
    source: str
    created_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class HistoricalSimilarityRequest(BaseModel):
    """Request to search for similar historical setups."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    strategy_key: str | None = None
    regime: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)
    max_results: int = Field(default=5, ge=1, le=20)
    min_similarity: float = Field(default=0.60, ge=0, le=1)
    source_run_id: str | None = None


class HistoricalSimilarityResponse(BaseModel):
    """Response from historical similarity search."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "unavailable", "no_matches", "degraded"]
    symbol: str
    strategy_key: str | None = None
    regime: str | None = None
    matches: list[HistoricalSimilarityMatch] = Field(default_factory=list)
    similarity_score: float | None = None  # Aggregate similarity if computed
    outcome_summary: dict[str, Any] = Field(default_factory=dict)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: str


# In-memory storage for latest searches
_LATEST_SIMILARITY_SEARCH: HistoricalSimilarityResponse | None = None
_SIMILARITY_SEARCH_HISTORY: list[HistoricalSimilarityResponse] = []


# Memory types to search for historical analogs
HISTORICAL_MEMORY_TYPES = [
    "strategy_playbook",
    "workflow_summary",
    "journal_lesson",
    "paper_trade_outcome",
    "model_evaluation",
    "historical_analog",
]


def _compute_outcome_summary(matches: list[HistoricalSimilarityMatch]) -> dict[str, Any]:
    """Compute aggregate outcome statistics from matches."""
    if not matches:
        return {"note": "No historical matches available"}

    total = len(matches)
    wins = sum(1 for m in matches if m.outcome_label == "win")
    losses = sum(1 for m in matches if m.outcome_label == "loss")
    scratches = sum(1 for m in matches if m.outcome_label == "scratch")
    unknown = sum(1 for m in matches if m.outcome_label == "unknown" or m.outcome_label is None)

    avg_similarity = sum(m.similarity_score for m in matches) / total if total > 0 else 0

    # Calculate R-multiple stats from matches with realized_r
    r_values = [m.realized_r for m in matches if m.realized_r is not None]
    avg_r = sum(r_values) / len(r_values) if r_values else None
    max_r = max(r_values) if r_values else None
    min_r = min(r_values) if r_values else None

    return {
        "total_matches": total,
        "wins": wins,
        "losses": losses,
        "scratches": scratches,
        "unknown_outcomes": unknown,
        "win_rate": round(wins / total, 2) if total > 0 else None,
        "average_similarity": round(avg_similarity, 3),
        "average_r_multiple": round(avg_r, 2) if avg_r is not None else None,
        "max_r_multiple": round(max_r, 2) if max_r is not None else None,
        "min_r_multiple": round(min_r, 2) if min_r is not None else None,
    }


def _filter_and_rank_matches(
    memories: list[dict[str, Any]],
    min_similarity: float,
    max_results: int,
    strategy_key: str | None = None,
    regime: str | None = None,
) -> list[HistoricalSimilarityMatch]:
    """Filter memories by similarity threshold and rank by relevance."""
    matches: list[HistoricalSimilarityMatch] = []

    for mem in memories:
        similarity = mem.get("similarity_score", 0)
        if similarity < min_similarity:
            continue

        # Strategy alignment bonus
        mem_strategy = mem.get("strategy_key")
        strategy_match = strategy_key and mem_strategy == strategy_key

        # Regime alignment bonus
        mem_regime = mem.get("regime")
        regime_match = regime and mem_regime == regime

        # Create match object
        match = HistoricalSimilarityMatch(
            memory_id=mem.get("memory_id", "unknown"),
            title=mem.get("title", "Untitled"),
            memory_type=mem.get("memory_type", "unknown"),
            strategy_key=mem_strategy,
            regime=mem_regime,
            similarity_score=round(similarity, 3),
            outcome_label=mem.get("metadata", {}).get("outcome_label"),
            realized_r=mem.get("metadata", {}).get("realized_r"),
            lesson=mem.get("content", "")[:200] if mem.get("content") else None,
            source=mem.get("data_source", "unknown"),
            created_at=mem.get("created_at", datetime.now(timezone.utc).isoformat()),
            metadata=mem.get("metadata", {}),
        )
        matches.append(match)

    # Sort by similarity score descending
    matches.sort(key=lambda x: x.similarity_score, reverse=True)

    # Return top N
    return matches[:max_results]


def run_historical_similarity_search(
    request: HistoricalSimilarityRequest,
) -> HistoricalSimilarityResponse:
    """Run historical similarity search for a symbol.

    Uses vector_memory_service when available. Returns degraded status with
    warnings if DB unavailable - NEVER invents fake matches.
    """
    global _LATEST_SIMILARITY_SEARCH, _SIMILARITY_SEARCH_HISTORY

    run_id = f"hist-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc).isoformat()

    matches: list[HistoricalSimilarityMatch] = []
    blockers: list[str] = []
    warnings: list[str] = []
    status: Literal["completed", "unavailable", "no_matches", "degraded"] = "completed"

    try:
        # Build search query from symbol + features
        search_terms = [request.symbol]
        if request.features:
            # Add key feature terms if provided
            for key in ["pattern", "setup", "context"]:
                if key in request.features:
                    search_terms.append(str(request.features[key]))

        query_text = " ".join(search_terms)

        # Try to query vector memory using available search_memory function
        search_result = search_memory(
            query=query_text,
            memory_type=None,  # Search all types
            symbol=request.symbol,
            strategy_key=request.strategy_key,
            limit=request.max_results * 2,  # Get more for filtering
        )

        memory_results = search_result.get("results", [])
        data_source = search_result.get("data_source", "unknown")

        if not memory_results:
            if "fallback" in data_source or "in_memory" in data_source:
                status = "degraded"
                warnings.append("Vector memory using fallback - limited search capability")
            else:
                status = "no_matches"
                warnings.append("No similar historical setups found in memory")
        else:
            # Convert MemoryRecord to dict format expected by _filter_and_rank_matches
            dict_results = []
            for mem in memory_results:
                dict_results.append({
                    "memory_id": mem.memory_id,
                    "title": mem.title,
                    "memory_type": mem.memory_type,
                    "strategy_key": mem.strategy_key,
                    "regime": mem.metadata.get("regime") if mem.metadata else None,
                    "similarity_score": mem.similarity_score or 0,
                    "data_source": data_source,
                    "created_at": mem.created_at.isoformat() if mem.created_at else datetime.now(timezone.utc).isoformat(),
                    "metadata": mem.metadata or {},
                    "content": mem.content,
                })

            # Filter and rank matches
            matches = _filter_and_rank_matches(
                memories=dict_results,
                min_similarity=request.min_similarity,
                max_results=request.max_results,
                strategy_key=request.strategy_key,
                regime=request.regime,
            )

            if not matches:
                status = "no_matches"
                warnings.append(f"No matches above similarity threshold {request.min_similarity}")
            elif len(matches) < request.max_results:
                warnings.append(f"Only {len(matches)} matches found (requested {request.max_results})")

    except Exception as e:
        status = "degraded"
        warnings.append(f"Vector memory search failed: {str(e)}")

    # Compute outcome summary from matches
    outcome_summary = _compute_outcome_summary(matches)

    # Calculate aggregate similarity score from top matches
    avg_similarity = None
    if matches:
        avg_similarity = round(sum(m.similarity_score for m in matches) / len(matches), 3)

    response = HistoricalSimilarityResponse(
        run_id=run_id,
        status=status,
        symbol=request.symbol,
        strategy_key=request.strategy_key,
        regime=request.regime,
        matches=matches,
        similarity_score=avg_similarity,
        outcome_summary=outcome_summary,
        blockers=blockers,
        warnings=warnings,
        checked_at=checked_at,
    )

    # Store in memory
    _LATEST_SIMILARITY_SEARCH = response
    _SIMILARITY_SEARCH_HISTORY.append(response)

    # Keep only last 100 searches
    if len(_SIMILARITY_SEARCH_HISTORY) > 100:
        _SIMILARITY_SEARCH_HISTORY = _SIMILARITY_SEARCH_HISTORY[-100:]

    return response


def get_latest_historical_similarity() -> HistoricalSimilarityResponse | None:
    """Get the most recent historical similarity search."""
    return _LATEST_SIMILARITY_SEARCH


def list_historical_similarity_searches(limit: int = 20) -> list[HistoricalSimilarityResponse]:
    """List recent historical similarity searches."""
    return _SIMILARITY_SEARCH_HISTORY[-limit:]


def get_similarity_for_symbol(symbol: str) -> HistoricalSimilarityResponse | None:
    """Get the most recent similarity search for a specific symbol."""
    for search in reversed(_SIMILARITY_SEARCH_HISTORY):
        if search.symbol.upper() == symbol.upper():
            return search
    return None
