"""Stage 13 — Post-Trade Evaluation (deterministic; no LLM).

Evaluates a closed (or simulated-closed) trade outcome. Produces metrics and labels
for downstream learning workflows. This stage MUST NOT submit orders or call brokers.
"""

from .models import (
    PostTradeEvaluationEvaluateRequest,
    PostTradeEvaluationResult,
    PostTradeEvaluationStatusResponse,
)
from .service import build_status, evaluate_post_trade, get_latest_evaluation

__all__ = [
    "PostTradeEvaluationEvaluateRequest",
    "PostTradeEvaluationResult",
    "PostTradeEvaluationStatusResponse",
    "build_status",
    "evaluate_post_trade",
    "get_latest_evaluation",
]

