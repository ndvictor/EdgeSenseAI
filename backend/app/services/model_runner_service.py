from typing import Any

from app.models.weighted_ranker import WeightedRankerOutput, run_weighted_ranker_v1
from app.models.xgboost_ranker import XGBoostRankerOutput, run_xgboost_ranker_safe
from app.services.feature_store_service import FeatureStoreRow
from app.strategies.registry import StrategyConfig


def run_weighted_ranker(feature_row: FeatureStoreRow, strategy_config: StrategyConfig) -> dict[str, Any]:
    return run_weighted_ranker_v1(feature_row, strategy_config).model_dump()


def run_xgboost_ranker(feature_row: FeatureStoreRow, strategy_config: StrategyConfig) -> dict[str, Any]:
    return run_xgboost_ranker_safe(feature_row, strategy_config).model_dump()


def _placeholder_model(model_key: str, reason: str) -> dict[str, Any]:
    return {
        "model": model_key,
        "model_name": model_key,
        "status": "placeholder_not_run",
        "reason": reason,
        "needed_inputs": [reason],
        "next_step": "Wire production data/model foundation before using this model.",
        "data_source": "placeholder",
    }


def run_selected_models(
    feature_row: FeatureStoreRow,
    strategy_config: StrategyConfig,
    selected_models: list[str],
) -> dict[str, list[dict[str, Any]]]:
    completed: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    placeholders: list[dict[str, Any]] = []
    not_trained: list[dict[str, Any]] = []

    for model_key in selected_models:
        if model_key == "weighted_ranker":
            output = run_weighted_ranker_v1(feature_row, strategy_config).model_dump()
            if output["status"] == "completed":
                completed.append(output)
            else:
                blocked.append(output)
        elif model_key == "xgboost_ranker":
            output = run_xgboost_ranker_safe(feature_row, strategy_config).model_dump()
            if output["status"] == "completed":
                completed.append(output)
            elif output["status"] in {"not_trained", "not_available"}:
                not_trained.append(output)
            else:
                blocked.append(output)
        else:
            placeholders.append(_placeholder_model(model_key, "Model is registered as a placeholder and is not production-ready."))

    return {
        "completed_models": completed,
        "blocked_models": blocked,
        "placeholder_models": placeholders,
        "not_trained_models": not_trained,
        "model_outputs": completed + not_trained + blocked + placeholders,
    }
