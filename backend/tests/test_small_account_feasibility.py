from __future__ import annotations

from app.services.small_account_feasibility.service import SmallAccountFeasibilityRequest, evaluate_small_account_feasibility


def _request(**overrides):
    payload = {
        "account_equity": 1000.0,
        "symbols": ["AMD"],
        "usable_symbols": ["AMD"],
        "selected_symbol": "AMD",
        "latest_price": 25.0,
        "spread_bps": 5.0,
        "avg_dollar_volume": 50_000_000.0,
        "planned_risk_dollars": 4.0,
        "open_positions": 0,
        "day_trades_used": 0,
        "proof_status": "paper_passed",
        "source_mode": "runtime",
        "using_mock_data": False,
        "persistence_status": "persisted",
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
    assert out.feasible_symbols == ["AMD"]
    assert out.blockers == []


def test_spread_too_wide_blocks():
    out = evaluate_small_account_feasibility(_request(spread_bps=21.0))

    assert out.decision == "blocked"
    assert "spread_too_wide_for_small_account" in out.blockers


def test_low_liquidity_blocks():
    out = evaluate_small_account_feasibility(_request(avg_dollar_volume=19_000_000.0))

    assert out.decision == "blocked"
    assert "avg_dollar_volume_below_small_account_minimum" in out.blockers


def test_risk_too_high_blocks():
    out = evaluate_small_account_feasibility(_request(planned_risk_dollars=5.01))

    assert out.decision == "blocked"
    assert "planned_risk_exceeds_small_account_limit" in out.blockers


def test_open_position_blocks():
    out = evaluate_small_account_feasibility(_request(open_positions=1))

    assert out.decision == "blocked"
    assert "max_open_positions_reached" in out.blockers


def test_day_trade_limit_blocks():
    out = evaluate_small_account_feasibility(_request(day_trades_used=3))

    assert out.decision == "blocked"
    assert "max_trades_per_day_reached" in out.blockers


def test_missing_price_blocks():
    out = evaluate_small_account_feasibility(_request(latest_price=None))

    assert out.decision == "blocked"
    assert "missing_latest_price" in out.blockers


def test_high_price_warns_and_degrades():
    out = evaluate_small_account_feasibility(_request(latest_price=76.0))

    assert out.decision == "degraded"
    assert "latest_price_above_small_account_preferred_max" in out.warnings


def test_mock_data_warns_but_does_not_block_by_itself():
    out = evaluate_small_account_feasibility(_request(using_mock_data=True))

    assert out.decision == "degraded"
    assert "mock_data_used_for_small_account_feasibility" in out.warnings
    assert out.blockers == []


def test_no_broker_order_or_llm_flags_are_true():
    out = evaluate_small_account_feasibility(_request())

    assert out.allow_submit is False
    assert out.submitted_order is False
    assert out.broker_called is False
    assert out.llm_used is False
