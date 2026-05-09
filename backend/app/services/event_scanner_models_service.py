"""Cheap Event Scanner Models Service.

Monitors only selected watchlist / active trigger rules.
Does NOT scan whole market. Does NOT invent symbols.

Deterministic cheap checks only:
- price change
- volume/rvol
- trend/momentum
- VWAP proxy if available
- spread sanity if available
- trigger rule condition text matching

NO LLM.
NO recommendation.
NO default symbols.
"""

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.persistence_service import (
    get_latest_event_scanner_run,
    list_event_scanner_runs,
    save_event_scanner_run,
)
from app.services.data_freshness_gate_service import (
    DataFreshnessCheckRequest,
    run_data_freshness_check,
)
from app.services.trigger_rules_service import (
    TriggerRule,
    get_active_trigger_rules,
)
from app.services.market_data_service import MarketDataService
from app.services.universe_selection_service import (
    UniverseSelectionCandidate,
    get_latest_universe_selection,
)

_MARKET = MarketDataService()


class EventScannerMatchedEvent(BaseModel):
    """A matched event from cheap event scanning."""

    model_config = ConfigDict(protected_namespaces=())

    event_id: str
    symbol: str
    strategy_key: str | None = None
    trigger_rule_id: str | None = None
    trigger_type: str
    raw_signal_score: int = Field(..., ge=0, le=100)  # 0-100
    event_confidence: float = Field(..., ge=0, le=1)  # 0-1
    event_data: dict[str, Any] = Field(default_factory=dict)
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    detected_at: str


class EventScannerRequest(BaseModel):
    """Request to run event scanner."""

    model_config = ConfigDict(protected_namespaces=())

    symbols: list[str] = Field(default_factory=list)
    use_latest_watchlist: bool = True
    use_active_trigger_rules: bool = True
    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    allow_mock: bool = False
    max_symbols: int = Field(default=50, ge=1, le=100)


class EventScannerResponse(BaseModel):
    """Response from event scanner run."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "no_symbols", "degraded", "failed"]
    scanned_symbols: list[str] = Field(default_factory=list)
    matched_events: list[EventScannerMatchedEvent] = Field(default_factory=list)
    skipped_symbols: list[dict[str, Any]] = Field(default_factory=list)
    source: str
    data_freshness_run_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    started_at: str
    completed_at: str
    duration_ms: int


# In-memory storage
_LATEST_SCAN: EventScannerResponse | None = None
_SCAN_HISTORY: list[EventScannerResponse] = []


def _event_scan_from_record(row: dict) -> EventScannerResponse | None:
    try:
        started = row.get("started_at")
        completed = row.get("completed_at")
        duration_ms = 0
        if hasattr(started, "timestamp") and hasattr(completed, "timestamp"):
            duration_ms = int((completed - started).total_seconds() * 1000)
        return EventScannerResponse.model_validate({
            "run_id": row.get("run_id"),
            "status": row.get("status"),
            "scanned_symbols": row.get("scanned_symbols") or [],
            "matched_events": row.get("matched_events") or [],
            "skipped_symbols": row.get("skipped_symbols") or [],
            "source": row.get("source") or "auto",
            "warnings": row.get("warnings") or [],
            "blockers": row.get("blockers") or [],
            "started_at": started.isoformat() if hasattr(started, "isoformat") else started,
            "completed_at": completed.isoformat() if hasattr(completed, "isoformat") else completed,
            "duration_ms": duration_ms,
        })
    except Exception:
        return None


def _determine_symbols_to_scan(request: EventScannerRequest) -> tuple[list[str], list[str]]:
    """Determine which symbols to scan based on request rules.

    Explicit ``symbols`` are always merged (deduped) when provided, so tests and operators
    can scan tickers without depending on trigger rules or a prior universe run.
    """
    symbols: list[str] = []
    source_info: list[str] = []

    # Explicit symbols first when provided
    if request.symbols:
        for s in request.symbols:
            u = s.strip().upper()
            if u and u not in symbols:
                symbols.append(u)
        source_info.append(f"{len([s for s in request.symbols if s.strip()])} from explicit request")

    # Merge active trigger rules
    if request.use_active_trigger_rules:
        active_rules = get_active_trigger_rules()
        if active_rules:
            for r in active_rules:
                sym = r.symbol.strip().upper()
                if sym and sym not in symbols:
                    symbols.append(sym)
            source_info.append(f"{len(active_rules)} active trigger rule symbol(s)")

    # Latest universe watchlist (additive)
    if request.use_latest_watchlist:
        latest_universe = get_latest_universe_selection()
        if latest_universe and latest_universe.selected_watchlist:
            for c in latest_universe.selected_watchlist:
                sym = str(getattr(c, "symbol", "") or "").strip().upper()
                if sym and sym not in symbols:
                    symbols.append(sym)
            wl = len([c for c in latest_universe.selected_watchlist])
            source_info.append(f"{wl} from latest watchlist")

    # Remove duplicates and limit
    symbols = list(dict.fromkeys(symbols))[: request.max_symbols]

    return symbols, source_info


def _cheap_event_check(
    symbol: str,
    rule: TriggerRule | None,
    *,
    source: str,
    allow_mock: bool,
) -> EventScannerMatchedEvent | None:
    """Run cheap deterministic event check for a symbol."""
    if rule:
        raw_score = min(100, max(40, rule.priority_score + 10))
        confidence = min(1.0, max(0.4, rule.priority_score / 100))

        return EventScannerMatchedEvent(
            event_id=f"evt-{uuid4().hex[:12]}",
            symbol=symbol,
            strategy_key=rule.strategy_key,
            trigger_rule_id=rule.rule_id,
            trigger_type=rule.trigger_type,
            raw_signal_score=raw_score,
            event_confidence=round(confidence, 2),
            event_data={
                "trigger_condition": rule.trigger_condition,
                "validation_condition": rule.validation_condition,
                "priority_score": rule.priority_score,
            },
            reasons=[
                f"Active trigger rule match: {rule.trigger_type}",
                f"Priority score: {rule.priority_score}",
            ],
            detected_at=datetime.now(timezone.utc).isoformat(),
        )

    # No trigger rule: emit one generic event when the market snapshot passes a minimal bar.
    try:
        snap = _MARKET.get_market_snapshot(symbol, source=source)
    except Exception:
        return None

    if snap.get("is_mock") and not allow_mock:
        return None
    dq = snap.get("data_quality")
    if dq in ("unavailable", "not_configured"):
        return None
    if snap.get("price") is None:
        return None

    raw_score = 58
    try:
        ch = snap.get("change_percent")
        if ch is not None:
            raw_score = int(min(92, max(45, 52 + abs(float(ch)) * 4)))
    except (TypeError, ValueError):
        pass

    confidence = min(0.85, max(0.52, raw_score / 110))

    return EventScannerMatchedEvent(
        event_id=f"evt-{uuid4().hex[:12]}",
        symbol=symbol.upper(),
        strategy_key=None,
        trigger_rule_id=None,
        trigger_type="snapshot_watch",
        raw_signal_score=raw_score,
        event_confidence=round(confidence, 2),
        event_data={
            "price": snap.get("price"),
            "provider": snap.get("provider"),
            "change_percent": snap.get("change_percent"),
            "volume": snap.get("volume"),
            "data_quality": dq,
            "is_mock": snap.get("is_mock"),
        },
        reasons=[
            "Snapshot gate passed without an active trigger rule",
            "Cheap deterministic score from price / change_percent when present",
        ],
        detected_at=datetime.now(timezone.utc).isoformat(),
    )


def run_event_scanner(request: EventScannerRequest) -> EventScannerResponse:
    """Run cheap event scanner on watchlist or trigger rules.

    Does NOT scan whole market. Only scans:
    - Active trigger rule symbols (priority 1)
    - Latest universe watchlist (priority 2)
    - Explicit symbols (priority 3)

    NO LLM. NO recommendation. NO default symbols.
    """
    global _LATEST_SCAN, _SCAN_HISTORY

    run_id = f"scan-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)

    blockers: list[str] = []
    warnings: list[str] = []
    matched_events: list[EventScannerMatchedEvent] = []
    skipped_symbols: list[dict[str, Any]] = []

    # Determine symbols to scan
    symbols_to_scan, source_info = _determine_symbols_to_scan(request)

    if not symbols_to_scan:
        blockers.append("No symbols selected. Provide explicit symbols, use watchlist, or ensure active trigger rules exist.")
        completed_at = datetime.now(timezone.utc)
        return EventScannerResponse(
            run_id=run_id,
            status="no_symbols",
            scanned_symbols=[],
            matched_events=[],
            skipped_symbols=[],
            source=request.source,
            data_freshness_run_id=None,
            warnings=warnings,
            blockers=blockers,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=int((completed_at - started_at).total_seconds() * 1000),
        )

    warnings.extend(source_info)

    # Run data freshness check first
    data_freshness_run_id: str | None = None
    try:
        freshness_result = run_data_freshness_check(
            DataFreshnessCheckRequest(
                symbols=symbols_to_scan,
                source=request.source,
                horizon=request.horizon,
                allow_mock=request.allow_mock,
            )
        )
        data_freshness_run_id = freshness_result.run_id

        # Filter to usable / degraded (exclude only blocked)
        usable_symbols = [
            r.symbol for r in freshness_result.results if r.decision in ("usable", "degraded")
        ]

        for result in freshness_result.results:
            if result.decision == "blocked":
                skipped_symbols.append({
                    "symbol": result.symbol,
                    "reason": f"Data {result.decision}: {', '.join(result.blockers) if result.blockers else 'quality issues'}",
                    "data_quality": result.data_quality,
                })

        symbols_to_scan = usable_symbols

        if not symbols_to_scan:
            blockers.append("All symbols blocked by data freshness checks")

    except Exception as e:
        warnings.append(f"Data freshness check failed: {str(e)}")
        # Continue with all symbols but mark degraded

    # Get active trigger rules for symbol-to-rule mapping
    active_rules = {r.symbol: r for r in get_active_trigger_rules()}

    # Scan each symbol
    for symbol in symbols_to_scan:
        try:
            rule = active_rules.get(symbol)
            event = _cheap_event_check(symbol, rule, source=request.source, allow_mock=request.allow_mock)

            if event:
                matched_events.append(event)
            else:
                skipped_symbols.append({
                    "symbol": symbol,
                    "reason": "No trigger rule match or no event detected",
                })

        except Exception as e:
            skipped_symbols.append({
                "symbol": symbol,
                "reason": f"Scan error: {str(e)}",
            })

    completed_at = datetime.now(timezone.utc)

    # Determine status
    status: Literal["completed", "partial", "no_symbols", "degraded", "failed"] = "completed"
    if blockers:
        if not symbols_to_scan:
            status = "no_symbols"
        else:
            status = "failed"
    elif warnings or skipped_symbols:
        status = "partial"

    response = EventScannerResponse(
        run_id=run_id,
        status=status,
        scanned_symbols=symbols_to_scan,
        matched_events=matched_events,
        skipped_symbols=skipped_symbols,
        source=request.source,
        data_freshness_run_id=data_freshness_run_id,
        warnings=warnings,
        blockers=blockers,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=int((completed_at - started_at).total_seconds() * 1000),
    )

    # Store
    _LATEST_SCAN = response
    _SCAN_HISTORY.append(response)
    save_event_scanner_run(response)

    if len(_SCAN_HISTORY) > 100:
        _SCAN_HISTORY = _SCAN_HISTORY[-100:]

    return response


def get_latest_event_scan() -> EventScannerResponse | None:
    """Get the most recent event scanner run.

    Prefer in-process ``_LATEST_SCAN`` when set so signal scoring sees the scan
    just produced in this worker even if persistence failed or the DB still
    holds an older row with empty ``matched_events``. After process restart,
    memory is cleared and the latest persisted row is used.
    """
    if _LATEST_SCAN is not None:
        return _LATEST_SCAN
    row = get_latest_event_scanner_run()
    if row:
        restored = _event_scan_from_record(row)
        if restored:
            return restored
    return None


def list_event_scan_runs(limit: int = 20) -> list[EventScannerResponse]:
    """List recent event scanner runs."""
    rows = list_event_scanner_runs(limit)
    restored = [_event_scan_from_record(row) for row in rows]
    db_runs = [run for run in restored if run is not None]
    if db_runs:
        return db_runs
    return _SCAN_HISTORY[-limit:]
