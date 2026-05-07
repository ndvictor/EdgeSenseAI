from __future__ import annotations

from typing import Any

from app.services.execution_planner.models import (
    ExecutionPlan,
    ExecutionPlannerPlanRequest,
    ExecutionPlannerStatusResponse,
    iso_utc_now,
)
from app.services.execution_planner.rules import build_execution_plan


_LATEST_PLAN: ExecutionPlan | None = None


def _deterministic_plan_id(ts_iso: str) -> str:
    compact = ts_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"ep_{compact}"


def get_latest_plan() -> ExecutionPlan | None:
    return _LATEST_PLAN


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

