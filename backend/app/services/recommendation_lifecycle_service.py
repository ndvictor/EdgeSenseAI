"""Recommendation Lifecycle Service - persistent storage for recommendation records.

This service stores recommendation lifecycle records created from decision workflow outputs.
Currently in-memory; designed to be replaced by Postgres persistence later.
"""

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

RecommendationStatus = Literal["pending_review", "approved", "rejected", "paper_trade_created", "expired"]


class RecommendationLifecycleRecord(BaseModel):
    """A recommendation record in the lifecycle with full metadata."""

    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(default_factory=lambda: f"rec-{uuid4().hex[:12]}")
    symbol: str
    asset_class: str = "stock"
    horizon: str = "swing"
    source: str = "decision_workflow"
    feature_row_id: str | None = None
    score: float
    confidence: float
    action_label: str
    status: RecommendationStatus = "pending_review"
    reason: str = ""
    risk_factors: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    workflow_run_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "horizon": self.horizon,
            "source": self.source,
            "feature_row_id": self.feature_row_id,
            "score": self.score,
            "confidence": self.confidence,
            "action_label": self.action_label,
            "status": self.status,
            "reason": self.reason,
            "risk_factors": self.risk_factors,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "workflow_run_id": self.workflow_run_id,
        }


class CreateRecommendationRequest(BaseModel):
    symbol: str
    asset_class: str = "stock"
    horizon: str = "swing"
    source: str = "decision_workflow"
    feature_row_id: str | None = None
    score: float
    confidence: float
    action_label: str
    reason: str = ""
    risk_factors: list[str] = Field(default_factory=list)
    workflow_run_id: str | None = None


# In-memory storage - replace with DB later
_RECOMMENDATION_LIFECYCLE: dict[str, RecommendationLifecycleRecord] = {}  # key: id
_RECOMMENDATIONS_BY_SYMBOL: dict[str, list[str]] = {}  # key: symbol, value: list of rec ids


def create_recommendation(request: CreateRecommendationRequest) -> RecommendationLifecycleRecord:
    """Create a new recommendation lifecycle record."""
    now = datetime.utcnow()
    record = RecommendationLifecycleRecord(
        symbol=request.symbol.upper(),
        asset_class=request.asset_class,
        horizon=request.horizon,
        source=request.source,
        feature_row_id=request.feature_row_id,
        score=request.score,
        confidence=request.confidence,
        action_label=request.action_label,
        reason=request.reason,
        risk_factors=request.risk_factors,
        created_at=now,
        updated_at=now,
        workflow_run_id=request.workflow_run_id,
    )
    _RECOMMENDATION_LIFECYCLE[record.id] = record

    # Index by symbol
    symbol_upper = request.symbol.upper()
    if symbol_upper not in _RECOMMENDATIONS_BY_SYMBOL:
        _RECOMMENDATIONS_BY_SYMBOL[symbol_upper] = []
    _RECOMMENDATIONS_BY_SYMBOL[symbol_upper].append(record.id)

    return record


def get_recommendation(id: str) -> RecommendationLifecycleRecord | None:
    """Get a specific recommendation by ID."""
    return _RECOMMENDATION_LIFECYCLE.get(id)


def list_recommendations(
    status: RecommendationStatus | None = None,
    symbol: str | None = None,
    limit: int = 100,
) -> list[RecommendationLifecycleRecord]:
    """List recommendation records with optional filtering."""
    records = list(_RECOMMENDATION_LIFECYCLE.values())

    if status:
        records = [r for r in records if r.status == status]

    if symbol:
        symbol_upper = symbol.upper()
        records = [r for r in records if r.symbol.upper() == symbol_upper]

    # Sort by created_at descending (most recent first)
    records = sorted(records, key=lambda r: r.created_at, reverse=True)

    return records[:limit]


def update_recommendation_status(id: str, status: RecommendationStatus) -> RecommendationLifecycleRecord | None:
    """Update the status of a recommendation."""
    record = _RECOMMENDATION_LIFECYCLE.get(id)
    if record is None:
        return None

    record.status = status
    record.updated_at = datetime.utcnow()
    return record


def approve_recommendation(id: str) -> RecommendationLifecycleRecord | None:
    """Approve a recommendation for paper trading."""
    return update_recommendation_status(id, "approved")


def reject_recommendation(id: str) -> RecommendationLifecycleRecord | None:
    """Reject a recommendation."""
    return update_recommendation_status(id, "rejected")


def expire_recommendation(id: str) -> RecommendationLifecycleRecord | None:
    """Mark a recommendation as expired."""
    return update_recommendation_status(id, "expired")


def get_recommendations_for_symbol(symbol: str) -> list[RecommendationLifecycleRecord]:
    """Get all recommendation records for a specific symbol."""
    symbol_upper = symbol.upper()
    rec_ids = _RECOMMENDATIONS_BY_SYMBOL.get(symbol_upper, [])
    return [_RECOMMENDATION_LIFECYCLE[id] for id in rec_ids if id in _RECOMMENDATION_LIFECYCLE]


def get_latest_recommendation_for_symbol(symbol: str) -> RecommendationLifecycleRecord | None:
    """Get the most recent recommendation for a symbol."""
    records = get_recommendations_for_symbol(symbol)
    if not records:
        return None
    return max(records, key=lambda r: r.created_at)


def get_recommendation_summary() -> dict[str, Any]:
    """Get summary statistics for recommendations."""
    all_records = list(_RECOMMENDATION_LIFECYCLE.values())

    by_status: dict[str, int] = {}
    for record in all_records:
        by_status[record.status] = by_status.get(record.status, 0) + 1

    return {
        "total_recommendations": len(all_records),
        "by_status": by_status,
        "pending_review": by_status.get("pending_review", 0),
        "approved": by_status.get("approved", 0),
        "rejected": by_status.get("rejected", 0),
        "expired": by_status.get("expired", 0),
    }


def clear_all_recommendations() -> int:
    """Clear all recommendation records (for testing). Returns count cleared."""
    count = len(_RECOMMENDATION_LIFECYCLE)
    _RECOMMENDATION_LIFECYCLE.clear()
    _RECOMMENDATIONS_BY_SYMBOL.clear()
    return count
