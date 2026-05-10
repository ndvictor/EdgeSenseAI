from __future__ import annotations

from app.services.model_registry.models import (
    ModelRoleDefinition,
    ModelValidationRequirements,
)
from app.services.strategy_registry.models import PromotionRequirements

_DEFAULT_PROMOTION = PromotionRequirements()

_MODEL_ROLES: dict[str, ModelRoleDefinition] = {
    "candidate_ranker_v1": ModelRoleDefinition(
        model_key="candidate_ranker_v1",
        display_name="Candidate Ranker v1",
        model_role="candidate_ranker",
        input_features=[
            "liquidity_score",
            "spread_bps",
            "relative_volume",
            "avg_daily_dollar_volume",
            "intraday_momentum_score",
            "range_compression_score",
            "vwap_distance_pct",
            "session_segment_id",
        ],
        target_label="ranked_candidate_quality_or_expected_edge_proxy",
        output_fields=[
            "rank_score",
            "rank_percentile",
            "explanatory_feature_attribution_stub",
        ],
        validation_requirements=ModelValidationRequirements(
            min_precision_at_k=0.55,
            notes=[
                "Ranker must be validated on forward windows; avoid random splits that leak future bars.",
            ],
        ),
        promotion_requirements=_DEFAULT_PROMOTION,
        allowed_strategy_keys=[
            "relative_volume_momentum_breakout_v1",
            "vwap_pullback_continuation_v1",
            "filtered_opening_range_breakout_v1",
            "liquidity_reclaim_v1",
            "no_trade_v1",
        ],
    ),
    "setup_classifier_v1": ModelRoleDefinition(
        model_key="setup_classifier_v1",
        display_name="Setup Classifier v1",
        model_role="setup_classifier",
        input_features=[
            "candle_sequence_embeddings_stub",
            "volume_trajectory_features",
            "vwap_structure_features",
            "opening_range_features",
            "spread_and_depth_summary",
            "rvol_trajectory_features",
        ],
        target_label="setup_class_among_defined_day_trading_setups",
        output_fields=[
            "setup_probabilities",
            "predicted_setup_id",
            "entropy_diagnostic",
        ],
        validation_requirements=ModelValidationRequirements(
            notes=[
                "Macro-F1 and calibrated probabilities required across sessions; monitor confusion "
                "between momentum breakout vs reclaim.",
            ],
        ),
        promotion_requirements=_DEFAULT_PROMOTION,
        allowed_strategy_keys=[
            "relative_volume_momentum_breakout_v1",
            "vwap_pullback_continuation_v1",
            "filtered_opening_range_breakout_v1",
            "liquidity_reclaim_v1",
        ],
    ),
    "meta_label_model_v1": ModelRoleDefinition(
        model_key="meta_label_model_v1",
        display_name="Meta-Label Model v1",
        model_role="meta_label",
        input_features=[
            "strategy_signal_features",
            "microstructure_features",
            "recent_trade_outcome_statistics_stub",
            "regime_flags_stub",
            "risk_overlay_features",
        ],
        target_label="trade_success_proxy_or_meta_label_outcome",
        output_fields=[
            "take_trade_probability",
            "expected_edge_bucket",
            "meta_confidence",
        ],
        validation_requirements=ModelValidationRequirements(
            requires_temporal_split_validation=True,
            notes=[
                "Must demonstrate stability across volatility regimes; label leakage checks required.",
            ],
        ),
        promotion_requirements=_DEFAULT_PROMOTION,
        allowed_strategy_keys=[
            "relative_volume_momentum_breakout_v1",
            "vwap_pullback_continuation_v1",
            "filtered_opening_range_breakout_v1",
            "liquidity_reclaim_v1",
            "no_trade_v1",
        ],
    ),
    "sizing_model_v1": ModelRoleDefinition(
        model_key="sizing_model_v1",
        display_name="Sizing Model v1",
        model_role="sizing",
        input_features=[
            "account_risk_budget_stub",
            "spread_bps",
            "atr_proxy_intraday",
            "liquidity_score",
            "meta_label_outputs_stub",
            "broker_constraints_stub",
        ],
        target_label="recommended_risk_fraction_or_position_weight",
        output_fields=[
            "size_fraction",
            "max_shares_cap_stub",
            "risk_reason_codes",
        ],
        validation_requirements=ModelValidationRequirements(
            notes=[
                "Sizing outputs must be bounded and monotone with respect to liquidity inputs in sanity checks.",
            ],
        ),
        promotion_requirements=_DEFAULT_PROMOTION,
        allowed_strategy_keys=[
            "relative_volume_momentum_breakout_v1",
            "vwap_pullback_continuation_v1",
            "filtered_opening_range_breakout_v1",
            "liquidity_reclaim_v1",
        ],
    ),
}


def list_model_role_keys() -> list[str]:
    return sorted(_MODEL_ROLES.keys())


def get_model_role(model_key: str) -> ModelRoleDefinition | None:
    return _MODEL_ROLES.get(model_key)


def iter_model_roles() -> list[ModelRoleDefinition]:
    return list(_MODEL_ROLES.values())
