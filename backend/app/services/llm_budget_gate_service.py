"""LLM Budget Gate Service.

Decides whether deeper LLM/agent validation is worth cost.
This gate defaults to deterministic/no-paid-call mode.

NO paid LLM calls here.
Only decides policy.
"""

from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class LLMBudgetGateRequest(BaseModel):
    """Request to evaluate LLM budget gate."""

    model_config = ConfigDict(protected_namespaces=())

    symbol: str | None = None
    strategy_key: str | None = None
    final_signal_score: float | None = Field(default=None, ge=0, le=100)
    confidence: float | None = Field(default=None, ge=0, le=1)
    complexity_flags: list[str] = Field(default_factory=list)
    estimated_tokens: int = Field(default=0, ge=0)
    requested_model_tier: Literal["disabled", "cheap", "standard", "strong"] = "disabled"
    daily_budget_remaining_usd: float | None = None
    dry_run: bool = True
    allow_paid_llm: bool = False


class LLMBudgetGateResponse(BaseModel):
    """Response from LLM budget gate evaluation."""

    model_config = ConfigDict(protected_namespaces=())

    run_id: str
    status: Literal["approved", "skipped", "blocked"]
    llm_validation_policy: Literal[
        "disabled", "deterministic_only", "cheap_summary_allowed", "strong_reasoning_allowed"
    ]
    selected_tier: Literal["disabled", "cheap", "standard", "strong"]
    estimated_cost_usd: float
    reason: str
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: datetime


# Constants
DEFAULT_MIN_SIGNAL_SCORE_FOR_LLM = 75.0
DEFAULT_MIN_DAILY_BUDGET_USD = 1.0
CHEAP_MODEL_COST_PER_1K_TOKENS = 0.0001  # $0.0001 per 1K tokens
STANDARD_MODEL_COST_PER_1K_TOKENS = 0.002  # $0.002 per 1K tokens
STRONG_MODEL_COST_PER_1K_TOKENS = 0.02  # $0.02 per 1K tokens

# In-memory storage for latest run
_LATEST_LLM_BUDGET_GATE: LLMBudgetGateResponse | None = None


def _calculate_cost(tokens: int, tier: str) -> float:
    """Calculate estimated cost in USD."""
    cost_per_1k = {
        "disabled": 0.0,
        "cheap": CHEAP_MODEL_COST_PER_1K_TOKENS,
        "standard": STANDARD_MODEL_COST_PER_1K_TOKENS,
        "strong": STRONG_MODEL_COST_PER_1K_TOKENS,
    }
    return (tokens / 1000) * cost_per_1k.get(tier, 0.0)


def evaluate_llm_budget_gate(request: LLMBudgetGateRequest) -> LLMBudgetGateResponse:
    """Evaluate whether LLM validation is worth the cost.

    Rules:
    - If allow_paid_llm=false, status must be skipped and policy deterministic_only.
    - If final_signal_score < 75, skip LLM.
    - If budget missing or insufficient, skip/block.
    - If requested_model_tier=disabled, skip.
    - Never call external LLM here.
    """
    run_id = f"llm-gate-{uuid4().hex[:12]}"
    checked_at = datetime.now(timezone.utc)
    blockers: list[str] = []
    warnings: list[str] = []
    reason = ""

    # Rule 1: If paid LLM not allowed, skip
    if not request.allow_paid_llm:
        return LLMBudgetGateResponse(
            run_id=run_id,
            status="skipped",
            llm_validation_policy="deterministic_only",
            selected_tier="disabled",
            estimated_cost_usd=0.0,
            reason="Paid LLM not allowed (allow_paid_llm=false). Using deterministic validation only.",
            blockers=[],
            warnings=[],
            checked_at=checked_at,
        )

    # Rule 2: If requested tier is disabled, skip
    if request.requested_model_tier == "disabled":
        return LLMBudgetGateResponse(
            run_id=run_id,
            status="skipped",
            llm_validation_policy="disabled",
            selected_tier="disabled",
            estimated_cost_usd=0.0,
            reason="LLM validation disabled by request.",
            blockers=[],
            warnings=[],
            checked_at=checked_at,
        )

    # Rule 3: If signal score too low, skip
    if request.final_signal_score is not None and request.final_signal_score < DEFAULT_MIN_SIGNAL_SCORE_FOR_LLM:
        return LLMBudgetGateResponse(
            run_id=run_id,
            status="skipped",
            llm_validation_policy="deterministic_only",
            selected_tier="disabled",
            estimated_cost_usd=0.0,
            reason=f"Signal score {request.final_signal_score:.1f} below threshold {DEFAULT_MIN_SIGNAL_SCORE_FOR_LLM}. Skipping LLM validation.",
            blockers=[],
            warnings=[f"Low signal score: {request.final_signal_score:.1f}"],
            checked_at=checked_at,
        )

    # Rule 4: Check budget
    estimated_cost = _calculate_cost(request.estimated_tokens, request.requested_model_tier)

    if request.daily_budget_remaining_usd is None:
        warnings.append("Daily budget not provided. Using default safety limit.")
        daily_budget = DEFAULT_MIN_DAILY_BUDGET_USD
    else:
        daily_budget = request.daily_budget_remaining_usd

    if daily_budget < estimated_cost:
        return LLMBudgetGateResponse(
            run_id=run_id,
            status="blocked",
            llm_validation_policy="deterministic_only",
            selected_tier="disabled",
            estimated_cost_usd=estimated_cost,
            reason=f"Insufficient budget: ${daily_budget:.4f} remaining, need ${estimated_cost:.4f}.",
            blockers=["insufficient_budget"],
            warnings=warnings,
            checked_at=checked_at,
        )

    # All checks passed - approve
    policy_map = {
        "cheap": "cheap_summary_allowed",
        "standard": "strong_reasoning_allowed",
        "strong": "strong_reasoning_allowed",
    }

    result = LLMBudgetGateResponse(
        run_id=run_id,
        status="approved",
        llm_validation_policy=policy_map.get(request.requested_model_tier, "deterministic_only"),
        selected_tier=request.requested_model_tier,
        estimated_cost_usd=estimated_cost,
        reason=f"LLM validation approved. Estimated cost: ${estimated_cost:.4f} for {request.estimated_tokens} tokens at {request.requested_model_tier} tier.",
        blockers=[],
        warnings=warnings,
        checked_at=checked_at,
    )

    # Store latest
    global _LATEST_LLM_BUDGET_GATE
    _LATEST_LLM_BUDGET_GATE = result

    return result


def get_latest_llm_budget_gate() -> LLMBudgetGateResponse | None:
    """Get the latest LLM budget gate evaluation."""
    return _LATEST_LLM_BUDGET_GATE
