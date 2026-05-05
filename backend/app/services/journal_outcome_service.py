"""Journal + Outcome Labeling Service.

Records expected vs actual outcome for recommendations, paper trades, no-trade decisions, and blocked candidates.

NO fake outcomes.
NO LLM calls.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.persistence_service import (
    get_database_table_status,
    get_journal_outcome as get_persisted_journal_outcome,
    list_journal_outcomes,
    save_journal_entry,
)

ResolutionPath = Literal[
    "target_first",
    "stop_first",
    "timed_exit",
    "invalidation_before_entry",
    "unknown",
]

_VALID_RESOLUTION_PATHS = frozenset({
    "target_first",
    "stop_first",
    "timed_exit",
    "invalidation_before_entry",
    "unknown",
})


class JournalEntryCreateRequest(BaseModel):
    """Request to create a journal entry."""

    model_config = ConfigDict(protected_namespaces=())

    source_type: Literal["recommendation", "paper_trade", "no_trade", "blocked_candidate", "manual_observation"] = "manual_observation"
    source_id: str | None = None
    symbol: str | None = None
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
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
    resolution_path: ResolutionPath | None = Field(
        default=None,
        description="Optional explicit resolution path (overrides deterministic inference).",
    )


class JournalEntryResponse(BaseModel):
    """Response from journal entry creation/retrieval."""

    model_config = ConfigDict(protected_namespaces=())

    id: str
    source_type: str
    source_id: str | None = None
    symbol: str | None = None
    outcome_label: Literal["win", "loss", "breakeven", "avoided_loss", "missed_opportunity", "invalidated", "unknown"] = "unknown"
    resolution_path: ResolutionPath = "unknown"
    mfe_percent: float | None = None
    mae_percent: float | None = None
    realized_r: float | None = None
    time_to_result_minutes: int | None = None
    followed_plan: bool | None = None
    confidence_error: float | None = None
    expected_vs_actual: str | None = None
    lessons: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class JournalOutcomeSummary(BaseModel):
    """Summary of journal outcomes."""

    model_config = ConfigDict(protected_namespaces=())

    total_entries: int
    wins: int
    losses: int
    breakeven: int
    unknown: int
    win_rate: float
    average_realized_r: float | None = None
    by_source_type: dict[str, int] = Field(default_factory=dict)
    by_symbol: dict[str, int] = Field(default_factory=dict)
    by_strategy: dict[str, int] = Field(default_factory=dict)
    recent_entries: list[JournalEntryResponse] = Field(default_factory=list)
    persistence_mode: str = "memory"


# In-memory storage
_JOURNAL_ENTRIES: dict[str, JournalEntryResponse] = {}
_JOURNAL_CREATE_REQUESTS: dict[str, JournalEntryCreateRequest] = {}  # Store original request for updates


def _price_tolerance(entry: float) -> float:
    return max(abs(entry) * 1e-6, 0.01)


def _parse_resolution_from_tags(tags: Any) -> ResolutionPath | None:
    if not tags or not isinstance(tags, (list, tuple)):
        return None
    for t in tags:
        if isinstance(t, str) and t.startswith("resolution_path="):
            val = t.split("=", 1)[1].strip()
            if val in _VALID_RESOLUTION_PATHS:
                return val  # type: ignore[return-value]
    return None


def _merge_resolution_tag(tags: list[str], resolution_path: ResolutionPath) -> list[str]:
    out = [t for t in tags if not (isinstance(t, str) and t.startswith("resolution_path="))]
    out.append(f"resolution_path={resolution_path}")
    return out


def _infer_direction(entry: float, stop: float, target: float) -> Literal["long", "short", "ambiguous"]:
    if stop < entry < target:
        return "long"
    if target < entry < stop:
        return "short"
    return "ambiguous"


def _compute_resolution_path(request: JournalEntryCreateRequest) -> ResolutionPath:
    """Infer how the trade resolved relative to stop/target (learning-loop labels).

    Uses exit vs stop/target bands for long and short structures. Does not invent tick-level
    ordering when both bands are touched; interior exits are labeled timed_exit.
    """
    if request.resolution_path and request.resolution_path in _VALID_RESOLUTION_PATHS:
        return request.resolution_path

    if request.entry_price is None:
        blob = " ".join(
            [
                (request.actual_outcome or "").lower(),
                (request.notes or "").lower(),
                " ".join(request.tags).lower() if request.tags else "",
            ]
        )
        if "invalidation_before_entry" in blob or "invalidated before entry" in blob or "setup invalidated" in blob:
            return "invalidation_before_entry"
        if request.actual_outcome and "invalid" in request.actual_outcome.lower():
            return "invalidation_before_entry"
        return "unknown"

    if request.exit_price is None or request.stop_loss is None or request.target_price is None:
        return "unknown"

    entry = float(request.entry_price)
    exit_p = float(request.exit_price)
    stop = float(request.stop_loss)
    target = float(request.target_price)
    direction = _infer_direction(entry, stop, target)
    if direction == "ambiguous":
        return "unknown"

    tol = _price_tolerance(entry)

    if direction == "long":
        near_stop = exit_p <= stop + tol
        near_target = exit_p >= target - tol
        if near_stop and not near_target:
            return "stop_first"
        if near_target and not near_stop:
            return "target_first"
        return "timed_exit"

    near_stop = exit_p >= stop - tol
    near_target = exit_p <= target + tol
    if near_stop and not near_target:
        return "stop_first"
    if near_target and not near_stop:
        return "target_first"
    return "timed_exit"


def _journal_response_from_row(row: dict) -> JournalEntryResponse | None:
    try:
        rp = row.get("resolution_path")
        if not isinstance(rp, str) or rp not in _VALID_RESOLUTION_PATHS:
            rp = _parse_resolution_from_tags(row.get("tags")) or "unknown"
        return JournalEntryResponse.model_validate({
            "id": row.get("id"),
            "source_type": row.get("source_type"),
            "source_id": row.get("source_id"),
            "symbol": row.get("symbol"),
            "outcome_label": row.get("outcome_label", "unknown"),
            "resolution_path": rp,
            "mfe_percent": row.get("mfe_percent"),
            "mae_percent": row.get("mae_percent"),
            "realized_r": row.get("realized_r"),
            "time_to_result_minutes": row.get("time_to_result_minutes"),
            "followed_plan": row.get("followed_plan"),
            "confidence_error": row.get("confidence_error"),
            "expected_vs_actual": row.get("expected_vs_actual"),
            "lessons": row.get("lessons") or [],
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at") or row.get("created_at"),
        })
    except Exception:
        return None


def _compute_outcome_label(
    entry_price: float | None,
    exit_price: float | None,
    stop_loss: float | None,
    target_price: float | None,
    actual_outcome: str | None,
    source_type: str,
) -> Literal["win", "loss", "breakeven", "avoided_loss", "missed_opportunity", "invalidated", "unknown"]:
    """Compute outcome label from price data."""
    
    # If manually marked as avoided loss
    if actual_outcome and "avoid" in actual_outcome.lower():
        return "avoided_loss"
    
    # If manually marked as missed opportunity
    if actual_outcome and "miss" in actual_outcome.lower():
        return "missed_opportunity"
    
    # If manually marked as invalidated
    if actual_outcome and "invalid" in actual_outcome.lower():
        return "invalidated"
    
    # If no-trade decision, outcome is unknown unless manually labeled
    if source_type == "no_trade":
        return "unknown"
    
    # If blocked candidate, outcome is unknown
    if source_type == "blocked_candidate":
        return "unknown"
    
    # Need entry and exit to determine win/loss
    if entry_price is None or exit_price is None:
        return "unknown"

    entry_f = float(entry_price)
    exit_f = float(exit_price)

    # Direction-aware PnL when stop/target bracket the entry (long vs short structure)
    if stop_loss is not None and target_price is not None:
        direction = _infer_direction(entry_f, float(stop_loss), float(target_price))
        if direction == "long":
            pnl = exit_f - entry_f
        elif direction == "short":
            pnl = entry_f - exit_f
        else:
            pnl = exit_f - entry_f
    else:
        pnl = exit_f - entry_f

    # Determine win/loss/ breakeven
    if abs(pnl) < 0.01:  # Within 1 cent is breakeven
        return "breakeven"
    elif pnl > 0:
        return "win"
    else:
        return "loss"


def _compute_mfe_mae(
    entry_price: float | None,
    max_favorable_price: float | None,
    max_adverse_price: float | None,
) -> tuple[float | None, float | None]:
    """Compute MFE (Max Favorable Excursion) and MAE (Max Adverse Excursion) percentages."""
    if entry_price is None or entry_price == 0:
        return None, None
    
    mfe_percent = None
    mae_percent = None
    
    if max_favorable_price is not None:
        mfe_percent = ((max_favorable_price - entry_price) / entry_price) * 100
    
    if max_adverse_price is not None:
        mae_percent = ((max_adverse_price - entry_price) / entry_price) * 100
    
    return mfe_percent, mae_percent


def _compute_realized_r(
    entry_price: float | None,
    exit_price: float | None,
    stop_loss: float | None,
) -> float | None:
    """Compute realized R (reward/risk ratio)."""
    if entry_price is None or exit_price is None or stop_loss is None:
        return None
    
    if stop_loss == entry_price:
        return None  # No risk defined
    
    risk = abs(entry_price - stop_loss)
    reward = exit_price - entry_price
    
    if risk == 0:
        return None
    
    return reward / risk


def _compute_time_to_result(
    opened_at: datetime | None,
    closed_at: datetime | None,
) -> int | None:
    """Compute time to result in minutes."""
    if opened_at is None or closed_at is None:
        return None
    
    delta = closed_at - opened_at
    return int(delta.total_seconds() / 60)


def _extract_lessons(
    outcome_label: str,
    realized_r: float | None,
    mfe_percent: float | None,
    mae_percent: float | None,
    followed_plan: bool | None,
    resolution_path: ResolutionPath,
) -> list[str]:
    """Extract lessons from outcome data."""
    lessons = []

    if resolution_path == "stop_first" and outcome_label == "loss":
        lessons.append("Resolved at stop before target — review entry, stop placement, or regime fit")

    if resolution_path == "target_first" and outcome_label == "win":
        lessons.append("Target reached before stop — planned reward/risk behavior")

    if resolution_path == "timed_exit" and outcome_label in ("win", "loss", "breakeven"):
        lessons.append("Exit between stop and target — tag as timed/rule-based exit for ranker calibration")

    if resolution_path == "invalidation_before_entry":
        lessons.append("Setup invalidated before entry — discipline / avoidance signal for scorecards")

    if outcome_label == "loss" and realized_r is not None:
        if realized_r < -1:
            lessons.append("Stop loss exceeded - risk management review needed")
        elif realized_r < -0.5:
            lessons.append("Partial stop hit - consider tighter stops")
    
    if outcome_label == "win" and realized_r is not None:
        if realized_r < 1:
            lessons.append("Win but below 1R - review entry timing")
        elif realized_r > 3:
            lessons.append("Strong 3R+ win - pattern to study")
    
    if mfe_percent is not None and mae_percent is not None:
        if mfe_percent > abs(mae_percent) * 2:
            lessons.append("Good risk control - MFE > 2x MAE")
        elif abs(mae_percent) > mfe_percent:
            lessons.append("Drawdown larger than gains - review sizing")
    
    if followed_plan is False:
        lessons.append("Did not follow plan - execution review needed")
    
    return lessons


def create_journal_entry(request: JournalEntryCreateRequest) -> JournalEntryResponse:
    """Create a journal entry with computed outcome metrics.
    
    Rules:
    - Do not invent outcomes
    - If exit/entry missing, outcome_label is unknown
    - Compute MFE, MAE, realized R from price data
    - Store in memory fallback; use persistence if available
    """
    entry_id = f"journal-{uuid4().hex[:12]}"
    now = datetime.now(timezone.utc)
    
    # Compute outcome metrics
    outcome_label = _compute_outcome_label(
        request.entry_price,
        request.exit_price,
        request.stop_loss,
        request.target_price,
        request.actual_outcome,
        request.source_type,
    )

    resolution_path = _compute_resolution_path(request)

    mfe_percent, mae_percent = _compute_mfe_mae(
        request.entry_price,
        request.max_favorable_price,
        request.max_adverse_price,
    )
    
    realized_r = _compute_realized_r(
        request.entry_price,
        request.exit_price,
        request.stop_loss,
    )
    
    time_to_result_minutes = _compute_time_to_result(
        request.opened_at,
        request.closed_at,
    )
    
    # Determine if plan was followed
    followed_plan = None
    if request.actual_outcome:
        followed_plan = "plan" in request.actual_outcome.lower() or "follow" in request.actual_outcome.lower()
    
    # Compute confidence error (if expected outcome provided)
    confidence_error = None
    expected_vs_actual = None
    if request.expected_outcome and request.actual_outcome:
        expected_vs_actual = f"Expected: {request.expected_outcome}, Actual: {request.actual_outcome}"
        # Simple confidence error estimation
        if "win" in request.expected_outcome.lower() and outcome_label == "loss":
            confidence_error = 1.0  # Full confidence error
        elif "loss" in request.expected_outcome.lower() and outcome_label == "win":
            confidence_error = 1.0
        elif outcome_label == "breakeven":
            confidence_error = 0.5
    
    # Extract lessons
    lessons = _extract_lessons(
        outcome_label,
        realized_r,
        mfe_percent,
        mae_percent,
        followed_plan,
        resolution_path,
    )

    persist_request = request.model_copy(
        update={"tags": _merge_resolution_tag(list(request.tags), resolution_path)}
    )

    response = JournalEntryResponse(
        id=entry_id,
        source_type=request.source_type,
        source_id=request.source_id,
        symbol=request.symbol,
        outcome_label=outcome_label,
        resolution_path=resolution_path,
        mfe_percent=mfe_percent,
        mae_percent=mae_percent,
        realized_r=realized_r,
        time_to_result_minutes=time_to_result_minutes,
        followed_plan=followed_plan,
        confidence_error=confidence_error,
        expected_vs_actual=expected_vs_actual,
        lessons=lessons,
        created_at=now,
        updated_at=now,
    )
    
    # Store in memory
    global _JOURNAL_ENTRIES, _JOURNAL_CREATE_REQUESTS
    _JOURNAL_ENTRIES[entry_id] = response
    _JOURNAL_CREATE_REQUESTS[entry_id] = persist_request

    # Try to persist to DB
    try:
        save_journal_entry(persist_request, response)
    except Exception:
        pass  # Memory fallback is acceptable
    
    return response


def get_journal_entry(entry_id: str) -> JournalEntryResponse | None:
    """Get a journal entry by ID."""
    if get_persistence_mode() == "postgres":
        row = get_persisted_journal_outcome(entry_id)
        if row:
            restored = _journal_response_from_row(row)
            if restored:
                return restored
    return _JOURNAL_ENTRIES.get(entry_id)


def list_journal_entries(
    source_type: str | None = None,
    symbol: str | None = None,
    outcome_label: str | None = None,
    limit: int = 100,
) -> list[JournalEntryResponse]:
    """List journal entries with optional filters."""
    rows = list_journal_outcomes(limit) if get_persistence_mode() == "postgres" else []
    if rows:
        restored = [_journal_response_from_row(row) for row in rows]
        entries = [entry for entry in restored if entry is not None]
        if source_type:
            entries = [e for e in entries if e.source_type == source_type]
        if symbol:
            entries = [e for e in entries if e.symbol and e.symbol.upper() == symbol.upper()]
        if outcome_label:
            entries = [e for e in entries if e.outcome_label == outcome_label]
        return entries[:limit]

    entries = list(_JOURNAL_ENTRIES.values())
    
    if source_type:
        entries = [e for e in entries if e.source_type == source_type]
    
    if symbol:
        entries = [e for e in entries if e.symbol and e.symbol.upper() == symbol.upper()]
    
    if outcome_label:
        entries = [e for e in entries if e.outcome_label == outcome_label]
    
    # Sort by created_at desc
    entries.sort(key=lambda e: e.created_at, reverse=True)
    
    return entries[:limit]


def get_journal_summary() -> JournalOutcomeSummary:
    """Get summary of journal outcomes."""
    persisted_rows = list_journal_outcomes(1000) if get_persistence_mode() == "postgres" else []
    if persisted_rows:
        entries = [entry for entry in (_journal_response_from_row(row) for row in persisted_rows) if entry is not None]
        total = len(entries)
        wins = sum(1 for e in entries if e.outcome_label == "win")
        losses = sum(1 for e in entries if e.outcome_label == "loss")
        breakeven = sum(1 for e in entries if e.outcome_label == "breakeven")
        unknown = sum(1 for e in entries if e.outcome_label == "unknown")
        realized_rs = [e.realized_r for e in entries if e.realized_r is not None]
        by_source_type: dict[str, int] = {}
        by_symbol: dict[str, int] = {}
        by_strategy: dict[str, int] = {}
        for row, entry in zip(persisted_rows, entries):
            by_source_type[entry.source_type] = by_source_type.get(entry.source_type, 0) + 1
            if entry.symbol:
                by_symbol[entry.symbol] = by_symbol.get(entry.symbol, 0) + 1
            if row.get("strategy_key"):
                by_strategy[row["strategy_key"]] = by_strategy.get(row["strategy_key"], 0) + 1
        return JournalOutcomeSummary(
            total_entries=total,
            wins=wins,
            losses=losses,
            breakeven=breakeven,
            unknown=unknown,
            win_rate=wins / (wins + losses) if (wins + losses) > 0 else 0.0,
            average_realized_r=sum(realized_rs) / len(realized_rs) if realized_rs else None,
            by_source_type=by_source_type,
            by_symbol=by_symbol,
            by_strategy=by_strategy,
            recent_entries=entries[:10],
            persistence_mode="postgres",
        )

    entries = list(_JOURNAL_ENTRIES.values())
    
    total = len(entries)
    wins = sum(1 for e in entries if e.outcome_label == "win")
    losses = sum(1 for e in entries if e.outcome_label == "loss")
    breakeven = sum(1 for e in entries if e.outcome_label == "breakeven")
    unknown = sum(1 for e in entries if e.outcome_label == "unknown")
    
    win_rate = wins / (wins + losses) if (wins + losses) > 0 else 0.0
    
    # Average realized R
    realized_rs = [e.realized_r for e in entries if e.realized_r is not None]
    average_realized_r = sum(realized_rs) / len(realized_rs) if realized_rs else None
    
    # By source type
    by_source_type: dict[str, int] = {}
    for e in entries:
        by_source_type[e.source_type] = by_source_type.get(e.source_type, 0) + 1
    
    # By symbol
    by_symbol: dict[str, int] = {}
    for e in entries:
        if e.symbol:
            by_symbol[e.symbol] = by_symbol.get(e.symbol, 0) + 1
    
    # By strategy (from stored requests)
    by_strategy: dict[str, int] = {}
    for entry_id, request in _JOURNAL_CREATE_REQUESTS.items():
        if request.strategy_key:
            by_strategy[request.strategy_key] = by_strategy.get(request.strategy_key, 0) + 1
    
    return JournalOutcomeSummary(
        total_entries=total,
        wins=wins,
        losses=losses,
        breakeven=breakeven,
        unknown=unknown,
        win_rate=win_rate,
        average_realized_r=average_realized_r,
        by_source_type=by_source_type,
        by_symbol=by_symbol,
        by_strategy=by_strategy,
        recent_entries=entries[:10],
        persistence_mode=get_persistence_mode(),
    )


def create_journal_entry_from_paper_trade(
    paper_trade_id: str,
    symbol: str,
    entry_price: float,
    exit_price: float | None,
    stop_loss: float,
    target_price: float,
    opened_at: datetime,
    closed_at: datetime | None,
    outcome_notes: str | None = None,
) -> JournalEntryResponse:
    """Create a journal entry from a paper trade outcome."""
    request = JournalEntryCreateRequest(
        source_type="paper_trade",
        source_id=paper_trade_id,
        symbol=symbol,
        entry_price=entry_price,
        exit_price=exit_price,
        stop_loss=stop_loss,
        target_price=target_price,
        opened_at=opened_at,
        closed_at=closed_at,
        notes=outcome_notes,
    )
    
    return create_journal_entry(request)


def get_latest_journal_entry() -> JournalEntryResponse | None:
    """Get the most recent journal entry."""
    rows = list_journal_outcomes(1) if get_persistence_mode() == "postgres" else []
    if rows:
        restored = _journal_response_from_row(rows[0])
        if restored:
            return restored
    entries = list(_JOURNAL_ENTRIES.values())
    if not entries:
        return None

    entries.sort(key=lambda e: e.created_at, reverse=True)
    return entries[0]


def get_persistence_mode() -> str:
    """Return the current persistence mode for journal entries."""
    status = get_database_table_status()
    return "postgres" if status.get("connected", False) else "memory"
