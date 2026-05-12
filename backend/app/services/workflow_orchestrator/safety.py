from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SUPPORTED_AUTONOMOUS_HORIZONS = ["day_trading"]
BLOCKED_AUTONOMOUS_HORIZONS = ["swing_trading", "swing", "multi_day", "overnight", "position_trade"]


@dataclass(frozen=True)
class OrchestratorSafetyResult:
    sanitized_request: dict[str, Any]
    blockers: list[str]
    warnings: list[str]


def enforce_orchestrator_safety(req: dict[str, Any]) -> OrchestratorSafetyResult:
    blockers: list[str] = []
    warnings: list[str] = []
    s = dict(req or {})
    mode = str(s.get("mode", "") or "").lower().strip()

    # v1 allows submit-capable runs only for the paper simulator path.
    # Live/broker execution remains controlled by live/broker gates and must not
    # be unlocked by this safety layer.
    if bool(s.get("allow_submit")) and mode != "paper_first":
        blockers.append("allow_submit_blocked_v1")
        s["allow_submit"] = False
    if bool(s.get("live_trading_enabled")):
        blockers.append("live_trading_enabled_blocked_v1")
    if str(s.get("asset_class", "stock")).lower() != "stock":
        blockers.append("asset_class_not_supported_v1")
    if str(s.get("horizon", "day_trading")).lower() != "day_trading":
        blockers.append("horizon_not_supported_for_autonomous_workflow")
        s["supported_horizons"] = SUPPORTED_AUTONOMOUS_HORIZONS
    return OrchestratorSafetyResult(sanitized_request=s, blockers=sorted(set(blockers)), warnings=sorted(set(warnings)))

