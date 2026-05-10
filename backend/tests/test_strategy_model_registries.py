from __future__ import annotations

from typing import Any

import pytest

from app.services.model_registry import (
    ModelRoleDefinition,
    get_model_role,
    iter_model_roles,
    list_model_role_keys,
)
from app.services.strategy_registry import (
    DayTradingStrategyDefinition,
    PromotionRequirements,
    get_strategy,
    iter_strategies,
    list_strategy_keys,
)

EXPECTED_STRATEGY_KEYS = {
    "relative_volume_momentum_breakout_v1",
    "vwap_pullback_continuation_v1",
    "filtered_opening_range_breakout_v1",
    "liquidity_reclaim_v1",
    "no_trade_v1",
}

EXPECTED_MODEL_ROLE_KEYS = {
    "candidate_ranker_v1",
    "setup_classifier_v1",
    "meta_label_model_v1",
    "sizing_model_v1",
}

_FORBIDDEN_TICKER_SUBSTRINGS = (
    "TEST_STOCK_D",
    "TEST_STOCK_B",
    "GOOGL",
    "GOOG",
    "AMZN",
    "TEST_STOCK_C",
    "TSLA",
    "META",
    "TEST_STOCK_A",
)


def _collect_strings(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            out.extend(_collect_strings(v))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            out.extend(_collect_strings(item))
    return out


def test_all_expected_strategy_keys_exist() -> None:
    keys = set(list_strategy_keys())
    assert EXPECTED_STRATEGY_KEYS == keys
    for k in EXPECTED_STRATEGY_KEYS:
        assert get_strategy(k) is not None


def test_strategies_are_stock_day_trading_only() -> None:
    for s in iter_strategies():
        assert s.asset_class == "stock"
        assert s.horizon == "day_trading"


def test_strategy_horizons_are_day_trading_not_multi_day_registry() -> None:
    """Horizon field is typed as day_trading only (not swing or multi-day hold)."""
    for s in iter_strategies():
        assert s.horizon == "day_trading"
        assert s.model_dump()["horizon"] == "day_trading"


def test_no_hardcoded_ticker_symbols_in_strategy_registry() -> None:
    blob = " ".join(_collect_strings([s.model_dump() for s in iter_strategies()])).upper()
    for t in _FORBIDDEN_TICKER_SUBSTRINGS:
        assert t not in blob


def test_promotion_requirements_on_every_strategy() -> None:
    for s in iter_strategies():
        assert isinstance(s.promotion_requirements, PromotionRequirements)
        pr = s.promotion_requirements
        assert pr.min_sample_size == 50
        assert pr.min_avg_r_multiple == pytest.approx(0.10)
        assert pr.min_profit_factor == pytest.approx(1.25)
        assert pr.max_drawdown_r_floor == pytest.approx(-8.0)
        assert pr.max_rule_violations == 0
        assert pr.requires_spread_slippage_acceptable is True
        assert pr.requires_small_account_feasible is True


def test_all_expected_model_roles_exist() -> None:
    keys = set(list_model_role_keys())
    assert EXPECTED_MODEL_ROLE_KEYS == keys
    for k in EXPECTED_MODEL_ROLE_KEYS:
        assert get_model_role(k) is not None


def test_model_roles_are_stock_day_trading() -> None:
    for m in iter_model_roles():
        assert m.asset_class == "stock"
        assert m.horizon == "day_trading"


def test_model_roles_default_to_research_only_not_active() -> None:
    for m in iter_model_roles():
        assert m.status == "research_only"
        assert m.status not in {"active", "approved_for_autonomous"}


def test_no_broker_llm_trade_enablement_on_definitions() -> None:
    for s in iter_strategies():
        assert s.llm_trade_decision_enabled is False
        assert s.broker_order_submission_enabled is False
    for m in iter_model_roles():
        assert m.llm_trade_decision_enabled is False
        assert m.broker_order_submission_enabled is False


def test_model_roles_reference_allowed_strategy_keys_only() -> None:
    allowed = set(list_strategy_keys())
    for m in iter_model_roles():
        for sk in m.allowed_strategy_keys:
            assert sk in allowed


def test_types_export() -> None:
    assert DayTradingStrategyDefinition.model_fields
    assert ModelRoleDefinition.model_fields
