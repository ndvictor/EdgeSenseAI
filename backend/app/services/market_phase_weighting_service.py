"""Market-phase weighted scoring for Universe Discovery.

Implements Phase 1-style deterministic weighting for Phase 2 intake:
- No ML, no LLMs
- Weights vary by market phase
- Penalizes small-account risks, stale/degraded data, and research-only groups
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
class MarketPhaseWeights:
    signal_weight: float
    volume_weight: float
    liquidity_weight: float
    regime_weight: float
    timing_weight: float
    risk_weight: float
    data_quality_weight: float


DEFAULT_PHASE_WEIGHTS: dict[MarketPhase, MarketPhaseWeights] = {
    "pre_market": MarketPhaseWeights(
        signal_weight=0.15,
        volume_weight=0.25,
        liquidity_weight=0.15,
        regime_weight=0.10,
        timing_weight=0.20,
        risk_weight=0.10,
        data_quality_weight=0.05,
    ),
    "market_open_first_30_min": MarketPhaseWeights(
        signal_weight=0.25,
        volume_weight=0.25,
        liquidity_weight=0.15,
        regime_weight=0.10,
        timing_weight=0.15,
        risk_weight=0.05,
        data_quality_weight=0.05,
    ),
    "market_open": MarketPhaseWeights(
        signal_weight=0.25,
        volume_weight=0.15,
        liquidity_weight=0.15,
        regime_weight=0.15,
        timing_weight=0.10,
        risk_weight=0.10,
        data_quality_weight=0.10,
    ),
    "midday": MarketPhaseWeights(
        signal_weight=0.15,
        volume_weight=0.10,
        liquidity_weight=0.15,
        regime_weight=0.20,
        timing_weight=0.10,
        risk_weight=0.15,
        data_quality_weight=0.15,
    ),
    "power_hour": MarketPhaseWeights(
        signal_weight=0.25,
        volume_weight=0.15,
        liquidity_weight=0.10,
        regime_weight=0.15,
        timing_weight=0.20,
        risk_weight=0.10,
        data_quality_weight=0.05,
    ),
    "after_hours": MarketPhaseWeights(
        signal_weight=0.10,
        volume_weight=0.10,
        liquidity_weight=0.10,
        regime_weight=0.20,
        timing_weight=0.10,
        risk_weight=0.20,
        data_quality_weight=0.20,
    ),
    "market_closed": MarketPhaseWeights(
        signal_weight=0.05,
        volume_weight=0.05,
        liquidity_weight=0.10,
        regime_weight=0.25,
        timing_weight=0.05,
        risk_weight=0.25,
        data_quality_weight=0.25,
    ),
}


def get_phase_weights(phase: MarketPhase) -> MarketPhaseWeights:
    return DEFAULT_PHASE_WEIGHTS.get(phase, DEFAULT_PHASE_WEIGHTS["market_closed"])


def clamp01(x: float) -> float:
    if x < 0:
        return 0.0
    if x > 1:
        return 1.0
    return x


def clamp100(x: float) -> float:
    if x < 0:
        return 0.0
    if x > 100:
        return 100.0
    return x


class MarketPhaseUniverseScorer:
    """Phase-aware scoring for universe discovery candidates.

    All component scores should be in [0, 100].
    """

    def __init__(self, market_phase: MarketPhase):
        self.market_phase = market_phase
        self.weights = get_phase_weights(market_phase)

    def score(
        self,
        *,
        signal_strength: float,
        volume_score: float,
        liquidity_score: float,
        regime_fit: float,
        timing_fit: float,
        risk_fit: float,
        data_quality_score: float,
        spread_penalty: float = 0.0,
        stale_signal_penalty: float = 0.0,
        small_account_penalty: float = 0.0,
        research_only_penalty: float = 0.0,
    ) -> float:
        w = self.weights
        base = (
            w.signal_weight * clamp100(signal_strength)
            + w.volume_weight * clamp100(volume_score)
            + w.liquidity_weight * clamp100(liquidity_score)
            + w.regime_weight * clamp100(regime_fit)
            + w.timing_weight * clamp100(timing_fit)
            + w.risk_weight * clamp100(risk_fit)
            + w.data_quality_weight * clamp100(data_quality_score)
        )
        penalties = (
            clamp100(spread_penalty)
            + clamp100(stale_signal_penalty)
            + clamp100(small_account_penalty)
            + clamp100(research_only_penalty)
        )
        return round(clamp100(base - penalties), 2)

