from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.strategy_registry.models import PromotionRequirements

ModelPromotionStatus = Literal[
    "research_only",
    "backtest_required",
    "paper_validation_required",
    "approved_for_autonomous",
    "active",
    "demoted",
    "blocked",
]


class ModelValidationRequirements(BaseModel):
    """Evidence expectations before a model role may advance (registry metadata only)."""

    requires_probability_calibration: bool = True
    requires_temporal_split_validation: bool = True
    requires_out_of_sample_holdout: bool = True
    min_precision_at_k: float | None = None
    max_expected_calibration_error: float | None = None
    notes: list[str] = Field(default_factory=list)


class ModelRoleDefinition(BaseModel):
    """ML model role metadata aligned to day-trading stocks (registry-only; no artifact loading)."""

    model_config = ConfigDict(protected_namespaces=())

    model_key: str
    display_name: str
    model_role: str
    asset_class: Literal["stock"] = "stock"
    horizon: Literal["day_trading"] = "day_trading"
    status: ModelPromotionStatus = "research_only"
    input_features: list[str]
    target_label: str
    output_fields: list[str]
    validation_requirements: ModelValidationRequirements
    promotion_requirements: PromotionRequirements
    allowed_strategy_keys: list[str]
    llm_trade_decision_enabled: bool = False
    broker_order_submission_enabled: bool = False
