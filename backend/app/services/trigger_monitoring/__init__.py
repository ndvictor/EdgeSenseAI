"""Stage 8 — Trigger Monitoring (deterministic AI-Agent, no LLM).

This package provides a lightweight orchestration layer that evaluates trigger state
for stock day-trading v1, without replacing existing primitives:
- trigger_rules (rule generation/registry)
- signal_scoring (signal scoring)
- market_scanner (candidate discovery)

No external API calls. No broker orders. No randomness.
"""

from .models import (
    CurrentState,
    EligibilityContext,
    TimingInfo,
    TriggerCandidate,
    TriggerEvaluation,
    TriggerMonitoringEvaluateRequest,
    TriggerMonitoringStatusResponse,
    WorkflowContext,
)
from .service import build_status, evaluate_trigger, get_latest_evaluation

__all__ = [
    "WorkflowContext",
    "EligibilityContext",
    "TriggerCandidate",
    "CurrentState",
    "TimingInfo",
    "TriggerEvaluation",
    "TriggerMonitoringEvaluateRequest",
    "TriggerMonitoringStatusResponse",
    "build_status",
    "evaluate_trigger",
    "get_latest_evaluation",
]

