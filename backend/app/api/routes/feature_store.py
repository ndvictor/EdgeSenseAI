from fastapi import APIRouter

from app.services.feature_store_service import (
    FeatureStoreRow,
    FeatureStoreRunRequest,
    FeatureStoreRunResponse,
    get_feature_rows_for_symbol,
    get_latest_feature_rows,
    run_feature_store_pipeline,
)

router = APIRouter()


@router.get("/feature-store/latest", response_model=list[FeatureStoreRow])
def get_latest_feature_store_rows():
    return get_latest_feature_rows()


@router.get("/feature-store/{symbol}", response_model=list[FeatureStoreRow])
def get_symbol_feature_store_rows(symbol: str):
    return get_feature_rows_for_symbol(symbol)


@router.post("/feature-store/run", response_model=FeatureStoreRunResponse)
def post_feature_store_run(request: FeatureStoreRunRequest):
    return run_feature_store_pipeline(request)
