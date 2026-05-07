"""Stage 14 — Learning Loop (deterministic; no LLM).

Consumes recent outcome metrics and recommends governance actions (promotion/demotion/monitoring).
This stage MUST NOT modify registries, submit orders, call brokers, or call any LLM.
"""

from .models import LearningLoopEvaluateRequest, LearningLoopDecision, LearningLoopStatusResponse
from .service import build_status, evaluate_learning_loop, get_latest_decision

__all__ = [
    "LearningLoopEvaluateRequest",
    "LearningLoopDecision",
    "LearningLoopStatusResponse",
    "build_status",
    "evaluate_learning_loop",
    "get_latest_decision",
]

