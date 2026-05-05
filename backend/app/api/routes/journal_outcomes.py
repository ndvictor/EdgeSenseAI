"""Journal Outcomes API routes."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.services.journal_outcome_service import (
    JournalEntryCreateRequest,
    JournalEntryResponse,
    ResolutionPath,
    create_journal_entry,
    create_journal_entry_from_paper_trade,
    get_journal_entry,
    get_journal_summary,
    list_journal_entries,
)

router = APIRouter()


class CreateJournalEntryRequest(BaseModel):
    """API request to create journal entry."""

    model_config = ConfigDict(protected_namespaces=())

    source_type: str = "manual_observation"
    source_id: str | None = None
    symbol: str | None = None
    asset_class: str = "stock"
    horizon: str = "swing"
    strategy_key: str | None = None
    regime: str | None = None
    model_stack: list[str] = Field(default_factory=list)
    expected_outcome: str | None = None
    actual_outcome: str | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    target_price: float | None = None
    stop_loss: float | None = None
    max_favorable_price: float | None = None
    max_adverse_price: float | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    resolution_path: ResolutionPath | None = None


class LabelFromPaperTradeRequest(BaseModel):
    """Request to create journal entry from paper trade."""

    model_config = ConfigDict(protected_namespaces=())

    paper_trade_id: str
    symbol: str
    entry_price: float
    exit_price: float | None = None
    stop_loss: float
    target_price: float
    opened_at: datetime
    closed_at: datetime | None = None
    outcome_notes: str | None = None


@router.post("/journal/outcomes", response_model=JournalEntryResponse)
def post_journal_outcome(request: CreateJournalEntryRequest):
    """Create a new journal outcome entry.
    
    Computes outcome label, MFE, MAE, realized R from price data.
    Does not invent outcomes - if data insufficient, label is 'unknown'.
    """
    internal_request = JournalEntryCreateRequest(
        source_type=request.source_type,  # type: ignore
        source_id=request.source_id,
        symbol=request.symbol,
        asset_class=request.asset_class,  # type: ignore
        horizon=request.horizon,  # type: ignore
        strategy_key=request.strategy_key,
        regime=request.regime,
        model_stack=request.model_stack,
        expected_outcome=request.expected_outcome,
        actual_outcome=request.actual_outcome,
        entry_price=request.entry_price,
        exit_price=request.exit_price,
        target_price=request.target_price,
        stop_loss=request.stop_loss,
        max_favorable_price=request.max_favorable_price,
        max_adverse_price=request.max_adverse_price,
        opened_at=request.opened_at,
        closed_at=request.closed_at,
        notes=request.notes,
        tags=request.tags,
        resolution_path=request.resolution_path,
    )
    return create_journal_entry(internal_request)


@router.get("/journal/outcomes")
def get_journal_outcomes(
    source_type: str | None = None,
    symbol: str | None = None,
    outcome_label: str | None = None,
    limit: int = 100,
):
    """List journal outcomes with optional filters."""
    return list_journal_entries(
        source_type=source_type,
        symbol=symbol,
        outcome_label=outcome_label,
        limit=limit,
    )


@router.get("/journal/outcomes/summary")
def get_journal_outcomes_summary():
    """Get summary statistics of journal outcomes."""
    return get_journal_summary()


@router.post("/journal/outcomes/label-from-paper-trade", response_model=JournalEntryResponse)
def post_label_from_paper_trade(request: LabelFromPaperTradeRequest):
    """Create a journal outcome entry from a closed paper trade."""
    return create_journal_entry_from_paper_trade(
        paper_trade_id=request.paper_trade_id,
        symbol=request.symbol,
        entry_price=request.entry_price,
        exit_price=request.exit_price,
        stop_loss=request.stop_loss,
        target_price=request.target_price,
        opened_at=request.opened_at,
        closed_at=request.closed_at,
        outcome_notes=request.outcome_notes,
    )


@router.get("/journal/outcomes/{entry_id}", response_model=JournalEntryResponse)
def get_journal_outcome(entry_id: str):
    """Get a specific journal outcome by ID."""
    entry = get_journal_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Journal entry not found")
    return entry
