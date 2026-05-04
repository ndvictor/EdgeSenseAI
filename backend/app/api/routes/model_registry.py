from fastapi import APIRouter, HTTPException

from app.services.backtest_research_service import (
    ModelBacktestRunRequest,
    ResearchExperimentRequest,
    StrategyBacktestRunRequest,
    create_model_backtest_request,
    create_research_experiment,
    create_strategy_backtest_request,
    get_research_summary,
)
from app.services.model_artifact_service import ModelArtifactRegisterRequest, get_artifact, latest_artifact, list_artifacts, register_model_artifact
from app.services.model_calibration_service import ModelCalibrationRunRequest, create_calibration, latest_passed_calibration, list_calibrations
from app.services.model_evaluation_service import ModelEvaluationRunRequest, create_evaluation, latest_passed_evaluation, list_evaluations
from app.services.model_promotion_service import (
    ModelPromotionDecisionRequest,
    ModelPromotionRequest,
    approve_model_promotion,
    get_model_promotion_eligibility,
    list_promotion_reviews,
    reject_model_promotion,
    request_model_promotion,
)
from app.services.model_registry_service import (
    get_active_working_models,
    get_blocked_models,
    get_candidate_models,
    get_model,
    get_model_eligibility,
    get_model_registry,
    get_model_registry_groups,
    get_models_by_group,
    get_untrained_internal_models,
)
from app.services.research_persistence_service import (
    list_model_backtest_runs,
    list_research_experiment_runs,
    list_strategy_backtest_runs,
)

router = APIRouter()


@router.get("/model-registry")
def get_registry():
    return get_model_registry()


@router.get("/model-registry/groups")
def get_groups():
    return get_model_registry_groups()


@router.get("/model-registry/active")
def get_active():
    return {"data_source": "model_registry", "models": get_active_working_models()}


@router.get("/model-registry/candidates")
def get_candidates():
    return {"data_source": "model_registry", "groups": get_candidate_models()}


@router.get("/model-registry/untrained-internal")
def get_untrained_internal():
    return {"data_source": "model_registry", "models": get_untrained_internal_models()}


@router.get("/model-registry/blocked")
def get_blocked():
    return {"data_source": "model_registry", "models": get_blocked_models()}


@router.get("/model-registry/group/{group}")
def get_group(group: str):
    return {"data_source": "model_registry", "group": group, "models": get_models_by_group(group)}


@router.get("/model-registry/{model_key}/eligibility")
def get_model_eligibility_by_key(model_key: str):
    return get_model_eligibility(model_key)


@router.get("/model-registry/{model_key}")
def get_model_by_key(model_key: str):
    model = get_model(model_key)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' is not registered")
    return model.model_dump()


# Model artifact APIs
@router.get("/model-artifacts")
def get_model_artifacts(model_key: str | None = None):
    return list_artifacts(model_key)


@router.get("/model-artifacts/{artifact_id}")
def get_model_artifact_by_id(artifact_id: str):
    return get_artifact(artifact_id)


@router.post("/model-artifacts/register")
def post_model_artifact(request: ModelArtifactRegisterRequest):
    return register_model_artifact(request)


@router.get("/model-artifacts/model/{model_key}/latest")
def get_latest_model_artifact(model_key: str):
    return latest_artifact(model_key)


# Evaluation APIs
@router.get("/model-evaluations")
def get_model_evaluations(model_key: str | None = None):
    return list_evaluations(model_key)


@router.get("/model-evaluations/model/{model_key}")
def get_model_evaluations_for_model(model_key: str):
    return list_evaluations(model_key)


@router.post("/model-evaluations/run")
def post_model_evaluation(request: ModelEvaluationRunRequest):
    return create_evaluation(request)


@router.get("/model-evaluations/model/{model_key}/latest-passed")
def get_latest_passed_model_evaluation(model_key: str):
    return latest_passed_evaluation(model_key)


# Calibration APIs
@router.get("/model-calibration")
def get_model_calibration(model_key: str | None = None):
    return list_calibrations(model_key)


@router.get("/model-calibration/model/{model_key}")
def get_model_calibration_for_model(model_key: str):
    return list_calibrations(model_key)


@router.post("/model-calibration/run")
def post_model_calibration(request: ModelCalibrationRunRequest):
    return create_calibration(request)


@router.get("/model-calibration/model/{model_key}/latest-passed")
def get_latest_passed_model_calibration(model_key: str):
    return latest_passed_calibration(model_key)


# Promotion APIs
@router.get("/model-promotion/status/{model_key}")
def get_model_promotion_status(model_key: str):
    return get_model_promotion_eligibility(model_key)


@router.post("/model-promotion/request")
def post_model_promotion_request(request: ModelPromotionRequest):
    return request_model_promotion(request)


@router.post("/model-promotion/{review_id}/approve")
def post_model_promotion_approve(review_id: str, request: ModelPromotionDecisionRequest):
    return approve_model_promotion(review_id, request)


@router.post("/model-promotion/{review_id}/reject")
def post_model_promotion_reject(review_id: str, request: ModelPromotionDecisionRequest):
    return reject_model_promotion(review_id, request)


@router.get("/model-promotion/reviews")
def get_model_promotion_reviews(model_key: str | None = None):
    return list_promotion_reviews(model_key)


@router.get("/model-promotion/reviews/model/{model_key}")
def get_model_promotion_reviews_for_model(model_key: str):
    return list_promotion_reviews(model_key)


# Research/backtest APIs
@router.get("/backtesting/research/summary")
def get_backtesting_research_summary():
    return get_research_summary()


@router.get("/backtesting/research/experiments")
def get_research_experiments(target_key: str | None = None, status: str | None = None):
    return {"data_source": "postgres_or_empty", "experiments": list_research_experiment_runs(target_key=target_key, status=status)}


@router.post("/backtesting/research/experiments")
def post_research_experiment(request: ResearchExperimentRequest):
    return create_research_experiment(request)


@router.get("/backtesting/research/model-backtests")
def get_model_backtests(model_key: str | None = None):
    return {"data_source": "postgres_or_empty", "model_backtests": list_model_backtest_runs(model_key)}


@router.post("/backtesting/research/model-backtests")
def post_model_backtest(request: ModelBacktestRunRequest):
    return create_model_backtest_request(request)


@router.get("/backtesting/research/strategy-backtests")
def get_strategy_backtests(strategy_key: str | None = None):
    return {"data_source": "postgres_or_empty", "strategy_backtests": list_strategy_backtest_runs(strategy_key)}


@router.post("/backtesting/research/strategy-backtests")
def post_strategy_backtest(request: StrategyBacktestRunRequest):
    return create_strategy_backtest_request(request)
