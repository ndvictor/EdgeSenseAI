from __future__ import annotations

from typing import Any

from app.services.execution_planner.models import (
    ExecutionPlan,
    ExecutionPlannerPlanRequest,
    ExecutionPlannerStatusResponse,
    ExecutionPlannerHandoff,
    PrecheckHandoffRequest,
    iso_utc_now,
)
from app.services.execution_planner.rules import build_execution_plan
from app.core.effective_runtime import effective_bool


_LATEST_PLAN: ExecutionPlan | None = None
_LATEST_HANDOFF: ExecutionPlannerHandoff | None = None


def _deterministic_plan_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"ep_{compact}"


def get_latest_plan() -> ExecutionPlan | None:
    return _LATEST_PLAN


def get_latest_handoff() -> ExecutionPlannerHandoff | None:
    return _LATEST_HANDOFF


def build_status() -> ExecutionPlannerStatusResponse:
    latest = get_latest_plan()
    updated_at = iso_utc_now()
    return ExecutionPlannerStatusResponse(
        status="ok",
        stage={"stage_number": 9, "stage_name": "Execution Planner", "stage_key": "execution_planner"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "planner_status": "ready",
            "llm_required": False,
            "asset_scope": ["stock"],
            "horizon_scope": ["day_trading"],
            "mode_scope": ["paper_first"],
            "latest_plan_id": (latest.plan_id if latest else None),
            "next_action": "Create execution plan from fired trigger.",
        },
        checkers=[
            {"key": "position_sizing_calculator", "label": "Position Sizing Calculator", "status": "ready", "uses_llm": False},
            {"key": "stop_target_calculator", "label": "Stop/Target Calculator", "status": "ready", "uses_llm": False},
            {"key": "order_type_selector", "label": "Order Type Selector", "status": "ready", "uses_llm": False},
            {"key": "slippage_spread_calculator", "label": "Slippage/Spread Calculator", "status": "ready", "uses_llm": False},
            {"key": "master_admin_gate", "label": "Master Admin Gate", "status": "ready", "uses_llm": False},
        ],
    )


def plan_execution(request: ExecutionPlannerPlanRequest) -> dict[str, Any]:
    """
    Deterministic Stage-9 execution planning.

    This is an AI-Agent *without* an LLM:
    it observes trigger + market snapshot + account state + master admin runtime gates,
    produces a plan (or blockers), and stores the latest plan.
    """
    global _LATEST_PLAN

    created_at = iso_utc_now()
    plan_id = _deterministic_plan_id(created_at)

    plan = build_execution_plan(plan_id=plan_id, created_at=created_at, request=request)
    _LATEST_PLAN = plan
    return {"status": "ok", "execution_plan": plan.model_dump()}


def _deterministic_handoff_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"eh_{compact}"


def precheck_handoff(request: PrecheckHandoffRequest) -> dict[str, Any]:
    """
    Safe Stage-9 -> Stage-10 handoff.

    v1 guarantees:
    - allow_submit is always forced False
    - never calls submit_execution
    - never calls broker APIs (offline precheck summary only)
    """
    global _LATEST_HANDOFF

    created_at = iso_utc_now()
    handoff_id = _deterministic_handoff_id(created_at)

    plan = request.execution_plan
    prefs = request.handoff_preferences

    blockers: list[str] = []
    warnings: list[str] = []

    # A) No submit (forced)
    allow_submit = False

    # B) Scope blockers
    if plan.asset_class.strip().lower() != "stock":
        blockers.append("asset_class_not_supported")
    if plan.horizon.strip().lower() != "day_trading":
        blockers.append("horizon_not_supported")

    # C) Plan blockers
    if plan.plan_status.strip().lower() != "planned":
        blockers.append("plan_not_planned")
    if plan.blockers:
        blockers.append("plan_contains_blockers")
    if plan.sizing.planned_quantity <= 0:
        blockers.append("planned_quantity_not_positive")
    if plan.risk.stop_loss is None:
        blockers.append("missing_stop_loss")
    if plan.entry.order_type not in {"market", "limit"}:
        blockers.append("order_type_not_supported")

    # D) Master Admin blockers (effective runtime)
    # Combine effective runtime gates with the plan's embedded readiness snapshot.
    # v1 behavior: if either indicates a hard block, handoff must be blocked.
    if not bool(plan.execution_readiness.workflow_enabled):
        blockers.append("workflow_disabled_by_master_admin")
    if not bool(plan.execution_readiness.execution_enabled):
        blockers.append("execution_disabled_by_master_admin")
    if bool(plan.execution_readiness.emergency_stop):
        blockers.append("emergency_stop_active")
    if bool(plan.execution_readiness.force_close_requested):
        blockers.append("force_close_requested")
    if not bool(plan.execution_readiness.paper_trading_enabled):
        blockers.append("paper_trading_disabled_by_master_admin")
    if bool(plan.execution_readiness.live_trading_enabled):
        blockers.append("live_trading_enabled_blocked_in_v1")

    if effective_bool("EMERGENCY_STOP"):
        blockers.append("emergency_stop_active")
    if not effective_bool("WORKFLOW_ENABLED"):
        blockers.append("workflow_disabled_by_master_admin")
    if not effective_bool("EXECUTION_ENABLED"):
        blockers.append("execution_disabled_by_master_admin")
    if effective_bool("FORCE_CLOSE_REQUESTED"):
        blockers.append("force_close_requested")
    if not effective_bool("PAPER_TRADING_ENABLED"):
        blockers.append("paper_trading_disabled_by_master_admin")
    if effective_bool("LIVE_TRADING_ENABLED"):
        blockers.append("live_trading_enabled_blocked_in_v1")

    broker_execution_enabled = effective_bool("BROKER_EXECUTION_ENABLED")
    requires_human_approval = effective_bool("REQUIRE_HUMAN_APPROVAL") or bool(prefs.require_human_approval)

    if not broker_execution_enabled:
        warnings.append("broker_execution_disabled_by_master_admin")

    # E) Build ExecutionRequest preview (no submission, no broker calls)
    execution_request_preview = {
        "org_slug": prefs.org_slug,
        "symbol": plan.symbol,
        "asset_class": "stock",
        "side": "buy",
        "quantity": int(plan.sizing.planned_quantity),
        "order_type": plan.entry.order_type,
        "limit_price": plan.entry.limit_price if plan.entry.order_type == "limit" else None,
        "time_in_force": "day",
        "source": str(prefs.source or "execution_planner"),
        "reason": "stage_9_execution_plan_precheck",
        "human_approval_confirmed": False,
        "metadata": {
            "plan_id": plan.plan_id,
            "handoff_id": handoff_id,
            "allow_submit": allow_submit,
        },
    }

    precheck_status: str = "passed"
    if blockers:
        precheck_status = "blocked"

    allowed_next_stages: list[str] = []
    if precheck_status == "passed":
        if requires_human_approval:
            allowed_next_stages = ["human_approval_queue"]
        else:
            allowed_next_stages = ["execution_precheck_complete"]

    next_action = (
        "Review precheck output in Auto-Execution Monitor or proceed through approved execution workflow later."
        if precheck_status == "passed"
        else "Review blockers before attempting execution precheck."
    )

    handoff = ExecutionPlannerHandoff(
        handoff_id=handoff_id,
        plan_id=plan.plan_id,
        symbol=plan.symbol,
        precheck_status=precheck_status,  # type: ignore[arg-type]
        submitted_order=False,
        broker_called=False,
        execution_request_preview=execution_request_preview,
        precheck={"status": precheck_status, "steps": []},
        blockers=blockers,
        warnings=list(plan.warnings) + warnings,
        allowed_next_stages=allowed_next_stages,
        next_action=next_action,
        created_at=created_at,
    )

    _LATEST_HANDOFF = handoff
    return {"status": "ok", "handoff": handoff.model_dump()}

