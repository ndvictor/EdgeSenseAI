"""Data ingestion status API routes."""

from fastapi import APIRouter

from app.services.data_ingestion_service import DataIngestionStatusResponse, build_data_ingestion_status

router = APIRouter()


@router.get("/data-ingestion/status", response_model=DataIngestionStatusResponse)
def get_data_ingestion_status() -> DataIngestionStatusResponse:
    return build_data_ingestion_status()

"""Data ingestion status API route."""

from fastapi import APIRouter

from app.services.data_ingestion_service import DataIngestionStatusResponse, build_data_ingestion_status

router = APIRouter()


@router.get("/data-ingestion/status", response_model=DataIngestionStatusResponse)
def get_data_ingestion_status():
    return build_data_ingestion_status()

