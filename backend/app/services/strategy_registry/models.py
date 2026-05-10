from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

StrategyPromotionStatus = Literal[
    "research_only",
    "backtest_required",
    "paper_validation_required",
    "approved_for_autonomous",
    "active",
    "demoted",
    "blocked",
]


class PromotionRequirements(BaseModel):
    """Documented promotion gates (thresholds are targets for evidence review)."""

    min_sample_size: int = Field(50, description="sample_size >= 50")
    min_avg_r_multiple: float = Field(0.10, description="avg_r > 0.10")
    min_profit_factor: float = Field(1.25, description="profit_factor > 1.25")
    max_drawdown_r_floor: float = Field(
        -8.0,
        description="max_drawdown_r must be greater than -8 (drawdown shallower than 8R loss).",
    )
    max_rule_violations: int = Field(0, description="rule_violations == 0")
    requires_spread_slippage_acceptable: bool = Field(
        True,
        description="spread_slippage_acceptable == true",
    )
    requires_small_account_feasible: bool = Field(
        True,
        description="small_account_feasible == true",
    )


class DayTradingStrategyDefinition(BaseModel):
    """Structured day-trading strategy metadata for the Alpha Engine (registry-only)."""

    strategy_key: str
    display_name: str
    setup_type: str
    asset_class: Literal["stock"] = "stock"
    horizon: Literal["day_trading"] = "day_trading"
    status: StrategyPromotionStatus = "research_only"
    allowed_sessions: list[str]
    min_price: float
    max_price: float
    max_spread_bps: float
    min_relative_volume: float
    min_avg_dollar_volume: float
    requires_vwap: bool
    entry_logic_summary: str
    stop_logic_summary: str
    target_logic_summary: str
    rejection_rules: list[str]
    required_features: list[str]
    small_account_notes: list[str]
    promotion_requirements: PromotionRequirements
    llm_trade_decision_enabled: bool = False
    broker_order_submission_enabled: bool = False
