from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SafetyResult:
    sanitized_inputs: dict[str, Any]
    blockers: list[str]
    warnings: list[str]


def enforce_phase2_safety(*, agent_key: str, inputs: dict[str, Any], context: dict[str, Any]) -> SafetyResult:
    """Shared Phase-2 safety checks and input sanitization.

    This is intentionally conservative and deterministic. It must not perform any external calls.
    """
    blockers: list[str] = []
    warnings: list[str] = []
    sanitized = dict(inputs or {})

    # Reject explicit live/broker submission intents anywhere in inputs.
    if bool(sanitized.get("live_trading_enabled")):
        blockers.append("live_trading_enabled_blocked_in_v1")

    if bool(sanitized.get("broker_execution_enabled")):
        blockers.append("broker_execution_enabled_blocked_in_v1")

    if bool(sanitized.get("allow_submit")):
        # v1: never submit from wrappers; force false and warn.
        sanitized["allow_submit"] = False
        warnings.append("allow_submit_forced_false_v1")

    if bool(sanitized.get("submitted_order")) or bool(sanitized.get("broker_called")):
        blockers.append("submit_or_broker_call_attempt_blocked")

    # Human approval: if caller claims confirmed without explicit context, treat as blocked.
    if bool(sanitized.get("human_approval_confirmed")) and not bool(context.get("human_approval_obtained")):
        blockers.append("human_approval_confirmed_without_context")

    # Asset/horizon enforcement when explicitly provided.
    asset_class = sanitized.get("asset_class")
    if isinstance(asset_class, str) and asset_class.strip().lower() != "stock":
        blockers.append("asset_class_not_supported_v1")

    horizon = sanitized.get("horizon")
    if isinstance(horizon, str) and horizon.strip().lower() not in {"day_trading", "day_trade"}:
        blockers.append("horizon_not_supported_v1")

    # Agent-specific hardening
    if agent_key in {"close_review_agent", "execution_planner_agent"}:
        # force no submit always
        if "review_preferences" in sanitized and isinstance(sanitized["review_preferences"], dict):
            sanitized["review_preferences"] = {**sanitized["review_preferences"], "allow_submit": False}
        if "handoff_preferences" in sanitized and isinstance(sanitized["handoff_preferences"], dict):
            sanitized["handoff_preferences"] = {**sanitized["handoff_preferences"], "allow_submit": False}

    return SafetyResult(sanitized_inputs=sanitized, blockers=sorted(set(blockers)), warnings=sorted(set(warnings)))

