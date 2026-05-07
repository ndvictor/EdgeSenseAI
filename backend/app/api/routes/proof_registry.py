from __future__ import annotations

from fastapi import APIRouter

from app.services.proof_registry.models import ProofRegistryRecordCreate
from app.services.proof_registry.service import (
    get_latest_proof_record,
    get_proof_registry_status,
    list_proof_records,
    save_proof_record,
)

router = APIRouter(prefix="/proof-registry", tags=["proof-registry"])


@router.get("/status")
def get_status():
    return get_proof_registry_status().model_dump()


@router.get("/records")
def get_records(limit: int = 50):
    return {"status": "ok", "records": [r.model_dump() for r in list_proof_records(limit=limit)]}


@router.get("/latest")
def get_latest():
    rec = get_latest_proof_record()
    return {"status": "ok", "record": rec.model_dump() if rec else None}


@router.post("/records")
def post_record(body: ProofRegistryRecordCreate):
    rec = save_proof_record(body)
    return {"status": "ok", "record": rec.model_dump()}

