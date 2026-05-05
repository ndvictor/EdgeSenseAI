"""Watchlist TTL rules for Universe Discovery.

Deterministic, safety-first:
- TTL shrinks during high-noise windows
- research_only never grants execution readiness
- degraded data never extends TTL for execution purposes
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MarketPhase = Literal[
    "pre_market",
    "market_open_first_30_min",
    "market_open",
    "midday",
    "power_hour",
    "after_hours",
    "market_closed",
]


@dataclass(frozen=True)
class TtlDecision:
    ttl_minutes: int
    reason: str


def _clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, int(x)))


def _base_ttl(scanner_group: str, market_phase: MarketPhase) -> tuple[int, int]:
    """Return (min,max) ttl minutes defaults."""
    g = scanner_group

    if g == "opening_range_breakout_group":
        if market_phase == "market_open_first_30_min":
            return (15, 30)
        if market_phase == "market_open":
            return (15, 45)
        if market_phase == "midday":
            return (0, 15)
        if market_phase == "power_hour":
            return (10, 30)
        return (0, 10)

    if g == "premarket_gap_momentum":
        if market_phase == "pre_market":
            return (60, 120)
        if market_phase == "market_open_first_30_min":
            return (15, 30)
        if market_phase == "market_open":
            return (10, 20)
        if market_phase == "midday":
            return (0, 10)
        if market_phase == "power_hour":
            return (0, 15)
        return (0, 10)

    if g == "high_rvol_momentum_group":
        if market_phase == "pre_market":
            return (60, 60)
        if market_phase == "market_open_first_30_min":
            return (15, 15)
        if market_phase == "market_open":
            return (10, 20)
        if market_phase == "midday":
            return (10, 10)
        if market_phase == "power_hour":
            return (15, 15)
        return (0, 10)

    if g == "vwap_reclaim_group":
        if market_phase == "market_open_first_30_min":
            return (10, 20)
        if market_phase == "market_open":
            return (20, 45)
        if market_phase == "midday":
            return (30, 60)
        if market_phase == "power_hour":
            return (15, 30)
        return (0, 15)

    if g == "breakout_retest_group":
        if market_phase == "pre_market":
            return (0, 0)  # research only default
        if market_phase == "market_open":
            return (60, 180)
        if market_phase == "midday":
            return (120, 240)
        if market_phase == "power_hour":
            return (30, 60)
        if market_phase in ("after_hours", "market_closed"):
            return (360, 1440)
        return (30, 90)

    if g == "relative_strength_rotation_group":
        # 1 trading day default
        return (360, 1440)

    if g == "mean_reversion_range_group":
        if market_phase == "market_open_first_30_min":
            return (0, 10)
        if market_phase == "market_open":
            return (15, 30)
        if market_phase == "midday":
            return (30, 90)
        if market_phase == "power_hour":
            return (15, 30)
        return (0, 15)

    if g == "etf_stock_lag_group":
        if market_phase == "market_open":
            return (15, 30)
        if market_phase == "midday":
            return (15, 45)
        if market_phase == "power_hour":
            return (10, 20)
        return (0, 15)

    if g == "earnings_news_drift_group":
        return (360, 1440)

    if g == "low_float_breakout_group":
        if market_phase == "market_open_first_30_min":
            return (5, 10)
        if market_phase == "market_open":
            return (5, 15)
        if market_phase == "midday":
            return (5, 10)
        if market_phase == "power_hour":
            return (5, 10)
        return (0, 10)

    # Default fallback
    return (30, 120)


def assign_watchlist_ttl_minutes(
    *,
    scanner_group: str,
    market_phase: MarketPhase,
    strategy_key: str,
    signal_strength: float,
    data_quality: str,
    risk_level: str,
    research_only: bool,
) -> TtlDecision:
    """Assign TTL minutes using group+phase defaults and modest adjustments.

    Adjustments:
    - high signal_strength can extend modestly, but never across phase boundaries meaningfully
    - degraded/mock/unavailable data should not extend TTL
    - research_only keeps TTL short (still can be watchlisted)
    """
    (mn, mx) = _base_ttl(scanner_group, market_phase)
    if mn == 0 and mx == 0:
        return TtlDecision(ttl_minutes=0, reason="Group/phase default expires immediately (research-only window)")

    # After-hours/closed: discovery can happen, execution readiness must be blocked elsewhere.
    base = int((mn + mx) / 2) if mx > mn else int(mn)

    # Research-only: keep short, but allow some watchlist persistence for study.
    if research_only:
        base = min(base, 15 if market_phase in ("market_open", "midday", "power_hour") else 60)

    # Data quality degraded: do not extend.
    dq = (data_quality or "").lower()
    if dq in ("mock", "degraded", "poor", "unavailable", "not_configured"):
        base = min(base, max(5, mn))

    # Signal strength: modest adjustment
    if signal_strength >= 85 and dq not in ("mock", "degraded", "poor", "unavailable", "not_configured"):
        base = int(base * 1.15)
    elif signal_strength <= 35:
        base = int(base * 0.75)

    # Risk level: clamp down if high risk
    rl = (risk_level or "").lower()
    if rl in ("high", "very_high", "extreme"):
        base = int(base * 0.75)

    ttl = _clamp_int(base, mn, mx if mx > 0 else max(mn, 15))
    return TtlDecision(ttl_minutes=ttl, reason=f"Base {mn}-{mx} for {scanner_group} in {market_phase} with adjustments")

