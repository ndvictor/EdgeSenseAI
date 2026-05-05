from fastapi import APIRouter

from app.services.normalization_status_service import NormalizationStatusResponse, build_normalization_status

router = APIRouter()


@router.get("/normalization/status", response_model=NormalizationStatusResponse)
def get_normalization_status() -> NormalizationStatusResponse:
    return build_normalization_status()

from fastapi import APIRouter

from app.services.normalization_status_service import NormalizationStatusResponse, build_normalization_status

router = APIRouter()


@router.get("/normalization/status", response_model=NormalizationStatusResponse)
def get_normalization_status() -> NormalizationStatusResponse:
    return build_normalization_status()

from fastapi import APIRouter

from app.services.normalization_status_service import NormalizationStatusResponse, build_normalization_status

router = APIRouter()


@router.get("/normalization/status", response_model=NormalizationStatusResponse)
def get_normalization_status() -> NormalizationStatusResponse:
    return build_normalization_status()

