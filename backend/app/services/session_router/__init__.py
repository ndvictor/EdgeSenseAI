"""Stage 3 — Session Router (deterministic AI-Agent, no LLM).

This package determines the current trading session for a market using
deterministic time/calendar rules (v1) and stores the latest evaluation in memory.

No external calendar APIs in v1. No broker calls. No live trading logic.
"""

from .models import SessionEvaluateRequest, SessionEvaluation, SessionRouterStatusResponse
from .service import build_status, evaluate_session, get_latest_session

__all__ = [
    "SessionEvaluateRequest",
    "SessionEvaluation",
    "SessionRouterStatusResponse",
    "build_status",
    "evaluate_session",
    "get_latest_session",
]

