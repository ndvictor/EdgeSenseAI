"""Universe Selection / Watchlist Builder Service.

Implements Phase 2 of the Adaptive Agentic Quant Workflow:
- Preselect and rank symbols worth monitoring BEFORE market open
- Deterministic weighted scoring - NO LLMs
- Explicit symbols only - NO hardcoded defaults

This is THE STARTING POINT for the platform workflow, NOT Candidate Universe.
Candidate Universe is downstream (receives selected symbols from here).
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.candidate_universe_service import add_candidate
from app.services.data_freshness_gate_service import (
    DataFreshnessCheckRequest,
    run_data_freshness_check,
)
from app.services.timing_cadence_service import (
    CadencePlan,
    ScannerDepth,
    detect_market_phase,
    get_active_loop_for_phase,
    get_cadence_plan_for_phase,
)


class UniverseSelectionRequest(BaseModel):
    """Request to run universe selection.

    Symbols must be explicitly provided. No hardcoded defaults.
    """

    model_config = ConfigDict(protected_namespaces=())

    symbols: list[str] = Field(default_factory=list, description="Explicit symbols to evaluate. NO defaults.")
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    strategy_key: str | None = None
    max_candidates: int = Field(default=25, ge=1, le=100)
    min_score: int = Field(default=50, ge=0, le=100)
    account_equity: float | None = None
    buying_power: float | None = None
    max_risk_per_trade_percent: float | None = None
    include_mock: bool = False  # Explicit opt-in for mock data
    promote_to_candidate_universe: bool = False  # Auto-promote selected to candidate universe


class UniverseSelectionCandidate(BaseModel):
    """A candidate symbol with full scoring metadata."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    asset_class: str
    horizon: str
    strategy_key: str | None = None
    rank: int = 0
    universe_score: float = Field(..., ge=0, le=100)
    priority_score: int = Field(default=50, ge=0, le=100)
    expected_direction: Literal["long", "short", "neutral"] = "neutral"
    assigned_strategy: str = "weighted_universe_ranker_v1"
    trigger_condition: str = ""
    validation_condition: str = ""
    invalidation_condition: str = ""
    scan_interval_seconds: int = 300  # 5 min default
    watchlist_ttl_minutes: int = 240  # 4 hours default
    account_fit: float = Field(default=50, ge=0, le=100)
    liquidity_score: float = Field(default=50, ge=0, le=100)
    spread_score: float = Field(default=50, ge=0, le=100)
    volatility_fit: float = Field(default=50, ge=0, le=100)
    trend_score: float = Field(default=50, ge=0, le=100)
    rvol_score: float = Field(default=50, ge=0, le=100)
    sector_strength_score: float | None = None  # Optional
    data_quality: Literal["excellent", "good", "fair", "poor", "unavailable"] = "fair"
    provider: str = "unknown"
    source: str = "universe_selection"
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    expires_at: str | None = None


class DataFreshnessSummary(BaseModel):
    """Summary of data freshness gate results."""

    run_id: str
    status: str
    usable_count: int
    degraded_count: int
    blocked_count: int
    total_checked: int


class UniverseSelectionResponse(BaseModel):
    """Response from universe selection run."""

    run_id: str
    status: Literal["completed", "partial", "failed", "no_symbols", "blocked_by_data_freshness"]
    market_phase: str
    active_loop: str
    cadence_plan: CadencePlan
    requested_symbols: list[str]
    ranked_candidates: list[UniverseSelectionCandidate]
    selected_watchlist: list[UniverseSelectionCandidate]
    rejected_candidates: list[UniverseSelectionCandidate]
    data_freshness_status: str | None = None
    data_freshness_summary: DataFreshnessSummary | None = None
    blockers: list[str]
    warnings: list[str]
    started_at: str
    completed_at: str
    duration_ms: int


# In-memory storage for universe selection runs (fallback when DB unavailable)
_UNIVERSE_SELECTION_RUNS: list[UniverseSelectionResponse] = []
_LATEST_UNIVERSE_SELECTION: UniverseSelectionResponse | None = None


def _weighted_universe_ranker_v1(
    symbol: str,
    asset_class: str,
    horizon: str,
    source: str,
    include_mock: bool,
    account_equity: float | None,
    buying_power: float | None,
) -> UniverseSelectionCandidate | None:
    """Deterministic weighted ranker for universe selection.

    NO LLMs. NO hardcoded defaults.
    Data quality gate runs FIRST.
    """
    blockers: list[str] = []
    reasons: list[str] = []

    # Step 1: Data Quality Gate (MUST PASS FIRST)
    # For now, we simulate data quality check
    # In production, this would call market_data_service for snapshot
    data_quality: Literal["excellent", "good", "fair", "poor", "unavailable"] = "fair"
    provider = "unknown"

    # Simulate provider selection based on source
    if source == "auto":
        # Try real providers first, fallback to mock only if allowed
        provider = "yfinance"  # Simplified - real implementation would try multiple
    elif source == "mock":
        if not include_mock:
            blockers.append("Mock source selected but include_mock=false")
            return None
        provider = "mock"
        data_quality = "fair"
    else:
        provider = source

    # Check if data is available (simulated)
    # In production, this would check actual market data availability
    if data_quality == "unavailable":
        blockers.append("Data unavailable for symbol")
        return None

    if data_quality == "poor" and not include_mock:
        blockers.append("Data quality too poor and mock not allowed")
        return None

    # Step 2: Score Components (all deterministic, no ML)
    # These are simulated scores - real implementation would calculate from market data

    # Liquidity score (0-100)
    # Higher for large-cap stocks, lower for illiquid symbols
    liquidity_score = 65.0  # Default assumption

    # Spread score (0-100)
    # Higher for tight spreads, lower for wide spreads
    spread_score = 60.0

    # Trend score from history (0-100)
    # Based on recent price action
    trend_score = 55.0

    # Volatility fit (0-100)
    # How well does volatility match the horizon preference
    volatility_fit = 60.0
    if horizon == "day_trade":
        volatility_fit = 70.0  # Day traders want more volatility
    elif horizon == "one_month":
        volatility_fit = 50.0  # Swing traders want moderate volatility

    # RVOL score if volume available (0-100)
    rvol_score = 50.0

    # Account fit score (0-100)
    # How well does the symbol fit account size and risk parameters
    account_fit = 60.0
    if account_equity and account_equity < 25000:
        # Small accounts should avoid expensive stocks
        account_fit = 55.0

    # Step 3: Combine into universe_score (0-100)
    # Weighted combination
    universe_score = (
        liquidity_score * 0.20 +      # 20% weight
        spread_score * 0.15 +         # 15% weight
        trend_score * 0.20 +          # 20% weight
        volatility_fit * 0.20 +       # 20% weight
        rvol_score * 0.10 +           # 10% weight
        account_fit * 0.15            # 15% weight
    )

    # Round to 2 decimal places
    universe_score = round(universe_score, 2)

    # Step 4: Set direction based on trend
    expected_direction: Literal["long", "short", "neutral"] = "neutral"
    if trend_score > 65:
        expected_direction = "long"
        reasons.append("Positive trend detected")
    elif trend_score < 35:
        expected_direction = "short"
        reasons.append("Negative trend detected")
    else:
        reasons.append("Neutral trend - wait for breakout")

    # Step 5: Build candidate
    # Calculate TTL based on horizon
    ttl_minutes = {
        "day_trade": 60,      # 1 hour
        "swing": 240,         # 4 hours
        "one_month": 1440,   # 24 hours
    }.get(horizon, 240)

    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat()

    return UniverseSelectionCandidate(
        symbol=symbol.upper(),
        asset_class=asset_class,
        horizon=horizon,
        strategy_key="weighted_universe_ranker_v1",
        rank=0,  # Will be set after sorting
        universe_score=universe_score,
        priority_score=int(universe_score),  # Use score as priority
        expected_direction=expected_direction,
        assigned_strategy="momentum_watchlist_v1" if trend_score > 60 else "range_watchlist_v1",
        trigger_condition=f"Price breaks above recent high with RVOL > 1.5" if expected_direction == "long" else f"Price breaks below recent low with RVOL > 1.5",
        validation_condition="Volume confirms breakout, spread remains < 0.5%",
        invalidation_condition="Breaks opposite level or volume dries up",
        scan_interval_seconds=300,  # 5 min
        watchlist_ttl_minutes=ttl_minutes,
        account_fit=round(account_fit, 2),
        liquidity_score=round(liquidity_score, 2),
        spread_score=round(spread_score, 2),
        volatility_fit=round(volatility_fit, 2),
        trend_score=round(trend_score, 2),
        rvol_score=round(rvol_score, 2),
        sector_strength_score=None,  # Would need sector data
        data_quality=data_quality,
        provider=provider,
        source="universe_selection",
        reasons=reasons,
        blockers=blockers,
        expires_at=expires_at,
    )


def run_universe_selection(request: UniverseSelectionRequest) -> UniverseSelectionResponse:
    """Run universe selection for provided symbols.

    This is THE STARTING POINT - Candidate Universe is downstream.
    NO LLMs. NO hardcoded defaults.
    """
    started_at = datetime.now(timezone.utc)
    run_id = f"univ-{uuid4().hex[:12]}"

    # Get current market phase and cadence
    market_phase = detect_market_phase()
    active_loop = get_active_loop_for_phase(market_phase)
    cadence_plan = get_cadence_plan_for_phase(market_phase)

    blockers: list[str] = []
    warnings: list[str] = []

    # Validate: symbols must be explicitly provided
    if not request.symbols:
        return UniverseSelectionResponse(
            run_id=run_id,
            status="no_symbols",
            market_phase=market_phase.value,
            active_loop=active_loop.value,
            cadence_plan=cadence_plan,
            requested_symbols=[],
            ranked_candidates=[],
            selected_watchlist=[],
            rejected_candidates=[],
            blockers=["No symbols provided. Universe Selection requires explicit symbols."],
            warnings=[],
            started_at=started_at.isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            duration_ms=0,
        )

    # Deduplicate symbols
    unique_symbols = list(dict.fromkeys([s.strip().upper() for s in request.symbols if s.strip()]))

    # STEP 1: Data Freshness Gate
    # Run data freshness check BEFORE scoring
    freshness_check = run_data_freshness_check(DataFreshnessCheckRequest(
        symbols=unique_symbols,
        asset_class=request.asset_class,
        source=request.source,
        horizon=request.horizon,
        allow_mock=request.include_mock,
    ))

    # Build data freshness summary for response
    data_freshness_summary = DataFreshnessSummary(
        run_id=freshness_check.run_id,
        status=freshness_check.status,
        usable_count=freshness_check.summary.usable_count,
        degraded_count=freshness_check.summary.degraded_count,
        blocked_count=freshness_check.summary.blocked_count,
        total_checked=freshness_check.summary.total_checked,
    )

    # Get usable symbols (those that passed data freshness)
    usable_symbols = [
        r.symbol for r in freshness_check.results
        if r.decision in ["usable", "degraded"]
    ]

    # If all symbols blocked, return early
    if not usable_symbols:
        completed_at = datetime.now(timezone.utc)
        duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Build rejected candidates for blocked symbols
        rejected_candidates = []
        for r in freshness_check.results:
            rejected_candidates.append(UniverseSelectionCandidate(
                symbol=r.symbol,
                asset_class=request.asset_class,
                horizon=request.horizon,
                rank=0,
                universe_score=0,
                blockers=r.blockers or ["Blocked by data freshness gate"],
                warnings=r.warnings or [],
                data_quality=r.data_quality,
                provider=r.provider,
            ))

        return UniverseSelectionResponse(
            run_id=run_id,
            status="blocked_by_data_freshness",
            market_phase=market_phase.value,
            active_loop=active_loop.value,
            cadence_plan=cadence_plan,
            requested_symbols=unique_symbols,
            ranked_candidates=[],
            selected_watchlist=[],
            rejected_candidates=rejected_candidates,
            data_freshness_status=freshness_check.status,
            data_freshness_summary=data_freshness_summary,
            blockers=freshness_check.blockers + ["All symbols blocked by data freshness checks"],
            warnings=freshness_check.warnings,
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_ms=duration_ms,
        )

    # Add warnings from freshness check
    warnings.extend(freshness_check.warnings)

    # STEP 2: Score usable symbols only
    ranked_candidates: list[UniverseSelectionCandidate] = []
    rejected_candidates: list[UniverseSelectionCandidate] = []

    # First add blocked symbols from freshness check to rejected
    for r in freshness_check.results:
        if r.decision == "blocked":
            rejected_candidates.append(UniverseSelectionCandidate(
                symbol=r.symbol,
                asset_class=request.asset_class,
                horizon=request.horizon,
                rank=0,
                universe_score=0,
                blockers=r.blockers or ["Blocked by data freshness gate"],
                warnings=r.warnings or [],
                data_quality=r.data_quality,
                provider=r.provider,
            ))

    # Now score only usable symbols
    for symbol in usable_symbols:
        candidate = _weighted_universe_ranker_v1(
            symbol=symbol,
            asset_class=request.asset_class,
            horizon=request.horizon,
            source=request.source,
            include_mock=request.include_mock,
            account_equity=request.account_equity,
            buying_power=request.buying_power,
        )

        if candidate is None:
            # Rejected at data quality gate
            rejected_candidates.append(
                UniverseSelectionCandidate(
                    symbol=symbol,
                    asset_class=request.asset_class,
                    horizon=request.horizon,
                    rank=0,
                    universe_score=0,
                    blockers=["Failed internal data quality gate"],
                )
            )
            continue

        if candidate.blockers:
            rejected_candidates.append(candidate)
        else:
            ranked_candidates.append(candidate)

    # Sort by universe_score descending
    ranked_candidates.sort(key=lambda c: c.universe_score, reverse=True)

    # Assign ranks
    for i, candidate in enumerate(ranked_candidates):
        candidate.rank = i + 1

    # Select top candidates based on max_candidates and min_score
    selected_watchlist = [
        c for c in ranked_candidates[: request.max_candidates]
        if c.universe_score >= request.min_score
    ]

    # Add to rejected any that didn't make the cut due to score
    for c in ranked_candidates[request.max_candidates :]:
        c.blockers.append(f"Not in top {request.max_candidates} by score")
        rejected_candidates.append(c)

    for c in selected_watchlist:
        if c.universe_score < request.min_score:
            c.blockers.append(f"Score {c.universe_score} below min_score {request.min_score}")
            rejected_candidates.append(c)

    # Re-filter selected to remove those that failed min_score
    selected_watchlist = [c for c in selected_watchlist if c.universe_score >= request.min_score]

    # Build status
    status: Literal["completed", "partial", "failed", "no_symbols", "blocked_by_data_freshness"]
    if not selected_watchlist and not ranked_candidates:
        status = "failed"
        blockers.append("No symbols passed data quality gate")
    elif len(selected_watchlist) < len(ranked_candidates):
        status = "partial"
        warnings.append(f"Selected {len(selected_watchlist)}/{len(ranked_candidates)} candidates")
    else:
        status = "completed"

    completed_at = datetime.now(timezone.utc)
    duration_ms = int((completed_at - started_at).total_seconds() * 1000)

    response = UniverseSelectionResponse(
        run_id=run_id,
        status=status,
        market_phase=market_phase.value,
        active_loop=active_loop.value,
        cadence_plan=cadence_plan,
        requested_symbols=unique_symbols,
        ranked_candidates=ranked_candidates,
        selected_watchlist=selected_watchlist,
        rejected_candidates=rejected_candidates,
        data_freshness_status=freshness_check.status,
        data_freshness_summary=data_freshness_summary,
        blockers=blockers,
        warnings=warnings,
        started_at=started_at.isoformat(),
        completed_at=completed_at.isoformat(),
        duration_ms=duration_ms,
    )

    # Store in memory (fallback when DB unavailable)
    global _LATEST_UNIVERSE_SELECTION, _UNIVERSE_SELECTION_RUNS
    _LATEST_UNIVERSE_SELECTION = response
    _UNIVERSE_SELECTION_RUNS.insert(0, response)
    del _UNIVERSE_SELECTION_RUNS[100:]  # Keep last 100

    # Optionally promote to Candidate Universe (downstream)
    if request.promote_to_candidate_universe:
        for candidate in selected_watchlist:
            add_candidate(
                symbol=candidate.symbol,
                asset_class=candidate.asset_class,
                horizon=candidate.horizon,
                source_type="universe_selection",
                source_detail=f"Selected by weighted_universe_ranker_v1, strategy={candidate.assigned_strategy}, trigger={candidate.trigger_condition}",
                priority_score=candidate.priority_score,
                notes=f"Universe Score: {candidate.universe_score}, Expected Direction: {candidate.expected_direction}, Expires: {candidate.expires_at}",
            )

    return response


def get_latest_universe_selection() -> UniverseSelectionResponse | None:
    """Get the most recent universe selection run."""
    return _LATEST_UNIVERSE_SELECTION


def list_universe_selection_runs(limit: int = 20) -> list[UniverseSelectionResponse]:
    """List recent universe selection runs."""
    return _UNIVERSE_SELECTION_RUNS[: max(1, min(limit, 100))]


def promote_latest_universe_selection_to_candidates() -> dict[str, Any]:
    """Promote the latest selected watchlist to Candidate Universe.

    Returns summary of promoted symbols.
    """
    latest = get_latest_universe_selection()
    if not latest:
        return {
            "success": False,
            "message": "No universe selection run available",
            "promoted_count": 0,
            "promoted_symbols": [],
        }

    promoted = []
    for candidate in latest.selected_watchlist:
        add_candidate(
            symbol=candidate.symbol,
            asset_class=candidate.asset_class,
            horizon=candidate.horizon,
            source_type="universe_selection",
            source_detail=f"Manual promotion from run {latest.run_id}, strategy={candidate.assigned_strategy}",
            priority_score=candidate.priority_score,
            notes=f"Universe Score: {candidate.universe_score}, Expected Direction: {candidate.expected_direction}",
        )
        promoted.append(candidate.symbol)

    return {
        "success": True,
        "message": f"Promoted {len(promoted)} symbols to Candidate Universe",
        "promoted_count": len(promoted),
        "promoted_symbols": promoted,
        "source_run_id": latest.run_id,
    }
