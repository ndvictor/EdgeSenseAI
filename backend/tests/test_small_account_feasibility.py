from __future__ import annotations

import pytest

from app.services.small_account_feasibility.service import SmallAccountFeasibilityRequest, evaluate_small_account_feasibility


def _request(**overrides):
    payload = {
        "account_equity": 1000.0,
        "buying_power": 1000.0,
        "symbols": ["TEST_STOCK_A"],
        "usable_symbols": ["TEST_STOCK_A"],
        "selected_symbol": "TEST_STOCK_A",
        "entry": 25.0,
        "stop": 24.0,
        "target": 28.0,
        "latest_price": 25.0,
        "spread_bps": 5.0,
        "volume": 5_000_000.0,
        "dollar_volume": 125_000_000.0,
        "avg_dollar_volume": 125_000_000.0,
        "planned_risk_dollars": 4.0,
        "open_positions": 0,
        "day_trades_used": 0,
        "proof_status": "paper_passed",
        "source_mode": "runtime",
        "using_non_real_data": False,
        "persistence_status": "persisted",
        "execution_mode": "plan_only",
    }
    payload.update(overrides)
    return SmallAccountFeasibilityRequest(**payload)


def test_small_account_limits_are_five_and_fifteen_dollars():
    out = evaluate_small_account_feasibility(_request())

    assert out.account_equity == 1000.0
    assert out.max_risk_dollars == 5.0
    assert out.max_daily_loss_dollars == 15.0


def test_valid_liquid_symbol_passes():
    out = evaluate_small_account_feasibility(_request())

    assert out.decision == "pass"
    assert out.account_feasibility_decision == "feasible"
    assert out.feasible_symbols == ["TEST_STOCK_A"]
    assert out.blockers == []


def test_spread_and_slippage_can_block_low_expected_r():
    out = evaluate_small_account_feasibility(
        _request(
            spread_bps=500.0,
            expected_r=0.15,
            min_expected_r=0.25,
        )
    )

    assert out.decision == "blocked"
    assert "expected_r_after_costs_below_minimum" in out.blockers


def test_low_avg_dollar_volume_alone_does_not_block():
    out = evaluate_small_account_feasibility(_request(avg_dollar_volume=19_000_000.0, dollar_volume=19_000_000.0))

    assert out.decision == "pass"


def test_risk_too_high_blocks():
    out = evaluate_small_account_feasibility(_request(planned_risk_dollars=5.01))

    assert out.decision == "blocked"
    assert "planned_risk_exceeds_policy_limit" in out.blockers


def test_open_position_blocks():
    out = evaluate_small_account_feasibility(_request(open_positions=1))

    assert out.decision == "blocked"
    assert "max_open_positions_reached" in out.blockers


def test_day_trade_limit_blocks():
    out = evaluate_small_account_feasibility(_request(day_trades_used=3))

    assert out.decision == "blocked"
    assert "max_trades_per_day_reached" in out.blockers


def test_missing_entry_blocks():
    out = evaluate_small_account_feasibility(_request(entry=None, latest_price=None))

    assert out.decision == "blocked"
    assert "missing_entry" in out.blockers


def test_high_share_price_does_not_degrade():
    out = evaluate_small_account_feasibility(_request(entry=760.0, stop=750.0, latest_price=760.0))

    assert out.decision == "pass"
    assert out.feasible_symbols == ["TEST_STOCK_A"]


def test_non_real_data_blocks():
    out = evaluate_small_account_feasibility(_request(using_non_real_data=True))

    assert out.account_feasibility_decision == "blocked"
    assert "non_real_or_synthetic_data" in out.blockers


def test_proof_missing_warns_and_degrades():
    out = evaluate_small_account_feasibility(_request(proof_status="proof_required"))

    assert out.account_feasibility_decision == "degraded"
    assert out.blockers == []
    assert "proof_not_ready_for_promotion" in out.warnings


def test_no_broker_order_or_llm_flags_are_true():
    out = evaluate_small_account_feasibility(_request())

    assert out.allow_submit is False
    assert out.submitted_order is False
    assert out.broker_called is False
    assert out.llm_used is False


def test_account_portfolio_feasibility_payload_fields():
    out = evaluate_small_account_feasibility(_request())

    assert out.account_feasibility_decision == "feasible"
    assert out.small_account_decision == "feasible"
    assert out.fractional_feasible is True
    assert out.buying_power_usage_pct is not None
    assert out.liquidity_participation_pct is not None
    assert out.expected_r_after_costs is not None
    assert isinstance(out.small_account_blockers, list)
    assert isinstance(out.small_account_warnings, list)


def test_high_priced_stock_fractional_example_matches_product_math():
    """entry=400, stop=396, equity=1000, max risk 1% => 10 risk dollars, 2.5 shares, 1000 notional."""
    out = evaluate_small_account_feasibility(
        _request(
            entry=400.0,
            stop=396.0,
            latest_price=400.0,
            max_risk_per_trade_pct=1.0,
            planned_risk_dollars=None,
            buying_power=5000.0,
            fractional_trading_enabled=True,
            avg_dollar_volume=400_000_000.0,
            dollar_volume=400_000_000.0,
            volume=1_000_000.0,
            spread_bps=8.0,
        )
    )

    assert "price" not in " ".join(out.blockers).lower()
    assert out.risk_dollars == pytest.approx(10.0)
    assert out.position_size_shares == pytest.approx(2.5)
    assert out.position_size_notional == pytest.approx(1000.0)


def test_liquidity_participation_too_high_blocks():
    out = evaluate_small_account_feasibility(
        _request(
            avg_dollar_volume=2400.0,
            dollar_volume=2400.0,
            planned_risk_dollars=5.0,
            entry=25.0,
            stop=24.0,
            max_liquidity_participation_pct=0.05,
        )
    )
    assert out.account_feasibility_decision == "blocked"
    assert "liquidity_participation_too_high" in out.blockers


def test_position_notional_exceeds_buying_power_blocks():
    out = evaluate_small_account_feasibility(
        _request(
            buying_power=100.0,
            planned_risk_dollars=5.0,
            entry=25.0,
            stop=24.0,
            avg_dollar_volume=500_000_000.0,
            dollar_volume=500_000_000.0,
        )
    )
    assert "position_notional_exceeds_buying_power" in out.blockers


def test_very_wide_spread_degraded_in_advisory_mode():
    out = evaluate_small_account_feasibility(
        _request(
            spread_bps=450.0,
            expected_r=1.0,
            min_expected_r=0.25,
            planned_risk_dollars=4.0,
            live_trading_enabled=False,
            allow_submit=False,
        )
    )
    assert out.account_feasibility_decision == "degraded"
    assert "spread_too_wide_for_execution_now" in out.warnings
    assert "expected_r_after_costs_below_minimum" not in out.blockers


def test_very_wide_spread_hard_blocks_in_live_regular_session():
    out = evaluate_small_account_feasibility(
        _request(
            spread_bps=450.0,
            expected_r=1.0,
            min_expected_r=0.25,
            planned_risk_dollars=4.0,
            live_trading_enabled=True,
            allow_submit=True,
            market_session="regular_market",
        )
    )
    assert out.account_feasibility_decision == "blocked"
    assert "spread_slippage_destroys_expected_r" in out.blockers
