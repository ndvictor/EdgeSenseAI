"""Stage 11 — Position Monitoring (deterministic AI-Agent, no LLM).

This module evaluates position health (PnL, thesis validity, and risk) for
stock day-trading v1. It does NOT call broker APIs and does NOT close positions.

It does not replace live_watchlist; it provides a separate deterministic evaluator
that UI and workflows can integrate with later.
"""

from .models import (
    MonitoringPreferences,
    PositionInput,
    PositionMonitoringEvaluateRequest,
    PositionMonitoringStatusResponse,
    PositionEvaluation,
    RiskStateInput,
    ThesisInput,
)
from .service import build_status, evaluate_position, get_latest_evaluation

__all__ = [
    "PositionInput",
    "ThesisInput",
    "RiskStateInput",
    "MonitoringPreferences",
    "PositionMonitoringEvaluateRequest",
    "PositionEvaluation",
    "PositionMonitoringStatusResponse",
    "build_status",
    "evaluate_position",
    "get_latest_evaluation",
]

