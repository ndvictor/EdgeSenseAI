from __future__ import annotations

import inspect

import pytest

from app.services.alpha_engine import (
    AlphaEngineRequest,
    AlphaRecommendation,
    CandidateFeatureRow,
    PricePathOrExit,
    compute_prediction_error,
    evaluate_prediction_outcome,
    generate_alpha_recommendation,
)
from app.services.alpha_engine.models import AlphaEntryPlan
from app.services.alpha_engine.recommendation_service import (
    _clamp_heuristic_win_probability,
    _heuristic_win_probability,
    _prediction_attachment,
)


def _base_candidate(**overrides):
    data = {
        "symbol": "TESTX",
        "last_price": 10.0,
        "volume": 5_000_000,
        "avg_volume": 1_000_000,
        "relative_volume": 5.0,
        "day_change_pct": 8.0,
        "spread_bps": 8.0,
        "vwap": 9.7,
        "price_above_vwap": True,
        "premarket_high": 10.2,
        "trend_score": 80.0,
        "liquidity_score": 85.0,
        "session_state": "regular",
        "source": "provider",
    }
    data.update(overrides)
    return CandidateFeatureRow(**data)


def _recommend(candidate: CandidateFeatureRow, **overrides):
    request = AlphaEngineRequest(candidates=[candidate], **overrides)
    return generate_alpha_recommendation(request)


def test_candidate_selected_has_recommendation_id() -> None:
    rec = _recommend(_base_candidate())
    assert rec.status == "candidate_selected"
    assert rec.recommendation_id is not None
    assert rec.recommendation_id.startswith("alpha_")


def test_heuristic_model_key_when_no_trained_evidence() -> None:
    rec = _recommend(_base_candidate())
    assert rec.prediction_model_key == "heuristic_alpha_v1"


def test_heuristic_prediction_warning_when_not_trained() -> None:
    rec = _recommend(_base_candidate())
    assert "heuristic_prediction_not_trained_model" in rec.warnings


def test_trained_evidence_uses_metadata_model_key_and_skips_heuristic_warning() -> None:
    c = _base_candidate()
    req = AlphaEngineRequest(
        candidates=[c],
        metadata={
            "trained_model_evidence": {"global": True},
            "prediction_model_key": "candidate_ranker_v1",
        },
    )
    rec = generate_alpha_recommendation(req)
    assert rec.status == "candidate_selected"
    assert rec.prediction_model_key == "candidate_ranker_v1"
    assert "heuristic_prediction_not_trained_model" not in rec.warnings


def test_win_probability_cap_and_floor_helpers() -> None:
    assert _clamp_heuristic_win_probability(0.20) == 0.35
    assert _clamp_heuristic_win_probability(0.95) == 0.70
    hi = _heuristic_win_probability(
        {"relative_volume_score": 80.0, "spread_score": 85.0, "evidence_score": 65.0},
        final_score=85.0,
    )
    assert hi == 0.70
    lo = _heuristic_win_probability(
        {"relative_volume_score": 40.0, "spread_score": 40.0, "evidence_score": 40.0},
        final_score=50.0,
    )
    assert lo == 0.50


def test_predicted_expected_value_r_matches_formula() -> None:
    rec = _recommend(_base_candidate())
    assert rec.predicted_win_probability is not None
    assert rec.entry_plan.expected_r == 2.0
    p = rec.predicted_win_probability
    tr = float(rec.entry_plan.expected_r)
    expected_ev = round(p * tr - (1.0 - p) * 1.0, 6)
    assert rec.predicted_expected_value_r == expected_ev
    assert rec.predicted_return_r == rec.predicted_expected_value_r


def test_predicted_return_pct_when_entry_and_risk_present() -> None:
    rec = _recommend(_base_candidate())
    assert rec.entry_plan.entry is not None and rec.entry_plan.risk_per_share is not None
    assert rec.predicted_return_r is not None
    exp_pct = round(
        float(rec.predicted_return_r) * float(rec.entry_plan.risk_per_share) / float(rec.entry_plan.entry) * 100.0,
        6,
    )
    assert rec.predicted_return_pct == exp_pct
    assert "prediction_pct_unavailable_missing_entry_or_risk" not in rec.warnings


def test_prediction_pct_missing_warning_when_entry_or_risk_missing() -> None:
    req = AlphaEngineRequest(candidates=[], metadata={})
    ep = AlphaEntryPlan(entry=None, stop=None, target=None, risk_per_share=None, expected_r=2.0)
    out = _prediction_attachment(
        request=req,
        symbol="TESTX",
        strategy_key="relative_volume_momentum_breakout_v1",
        final_score=85.0,
        component_scores={
            "relative_volume_score": 90.0,
            "spread_score": 90.0,
            "evidence_score": 65.0,
        },
        entry_plan=ep,
    )
    assert out["predicted_return_pct"] is None
    assert out["predicted_return_r"] is not None
    assert "prediction_pct_unavailable_missing_entry_or_risk" in out["extra_warnings"]


def test_outcome_evaluator_actual_return_r() -> None:
    rec = AlphaRecommendation(
        status="candidate_selected",
        symbol="TESTX",
        strategy_key="relative_volume_momentum_breakout_v1",
        recommendation_id="alpha_test",
        predicted_return_r=1.0,
        predicted_return_pct=3.0,
        predicted_win_probability=0.6,
        predicted_expected_value_r=1.0,
        prediction_horizon_minutes=60,
        prediction_model_key="heuristic_alpha_v1",
        entry_plan=AlphaEntryPlan(entry=10.0, stop=9.7, target=11.0, risk_per_share=0.3, expected_r=2.0),
    )
    out = evaluate_prediction_outcome(rec, PricePathOrExit(exit_price=10.6))
    assert out.actual_return_r is not None
    assert out.actual_return_r == pytest.approx((10.6 - 10.0) / 0.3)


def test_outcome_evaluator_prediction_error_r() -> None:
    rec = AlphaRecommendation(
        status="candidate_selected",
        symbol="TESTX",
        strategy_key="relative_volume_momentum_breakout_v1",
        recommendation_id="alpha_test",
        predicted_return_r=1.0,
        entry_plan=AlphaEntryPlan(entry=10.0, stop=9.7, target=11.0, risk_per_share=0.3, expected_r=2.0),
    )
    out = evaluate_prediction_outcome(rec, PricePathOrExit(exit_price=10.6))
    assert out.actual_return_r == pytest.approx(2.0)
    assert out.prediction_error_r == pytest.approx(1.0)


def test_price_path_mfe_mae_and_hits() -> None:
    rec = AlphaRecommendation(
        status="candidate_selected",
        symbol="TESTX",
        strategy_key="relative_volume_momentum_breakout_v1",
        entry_plan=AlphaEntryPlan(entry=10.0, stop=9.5, target=11.0, risk_per_share=0.5, expected_r=2.0),
    )
    path = [10.0, 11.2, 9.4, 10.1]
    out = evaluate_prediction_outcome(rec, PricePathOrExit(price_path=path))
    assert out.max_favorable_excursion_r == pytest.approx((11.2 - 10.0) / 0.5)
    assert out.max_adverse_excursion_r == pytest.approx((10.0 - 9.4) / 0.5)
    assert out.hit_target is True
    assert out.hit_stop is True


def test_compute_prediction_error_none_when_missing() -> None:
    assert compute_prediction_error(None, 1.0) is None
    assert compute_prediction_error(1.0, None) is None


def test_no_broker_llm_in_recommendation_or_evaluator() -> None:
    rec = _recommend(_base_candidate())
    assert rec.broker_called is False
    assert rec.submitted_order is False
    assert rec.llm_used_for_trade_decision is False

    src = inspect.getsource(evaluate_prediction_outcome)
    assert "alpaca" not in src.lower()
    assert "openai" not in src.lower()
    assert "llm" not in src.lower()
