"""Universe Discovery Engine (stocks) - opportunity intake layer.

Runs BEFORE Candidate Universe:
- Produces watchlist candidates mapped to strategy keys + trigger rules + TTL
- Does NOT enable execution (execution_allowed is false by default)
- Keeps manual symbol input (explicit symbols only)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.services.candidate_universe_service import add_candidate
from app.services.data_freshness_gate_service import DataFreshnessCheckRequest, run_data_freshness_check
from app.services.market_data_service import MarketDataService
from app.services.market_phase_weighting_service import MarketPhaseUniverseScorer
from app.services.timing_cadence_service import MarketPhase, detect_market_phase
from app.services.watchlist_ttl_service import assign_watchlist_ttl_minutes


DiscoveryMarketPhase = Literal[
    "pre_market",
    "market_open_first_30_min",
    "market_open",
    "midday",
    "power_hour",
    "after_hours",
    "market_closed",
]


class UniverseDiscoverRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbols: list[str] = Field(default_factory=list)
    asset_class: Literal["stock", "option", "crypto"] = "stock"
    horizon: Literal["day_trade", "swing", "one_month"] = "swing"
    market_phase: Literal["auto"] | DiscoveryMarketPhase = "auto"
    scanner_groups: list[str] = Field(default_factory=list)
    source: Literal["auto", "yfinance", "alpaca", "polygon", "mock"] = "auto"
    allow_mock: bool = False
    small_account_mode: bool = True
    promote_to_candidate_universe: bool = False


class UniverseDiscoveryCandidate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str
    strategy_key: str
    scanner_group: str
    universe_score: float = Field(..., ge=0, le=100)
    market_phase: str
    expected_direction: Literal["long", "short", "neutral"] = "neutral"
    watchlist_ttl_minutes: int = 0
    trigger_condition: str = ""
    invalidation_condition: str = ""
    reasons: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_quality: str = "unknown"
    execution_allowed: Literal[False] = False
    research_only: bool = False

    # Useful diagnostics
    signal_strength: float = Field(default=50, ge=0, le=100)
    volume_score: float = Field(default=50, ge=0, le=100)
    liquidity_score: float = Field(default=50, ge=0, le=100)
    timing_fit: float = Field(default=50, ge=0, le=100)
    risk_fit: float = Field(default=50, ge=0, le=100)
    data_quality_score: float = Field(default=50, ge=0, le=100)
    spread_percent: float | None = None


class UniverseDiscoverResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["completed", "partial", "blocked"]
    market_phase: str
    scanner_groups_run: list[str]
    selected_watchlist: list[UniverseDiscoveryCandidate]
    rejected_candidates: list[UniverseDiscoveryCandidate]
    research_only_candidates: list[UniverseDiscoveryCandidate]
    blockers: list[str]
    warnings: list[str]
    created_at: str


_MARKET_DATA = MarketDataService()


def _phase_from_request(market_phase: Literal["auto"] | DiscoveryMarketPhase) -> DiscoveryMarketPhase:
    if market_phase != "auto":
        return market_phase
    phase = detect_market_phase()
    # Enum -> str
    return str(phase.value)  # type: ignore[return-value]


def _normalize_groups(groups: list[str]) -> list[str]:
    if not groups:
        # Default: safe, common intraday groups (no low-float)
        return [
            "opening_range_breakout_group",
            "high_rvol_momentum_group",
            "vwap_reclaim_group",
            "relative_strength_rotation_group",
            "mean_reversion_range_group",
            "etf_stock_lag_group",
            "earnings_news_drift_group",
        ]
    return [g.strip() for g in groups if g.strip()]


def _strategy_map_for_group(group: str) -> list[str]:
    mapping: dict[str, list[str]] = {
        "premarket_gap_momentum": ["gap_and_go", "high_rvol_momentum", "opening_range_breakout"],
        "opening_range_breakout_group": ["opening_range_breakout", "liquidity_filtered_momentum"],
        "high_rvol_momentum_group": ["high_rvol_momentum", "vwap_reclaim_momentum", "liquidity_filtered_momentum"],
        "vwap_reclaim_group": ["vwap_reclaim_momentum", "pullback_to_ema_vwap"],
        "breakout_retest_group": ["breakout_retest_continuation", "trend_following_pullback"],
        "relative_strength_rotation_group": ["relative_strength_rotation", "trend_following_pullback"],
        "mean_reversion_range_group": ["mean_reversion_range_fade", "support_resistance_fade", "bollinger_band_fade"],
        "etf_stock_lag_group": ["etf_stock_lag_arbitrage_lite", "relative_strength_rotation"],
        "earnings_news_drift_group": ["earnings_drift_long", "earnings_drift_short", "gap_and_go"],
        "low_float_breakout_group": ["low_float_breakout"],
    }
    return mapping.get(group, ["universe_watchlist"])


def _pick_strategy_key(group: str, horizon: str) -> str:
    # Pick a representative strategy key (front-end + downstream can refine later).
    keys = _strategy_map_for_group(group)
    # Prefer ORB in day_trade contexts
    if horizon == "day_trade" and "opening_range_breakout" in keys:
        return "opening_range_breakout"
    return keys[0]


def _data_quality_score_from_freshness(quality: str) -> float:
    q = (quality or "").lower()
    if q == "excellent":
        return 95.0
    if q == "good":
        return 80.0
    if q == "fair":
        return 60.0
    if q == "poor":
        return 35.0
    if q in ("unavailable", "not_configured"):
        return 0.0
    if q == "mock":
        return 15.0
    return 50.0


def _build_trigger_and_invalidation(group: str) -> tuple[str, str]:
    if group == "premarket_gap_momentum":
        return (
            "Break premarket high/low with RVOL confirmation; or ORH break and hold after open",
            "Loses VWAP; volume fades; spread too wide; TTL expires without trigger",
        )
    if group == "opening_range_breakout_group":
        return (
            "Break above opening range high with RVOL, above VWAP, spread acceptable",
            "Fails breakout (falls back into range); loses VWAP; TTL expires",
        )
    if group == "high_rvol_momentum_group":
        return (
            "RVOL above threshold with continuation; above VWAP; liquidity clean",
            "Momentum stalls; breaks VWAP; spread unknown/wide; TTL expires",
        )
    if group == "vwap_reclaim_group":
        return (
            "Reclaims VWAP and holds confirmation candle with RVOL support",
            "Rejects VWAP reclaim; loses VWAP; stop not definable; TTL expires",
        )
    if group == "breakout_retest_group":
        return (
            "Breakout level retest holds and resumes higher; reward/risk >= 2",
            "Breakout level fails; volume fails; R/R < 2; TTL expires",
        )
    if group == "relative_strength_rotation_group":
        return (
            "Relative strength rank >= 75 vs SPY/QQQ, trend intact, risk/reward acceptable",
            "Relative strength fades; trend breaks; sector weakens",
        )
    if group == "mean_reversion_range_group":
        return (
            "Overextension from VWAP into support/resistance with exhaustion signal; sideways regime",
            "Range breaks; trend accelerates against fade; spread not acceptable",
        )
    if group == "etf_stock_lag_group":
        return (
            "ETF moves first, stock confirms lag catch-up, correlation meaningful, liquidity clean",
            "Correlation breaks; lag fails; spread unknown; TTL expires",
        )
    if group == "earnings_news_drift_group":
        return (
            "News/earnings event exists, direction aligns with price/volume, RVOL confirms",
            "Event thesis invalidated; volume dries; price reverses through VWAP/level",
        )
    if group == "low_float_breakout_group":
        return (
            "Low float + extreme RVOL breakout (research only) with halt/spread warnings",
            "Any sign of halt risk / wide spreads; do not execute; TTL expires quickly",
        )
    return ("Trigger pending", "TTL expires")


def _small_account_penalty(*, small_account_mode: bool, has_bid_ask: bool, spread_percent: float | None, risk_level: str, research_only: bool) -> float:
    if not small_account_mode:
        return 0.0
    penalty = 0.0
    if not has_bid_ask or spread_percent is None:
        penalty += 12.0
    if spread_percent is not None and spread_percent > 0.8:
        penalty += 12.0
    if risk_level in ("high", "very_high", "extreme"):
        penalty += 10.0
    if research_only:
        penalty += 8.0
    return penalty


def discover_universe(request: UniverseDiscoverRequest) -> UniverseDiscoverResponse:
    run_id = f"ud-{uuid4().hex[:12]}"
    created_at = datetime.now(timezone.utc).isoformat()

    symbols = [s.strip().upper() for s in request.symbols if s and s.strip()]
    if not symbols:
        return UniverseDiscoverResponse(
            run_id=run_id,
            status="blocked",
            market_phase="market_closed",
            scanner_groups_run=[],
            selected_watchlist=[],
            rejected_candidates=[],
            research_only_candidates=[],
            blockers=["No symbols provided. Universe Discovery requires explicit symbols."],
            warnings=[],
            created_at=created_at,
        )

    phase = _phase_from_request(request.market_phase)
    groups = _normalize_groups(request.scanner_groups)

    blockers: list[str] = []
    warnings: list[str] = []

    # Data freshness gate: allow discovery even if degraded; but capture bid/ask + spread for execution block.
    freshness = run_data_freshness_check(
        DataFreshnessCheckRequest(
            symbols=symbols,
            asset_class=request.asset_class,
            source=request.source,
            require_bid_ask=False,
            allow_mock=request.allow_mock,
            market_phase=phase,
            horizon=request.horizon,
        )
    )
    freshness_by_symbol = {r.symbol: r for r in freshness.results}
    if freshness.status == "fail":
        warnings.append("Data freshness gate returned fail; discovery continues but execution will be blocked.")

    candidates: list[UniverseDiscoveryCandidate] = []

    for sym in symbols:
        fres = freshness_by_symbol.get(sym)
        if not fres:
            blockers.append(f"{sym}: No freshness result")
            continue

        # Snapshot for extra fields (optional).
        try:
            snapshot = _MARKET_DATA.get_market_snapshot(sym, source=request.source)
        except Exception as e:
            snapshot = {"symbol": sym, "data_quality": "unavailable", "provider": "unknown", "error": str(e)}

        is_mock = bool(snapshot.get("is_mock", False))
        dq = snapshot.get("data_quality") or fres.data_quality or "unavailable"
        data_quality_score = _data_quality_score_from_freshness(str(dq))

        bid = snapshot.get("bid")
        ask = snapshot.get("ask")
        has_bid_ask = bid is not None and ask is not None
        spread_percent = snapshot.get("spread_percent") or fres.spread_percent

        # Execution rules (always false for discovery output, but we keep blockers/warnings)
        execution_blockers: list[str] = []
        if is_mock:
            execution_blockers.append("Mock data cannot be used for execution.")
        if not has_bid_ask or spread_percent is None:
            execution_blockers.append("Bid/ask or spread unavailable; execution blocked.")

        # Simple deterministic component scores (placeholder; becomes richer as providers mature)
        # Use availability flags to set baselines.
        volume_score = 65.0 if fres.has_volume else 40.0
        liquidity_score = 70.0 if fres.has_price else 0.0
        timing_fit = 60.0 if phase in ("market_open_first_30_min", "market_open", "power_hour") else 50.0
        regime_fit = 50.0  # no regime model dependency for v1
        risk_fit = 55.0
        risk_level = "medium"

        if spread_percent is not None and spread_percent > 1.2:
            risk_fit = 35.0
            risk_level = "high"

        # Use change_percent / gap as proxy signal strength where available
        change_percent = snapshot.get("change_percent")
        if isinstance(change_percent, (int, float)):
            signal_strength = min(100.0, max(0.0, abs(float(change_percent)) * 12.5))  # 8% -> 100
        else:
            signal_strength = 55.0 if fres.has_price else 0.0

        for group in groups:
            research_only = group == "low_float_breakout_group"
            strategy_key = _pick_strategy_key(group, request.horizon)
            trigger, invalidation = _build_trigger_and_invalidation(group)

            # Phase-based scoring
            scorer = MarketPhaseUniverseScorer(phase)
            spread_penalty = 0.0
            if spread_percent is None:
                spread_penalty = 12.0
            elif spread_percent > 0.8:
                spread_penalty = 12.0
            elif spread_percent > 0.4:
                spread_penalty = 6.0

            stale_penalty = 0.0
            if fres.freshness_status == "stale":
                stale_penalty = 10.0

            research_only_penalty = 15.0 if research_only else 0.0
            small_penalty = _small_account_penalty(
                small_account_mode=request.small_account_mode,
                has_bid_ask=has_bid_ask,
                spread_percent=spread_percent,
                risk_level=risk_level,
                research_only=research_only,
            )

            universe_score = scorer.score(
                signal_strength=signal_strength,
                volume_score=volume_score,
                liquidity_score=liquidity_score,
                regime_fit=regime_fit,
                timing_fit=timing_fit,
                risk_fit=risk_fit,
                data_quality_score=data_quality_score,
                spread_penalty=spread_penalty,
                stale_signal_penalty=stale_penalty,
                small_account_penalty=small_penalty,
                research_only_penalty=research_only_penalty,
            )

            ttl_decision = assign_watchlist_ttl_minutes(
                scanner_group=group,
                market_phase=phase,
                strategy_key=strategy_key,
                signal_strength=signal_strength,
                data_quality=("mock" if is_mock else ("degraded" if not has_bid_ask or spread_percent is None else str(dq))),
                risk_level=risk_level,
                research_only=research_only,
            )

            c_blockers = list(execution_blockers)
            c_warnings: list[str] = []
            if freshness.status in ("warn", "fail"):
                c_warnings.append("Data freshness gate is not pass; treat as watch-only.")

            reasons = [
                f"group={group}",
                f"phase={phase}",
                ttl_decision.reason,
            ]
            if isinstance(change_percent, (int, float)):
                reasons.append(f"change_percent={float(change_percent):.2f}")

            candidates.append(
                UniverseDiscoveryCandidate(
                    symbol=sym,
                    strategy_key=strategy_key,
                    scanner_group=group,
                    universe_score=universe_score,
                    market_phase=phase,
                    expected_direction="long" if (change_percent or 0) > 0 else "short" if (change_percent or 0) < 0 else "neutral",
                    watchlist_ttl_minutes=ttl_decision.ttl_minutes,
                    trigger_condition=trigger,
                    invalidation_condition=invalidation,
                    reasons=reasons,
                    blockers=c_blockers,
                    warnings=c_warnings,
                    data_quality=str(dq),
                    execution_allowed=False,
                    research_only=research_only,
                    signal_strength=signal_strength,
                    volume_score=volume_score,
                    liquidity_score=liquidity_score,
                    timing_fit=timing_fit,
                    risk_fit=risk_fit,
                    data_quality_score=data_quality_score,
                    spread_percent=spread_percent,
                )
            )

    # Partition candidates
    research_only_candidates = [c for c in candidates if c.research_only]
    non_research = [c for c in candidates if not c.research_only]

    # Select watchlist: top N by score per group (simple v1). Rejected is the rest.
    selected: list[UniverseDiscoveryCandidate] = []
    rejected: list[UniverseDiscoveryCandidate] = []

    for group in groups:
        group_candidates = [c for c in non_research if c.scanner_group == group]
        group_candidates.sort(key=lambda c: c.universe_score, reverse=True)
        take = min(10, len(group_candidates))
        selected.extend(group_candidates[:take])
        rejected.extend(group_candidates[take:])

    selected.sort(key=lambda c: c.universe_score, reverse=True)
    rejected.sort(key=lambda c: c.universe_score, reverse=True)
    research_only_candidates.sort(key=lambda c: c.universe_score, reverse=True)

    # Promotion: only when explicitly enabled
    if request.promote_to_candidate_universe and selected:
        promoted = 0
        for c in selected:
            try:
                add_candidate(
                    symbol=c.symbol,
                    asset_class=request.asset_class,
                    horizon=request.horizon,
                    source_type="universe_discovery",
                    source_detail=f"{run_id}:{c.scanner_group}:{c.strategy_key}",
                    priority_score=float(c.universe_score),
                    notes="; ".join(c.reasons[:3]),
                )
                promoted += 1
            except Exception as e:
                warnings.append(f"Failed to promote {c.symbol}: {e}")
        warnings.append(f"Promoted {promoted} watchlist entries to Candidate Universe")

    status: Literal["completed", "partial", "blocked"] = "completed"
    if blockers and not selected and not research_only_candidates:
        status = "blocked"
    elif blockers:
        status = "partial"

    return UniverseDiscoverResponse(
        run_id=run_id,
        status=status,
        market_phase=phase,
        scanner_groups_run=groups,
        selected_watchlist=selected,
        rejected_candidates=rejected,
        research_only_candidates=research_only_candidates,
        blockers=blockers,
        warnings=warnings,
        created_at=created_at,
    )

