from typing import Any

from app.models.weighted_ranker import run_weighted_ranker_v1
from app.models.xgboost_ranker import run_xgboost_ranker_safe
from app.services.feature_store_service import FeatureStoreRow
from app.services.model_registry_service import get_model, is_model_eligible_for_active_scoring, skipped_model_record
from app.services.persistence_service import save_model_run_output
from app.strategies.registry import StrategyConfig


def run_weighted_ranker(feature_row: FeatureStoreRow, strategy_config: StrategyConfig) -> dict[str, Any]:
    return run_weighted_ranker_v1(feature_row, strategy_config).model_dump()


def run_xgboost_ranker(feature_row: FeatureStoreRow, strategy_config: StrategyConfig) -> dict[str, Any]:
    # Safe wrapper only. The governed registry blocks this from active scoring until trained/evaluated/calibrated/approved.
    if not is_model_eligible_for_active_scoring("xgboost_ranker"):
        return skipped_model_record("xgboost_ranker", status="not_trained")
    return run_xgboost_ranker_safe(feature_row, strategy_config).model_dump()


def _inactive_model(model_key: str) -> dict[str, Any]:
    entry = get_model(model_key)
    if entry:
        status = "not_trained" if entry.group == "untrained_internal_models" else "candidate_not_active"
        return skipped_model_record(model_key, status=status)
    return {
        "model": model_key,
        "model_name": model_key,
        "status": "not_registered",
        "reason": "Model is not registered in the governed model registry.",
        "needed_inputs": ["model_registry_entry"],
        "next_step": "Register, evaluate, calibrate, and approve this model before use.",
        "data_source": "model_registry",
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
    skipped: list[dict[str, Any]] = []

    normalized = ["weighted_ranker_v1" if model == "weighted_ranker" else model for model in selected_models]

    for model_key in normalized:
        if not is_model_eligible_for_active_scoring(model_key):
            record = _inactive_model(model_key)
            if record.get("status") in {"not_trained", "not_available"}:
                not_trained.append(record)
            elif record.get("status") in {"candidate_not_active", "not_registered"}:
                skipped.append(record)
            else:
                blocked.append(record)
            continue

        if model_key == "weighted_ranker_v1":
            output = run_weighted_ranker_v1(feature_row, strategy_config).model_dump()
            output["model"] = "weighted_ranker_v1"
            output["model_name"] = output.get("model_name", "Weighted Ranker V1")
            save_model_run_output(output, feature_row=feature_row, strategy_key=strategy_config.strategy_key)
            if output["status"] == "completed":
                completed.append(output)
            else:
                blocked.append(output)
        elif model_key == "xgboost_ranker":
            output = run_xgboost_ranker_safe(feature_row, strategy_config).model_dump()
            save_model_run_output(output, feature_row=feature_row, strategy_key=strategy_config.strategy_key)
            if output["status"] == "completed":
                completed.append(output)
            elif output["status"] in {"not_trained", "not_available"}:
                not_trained.append(output)
            else:
                blocked.append(output)
        else:
            skipped.append(_inactive_model(model_key))

    return {
        "completed_models": completed,
        "blocked_models": blocked,
        "placeholder_models": placeholders,
        "not_trained_models": not_trained,
        "skipped_models": skipped,
        "model_outputs": completed + not_trained + blocked + placeholders + skipped,
    }
