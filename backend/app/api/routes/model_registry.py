from fastapi import APIRouter, HTTPException

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


@router.get("/model-registry/{model_key}")
def get_model_by_key(model_key: str):
    model = get_model(model_key)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' is not registered")
    return model.model_dump()


@router.get("/model-registry/{model_key}/eligibility")
def get_model_eligibility_by_key(model_key: str):
    return get_model_eligibility(model_key)
