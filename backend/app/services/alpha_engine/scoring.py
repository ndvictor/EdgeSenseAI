from __future__ import annotations

import math
from typing import Any

from app.services.alpha_engine.models import AlphaEntryPlan, CandidateFeatureRow


def clamp_score(value: float | None, default: float = 0.0) -> float:
    if value is None:
        value = default
    try:
        return round(max(0.0, min(100.0, float(value))), 2)
    except (TypeError, ValueError):
        return round(max(0.0, min(100.0, float(default))), 2)


def _interpolate(x: float, x0: float, y0: float, x1: float, y1: float) -> float:
    if x1 == x0:
        return y1
    return y0 + (x - x0) * (y1 - y0) / (x1 - x0)


def score_relative_volume(relative_volume: float | None) -> float:
    if relative_volume is None:
        return 0.0
    rv = float(relative_volume)
    if rv <= 1.0:
        return clamp_score(_interpolate(rv, 0.0, 0.0, 1.0, 30.0))
    if rv <= 1.5:
        return clamp_score(_interpolate(rv, 1.0, 30.0, 1.5, 55.0))
    if rv <= 2.0:
        return clamp_score(_interpolate(rv, 1.5, 55.0, 2.0, 75.0))
    if rv <= 3.0:
        return clamp_score(_interpolate(rv, 2.0, 75.0, 3.0, 100.0))
    return 100.0


def score_spread(spread_bps: float | None, max_spread_bps: float = 20) -> float:
    if spread_bps is None:
        return 0.0
    spread = max(0.0, float(spread_bps))
    max_spread = max(0.01, float(max_spread_bps))
    if spread <= max_spread:
        return clamp_score(_interpolate(spread, 0.0, 100.0, max_spread, 50.0))
    if spread >= max_spread * 2:
        return 0.0
    return clamp_score(_interpolate(spread, max_spread, 25.0, max_spread * 2, 0.0))


def score_liquidity(row: CandidateFeatureRow) -> float:
    if row.liquidity_score is not None:
        return clamp_score(row.liquidity_score)
    if row.volume is None or row.avg_volume is None or row.avg_volume <= 0:
        return 0.0
    volume_ratio = max(0.0, float(row.volume) / float(row.avg_volume))
    return clamp_score(volume_ratio * 25.0)


def score_trend(row: CandidateFeatureRow) -> float:
    if row.trend_score is not None:
        return clamp_score(row.trend_score)
    if row.day_change_pct is None:
        return 0.0
    score = 45.0 + max(-30.0, min(35.0, float(row.day_change_pct) * 5.0))
    if row.price_above_vwap is True:
        score += 15.0
    elif row.price_above_vwap is False:
        score -= 15.0
    return clamp_score(score)


def score_small_account_fit(row: CandidateFeatureRow, account_equity: float = 1000, max_price: float = 75) -> tuple[float, list[str]]:
    warnings: list[str] = []
    if row.last_price is None:
        return 0.0, warnings
    price = float(row.last_price)
    spread = float(row.spread_bps or 0)
    if price < 2 or spread > 20:
        return 0.0, warnings
    score = 100.0
    if price > max_price:
        score -= 30.0
        warnings.append("high_price_reduces_flexibility")
    score -= min(30.0, max(0.0, spread - 5.0) * 1.5)
    if account_equity <= 1000 and price > 50:
        score -= 15.0
    return clamp_score(score), warnings


def estimate_entry_plan(row: CandidateFeatureRow, playbook: dict[str, Any], max_risk_dollars: float = 5.0) -> AlphaEntryPlan:
    if row.last_price is None:
        return AlphaEntryPlan(notes=["last_price_missing_no_entry_plan"])
    entry = float(row.last_price)
    if row.vwap is not None and row.price_above_vwap:
        stop = min(float(row.vwap), entry * 0.985)
    else:
        stop = entry * 0.985
    risk_per_share = max(entry - stop, entry * 0.005)
    target_r = float(playbook.get("target_r") or 1.5)
    target = entry + target_r * risk_per_share
    position_size = math.floor(float(max_risk_dollars) / risk_per_share) if risk_per_share > 0 else None
    notes: list[str] = []
    if position_size is not None and position_size <= 0:
        notes.append("position_size_estimate_zero_for_risk_limit")
    return AlphaEntryPlan(
        entry=round(entry, 4),
        stop=round(stop, 4),
        target=round(target, 4),
        risk_per_share=round(risk_per_share, 4),
        risk_dollars=round(float(max_risk_dollars), 2),
        expected_r=target_r,
        position_size_estimate=position_size,
        plan_type=str(playbook.get("setup_type") or ""),
        notes=notes,
    )


def compute_final_score(component_scores: dict[str, float]) -> float:
    score = (
        0.25 * component_scores.get("liquidity_score", 0.0)
        + 0.20 * component_scores.get("relative_volume_score", 0.0)
        + 0.15 * component_scores.get("trend_score", 0.0)
        + 0.15 * component_scores.get("strategy_fit_score", 0.0)
        + 0.10 * component_scores.get("spread_score", 0.0)
        + 0.10 * component_scores.get("evidence_score", 0.0)
        + 0.05 * component_scores.get("model_score", 0.0)
    )
    return clamp_score(score)
