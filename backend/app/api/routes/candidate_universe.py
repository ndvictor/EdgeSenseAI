"""Candidate Universe API Routes.

Endpoints for managing the candidate universe:
- GET /api/candidate-universe - list candidates
- POST /api/candidate-universe/add - add single candidate
- POST /api/candidate-universe/bulk-add - add multiple candidates
- POST /api/candidate-universe/remove - remove a candidate
- POST /api/candidate-universe/clear - clear all candidates
"""

from typing import Any

from fastapi import APIRouter

from app.services.candidate_universe_service import (
    AddCandidateRequest,
    BulkAddRequest,
    CandidateUniverseEntry,
    RemoveCandidateRequest,
    add_candidate,
    bulk_add_candidates,
    clear_candidates,
    get_candidate_universe_summary,
    list_active_candidates,
    list_candidates,
    remove_candidate,
)

router = APIRouter()


@router.get("/candidate-universe", response_model=dict[str, Any])
def get_candidate_universe(status: str | None = None):
    """Get candidate universe list and summary.

    Query params:
        status: Filter by status (active, paused, removed)
    """
    candidates = list_candidates(status)
    summary = get_candidate_universe_summary()
    return {
        "candidates": [c.to_dict() for c in candidates],
        "summary": summary,
    }


@router.post("/candidate-universe/add", response_model=dict[str, Any])
def post_add_candidate(request: AddCandidateRequest):
    """Add a single symbol to the candidate universe."""
    entry = add_candidate(
        symbol=request.symbol,
        asset_class=request.asset_class,
        horizon=request.horizon,
        source_type=request.source_type,
        source_detail=request.source_detail,
        priority_score=request.priority_score,
        notes=request.notes,
    )
    return {
        "success": True,
        "message": f"Added {entry.symbol} to candidate universe",
        "candidate": entry.to_dict(),
    }


@router.post("/candidate-universe/bulk-add", response_model=dict[str, Any])
def post_bulk_add_candidates(request: BulkAddRequest):
    """Add multiple symbols to the candidate universe."""
    entries = bulk_add_candidates(
        symbols=request.symbols,
        asset_class=request.asset_class,
        horizon=request.horizon,
        source_type=request.source_type,
        source_detail=request.source_detail,
        priority_score=request.priority_score,
        notes=request.notes,
    )
    return {
        "success": True,
        "message": f"Added {len(entries)} candidates to universe",
        "candidates": [e.to_dict() for e in entries],
    }


@router.post("/candidate-universe/remove", response_model=dict[str, Any])
def post_remove_candidate(request: RemoveCandidateRequest):
    """Remove a symbol from the candidate universe (soft delete)."""
    entry = remove_candidate(request.symbol)
    if entry:
        return {
            "success": True,
            "message": f"Removed {entry.symbol} from candidate universe",
            "candidate": entry.to_dict(),
        }
    return {
        "success": False,
        "message": f"Symbol {request.symbol} not found in candidate universe",
    }


@router.post("/candidate-universe/clear", response_model=dict[str, Any])
def post_clear_candidates():
    """Clear all candidates from the universe (hard delete)."""
    count = clear_candidates()
    return {
        "success": True,
        "message": f"Cleared {count} candidates from universe",
    }


@router.get("/candidate-universe/summary", response_model=dict[str, Any])
def get_candidate_universe_summary_route():
    """Get summary of candidate universe (counts by status)."""
    return get_candidate_universe_summary()


@router.get("/candidate-universe/active", response_model=list[str])
def get_active_candidate_symbols():
    """Get list of active candidate symbols only."""
    active = list_active_candidates()
    return [c.symbol for c in active]
