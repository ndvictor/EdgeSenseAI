from __future__ import annotations

from pathlib import Path

from app.services.alpha_engine import AlphaEngineRequest, CandidateFeatureRow, generate_alpha_recommendation


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


def _assert_no_execution_flags(rec):
    assert rec.submitted_order is False
    assert rec.broker_called is False
    assert rec.llm_used_for_trade_decision is False


def test_high_relative_volume_breakout_selected():
    rec = _recommend(_base_candidate())

    assert rec.status == "candidate_selected"
    assert rec.strategy_key == "relative_volume_momentum_breakout_v1"
    _assert_no_execution_flags(rec)


def test_vwap_pullback_candidate_scores():
    rec = _recommend(
        _base_candidate(
            relative_volume=1.8,
            spread_bps=10,
            price_above_vwap=True,
            trend_score=75,
            liquidity_score=80,
        )
    )

    assert rec.status in {"candidate_selected", "watchlist_only"}
    assert rec.strategy_key is not None
    _assert_no_execution_flags(rec)


def test_wide_spread_rejected():
    rec = _recommend(_base_candidate(spread_bps=55))

    assert rec.status in {"no_qualified_setup", "blocked"}
    assert "spread" in rec.reason or any("spread" in blocker for blocker in rec.blockers)


def test_missing_last_price_rejected():
    rec = _recommend(_base_candidate(last_price=None))

    assert rec.status in {"no_qualified_setup", "data_unavailable"}
    assert rec.entry_plan.entry is None
    _assert_no_execution_flags(rec)


def test_synthetic_candidate_rejected():
    rec = _recommend(_base_candidate(synthetic=True))

    assert rec.status != "candidate_selected"
    assert rec.symbol is None


def test_non_real_candidate_rejected():
    rec = _recommend(_base_candidate(non_real=True))

    assert rec.status != "candidate_selected"
    assert rec.symbol is None


def test_no_candidates_returns_no_qualified_setup():
    rec = generate_alpha_recommendation(AlphaEngineRequest(candidates=[]))

    assert rec.status == "no_qualified_setup"
    assert rec.symbol is None
    assert rec.reason == "No real scanner/provider candidates were supplied."


def test_no_hardcoded_symbols_in_module():
    forbidden = {"TEST_STOCK_A", "TEST_STOCK_D", "TEST_STOCK_B", "TSLA", "SPY", "QQQ"}
    source_dir = Path(__file__).resolve().parents[1] / "app" / "services" / "alpha_engine"
    source = "\n".join(path.read_text() for path in source_dir.glob("*.py"))
    for symbol in forbidden:
        assert symbol not in source


def test_llm_not_used_for_trade_decision():
    rec = _recommend(_base_candidate())

    assert rec.llm_used_for_trade_decision is False


def test_small_account_high_price_warns_or_degrades():
    rec = _recommend(_base_candidate(last_price=120, spread_bps=10))

    assert "high_price_reduces_flexibility" in rec.warnings or rec.status == "no_qualified_setup"


def test_evidence_missing_does_not_claim_proven():
    rec = _recommend(_base_candidate())

    assert "proof_missing_or_backtest_required" in rec.warnings
    assert rec.evidence_summary.get("proof_status") != "proven"


def test_threshold_watchlist_only():
    rec = _recommend(
        _base_candidate(
            relative_volume=2.0,
            spread_bps=14,
            day_change_pct=2,
            trend_score=62,
            liquidity_score=58,
            price_above_vwap=True,
        )
    )

    assert rec.status in {"watchlist_only", "no_qualified_setup"}
    if rec.status == "watchlist_only":
        assert "candidate_needs_confirmation" in rec.warnings


def test_no_order_submission_flags():
    for rec in [
        _recommend(_base_candidate()),
        _recommend(_base_candidate(spread_bps=55)),
        generate_alpha_recommendation(AlphaEngineRequest(candidates=[])),
    ]:
        _assert_no_execution_flags(rec)
