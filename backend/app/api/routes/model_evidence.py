from __future__ import annotations

from fastapi import APIRouter

from app.services.model_evidence.models import ModelEvidenceCreate
from app.services.model_evidence.service import (
    get_latest_model_evidence,
    get_model_evidence_status,
    list_model_evidence,
    save_model_evidence,
)

router = APIRouter(prefix="/model-evidence", tags=["model-evidence"])


@router.get("/status")
def get_status():
    return get_model_evidence_status().model_dump()


@router.get("/records")
def get_records(limit: int = 50):
    return {"status": "ok", "records": [r.model_dump() for r in list_model_evidence(limit=limit)]}


@router.get("/latest")
def get_latest():
    rec = get_latest_model_evidence()
    return {"status": "ok", "record": rec.model_dump() if rec else None}


@router.post("/records")
def post_record(body: ModelEvidenceCreate):
    rec = save_model_evidence(body)
    return {"status": "ok", "record": rec.model_dump()}

