from typing import Any

from pydantic import BaseModel, Field

from app.services.feature_store_service import FeatureStoreRow
from app.strategies.registry import StrategyConfig


class FeatureContribution(BaseModel):
    feature: str
    value: float
    normalized_value: float
    weight: float
    contribution: float
    available: bool = True


class WeightedRankerOutput(BaseModel):
    model: str = "weighted_ranker"
    model_name: str = "weighted_ranker_v1"
    model_type: str = "deterministic_statistical_baseline"
    status: str = "completed"
    prediction_score: float
    probability_score: float
    expected_return_score: float
    expected_return_score_source: str = "placeholder_estimate_derived_from_rank_score"
    volatility_adjusted_score: float
    rank_score: float
    confidence_score: float
    feature_contributions: list[FeatureContribution] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    data_source: str = "source_backed"
    pricing: None = None
    cost: None = None


_FEATURE_WEIGHT_ALIASES = {
    "technical": "technical_score",
    "momentum": "momentum_score",
    "volume": "volume_score",
    "rvol": "rvol_score",
    "options": "options_score",
    "options_flow": "options_score",
    "sentiment": "sentiment_score",
    "macro": "macro_score",
    "regime": "regime_score",
    "liquidity": "liquidity_score",
    "volatility": "volatility_score",
    "model": "technical_score",
    "risk": "liquidity_score",
}

_DEFAULT_WEIGHTS = {
    "technical": 0.30,
    "momentum": 0.20,
    "volume": 0.15,
    "rvol": 0.15,
    "liquidity": 0.10,
    "volatility": 0.10,
}


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def _normalize_feature_value(value: float | None) -> float | None:
    if value is None:
        return None
    numeric = float(value)
    if numeric > 1:
        numeric = numeric / 100
    return _clamp(numeric)


def _feature_value(row: FeatureStoreRow, feature_name: str) -> float | None:
    return getattr(row, feature_name, None)


def _weights_for_strategy(strategy: StrategyConfig) -> dict[str, float]:
    raw_weights = strategy.default_weights or _DEFAULT_WEIGHTS
    expanded: dict[str, float] = {}
    for key, weight in raw_weights.items():
        feature_name = _FEATURE_WEIGHT_ALIASES.get(key, key if key.endswith("_score") else "")
        if feature_name:
            expanded[feature_name] = expanded.get(feature_name, 0.0) + float(weight)
    if not expanded:
        expanded = {_FEATURE_WEIGHT_ALIASES[key]: value for key, value in _DEFAULT_WEIGHTS.items()}
    return expanded


def run_weighted_ranker_v1(
    feature_row: FeatureStoreRow,
    strategy_config: StrategyConfig,
    model_parameters: dict[str, Any] | None = None,
) -> WeightedRankerOutput:
    del model_parameters
    weights = _weights_for_strategy(strategy_config)
    required_fields = {
        _FEATURE_WEIGHT_ALIASES.get(rule.split()[0], rule.split()[0])
        for rule in strategy_config.validation_rules
        if "required" in rule.lower()
    }
    required_fields.discard("")

    contributions: list[FeatureContribution] = []
    warnings: list[str] = []
    weighted_total = 0.0
    available_weight = 0.0
    for feature_name, weight in weights.items():
        value = _feature_value(feature_row, feature_name)
        normalized = _normalize_feature_value(value)
        if normalized is None:
            if feature_name in required_fields:
                warnings.append(f"Required feature {feature_name} is missing.")
            else:
                warnings.append(f"Optional feature {feature_name} is unavailable and ignored.")
            continue
        contribution = normalized * weight
        weighted_total += contribution
        available_weight += weight
        contributions.append(
            FeatureContribution(
                feature=feature_name,
                value=float(value),
                normalized_value=round(normalized, 4),
                weight=round(weight, 4),
                contribution=round(contribution, 4),
            )
        )

    raw_score = weighted_total / available_weight if available_weight else 0.0
    regime_value = _normalize_feature_value(feature_row.regime_score)
    liquidity_value = _normalize_feature_value(feature_row.liquidity_score)
    volatility_value = _normalize_feature_value(feature_row.volatility_score)
    confidence_value = _normalize_feature_value(feature_row.confidence)

    regime_adjustment = ((regime_value - 0.5) * 0.08) if regime_value is not None else 0.0
    liquidity_adjustment = ((liquidity_value - 0.5) * 0.07) if liquidity_value is not None else 0.0
    volatility_adjustment = -max(0.0, (volatility_value or 0.0) - 0.65) * 0.10
    confidence_adjustment = ((confidence_value - 0.5) * 0.05) if confidence_value is not None else -0.03

    final_score = _clamp(raw_score + regime_adjustment + liquidity_adjustment + volatility_adjustment + confidence_adjustment)
    volatility_adjusted_score = _clamp(final_score + volatility_adjustment)
    confidence_score = _clamp((confidence_value if confidence_value is not None else 0.5) * (0.85 if warnings else 1.0))
    probability_score = _clamp(0.5 + (final_score - 0.5) * 0.85)
    expected_return_score = _clamp((final_score - 0.5) * 0.20 + 0.05, 0.0, 0.20)

    if not contributions:
        warnings.append("No weighted features were available; score is a blocked baseline.")

    data_source = feature_row.data_source if feature_row.data_source in {"source_backed", "demo"} else "placeholder"
    return WeightedRankerOutput(
        prediction_score=round(final_score, 4),
        probability_score=round(probability_score, 4),
        expected_return_score=round(expected_return_score, 4),
        volatility_adjusted_score=round(volatility_adjusted_score, 4),
        rank_score=round(final_score, 4),
        confidence_score=round(confidence_score, 4),
        feature_contributions=contributions,
        warnings=warnings,
        data_source=data_source,
    )
