from __future__ import annotations

from fastapi import APIRouter

from app.services.strategy_evidence.models import StrategyEvidenceCreate
from app.services.strategy_evidence.service import (
    get_latest_strategy_evidence,
    get_strategy_evidence_status,
    list_strategy_evidence,
    save_strategy_evidence,
)

router = APIRouter(prefix="/strategy-evidence", tags=["strategy-evidence"])


@router.get("/status")
def get_status():
    return get_strategy_evidence_status().model_dump()


@router.get("/records")
def get_records(limit: int = 50):
    return {"status": "ok", "records": [r.model_dump() for r in list_strategy_evidence(limit=limit)]}


@router.get("/latest")
def get_latest():
    rec = get_latest_strategy_evidence()
    return {"status": "ok", "record": rec.model_dump() if rec else None}


@router.post("/records")
def post_record(body: StrategyEvidenceCreate):
    rec = save_strategy_evidence(body)
    return {"status": "ok", "record": rec.model_dump()}

