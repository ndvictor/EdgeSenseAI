from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class OrchestratorSafetyResult:
    sanitized_request: dict[str, Any]
    blockers: list[str]
    warnings: list[str]


def enforce_orchestrator_safety(req: dict[str, Any]) -> OrchestratorSafetyResult:
    blockers: list[str] = []
    warnings: list[str] = []
    s = dict(req or {})

    # Always enforce: v1 paper-first; never submit.
    if bool(s.get("allow_submit")):
        blockers.append("allow_submit_blocked_v1")
        s["allow_submit"] = False
    if bool(s.get("live_trading_enabled")):
        blockers.append("live_trading_enabled_blocked_v1")
    if str(s.get("asset_class", "stock")).lower() != "stock":
        blockers.append("asset_class_not_supported_v1")
    if str(s.get("horizon", "day_trading")).lower() not in {"day_trading", "day_trade"}:
        blockers.append("horizon_not_supported_v1")
    return OrchestratorSafetyResult(sanitized_request=s, blockers=sorted(set(blockers)), warnings=sorted(set(warnings)))

