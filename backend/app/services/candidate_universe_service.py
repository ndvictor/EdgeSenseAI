"""Candidate Universe Service - persistent candidate storage for decision workflows.

This service stores symbols that should be ranked by Command Center.
Candidates can come from: manual entry, watchlist, scanner, stock search, or strategy workflow.
Currently in-memory; designed to be replaced by Postgres persistence later.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class CandidateSourceType:
    MANUAL = "manual"
    WATCHLIST = "watchlist"
    SCANNER = "scanner"
    STOCK_SEARCH = "stock_search"
    STRATEGY_WORKFLOW = "strategy_workflow"


class CandidateStatus:
    ACTIVE = "active"
    PAUSED = "paused"
    REMOVED = "removed"


class CandidateUniverseEntry(BaseModel):
    """A candidate symbol in the universe with metadata about its origin and status."""

    model_config = ConfigDict(protected_namespaces=())

    id: str = Field(default_factory=lambda: f"cand-{uuid4().hex[:12]}")
    symbol: str
    asset_class: str = "stock"
    horizon: str = "swing"
    source_type: str  # manual | watchlist | scanner | stock_search | strategy_workflow
    source_detail: str = ""
    priority_score: float = 50.0
    status: str = "active"  # active | paused | removed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_ranked_at: datetime | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "asset_class": self.asset_class,
            "horizon": self.horizon,
            "source_type": self.source_type,
            "source_detail": self.source_detail,
            "priority_score": self.priority_score,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_ranked_at": self.last_ranked_at.isoformat() if self.last_ranked_at else None,
            "notes": self.notes,
        }


class AddCandidateRequest(BaseModel):
    symbol: str
    asset_class: str = "stock"
    horizon: str = "swing"
    source_type: str = "manual"
    source_detail: str = ""
    priority_score: float = 50.0
    notes: str = ""


class BulkAddRequest(BaseModel):
    symbols: list[str]
    asset_class: str = "stock"
    horizon: str = "swing"
    source_type: str = "manual"
    source_detail: str = ""
    priority_score: float = 50.0
    notes: str = ""


class RemoveCandidateRequest(BaseModel):
    symbol: str


# In-memory storage - replace with DB later
_CANDIDATE_UNIVERSE: dict[str, CandidateUniverseEntry] = {}  # key: symbol (uppercase)


def list_candidates(status: str | None = None) -> list[CandidateUniverseEntry]:
    """List all candidates, optionally filtered by status."""
    candidates = list(_CANDIDATE_UNIVERSE.values())
    if status:
        candidates = [c for c in candidates if c.status == status]
    return sorted(candidates, key=lambda c: (-c.priority_score, c.created_at), reverse=False)


def list_active_candidates() -> list[CandidateUniverseEntry]:
    """List only active candidates, sorted by priority score descending."""
    candidates = [c for c in _CANDIDATE_UNIVERSE.values() if c.status == CandidateStatus.ACTIVE]
    return sorted(candidates, key=lambda c: (-c.priority_score, c.created_at), reverse=False)


def get_candidate(symbol: str) -> CandidateUniverseEntry | None:
    """Get a specific candidate by symbol."""
    return _CANDIDATE_UNIVERSE.get(symbol.upper())


def add_candidate(
    symbol: str,
    asset_class: str = "stock",
    horizon: str = "swing",
    source_type: str = "manual",
    source_detail: str = "",
    priority_score: float = 50.0,
    notes: str = "",
) -> CandidateUniverseEntry:
    """Add a new candidate to the universe, or update if exists."""
    symbol_upper = symbol.upper().strip()
    now = datetime.utcnow()

    if symbol_upper in _CANDIDATE_UNIVERSE:
        # Update existing
        existing = _CANDIDATE_UNIVERSE[symbol_upper]
        existing.asset_class = asset_class
        existing.horizon = horizon
        existing.source_type = source_type
        existing.source_detail = source_detail
        existing.priority_score = priority_score
        existing.status = CandidateStatus.ACTIVE  # Reactivate if was removed
        existing.updated_at = now
        if notes:
            existing.notes = notes
        return existing

    # Create new
    entry = CandidateUniverseEntry(
        symbol=symbol_upper,
        asset_class=asset_class,
        horizon=horizon,
        source_type=source_type,
        source_detail=source_detail,
        priority_score=priority_score,
        status=CandidateStatus.ACTIVE,
        created_at=now,
        updated_at=now,
        notes=notes,
    )
    _CANDIDATE_UNIVERSE[symbol_upper] = entry
    return entry


def bulk_add_candidates(
    symbols: list[str],
    asset_class: str = "stock",
    horizon: str = "swing",
    source_type: str = "manual",
    source_detail: str = "",
    priority_score: float = 50.0,
    notes: str = "",
) -> list[CandidateUniverseEntry]:
    """Add multiple candidates at once."""
    added = []
    for symbol in symbols:
        if symbol and symbol.strip():
            entry = add_candidate(
                symbol=symbol.strip(),
                asset_class=asset_class,
                horizon=horizon,
                source_type=source_type,
                source_detail=source_detail,
                priority_score=priority_score,
                notes=notes,
            )
            added.append(entry)
    return added


def remove_candidate(symbol: str) -> CandidateUniverseEntry | None:
    """Soft-remove a candidate (mark as removed, don't delete)."""
    symbol_upper = symbol.upper().strip()
    entry = _CANDIDATE_UNIVERSE.get(symbol_upper)
    if entry:
        entry.status = CandidateStatus.REMOVED
        entry.updated_at = datetime.utcnow()
    return entry


def clear_candidates() -> int:
    """Clear all candidates (hard delete). Returns count cleared."""
    count = len(_CANDIDATE_UNIVERSE)
    _CANDIDATE_UNIVERSE.clear()
    return count


def update_last_ranked(symbol: str) -> None:
    """Update the last_ranked_at timestamp for a candidate."""
    symbol_upper = symbol.upper().strip()
    entry = _CANDIDATE_UNIVERSE.get(symbol_upper)
    if entry:
        entry.last_ranked_at = datetime.utcnow()
        entry.updated_at = datetime.utcnow()


def get_candidate_symbols() -> list[str]:
    """Get list of active candidate symbols only."""
    return [c.symbol for c in _CANDIDATE_UNIVERSE.values() if c.status == CandidateStatus.ACTIVE]


def get_candidate_universe_summary() -> dict[str, Any]:
    """Get summary statistics for the candidate universe."""
    all_candidates = list(_CANDIDATE_UNIVERSE.values())
    active = [c for c in all_candidates if c.status == CandidateStatus.ACTIVE]
    paused = [c for c in all_candidates if c.status == CandidateStatus.PAUSED]
    removed = [c for c in all_candidates if c.status == CandidateStatus.REMOVED]

    return {
        "total_candidates": len(all_candidates),
        "active_count": len(active),
        "paused_count": len(paused),
        "removed_count": len(removed),
        "active_symbols": [c.symbol for c in active],
    }
