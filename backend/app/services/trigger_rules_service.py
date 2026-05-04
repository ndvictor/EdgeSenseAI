"""Trigger Rules + Watchlist TTL Service.

Generates deterministic trigger rules and expiration windows for
universe-selected watchlist candidates.

NO buy/sell recommendations. Only monitoring trigger rules.
NO LLM.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.persistence_service import (
    get_latest_trigger_rule_run,
    list_trigger_rule_runs,
    save_trigger_rule_run,
)
from app.services.universe_selection_service import (
    UniverseSelectionCandidate,
    get_latest_universe_selection,
)


class TriggerRule(BaseModel):
    """A deterministic trigger rule for monitoring a symbol."""

    model_config = ConfigDict(protected_namespaces=())

    rule_id: str
    symbol: str
    asset_class: Literal["stock", "option", "crypto"]
    horizon: Literal["day_trade", "swing", "one_month"]
    strategy_key: str | None = None
    trigger_type: str
    trigger_condition: str
    validation_condition: str
    invalidation_condition: str
    ttl_minutes: int = Field(..., ge=15, le=1440)  # 15 min to 24 hours
    scan_interval_seconds: int = Field(..., ge=30, le=3600)  # 30 sec to 1 hour
    cooldown_minutes: int = Field(default=15, ge=5, le=120)
    priority_score: int = Field(..., ge=0, le=100)
    expires_at: str
    status: Literal["active", "expired", "disabled", "triggered"]
    reasons: list[str] = Field(default_factory=list)
    created_from: str  # "universe_selection", "manual", "upper_workflow"
    source_run_id: str | None = None


class TriggerRuleBuildRequest(BaseModel):
    """Request to build trigger rules from candidates."""

    model_config = ConfigDict(protected_namespaces=())

    candidates: list[UniverseSelectionCandidate] = Field(default_factory=list)
    symbols: list[str] = Field(default_factory=list)
    use_latest_watchlist: bool = True
    strategy_key: str | None = None
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    market_phase: str | None = None
    active_loop: str | None = None
    cadence_plan: dict[str, Any] | None = None
    source_run_id: str | None = None


class TriggerRuleBuildResponse(BaseModel):
    """Response with generated trigger rules."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "no_candidates", "failed"]
    rules: list[TriggerRule] = Field(default_factory=list)
    active_rules: list[str] = Field(default_factory=list)
    expired_rules: list[str] = Field(default_factory=list)
    total_rules: int = 0
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str


# In-memory storage
_LATEST_TRIGGER_RULES: TriggerRuleBuildResponse | None = None
_TRIGGER_RULES_HISTORY: list[TriggerRuleBuildResponse] = []
_ACTIVE_RULES: dict[str, TriggerRule] = {}  # rule_id -> rule


def _trigger_response_from_record(row: dict) -> TriggerRuleBuildResponse | None:
    try:
        rules = row.get("rules") or []
        created_at = row.get("created_at")
        return TriggerRuleBuildResponse.model_validate({
            "run_id": row.get("run_id"),
            "status": row.get("status"),
            "rules": rules,
            "active_rules": [rule.get("rule_id") for rule in rules if isinstance(rule, dict) and rule.get("status") == "active"],
            "expired_rules": [rule.get("rule_id") for rule in rules if isinstance(rule, dict) and rule.get("status") == "expired"],
            "total_rules": len(rules),
            "blockers": row.get("blockers") or [],
            "warnings": row.get("warnings") or [],
            "created_at": created_at.isoformat() if hasattr(created_at, "isoformat") else created_at,
        })
    except Exception:
        return None


# Baseline rule templates by strategy family
RULE_TEMPLATES: dict[str, dict[str, Any]] = {
    "stock_swing": {
        "trigger_type": "trend_continuation",
        "trigger_condition": "Price holds above 20 EMA with volume above 20-day average AND no distribution signals",
        "validation_condition": "RVOL > 1.2 AND bid-ask spread < 0.3% AND data freshness pass",
        "invalidation_condition": "Close below 20 EMA on volume OR data freshness failure OR RVOL < 0.8",
        "ttl_minutes": 240,  # 4 hours
        "scan_interval_seconds": 300,  # 5 min
        "cooldown_minutes": 30,
    },
    "stock_day_trading": {
        "trigger_type": "vwap_reclaim",
        "trigger_condition": "Price reclaims VWAP with RVOL > 1.5 AND cumulative delta positive for 3 consecutive bars",
        "validation_condition": "Spread < 0.2% AND liquidity score > 60 AND no opening range violation",
        "invalidation_condition": "Loss of VWAP for 2 consecutive bars OR spread > 0.5% OR liquidity score < 40",
        "ttl_minutes": 60,  # 1 hour
        "scan_interval_seconds": 60,  # 1 min
        "cooldown_minutes": 15,
    },
    "crypto_intraday": {
        "trigger_type": "momentum_continuation",
        "trigger_condition": "Higher highs + higher lows on 15m with volume expansion AND volatility within 30-day range",
        "validation_condition": "RVOL > 1.3 AND funding rate neutral AND no liquidation cascade alerts",
        "invalidation_condition": "Break of 15m higher low OR RVOL < 0.9 OR volatility spike > 2 sigma",
        "ttl_minutes": 120,  # 2 hours
        "scan_interval_seconds": 120,  # 2 min
        "cooldown_minutes": 20,
    },
    "options_swing": {
        "trigger_type": "underlying_confirmation",
        "trigger_condition": "Underlying shows trend continuation with IV percentile < 70 AND volume confirmation",
        "validation_condition": "Options spread < 5% AND open interest > 100 contracts AND delta 0.40-0.60",
        "invalidation_condition": "IV expansion > 10% OR underlying trend break OR options liquidity dry-up",
        "ttl_minutes": 180,  # 3 hours
        "scan_interval_seconds": 300,  # 5 min
        "cooldown_minutes": 45,
    },
}


def _get_strategy_family(strategy_key: str | None) -> str:
    """Map strategy key to strategy family for rule templates."""
    if not strategy_key:
        return "stock_swing"

    strategy_key_lower = strategy_key.lower()
    if "day" in strategy_key_lower or "intraday" in strategy_key_lower:
        if "crypto" in strategy_key_lower:
            return "crypto_intraday"
        return "stock_day_trading"
    elif "option" in strategy_key_lower:
        return "options_swing"
    elif "crypto" in strategy_key_lower:
        return "crypto_intraday"
    else:
        return "stock_swing"


def _calculate_ttl(
    horizon: Literal["day_trade", "swing", "one_month"],
    market_phase: str | None,
    priority_score: int,
) -> int:
    """Calculate TTL in minutes based on horizon and market conditions."""
    base_ttl = {
        "day_trade": 60,  # 1 hour
        "swing": 240,  # 4 hours
        "one_month": 720,  # 12 hours
    }.get(horizon, 240)

    # Adjust for market phase
    if market_phase:
        if "market_open_first_30_min" in market_phase:
            base_ttl = min(base_ttl, 90)  # Shorter during open
        elif "power_hour" in market_phase:
            base_ttl = min(base_ttl, 120)  # Shorter during power hour
        elif "market_closed" in market_phase:
            base_ttl = 30  # Very short when closed

    # Adjust for priority
    if priority_score >= 80:
        base_ttl = int(base_ttl * 1.2)  # 20% longer for high priority
    elif priority_score < 40:
        base_ttl = int(base_ttl * 0.7)  # 30% shorter for low priority

    return max(15, min(base_ttl, 1440))  # Clamp 15 min to 24 hours


def _calculate_scan_interval(
    horizon: Literal["day_trade", "swing", "one_month"],
    priority_score: int,
) -> int:
    """Calculate scan interval in seconds."""
    base_interval = {
        "day_trade": 60,  # 1 min
        "swing": 300,  # 5 min
        "one_month": 900,  # 15 min
    }.get(horizon, 300)

    # Adjust for priority
    if priority_score >= 80:
        base_interval = max(30, int(base_interval * 0.6))  # 40% faster
    elif priority_score < 40:
        base_interval = int(base_interval * 1.5)  # 50% slower

    return max(30, min(base_interval, 3600))  # Clamp 30 sec to 1 hour


def _build_trigger_rule(
    candidate: UniverseSelectionCandidate,
    market_phase: str | None,
    source_run_id: str | None,
    created_at: datetime,
) -> TriggerRule:
    """Build a trigger rule from a universe selection candidate."""
    strategy_family = _get_strategy_family(candidate.strategy_key)
    template = RULE_TEMPLATES.get(strategy_family, RULE_TEMPLATES["stock_swing"])

    # Calculate dynamic values
    priority_score = candidate.priority_score
    ttl_minutes = _calculate_ttl(candidate.horizon, market_phase, priority_score)
    scan_interval = _calculate_scan_interval(candidate.horizon, priority_score)
    expires_at = (created_at + timedelta(minutes=ttl_minutes)).isoformat()

    # Build rule
    rule = TriggerRule(
        rule_id=f"rule-{uuid4().hex[:12]}",
        symbol=candidate.symbol,
        asset_class=candidate.asset_class,
        horizon=candidate.horizon,
        strategy_key=candidate.strategy_key,
        trigger_type=template["trigger_type"],
        trigger_condition=template["trigger_condition"],
        validation_condition=template["validation_condition"],
        invalidation_condition=template["invalidation_condition"],
        ttl_minutes=ttl_minutes,
        scan_interval_seconds=scan_interval,
        cooldown_minutes=template["cooldown_minutes"],
        priority_score=priority_score,
        expires_at=expires_at,
        status="active",
        reasons=[
            f"Generated from universe selection candidate (score: {candidate.universe_score:.1f})",
            f"Direction bias: {candidate.expected_direction}",
        ],
        created_from="universe_selection",
        source_run_id=source_run_id,
    )

    return rule


def _expire_old_rules() -> None:
    """Mark expired rules based on TTL."""
    now = datetime.now(timezone.utc)
    for rule_id, rule in list(_ACTIVE_RULES.items()):
        try:
            expires = datetime.fromisoformat(rule.expires_at.replace("Z", "+00:00"))
            if expires < now:
                rule.status = "expired"
                _ACTIVE_RULES.pop(rule_id, None)
        except (ValueError, TypeError):
            # Invalid date format, mark as expired
            rule.status = "expired"
            _ACTIVE_RULES.pop(rule_id, None)


def run_trigger_rule_build(
    request: TriggerRuleBuildRequest,
) -> TriggerRuleBuildResponse:
    """Build trigger rules from universe selection candidates.

    NO buy/sell recommendations. Only monitoring trigger rules with TTL.
    """
    global _LATEST_TRIGGER_RULES, _TRIGGER_RULES_HISTORY, _ACTIVE_RULES

    run_id = f"trig-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc)

    # Expire old rules first
    _expire_old_rules()

    rules: list[TriggerRule] = []
    blockers: list[str] = []
    warnings: list[str] = []
    status: Literal["completed", "partial", "no_candidates", "failed"] = "completed"

    # Get candidates to build rules for
    candidates: list[UniverseSelectionCandidate] = []

    if request.candidates:
        candidates = request.candidates
    elif request.symbols:
        # Create minimal candidates from symbols
        for symbol in request.symbols:
            candidates.append(
                UniverseSelectionCandidate(
                    symbol=symbol,
                    asset_class=request.strategy_key or "stock",
                    horizon=request.horizon,
                    universe_score=50.0,
                    priority_score=50,
                )
            )
    elif request.use_latest_watchlist:
        # Get from latest universe selection
        latest_universe = get_latest_universe_selection()
        if latest_universe and latest_universe.selected_watchlist:
            candidates = latest_universe.selected_watchlist
            warnings.append(f"Using {len(candidates)} symbols from latest universe selection watchlist")
        else:
            blockers.append("No latest universe selection watchlist available")
            status = "no_candidates"
    else:
        blockers.append("No candidates, symbols, or watchlist specified")
        status = "no_candidates"

    if not candidates and status != "no_candidates":
        blockers.append("No candidates available to build trigger rules")
        status = "no_candidates"

    # Build rules for candidates
    if candidates:
        for candidate in candidates:
            try:
                rule = _build_trigger_rule(
                    candidate=candidate,
                    market_phase=request.market_phase,
                    source_run_id=request.source_run_id,
                    created_at=created_at,
                )
                rules.append(rule)
                _ACTIVE_RULES[rule.rule_id] = rule
            except Exception as e:
                warnings.append(f"Failed to build rule for {candidate.symbol}: {str(e)}")

    if not rules and status != "no_candidates":
        status = "failed"
        blockers.append("Failed to build any trigger rules")
    elif rules and warnings:
        status = "partial"

    # Identify active vs expired
    active_ids = [r.rule_id for r in rules if r.status == "active"]
    expired_ids = [r.rule_id for r in rules if r.status == "expired"]

    response = TriggerRuleBuildResponse(
        run_id=run_id,
        status=status,
        rules=rules,
        active_rules=active_ids,
        expired_rules=expired_ids,
        total_rules=len(rules),
        blockers=blockers,
        warnings=warnings,
        created_at=created_at.isoformat(),
    )

    # Store in history
    _LATEST_TRIGGER_RULES = response
    _TRIGGER_RULES_HISTORY.append(response)
    save_trigger_rule_run(response)

    # Keep only last 100
    if len(_TRIGGER_RULES_HISTORY) > 100:
        _TRIGGER_RULES_HISTORY = _TRIGGER_RULES_HISTORY[-100:]

    return response


def get_latest_trigger_rules() -> TriggerRuleBuildResponse | None:
    """Get the most recent trigger rule build."""
    row = get_latest_trigger_rule_run()
    if row:
        restored = _trigger_response_from_record(row)
        if restored:
            return restored
    return _LATEST_TRIGGER_RULES


def list_trigger_rule_builds(limit: int = 20) -> list[TriggerRuleBuildResponse]:
    """List recent trigger rule builds."""
    rows = list_trigger_rule_runs(limit)
    restored = [_trigger_response_from_record(row) for row in rows]
    db_runs = [run for run in restored if run is not None]
    if db_runs:
        return db_runs
    return _TRIGGER_RULES_HISTORY[-limit:]


def get_active_trigger_rules() -> list[TriggerRule]:
    """Get currently active (non-expired) trigger rules."""
    _expire_old_rules()
    return [r for r in _ACTIVE_RULES.values() if r.status == "active"]


def expire_trigger_rule(rule_id: str) -> bool:
    """Manually expire a trigger rule."""
    if rule_id in _ACTIVE_RULES:
        _ACTIVE_RULES[rule_id].status = "expired"
        return True
    return False


def expire_all_trigger_rules() -> int:
    """Expire all active trigger rules. Returns count expired."""
    count = 0
    for rule in _ACTIVE_RULES.values():
        if rule.status == "active":
            rule.status = "expired"
            count += 1
    _ACTIVE_RULES.clear()
    return count
