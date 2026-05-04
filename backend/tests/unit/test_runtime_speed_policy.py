import pytest

from app.services.runtime_speed_policy_service import get_runtime_speed_policy
from app.services.timing_cadence_service import MarketPhase, detect_market_phase, get_cadence_plan_for_phase


@pytest.mark.unit
def test_runtime_speed_policy_keeps_llm_out_of_hot_path():
    policy = get_runtime_speed_policy()
    assert policy.status == "configured"
    assert policy.hot_path.allow_llm_in_loop is False
    assert policy.hot_path.allow_network_provider_calls is False
    assert policy.hot_path.latency_budget_ms <= 500
    assert policy.warm_path.allow_llm_in_loop is False
    assert policy.cold_path.allow_llm_in_loop is True
    assert any("Human approval" in note for note in policy.safety_notes)


@pytest.mark.unit
def test_market_phase_cadence_is_deterministic_and_safe():
    plan = get_cadence_plan_for_phase(MarketPhase.MARKET_OPEN_FIRST_30_MIN)
    assert plan.scan_interval_seconds <= 30
    assert plan.llm_budget_mode in {"conservative", "minimal", "disabled"}
    assert plan.scanner_depth == "deep"


@pytest.mark.unit
def test_market_closed_uses_minimal_no_llm_cadence():
    plan = get_cadence_plan_for_phase(MarketPhase.MARKET_CLOSED)
    assert plan.scan_interval_seconds >= 300
    assert plan.llm_validation_policy == "disabled"
    assert plan.llm_budget_mode == "disabled"
    assert plan.scanner_depth == "minimal"
