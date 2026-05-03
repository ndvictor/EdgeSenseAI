"""Timing & Cadence Service - Minimal deterministic market phase detection.

Implements Phase 1 of the Adaptive Agentic Quant Workflow:
- Market Phase Scheduler
- Timing & Cadence Agent
- Returns deterministic plans based on current time (US Eastern)

This service does NOT use LLMs. It uses deterministic rules.
"""

from datetime import datetime, time
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.settings import settings


class MarketPhase(str, Enum):
    MARKET_CLOSED = "market_closed"
    PRE_MARKET = "pre_market"
    MARKET_OPEN_FIRST_30_MIN = "market_open_first_30_min"
    MARKET_OPEN = "market_open"
    MIDDAY = "midday"
    POWER_HOUR = "power_hour"
    AFTER_HOURS = "after_hours"


class ActiveLoop(str, Enum):
    RESEARCH_BACKTESTING_LOOP = "research_backtesting_loop"
    PRE_MARKET_PLANNING_LOOP = "pre_market_planning_loop"
    FAST_SCANNING_LOOP = "fast_scanning_loop"
    REDUCED_CADENCE_PRUNING_LOOP = "reduced_cadence_pruning_loop"
    POWER_HOUR_ROTATION_LOOP = "power_hour_rotation_loop"
    AFTER_HOURS_JOURNAL_RESEARCH_LOOP = "after_hours_journal_research_loop"


class ScannerDepth(str, Enum):
    DEEP = "deep"  # Full analysis, all agents
    STANDARD = "standard"  # Core agents only
    LIGHT = "light"  # Price/volume only
    MINIMAL = "minimal"  # Basic checks only


class LLMBudgetMode(str, Enum):
    FULL = "full"  # All LLM features enabled
    CONSERVATIVE = "conservative"  # Limit LLM calls
    MINIMAL = "minimal"  # LLM only for critical validation
    DISABLED = "disabled"  # No LLM calls


class LLMValidationPolicy(str, Enum):
    STRICT = "strict"  # All signals must pass LLM validation
    MODERATE = "moderate"  # High-confidence signals auto-approved
    PERMISSIVE = "permissive"  # Only anomalies trigger LLM review
    DISABLED = "disabled"  # No LLM validation


class CadencePlan(BaseModel):
    """Deterministic cadence plan for current market phase."""

    scan_interval_seconds: int = Field(..., description="Seconds between scans")
    strategy_refresh_minutes: int = Field(..., description="Minutes between strategy re-evaluation")
    universe_refresh_minutes: int = Field(..., description="Minutes between universe re-selection")
    watchlist_ttl_minutes: int = Field(..., description="Watchlist entry time-to-live")
    llm_validation_policy: LLMValidationPolicy = Field(..., description="LLM validation strictness")
    llm_budget_mode: LLMBudgetMode = Field(..., description="LLM budget mode")
    scanner_depth: ScannerDepth = Field(..., description="How deep scans should go")


class RuntimePhaseResponse(BaseModel):
    """Response from runtime phase endpoint."""

    market_phase: MarketPhase
    current_time_et: str
    market_open_time_et: str = "09:30"
    market_close_time_et: str = "16:00"
    is_trading_day: bool = True  # Simplified - assumes all days are trading days
    live_trading_allowed: Literal[False] = False  # ALWAYS FALSE per architecture
    human_approval_required: Literal[True] = True  # ALWAYS TRUE per architecture
    timestamp: str


class RuntimeCadenceResponse(BaseModel):
    """Response from runtime cadence endpoint."""

    market_phase: MarketPhase
    active_loop: ActiveLoop
    cadence_plan: CadencePlan
    live_trading_allowed: Literal[False] = False  # ALWAYS FALSE per architecture
    human_approval_required: Literal[True] = True  # ALWAYS TRUE per architecture
    timestamp: str


class RuntimeCadenceSimulateRequest(BaseModel):
    """Request to simulate cadence for a specific time."""

    simulate_time_et: str = Field(..., description="Time in HH:MM format ET")
    is_trading_day: bool = True


class AIOpsSummary(BaseModel):
    """AI Ops summary including market phase and cadence."""

    market_phase: MarketPhase
    cadence_plan: CadencePlan
    active_loop: ActiveLoop
    scan_mode: ScannerDepth
    llm_validation_policy: LLMValidationPolicy
    live_trading_allowed: Literal[False] = False
    human_approval_required: Literal[True] = True


def _get_current_time_et() -> datetime:
    """Get current time in US Eastern (ET)."""
    from datetime import timezone
    import pytz

    et_tz = pytz.timezone("America/New_York")
    return datetime.now(et_tz)


def _parse_time_et(time_str: str) -> time:
    """Parse time string HH:MM to time object."""
    hour, minute = map(int, time_str.split(":"))
    return time(hour, minute)


def detect_market_phase(current_time: datetime | None = None) -> MarketPhase:
    """Detect current market phase based on time.

    Uses deterministic rules - no ML, no LLM.
    """
    if current_time is None:
        current_time = _get_current_time_et()

    current_time_only = current_time.time()

    # Market hours in ET
    pre_market_start = time(4, 0)
    market_open = time(9, 30)
    market_open_30min = time(10, 0)  # 09:30 + 30 min
    midday_start = time(11, 0)
    power_hour_start = time(15, 0)  # 3 PM
    market_close = time(16, 0)
    after_hours_end = time(20, 0)

    # Weekend check (simplified - just check if Saturday or Sunday)
    if current_time.weekday() >= 5:  # Saturday=5, Sunday=6
        return MarketPhase.MARKET_CLOSED

    if current_time_only < pre_market_start:
        return MarketPhase.MARKET_CLOSED
    elif current_time_only < market_open:
        return MarketPhase.PRE_MARKET
    elif current_time_only < market_open_30min:
        return MarketPhase.MARKET_OPEN_FIRST_30_MIN
    elif current_time_only < midday_start:
        return MarketPhase.MARKET_OPEN
    elif current_time_only < power_hour_start:
        return MarketPhase.MIDDAY
    elif current_time_only < market_close:
        return MarketPhase.POWER_HOUR
    elif current_time_only < after_hours_end:
        return MarketPhase.AFTER_HOURS
    else:
        return MarketPhase.MARKET_CLOSED


def get_active_loop_for_phase(phase: MarketPhase) -> ActiveLoop:
    """Get the active operational loop for a market phase."""
    loop_map = {
        MarketPhase.MARKET_CLOSED: ActiveLoop.RESEARCH_BACKTESTING_LOOP,
        MarketPhase.PRE_MARKET: ActiveLoop.PRE_MARKET_PLANNING_LOOP,
        MarketPhase.MARKET_OPEN_FIRST_30_MIN: ActiveLoop.FAST_SCANNING_LOOP,
        MarketPhase.MARKET_OPEN: ActiveLoop.FAST_SCANNING_LOOP,
        MarketPhase.MIDDAY: ActiveLoop.REDUCED_CADENCE_PRUNING_LOOP,
        MarketPhase.POWER_HOUR: ActiveLoop.POWER_HOUR_ROTATION_LOOP,
        MarketPhase.AFTER_HOURS: ActiveLoop.AFTER_HOURS_JOURNAL_RESEARCH_LOOP,
    }
    return loop_map.get(phase, ActiveLoop.RESEARCH_BACKTESTING_LOOP)


def get_cadence_plan_for_phase(phase: MarketPhase) -> CadencePlan:
    """Get deterministic cadence plan for a market phase.

    All plans respect:
    - live_trading_allowed = False
    - human_approval_required = True
    - LLM Budget Gate is enforced
    """
    base_plan = {
        MarketPhase.MARKET_CLOSED: CadencePlan(
            scan_interval_seconds=300,  # 5 min - relaxed
            strategy_refresh_minutes=60,
            universe_refresh_minutes=240,  # 4 hours
            watchlist_ttl_minutes=480,
            llm_validation_policy=LLMValidationPolicy.DISABLED,  # No LLM during closed
            llm_budget_mode=LLMBudgetMode.DISABLED,
            scanner_depth=ScannerDepth.MINIMAL,
        ),
        MarketPhase.PRE_MARKET: CadencePlan(
            scan_interval_seconds=60,  # 1 min - preparing
            strategy_refresh_minutes=15,
            universe_refresh_minutes=30,
            watchlist_ttl_minutes=60,
            llm_validation_policy=LLMValidationPolicy.MODERATE,
            llm_budget_mode=LLMBudgetMode.CONSERVATIVE,
            scanner_depth=ScannerDepth.STANDARD,
        ),
        MarketPhase.MARKET_OPEN_FIRST_30_MIN: CadencePlan(
            scan_interval_seconds=30,  # 30 sec - high activity
            strategy_refresh_minutes=5,
            universe_refresh_minutes=15,
            watchlist_ttl_minutes=30,
            llm_validation_policy=LLMValidationPolicy.MODERATE,
            llm_budget_mode=LLMBudgetMode.CONSERVATIVE,
            scanner_depth=ScannerDepth.DEEP,
        ),
        MarketPhase.MARKET_OPEN: CadencePlan(
            scan_interval_seconds=60,  # 1 min
            strategy_refresh_minutes=10,
            universe_refresh_minutes=30,
            watchlist_ttl_minutes=45,
            llm_validation_policy=LLMValidationPolicy.MODERATE,
            llm_budget_mode=LLMBudgetMode.CONSERVATIVE,
            scanner_depth=ScannerDepth.STANDARD,
        ),
        MarketPhase.MIDDAY: CadencePlan(
            scan_interval_seconds=120,  # 2 min - reduced
            strategy_refresh_minutes=20,
            universe_refresh_minutes=60,
            watchlist_ttl_minutes=90,
            llm_validation_policy=LLMValidationPolicy.PERMISSIVE,
            llm_budget_mode=LLMBudgetMode.MINIMAL,
            scanner_depth=ScannerDepth.LIGHT,
        ),
        MarketPhase.POWER_HOUR: CadencePlan(
            scan_interval_seconds=45,  # 45 sec - elevated
            strategy_refresh_minutes=10,
            universe_refresh_minutes=20,
            watchlist_ttl_minutes=40,
            llm_validation_policy=LLMValidationPolicy.MODERATE,
            llm_budget_mode=LLMBudgetMode.CONSERVATIVE,
            scanner_depth=ScannerDepth.STANDARD,
        ),
        MarketPhase.AFTER_HOURS: CadencePlan(
            scan_interval_seconds=300,  # 5 min - relaxed
            strategy_refresh_minutes=60,
            universe_refresh_minutes=180,
            watchlist_ttl_minutes=360,
            llm_validation_policy=LLMValidationPolicy.DISABLED,
            llm_budget_mode=LLMBudgetMode.DISABLED,
            scanner_depth=ScannerDepth.MINIMAL,
        ),
    }
    return base_plan.get(phase, base_plan[MarketPhase.MARKET_CLOSED])


def get_runtime_phase() -> RuntimePhaseResponse:
    """Get current runtime phase information."""
    now = _get_current_time_et()
    phase = detect_market_phase(now)

    return RuntimePhaseResponse(
        market_phase=phase,
        current_time_et=now.strftime("%H:%M:%S"),
        is_trading_day=now.weekday() < 5,
        live_trading_allowed=False,  # ALWAYS FALSE
        human_approval_required=True,  # ALWAYS TRUE
        timestamp=datetime.utcnow().isoformat(),
    )


def get_runtime_cadence() -> RuntimeCadenceResponse:
    """Get current runtime cadence plan."""
    now = _get_current_time_et()
    phase = detect_market_phase(now)
    active_loop = get_active_loop_for_phase(phase)
    cadence_plan = get_cadence_plan_for_phase(phase)

    return RuntimeCadenceResponse(
        market_phase=phase,
        active_loop=active_loop,
        cadence_plan=cadence_plan,
        live_trading_allowed=False,  # ALWAYS FALSE
        human_approval_required=True,  # ALWAYS TRUE
        timestamp=datetime.utcnow().isoformat(),
    )


def simulate_cadence_for_time(request: RuntimeCadenceSimulateRequest) -> RuntimeCadenceResponse:
    """Simulate cadence plan for a specific time (for testing/backtesting)."""
    from datetime import datetime as dt

    # Parse the simulate time
    hour, minute = map(int, request.simulate_time_et.split(":"))

    # Create a datetime with today's date but requested time
    now = _get_current_time_et()
    simulate_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    phase = detect_market_phase(simulate_dt)
    active_loop = get_active_loop_for_phase(phase)
    cadence_plan = get_cadence_plan_for_phase(phase)

    return RuntimeCadenceResponse(
        market_phase=phase,
        active_loop=active_loop,
        cadence_plan=cadence_plan,
        live_trading_allowed=False,  # ALWAYS FALSE
        human_approval_required=True,  # ALWAYS TRUE
        timestamp=datetime.utcnow().isoformat(),
    )


def get_ai_ops_summary() -> AIOpsSummary:
    """Get AI Ops summary for display in Command Center."""
    now = _get_current_time_et()
    phase = detect_market_phase(now)
    active_loop = get_active_loop_for_phase(phase)
    cadence_plan = get_cadence_plan_for_phase(phase)

    return AIOpsSummary(
        market_phase=phase,
        cadence_plan=cadence_plan,
        active_loop=active_loop,
        scan_mode=cadence_plan.scanner_depth,
        llm_validation_policy=cadence_plan.llm_validation_policy,
        live_trading_allowed=False,
        human_approval_required=True,
    )
