from __future__ import annotations

from fastapi import APIRouter

from app.services.model_ranker_service import (
    ModelRankerRequest,
    get_latest_model_ranking,
    list_model_ranking_history,
    run_model_ranker,
)

router = APIRouter(prefix="/model-ranker", tags=["model-ranker"])


@router.post("/run")
def post_model_ranker_run(body: ModelRankerRequest):
    return run_model_ranker(body).model_dump()


@router.get("/latest")
def get_model_ranker_latest():
    latest = get_latest_model_ranking()
    return {"status": "ok", "ranking": latest.model_dump() if latest else None}


@router.get("/history")
def get_model_ranker_history(limit: int = 20):
    return {"status": "ok", "rankings": [r.model_dump() for r in list_model_ranking_history(limit=limit)]}
