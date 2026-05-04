from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.services.feature_store_service import FeatureStoreRow, get_feature_row_by_id, get_feature_rows_for_symbol
from app.services.model_registry_service import get_model_selection_summary, is_model_eligible_for_active_scoring, skipped_model_record
from app.services.model_runner_service import run_selected_models
from app.strategies.registry import StrategyConfig, get_strategy


class ModelRegistryItem(BaseModel):
    key: str
    name: str
    status: str
    should_run_when: list[str]
    data_source: str = "model_registry"


class ModelRunPlanRequest(BaseModel):
    symbols: list[str] = Field(default_factory=lambda: ["AMD"])
    asset_class: str = "stock"
    horizon: Literal["intraday", "day_trade", "swing", "one_month"] | str = "swing"
    source: str = "auto"
    strategy_key: str | None = None
    feature_row_id: str | None = None
    selected_models: list[str] | None = None
    feature_rows: list[FeatureStoreRow] | None = None


class PlannedModel(BaseModel):
    key: str
    status: str
    should_run: bool
    reason: str
    data_source: str = "model_registry"


class ModelRunPlanResponse(BaseModel):
    data_source: str
    models: list[PlannedModel]
    feature_rows_used: int
    warnings: list[str] = Field(default_factory=list)


class ModelRunRequest(ModelRunPlanRequest):
    pass


class ModelRunResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    status: str
    data_source: str
    plan: ModelRunPlanResponse
    feature_rows: list[FeatureStoreRow]
    results: list[dict[str, Any]]
    model_outputs: list[dict[str, Any]] = Field(default_factory=list)
    completed_models: list[dict[str, Any]] = Field(default_factory=list)
    blocked_models: list[dict[str, Any]] = Field(default_factory=list)
    placeholder_models: list[dict[str, Any]] = Field(default_factory=list)
    not_trained_models: list[dict[str, Any]] = Field(default_factory=list)
    skipped_models: list[dict[str, Any]] = Field(default_factory=list)
    next_action: str = "Review model outputs with risk filter before recommendation."
    warnings: list[str] = Field(default_factory=list)


def _legacy_model_contract(model: dict[str, Any]) -> dict[str, Any]:
    """Preserve /api/model-runs/registry compatibility while exposing governed registry fields."""
    should_run_when = model.get("should_run_when") or []
    if not should_run_when:
        if model.get("group") == "active_working_models":
            should_run_when = ["feature row exists", "data quality is pass or warn", "model registry eligibility passes"]
        elif model.get("group") == "untrained_internal_models":
            should_run_when = ["trained artifact exists", "evaluation passed", "calibration passed", "owner approved"]
        else:
            should_run_when = ["research wrapper exists", "evaluation passed", "owner approved"]
    return {
        **model,
        "key": model.get("key") or model.get("model_key"),
        "name": model.get("name") or model.get("display_name") or model.get("model_key"),
        "should_run_when": should_run_when,
    }


def get_model_registry() -> dict[str, Any]:
    summary = get_model_selection_summary()
    active = [_legacy_model_contract(model) for model in summary["active_models"]]
    candidates = {
        group: [_legacy_model_contract(model) for model in models]
        for group, models in summary["candidate_models"].items()
    }
    untrained = [_legacy_model_contract(model) for model in summary["untrained_internal_models"]]
    blocked = [_legacy_model_contract(model) for model in summary["blocked_models"]]
    all_models = active + untrained + blocked + [model for group in candidates.values() for model in group]
    return {
        "data_source": "model_registry",
        "models": all_models,
        "available_model_count": len(active),
        "placeholder_model_count": len([model for model in all_models if model.get("group") != "active_working_models"]),
        "active_models": active,
        "candidate_models": candidates,
        "untrained_internal_models": untrained,
        "blocked_models": blocked,
        "eligible_active_scoring_models": [_legacy_model_contract(model) for model in summary["eligible_active_scoring_models"]],
        "product_truth": summary["product_truth"],
    }


def _feature_fields_available(row: FeatureStoreRow) -> bool:
    return row.technical_score is not None and row.momentum_score is not None and row.rvol_score is not None


def plan_model_runs(request: ModelRunPlanRequest) -> ModelRunPlanResponse:
    rows = request.feature_rows or []
    has_rows = bool(rows)
    usable_rows = [row for row in rows if row.data_quality in {"pass", "warn"} and _feature_fields_available(row)]
    warnings: list[str] = []
    if not has_rows:
        warnings.append("No feature rows were supplied; run endpoint will build feature rows before scoring.")
    if rows and not usable_rows:
        warnings.append("Feature rows exist, but quality or required feature fields block active scoring.")

    summary = get_model_selection_summary()
    models: list[PlannedModel] = []
    for model in summary["active_models"]:
        key = model["model_key"]
        eligible = is_model_eligible_for_active_scoring(key)
        models.append(PlannedModel(
            key=key,
            status=model["status"],
            should_run=bool(has_rows and usable_rows and eligible),
            reason="Eligible active baseline; runs only when usable feature rows exist." if eligible else model.get("blocked_reason") or "Not eligible for active scoring.",
            data_source="source_backed" if usable_rows and eligible else "model_registry",
        ))

    for model in summary["untrained_internal_models"]:
        models.append(PlannedModel(
            key=model["model_key"],
            status=model["status"],
            should_run=False,
            reason=model.get("blocked_reason") or "Untrained internal model is not eligible for active scoring.",
            data_source="model_registry",
        ))

    for group_models in summary["candidate_models"].values():
        for model in group_models:
            models.append(PlannedModel(
                key=model["model_key"],
                status="candidate_not_active",
                should_run=False,
                reason=model.get("blocked_reason") or "Research candidate; not eligible for active scoring.",
                data_source="model_registry",
            ))

    for model in summary["blocked_models"]:
        models.append(PlannedModel(
            key=model["model_key"],
            status="blocked",
            should_run=False,
            reason=model.get("blocked_reason") or "Blocked by model registry.",
            data_source="model_registry",
        ))

    return ModelRunPlanResponse(
        data_source="source_backed" if any(model.data_source == "source_backed" for model in models) else "model_registry",
        models=models,
        feature_rows_used=len(rows),
        warnings=warnings,
    )


def _strategy_for_request(request: ModelRunRequest) -> StrategyConfig:
    if request.strategy_key:
        strategy = get_strategy(request.strategy_key)
        if strategy:
            return strategy
    fallback_key = "stock_day_trading" if request.horizon == "day_trade" else "stock_swing"
    return get_strategy(fallback_key) or get_strategy("stock_swing")  # type: ignore[return-value]


def _rows_for_request(request: ModelRunRequest) -> list[FeatureStoreRow]:
    if request.feature_rows:
        return request.feature_rows
    if request.feature_row_id:
        row = get_feature_row_by_id(request.feature_row_id)
        return [row] if row else []
    rows: list[FeatureStoreRow] = []
    for symbol in request.symbols:
        symbol_rows = get_feature_rows_for_symbol(symbol)
        if symbol_rows:
            rows.append(symbol_rows[0])
    return rows


def _default_selected_models(plan: ModelRunPlanResponse, usable_rows: list[FeatureStoreRow]) -> list[str]:
    eligible = [model.key for model in plan.models if model.should_run and is_model_eligible_for_active_scoring(model.key)]
    if usable_rows and "weighted_ranker_v1" not in eligible and is_model_eligible_for_active_scoring("weighted_ranker_v1"):
        eligible.insert(0, "weighted_ranker_v1")
    return eligible


def run_model_orchestrator(request: ModelRunRequest) -> ModelRunResponse:
    rows = _rows_for_request(request)
    warnings: list[str] = []
    if not rows:
        plan = plan_model_runs(ModelRunPlanRequest(**request.model_dump(exclude={"feature_rows"}), feature_rows=[]))
        return ModelRunResponse(
            status="blocked",
            data_source="model_registry",
            plan=plan,
            feature_rows=[],
            results=[],
            blocked_models=[{"model": "model_orchestrator", "status": "blocked", "reason": "No feature row exists. Run /api/feature-store/run first or provide feature_row_id.", "data_source": "placeholder"}],
            next_action="Run feature-store pipeline before model execution.",
            warnings=warnings + ["No feature rows available for model execution."],
        )

    plan = plan_model_runs(ModelRunPlanRequest(**request.model_dump(exclude={"feature_rows"}), feature_rows=rows))
    usable_rows = [row for row in rows if row.data_quality in {"pass", "warn"} and _feature_fields_available(row)]
    requested_models = ["weighted_ranker_v1" if model == "weighted_ranker" else model for model in (request.selected_models or [])]
    eligible_requested = [model for model in requested_models if is_model_eligible_for_active_scoring(model)]
    explicitly_skipped = [skipped_model_record(model, status="not_trained" if model == "xgboost_ranker" else "candidate_not_active") for model in requested_models if not is_model_eligible_for_active_scoring(model)]
    selected_models = eligible_requested or _default_selected_models(plan, usable_rows)
    strategy = _strategy_for_request(request)
    runner_outputs = {"completed_models": [], "blocked_models": [], "placeholder_models": [], "not_trained_models": [], "skipped_models": [], "model_outputs": []}
    for row in usable_rows:
        row_outputs = run_selected_models(row, strategy, selected_models + [model for model in requested_models if model not in selected_models])
        for key, values in row_outputs.items():
            runner_outputs[key].extend(values)

    if explicitly_skipped:
        runner_outputs["skipped_models"].extend(explicitly_skipped)

    for model in plan.models:
        if not model.should_run and model.key not in selected_models and model.key not in requested_models:
            record = skipped_model_record(model.key, status="not_trained" if model.key == "xgboost_ranker" else model.status)
            if record.get("status") == "not_trained":
                runner_outputs["not_trained_models"].append(record)
            else:
                runner_outputs["skipped_models"].append(record)

    model_outputs = runner_outputs["model_outputs"] + runner_outputs["placeholder_models"] + runner_outputs["skipped_models"]
    completed = runner_outputs["completed_models"]
    not_trained = runner_outputs["not_trained_models"]
    next_action = "Review weighted_ranker_v1 with risk filter before recommendation." if completed else "Resolve blocked model inputs before treating outputs as actionable."

    return ModelRunResponse(
        status="completed",
        data_source="source_backed" if any(row.data_source == "source_backed" for row in rows) else "model_registry",
        plan=plan,
        feature_rows=rows,
        results=model_outputs,
        model_outputs=model_outputs,
        completed_models=completed,
        blocked_models=runner_outputs["blocked_models"],
        placeholder_models=runner_outputs["placeholder_models"],
        not_trained_models=not_trained,
        skipped_models=runner_outputs["skipped_models"],
        next_action=next_action,
        warnings=warnings + plan.warnings,
    )
