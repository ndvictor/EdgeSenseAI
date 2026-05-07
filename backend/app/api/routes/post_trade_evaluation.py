"""Stage 13 — Post-Trade Evaluation (AI-Agent, no LLM) API routes."""

from fastapi import APIRouter

from app.services.post_trade_evaluation.models import PostTradeEvaluationEvaluateRequest
from app.services.post_trade_evaluation.service import build_status, evaluate_post_trade, get_latest_evaluation

router = APIRouter(prefix="/post-trade-evaluation", tags=["post-trade-evaluation"])


@router.get("/status")
def get_post_trade_evaluation_status():
    return build_status().model_dump()


@router.post("/evaluate")
def post_post_trade_evaluation_evaluate(request: PostTradeEvaluationEvaluateRequest):
    return evaluate_post_trade(request)


@router.get("/latest")
def get_post_trade_evaluation_latest():
    latest = get_latest_evaluation()
    if latest is None:
        return {"status": "not_found", "message": "No post-trade evaluation found yet."}
    return {"status": "ok", "post_trade_evaluation": latest.model_dump()}

