from __future__ import annotations

from datetime import datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field

from app.services.auto_run_control_service import get_auto_run_state

MarketPhase = Literal[
    "market_closed",
    "pre_market",
    "market_open_first_30_min",
    "market_open",
    "midday",
    "power_hour",
    "after_hours",
]

ActiveLoop = Literal[
    "research_backtest_loop",
    "pre_market_planning_loop",
    "fast_scanning_loop",
    "selective_monitoring_loop",
    "power_hour_review_loop",
    "after_hours_learning_loop",
]


class MarketPhaseStatus(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    market_phase: MarketPhase
    active_loop: ActiveLoop
    timezone: str
    local_time: str
    is_regular_session: bool
    is_market_day: bool
    next_transition_hint: str
    data_source: str = "deterministic_clock"


class CadencePlan(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    market_phase: MarketPhase
    active_loop: ActiveLoop
    scan_mode: str
    top_watchlist_scan_seconds: int
    secondary_watchlist_scan_seconds: int
    strategy_refresh_minutes: int
    regime_refresh_minutes: int
    watchlist_ttl_minutes: int
    cooldown_if_failed_minutes: int
    llm_validation_policy: str
    llm_budget_mode: str
    research_jobs_enabled: bool
    live_trading_allowed: bool
    paper_trading_allowed: bool
    human_approval_required: bool
    notes: list[str] = Field(default_factory=list)
    data_source: str = "deterministic_cadence_policy"


class CadenceSimulationRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    market_phase: MarketPhase | None = None
    account_size: float | None = None
    buying_power: float | None = None
    risk_mode: str | None = None
    volatility_state: str | None = None
    strategy_key: str | None = None


def _now_local(now: datetime | None = None) -> datetime:
    if now is None:
        return datetime.now(ZoneInfo("America/New_York"))
    if now.tzinfo is None:
        return now.replace(tzinfo=ZoneInfo("America/New_York"))
    return now.astimezone(ZoneInfo("America/New_York"))


def _is_market_day(local_now: datetime) -> bool:
    return local_now.weekday() < 5


def detect_market_phase(now: datetime | None = None) -> MarketPhaseStatus:
    local_now = _now_local(now)
    is_market_day = _is_market_day(local_now)
    current = local_now.time()

    phase: MarketPhase
    loop: ActiveLoop
    is_regular_session = False
    hint = "Research and preparation mode."

    if not is_market_day:
        phase = "market_closed"
        loop = "research_backtest_loop"
        hint = "Next weekday pre-market planning loop."
    elif time(4, 0) <= current < time(9, 30):
        phase = "pre_market"
        loop = "pre_market_planning_loop"
        hint = "Regular session begins at 09:30 ET."
    elif time(9, 30) <= current < time(10, 0):
        phase = "market_open_first_30_min"
        loop = "fast_scanning_loop"
        is_regular_session = True
        hint = "First 30 minutes favors higher cadence and stricter filters."
    elif time(10, 0) <= current < time(11, 30):
        phase = "market_open"
        loop = "fast_scanning_loop"
        is_regular_session = True
        hint = "Continue active scanning for watchlist triggers."
    elif time(11, 30) <= current < time(15, 0):
        phase = "midday"
        loop = "selective_monitoring_loop"
        is_regular_session = True
        hint = "Reduce noise, prune stale watchlist items, and lower cadence."
    elif time(15, 0) <= current < time(16, 0):
        phase = "power_hour"
        loop = "power_hour_review_loop"
        is_regular_session = True
        hint = "Review active setups, timeouts, and rotation rules."
    elif time(16, 0) <= current < time(20, 0):
        phase = "after_hours"
        loop = "after_hours_learning_loop"
        hint = "Journal, label outcomes, and plan research/backtests."
    else:
        phase = "market_closed"
        loop = "research_backtest_loop"
        hint = "Market closed. Run research, model evaluation, and planning jobs."

    return MarketPhaseStatus(
        market_phase=phase,
        active_loop=loop,
        timezone="America/New_York",
        local_time=local_now.isoformat(),
        is_regular_session=is_regular_session,
        is_market_day=is_market_day,
        next_transition_hint=hint,
    )


def build_cadence_plan(market_phase: MarketPhase | None = None, context: dict[str, Any] | None = None) -> CadencePlan:
    phase_status = detect_market_phase()
    phase = market_phase or phase_status.market_phase
    auto_run = get_auto_run_state()
    context = context or {}
    volatility_state = str(context.get("volatility_state") or "normal")

    defaults: dict[MarketPhase, dict[str, Any]] = {
        "market_closed": {
            "active_loop": "research_backtest_loop",
            "scan_mode": "disabled_research_only",
            "top": 300,
            "secondary": 900,
            "strategy": 60,
            "regime": 60,
            "ttl": 1440,
            "cooldown": 60,
            "llm_policy": "research_summaries_only",
            "budget": "low",
            "research": True,
        },
        "pre_market": {
            "active_loop": "pre_market_planning_loop",
            "scan_mode": "planning_watchlist_build",
            "top": 60,
            "secondary": 180,
            "strategy": 15,
            "regime": 10,
            "ttl": 180,
            "cooldown": 30,
            "llm_policy": "only_for_strategy_debate_or_conflict",
            "budget": "medium",
            "research": False,
        },
        "market_open_first_30_min": {
            "active_loop": "fast_scanning_loop",
            "scan_mode": "high_cadence_strict_filters",
            "top": 5,
            "secondary": 30,
            "strategy": 5,
            "regime": 3,
            "ttl": 45,
            "cooldown": 15,
            "llm_policy": "only_if_meta_score_above_threshold",
            "budget": "controlled_medium",
            "research": False,
        },
        "market_open": {
            "active_loop": "fast_scanning_loop",
            "scan_mode": "active_watchlist_trigger_scan",
            "top": 15,
            "secondary": 60,
            "strategy": 10,
            "regime": 5,
            "ttl": 60,
            "cooldown": 15,
            "llm_policy": "only_after_trigger_and_risk_precheck",
            "budget": "controlled_medium",
            "research": False,
        },
        "midday": {
            "active_loop": "selective_monitoring_loop",
            "scan_mode": "lower_cadence_prune_noise",
            "top": 60,
            "secondary": 300,
            "strategy": 15,
            "regime": 10,
            "ttl": 45,
            "cooldown": 30,
            "llm_policy": "avoid_unless_high_score_conflict",
            "budget": "low",
            "research": False,
        },
        "power_hour": {
            "active_loop": "power_hour_review_loop",
            "scan_mode": "active_setup_review_and_rotation",
            "top": 15,
            "secondary": 60,
            "strategy": 10,
            "regime": 5,
            "ttl": 45,
            "cooldown": 15,
            "llm_policy": "only_for_validated_high_priority_setups",
            "budget": "controlled_medium",
            "research": False,
        },
        "after_hours": {
            "active_loop": "after_hours_learning_loop",
            "scan_mode": "disabled_learning_only",
            "top": 300,
            "secondary": 900,
            "strategy": 60,
            "regime": 60,
            "ttl": 1440,
            "cooldown": 60,
            "llm_policy": "journal_and_research_summaries",
            "budget": "low",
            "research": True,
        },
    }
    config = defaults[phase]

    top_scan = int(config["top"])
    secondary_scan = int(config["secondary"])
    notes = [
        "Cadence is deterministic and paper/research-only.",
        "LLMs are gated and should not scan the whole market.",
        "Risk and approval controls remain authoritative.",
    ]
    if volatility_state in {"high", "elevated", "panic"} and phase in {"market_open_first_30_min", "market_open", "power_hour"}:
        top_scan = max(top_scan, 10)
        secondary_scan = max(secondary_scan, 60)
        notes.append("Elevated volatility detected: cadence is not increased below safety minimums.")

    return CadencePlan(
        market_phase=phase,
        active_loop=config["active_loop"],
        scan_mode=config["scan_mode"],
        top_watchlist_scan_seconds=top_scan,
        secondary_watchlist_scan_seconds=secondary_scan,
        strategy_refresh_minutes=int(config["strategy"]),
        regime_refresh_minutes=int(config["regime"]),
        watchlist_ttl_minutes=int(config["ttl"]),
        cooldown_if_failed_minutes=int(config["cooldown"]),
        llm_validation_policy=config["llm_policy"],
        llm_budget_mode=config["budget"],
        research_jobs_enabled=bool(config["research"]),
        live_trading_allowed=False,
        paper_trading_allowed=auto_run.paper_trading_enabled,
        human_approval_required=auto_run.require_human_approval,
        notes=notes,
    )


def simulate_cadence_plan(request: CadenceSimulationRequest) -> CadencePlan:
    return build_cadence_plan(
        market_phase=request.market_phase,
        context={
            "account_size": request.account_size,
            "buying_power": request.buying_power,
            "risk_mode": request.risk_mode,
            "volatility_state": request.volatility_state,
            "strategy_key": request.strategy_key,
        },
    )
