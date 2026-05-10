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
        "avg_volume": 8_000_000.0,
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
    out = evaluate_account_feasibility(_base(fractional_trading_enabled=False, entry=500.0, stop=492.0))
    assert out.position_size_shares == 1.0


def test_invalid_stop_risk_per_share_blocks():
    out = evaluate_account_feasibility(_base(entry=100.0, stop=100.0))
    assert out.account_feasibility_decision == "blocked"
    assert "risk_per_share_invalid" in out.blockers


def test_notional_above_buying_power_blocks():
    # planned_risk=10 with risk_per_share=10 -> 1 share at $500 = $500 notional,
    # which exceeds a $50 buying_power cap.
    out = evaluate_account_feasibility(
        _base(buying_power=50.0, planned_risk_dollars=10.0, entry=500.0, stop=490.0)
    )
    assert "position_notional_exceeds_buying_power" in out.blockers


def test_notional_above_max_position_notional_blocks():
    out = evaluate_account_feasibility(_base(max_position_notional=250.0))
    assert "position_notional_exceeds_max_position_notional" in out.blockers


def test_liquidity_participation_too_high_blocks():
    # shares=1, notional=$100, dollar_volume=$10k -> participation=1% > 0.5% cap.
    out = evaluate_account_feasibility(
        _base(
            volume=100.0,
            dollar_volume=10_000.0,
            max_liquidity_participation_pct=0.005,
            planned_risk_dollars=10.0,
            entry=100.0,
            stop=90.0,
        )
    )
    assert "liquidity_participation_too_high" in out.blockers


def test_spread_slippage_blocks_low_expected_r():
    out = evaluate_account_feasibility(
        _base(spread_bps=400.0, expected_r=0.2, min_expected_r_after_costs=0.25, predicted_expected_value_r=None)
    )
    assert "expected_r_after_costs_below_minimum" in out.blockers


def test_missing_rvol_does_not_automatically_block():
    out = evaluate_account_feasibility(_base())
    assert out.account_feasibility_decision == "feasible"
    assert "relative_volume" not in " ".join(out.blockers).lower()


def test_missing_entry_or_stop_blocks():
    no_entry = evaluate_account_feasibility(_base(entry=None, latest_price=None))
    no_stop = evaluate_account_feasibility(_base(stop=None))
    assert "missing_entry" in no_entry.blockers
    assert "missing_stop" in no_stop.blockers


def test_live_mode_blocked_when_disabled():
    out = evaluate_account_feasibility(_base(execution_mode="live", live_trading_enabled=False, broker_execution_enabled=True))
    assert "execution_mode_live_not_allowed" in out.blockers


# ---------------------------------------------------------------------------
# Percent-convention tests (human percent values converted to fractions once)
# ---------------------------------------------------------------------------


def _policy_only(account_equity: float, **kw):
    """Build an input that exercises only the policy-conversion math.

    Missing entry/stop intentionally short-circuit the feasibility math; we
    only inspect ``max_risk_dollars`` / ``max_daily_loss_dollars`` /
    ``max_position_notional`` here.
    """
    base = {
        "account_equity": account_equity,
        "buying_power": account_equity,
        "fractional_trading_enabled": True,
    }
    base.update(kw)
    return AccountFeasibilityInput(**base)


def test_max_risk_per_trade_pct_zero_point_five_on_200k_is_1000():
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_risk_pct=0.5))
    assert out.max_risk_dollars == pytest.approx(1000.0, rel=1e-6)


def test_max_daily_loss_pct_one_point_five_on_200k_is_3000():
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_daily_loss_pct=1.5))
    assert out.max_daily_loss_dollars == pytest.approx(3000.0, rel=1e-6)


def test_max_position_notional_pct_100_on_200k_is_200000():
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_position_notional_pct=100.0))
    assert out.max_position_notional == pytest.approx(200_000.0, rel=1e-6)


def test_zero_point_five_is_not_treated_as_50_percent():
    # 0.5% of $200k = $1000, not $100k (which would be 50%).
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_risk_pct=0.5))
    assert out.max_risk_dollars == pytest.approx(1000.0, rel=1e-6)
    assert out.max_risk_dollars != pytest.approx(100_000.0)


def test_one_point_five_is_not_treated_as_150_percent():
    # 1.5% of $200k = $3000, not $300k (which would be 150%).
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_daily_loss_pct=1.5))
    assert out.max_daily_loss_dollars == pytest.approx(3000.0, rel=1e-6)
    assert out.max_daily_loss_dollars != pytest.approx(300_000.0)


def test_one_hundred_is_not_treated_as_10000_percent():
    # 100% of $200k = $200k, never $20M.
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_position_notional_pct=100.0))
    assert out.max_position_notional == pytest.approx(200_000.0, rel=1e-6)
    assert out.max_position_notional != pytest.approx(20_000_000.0)


def test_value_above_100_percent_is_rejected_and_default_used():
    # 250 means "250%", which is invalid. The service must reject and use the
    # configured default (100%), not multiply equity by 250.
    out = evaluate_account_feasibility(_policy_only(200_000.0, max_position_notional_pct=250.0))
    assert out.max_position_notional == pytest.approx(200_000.0, rel=1e-6)
    assert "risk_policy_default_used" in out.warnings


def test_internal_fraction_conversion_applied_exactly_once():
    """Defense-in-depth: assert the math reproduces ``equity * pct / 100`` and
    not ``equity * pct`` (no division) or ``equity * pct / 10000`` (double-divided).
    """
    equity = 50_000.0
    out = evaluate_account_feasibility(
        _policy_only(equity, max_risk_pct=2.0, max_daily_loss_pct=3.0, max_position_notional_pct=80.0)
    )
    assert out.max_risk_dollars == pytest.approx(equity * 2.0 / 100.0, rel=1e-6)
    assert out.max_daily_loss_dollars == pytest.approx(equity * 3.0 / 100.0, rel=1e-6)
    assert out.max_position_notional == pytest.approx(equity * 80.0 / 100.0, rel=1e-6)


def test_missing_account_equity_returns_data_unavailable():
    out = evaluate_account_feasibility(
        AccountFeasibilityInput(account_equity=None, buying_power=1000.0)
    )
    assert out.account_feasibility_decision == "data_unavailable"
    assert "account_equity_unavailable" in out.blockers


def test_missing_buying_power_returns_data_unavailable():
    out = evaluate_account_feasibility(
        AccountFeasibilityInput(account_equity=1000.0, buying_power=None)
    )
    assert out.account_feasibility_decision == "data_unavailable"
    assert "buying_power_unavailable" in out.blockers


def test_daily_loss_first_trade_does_not_block():
    # planned_risk=10 with 1.5% daily-loss policy on $1000 -> max=$15. First
    # trade with current_daily_loss=0 must not block.
    out = evaluate_account_feasibility(_base(current_daily_loss=0.0))
    assert "daily_loss_limit_would_be_exceeded" not in out.blockers


def test_daily_loss_blocks_only_when_cumulative_would_exceed_cap():
    # max_daily_loss = 1.5% of $1000 = $15. current=10, planned=10 -> 20 > 15.
    out = evaluate_account_feasibility(_base(current_daily_loss=10.0, planned_risk_dollars=10.0))
    assert "daily_loss_limit_would_be_exceeded" in out.blockers


def test_high_priced_stock_passes_when_fractional_sizing_fits():
    # $300 share price with $1000 buying power and fractional shares enabled
    # must not be blocked solely because the share price is high.
    out = evaluate_account_feasibility(
        _base(entry=300.0, stop=297.0, planned_risk_dollars=10.0, fractional_trading_enabled=True)
    )
    assert out.account_feasibility_decision == "feasible"
    assert out.fractional_feasible is True
    # raw shares = 10 / 3 ~= 3.333; notional ~= $1000.
    assert out.position_size_shares == pytest.approx(10.0 / 3.0, rel=1e-3)


def test_large_account_buying_power_is_respected():
    # $200k buying power must remain $200k -- never silently capped to $1000.
    out = evaluate_account_feasibility(
        _policy_only(200_000.0, buying_power=200_000.0, max_position_notional_pct=100.0)
    )
    assert out.buying_power == pytest.approx(200_000.0, rel=1e-6)
    assert out.max_position_notional == pytest.approx(200_000.0, rel=1e-6)
