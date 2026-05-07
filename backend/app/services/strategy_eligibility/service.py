from __future__ import annotations

from typing import Any

from app.services.strategy_eligibility.models import (
    SUPPORTED_STRATEGY_GROUPS,
    StrategyEligibilityCheckRequest,
    StrategyEligibilityResult,
    StrategyEligibilityStatusResponse,
    iso_utc_now,
)
from app.services.strategy_eligibility.rules import (
    data_quality_gate,
    decide_eligibility_v1,
    liquidity_gate,
    proof_status_checker,
    requirements_checker,
    risk_budget_gate,
)

# In-memory latest eligibility check (single-process; deterministic and test-friendly).
_LATEST_CHECK: StrategyEligibilityResult | None = None


def _deterministic_check_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"se_{compact}"


def get_latest_check() -> StrategyEligibilityResult | None:
    return _LATEST_CHECK


def build_status() -> StrategyEligibilityStatusResponse:
    latest = get_latest_check()
    updated_at = iso_utc_now()
    return StrategyEligibilityStatusResponse(
        status="ok",
        stage={
            "stage_number": 7,
            "stage_name": "Strategy Requirements & Eligibility Checker",
            "stage_key": "strategy_eligibility",
        },
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "checker_status": "ready",
            "llm_required": False,
            "latest_check_id": (latest.check_id if latest else None),
            "next_action": "Run an eligibility check before trigger monitoring.",
        },
        supported_strategy_groups=list(SUPPORTED_STRATEGY_GROUPS),
        checkers=[
            {"key": "proof_status_checker", "label": "Proof Status Checker", "status": "ready", "uses_llm": False},
            {"key": "data_quality_gate", "label": "Data Quality Gate", "status": "ready", "uses_llm": False},
            {"key": "risk_budget_gate", "label": "Risk Budget Gate", "status": "ready", "uses_llm": False},
            {"key": "liquidity_gate", "label": "Liquidity Gate", "status": "ready", "uses_llm": False},
            {"key": "requirements_checker", "label": "Strategy Requirements Checker", "status": "ready", "uses_llm": False},
        ],
    )


def check_strategy_eligibility(request: StrategyEligibilityCheckRequest) -> dict[str, Any]:
    """
    Deterministic Stage-7 eligibility evaluation.

    This is an AI-Agent *without* an LLM:
    it observes workflow/market/account state, evaluates constraints and requirements,
    chooses an eligibility status, and stores the latest check.
    """
    global _LATEST_CHECK

    created_at = iso_utc_now()
    check_id = _deterministic_check_id(created_at)

    proof_eval = proof_status_checker(request.strategy_candidate.proof_status, request.strategy_candidate.paper_status)
    dq_eval = data_quality_gate(request.market_condition.data_quality)
    risk_eval = risk_budget_gate(request.account_state.risk_budget_available)
    liq_eval = liquidity_gate(request.market_condition.liquidity_state)

    req_eval, _, _, _ = requirements_checker(request.strategy_candidate.strategy_group, request.market_condition, request.features)

    decision = decide_eligibility_v1(
        workflow=request.workflow_context,
        strategy=request.strategy_candidate,
        market=request.market_condition,
        features=request.features,
        account=request.account_state,
    )

    result = StrategyEligibilityResult(
        check_id=check_id,
        strategy_key=request.strategy_candidate.strategy_key,
        strategy_group=request.strategy_candidate.strategy_group,
        eligible=decision.eligible,
        eligibility_status=decision.eligibility_status,
        reason=decision.reason,
        proof_status=request.strategy_candidate.proof_status,
        paper_status=request.strategy_candidate.paper_status,
        requirements_passed=decision.requirements_passed,
        requirements_failed=decision.requirements_failed,
        blockers=decision.blockers,
        warnings=decision.warnings,
        checkers={
            "proof_status_checker": {"status": proof_eval.status, "message": proof_eval.message},
            "data_quality_gate": {"status": dq_eval.status, "message": dq_eval.message},
            "risk_budget_gate": {"status": risk_eval.status, "message": risk_eval.message},
            "liquidity_gate": {"status": liq_eval.status, "message": liq_eval.message},
            "requirements_checker": {"status": req_eval.status, "message": req_eval.message},
        },
        next_action=decision.next_action,
        created_at=created_at,
    )

    _LATEST_CHECK = result
    return {"status": "ok", "eligibility": result.model_dump()}

