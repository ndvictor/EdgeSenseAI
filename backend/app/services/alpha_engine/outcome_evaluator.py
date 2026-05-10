from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

from app.services.alpha_engine.models import AlphaPredictionOutcome, AlphaRecommendation


class PricePathOrExit(BaseModel):
    """Observed prices after recommendation time (no broker or LLM involvement)."""

    exit_price: float | None = None
    price_path: list[float] | None = None


def compute_prediction_error(predicted_return_r: float | None, actual_return_r: float | None) -> float | None:
    if predicted_return_r is None or actual_return_r is None:
        return None
    return float(actual_return_r) - float(predicted_return_r)


def _iso_evaluated_at() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _coerce_inputs(price_path_or_exit: PricePathOrExit | dict[str, Any]) -> PricePathOrExit:
    if isinstance(price_path_or_exit, PricePathOrExit):
        return price_path_or_exit
    return PricePathOrExit.model_validate(price_path_or_exit)


def evaluate_prediction_outcome(
    recommendation: AlphaRecommendation,
    price_path_or_exit: PricePathOrExit | dict[str, Any],
) -> AlphaPredictionOutcome:
    """
    Compare prediction fields on a recommendation to realized exit and/or an intraday price path.
    Assumes long bias consistent with Alpha entry plans (entry/stop/target).
    """
    px = _coerce_inputs(price_path_or_exit)
    entry = recommendation.entry_plan.entry
    stop = recommendation.entry_plan.stop
    target = recommendation.entry_plan.target
    risk = recommendation.entry_plan.risk_per_share

    actual_return_pct: float | None = None
    actual_return_r: float | None = None
    mfe_r: float | None = None
    mae_r: float | None = None
    hit_target = False
    hit_stop = False

    path = list(px.price_path) if px.price_path else []
    exit_p = px.exit_price

    if entry is not None and risk is not None and float(risk) > 0:
        entry_f = float(entry)
        risk_f = float(risk)
        if path:
            highs = [(float(p) - entry_f) / risk_f for p in path]
            lows = [(entry_f - float(p)) / risk_f for p in path]
            mfe_r = max(highs) if highs else None
            mae_r = max(lows) if lows else None
        if path and target is not None:
            tf = float(target)
            hit_target = any(float(p) >= tf for p in path)
        if path and stop is not None:
            sf = float(stop)
            hit_stop = any(float(p) <= sf for p in path)

        if exit_p is not None:
            exit_f = float(exit_p)
            actual_return_r = (exit_f - entry_f) / risk_f
            if entry_f != 0:
                actual_return_pct = (exit_f - entry_f) / entry_f * 100.0

    pred_r = recommendation.predicted_return_r
    err_r = compute_prediction_error(pred_r, actual_return_r)

    return AlphaPredictionOutcome(
        recommendation_id=recommendation.recommendation_id,
        symbol=recommendation.symbol,
        strategy_key=recommendation.strategy_key,
        prediction_model_key=recommendation.prediction_model_key,
        predicted_return_pct=recommendation.predicted_return_pct,
        predicted_return_r=recommendation.predicted_return_r,
        predicted_win_probability=recommendation.predicted_win_probability,
        predicted_expected_value_r=recommendation.predicted_expected_value_r,
        prediction_horizon_minutes=recommendation.prediction_horizon_minutes,
        entry_price=entry,
        stop_price=stop,
        target_price=target,
        actual_return_pct=actual_return_pct,
        actual_return_r=actual_return_r,
        max_favorable_excursion_r=mfe_r,
        max_adverse_excursion_r=mae_r,
        hit_target=hit_target,
        hit_stop=hit_stop,
        prediction_error_r=err_r,
        evaluated_at=_iso_evaluated_at(),
    )
