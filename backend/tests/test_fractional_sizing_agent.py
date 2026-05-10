from __future__ import annotations

import pytest

from app.services.fractional_sizing_service import AccountFeasibilityInput, evaluate_account_feasibility


def _base(**kw):
    d = {
        "account_equity": 1000.0,
        "buying_power": 1000.0,
        "fractional_trading_enabled": True,
        "selected_symbol": "HI",
        "usable_symbols": ["HI"],
        "symbols": ["HI"],
        "entry": 500.0,
        "stop": 495.0,
        "spread_bps": 8.0,
        "volume": 10_000_000.0,
        "dollar_volume": 5_000_000_000.0,
        "planned_risk_dollars": 10.0,
        "max_risk_pct": 10.0,
        "execution_mode": "plan_only",
        "expected_r": 1.2,
        "predicted_expected_value_r": 0.4,
        "proof_status": "paper_passed",
    }
    d.update(kw)
    return AccountFeasibilityInput(**d)


def test_high_price_not_rejected_when_fractional_risk_fits():
    out = evaluate_account_feasibility(_base())
    assert out.account_feasibility_decision == "feasible"
    assert out.position_size_shares is not None
    assert out.position_size_shares == pytest.approx(2.0, rel=1e-3)


def test_fractional_shares_allow_decimal_size():
    out = evaluate_account_feasibility(_base(fractional_trading_enabled=True))
    assert out.fractional_feasible is True
    assert out.position_size_shares == pytest.approx(2.0, rel=1e-3)


def test_whole_share_mode_floors_position():
    out = evaluate_account_feasibility(_base(fractional_trading_enabled=False))
    assert out.position_size_shares == 2.0


def test_invalid_stop_risk_per_share_blocks():
    out = evaluate_account_feasibility(_base(entry=100.0, stop=100.0))
    assert out.account_feasibility_decision == "blocked"
    assert "risk_per_share_invalid" in out.blockers


def test_notional_above_buying_power_blocks():
    out = evaluate_account_feasibility(_base(buying_power=50.0, planned_risk_dollars=40.0, entry=500.0, stop=490.0))
    assert "position_notional_exceeds_buying_power" in out.blockers


def test_liquidity_participation_too_high_blocks():
    out = evaluate_account_feasibility(
        _base(volume=100.0, dollar_volume=50_000.0, max_liquidity_participation_pct=0.01, planned_risk_dollars=50.0, entry=100.0, stop=90.0)
    )
    assert "liquidity_participation_too_high" in out.blockers


def test_spread_slippage_blocks_low_expected_r():
    out = evaluate_account_feasibility(
        _base(spread_bps=400.0, expected_r=0.2, min_expected_r_after_costs=0.25, predicted_expected_value_r=None)
    )
    assert "expected_r_after_costs_below_minimum" in out.blockers


def test_live_mode_blocked_when_disabled():
    out = evaluate_account_feasibility(_base(execution_mode="live", live_trading_enabled=False, broker_execution_enabled=True))
    assert "execution_mode_live_not_allowed" in out.blockers
