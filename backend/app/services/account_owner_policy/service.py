from __future__ import annotations

from app.core.effective_runtime import effective_bool
from app.services.account_owner_policy.models import AccountOwnerPolicyRequest, AccountOwnerPolicyResponse
from app.services.agent_runtime.models import iso_utc_now


def _effective_gates() -> dict:
    return {
        "workflow_enabled": effective_bool("WORKFLOW_ENABLED"),
        "execution_enabled": effective_bool("EXECUTION_ENABLED"),
        "paper_trading_enabled": effective_bool("PAPER_TRADING_ENABLED"),
        "live_trading_enabled": effective_bool("LIVE_TRADING_ENABLED"),
        "broker_execution_enabled": effective_bool("BROKER_EXECUTION_ENABLED"),
        "human_approval_required": effective_bool("REQUIRE_HUMAN_APPROVAL"),
        "emergency_stop": effective_bool("EMERGENCY_STOP"),
        "force_close_requested": effective_bool("FORCE_CLOSE_REQUESTED"),
    }


def evaluate_owner_policy(req: AccountOwnerPolicyRequest) -> AccountOwnerPolicyResponse:
    gates = _effective_gates()
    blockers: list[str] = []
    warnings: list[str] = []

    if not gates["workflow_enabled"]:
        blockers.append("workflow_disabled_by_owner_policy")
    if gates["emergency_stop"]:
        blockers.append("emergency_stop_active")
    if gates["force_close_requested"]:
        warnings.append("force_close_requested_active")

    # Execution constraints: paper-first only in v1 surfaces
    if gates["live_trading_enabled"]:
        blockers.append("live_trading_enabled_blocked_in_v1")
    if not gates["paper_trading_enabled"]:
        blockers.append("paper_trading_disabled_by_owner_policy")

    decision: str = "allow" if not blockers else "blocked"
    next_action = "Proceed to data readiness checks." if decision == "allow" else "Resolve owner policy blockers in Settings (master gates)."

    return AccountOwnerPolicyResponse(
        status="ok",
        decision=decision,  # type: ignore[arg-type]
        gates=gates,
        blockers=blockers,
        warnings=warnings,
        next_action=next_action,
        checked_at=iso_utc_now(),
    )

