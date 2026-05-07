"""Stage 7 — Strategy Requirements & Eligibility Checker (deterministic AI-Agent, no LLM).

Stage 5 decides the workflow *route*. Stage 7 decides whether a specific
strategy/response is eligible *within* the chosen route, given proofs, gates,
and strategy requirements.

No external calls. No LLM. No broker actions.
"""

from .models import StrategyEligibilityCheckRequest, StrategyEligibilityResult, StrategyEligibilityStatusResponse
from .service import build_status, check_strategy_eligibility, get_latest_check

__all__ = [
    "StrategyEligibilityCheckRequest",
    "StrategyEligibilityResult",
    "StrategyEligibilityStatusResponse",
    "build_status",
    "check_strategy_eligibility",
    "get_latest_check",
]

