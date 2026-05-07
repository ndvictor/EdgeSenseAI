from __future__ import annotations

from app.core.effective_runtime import effective_bool
from app.services.workflow_runbook.models import (
    RunbookLatestResponse,
    RunbookStagesResponse,
    RunbookStatusResponse,
    StageDescriptor,
    StageHealth,
    iso_utc_now,
)


def _master_gates() -> dict:
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


def _stage_inventory() -> list[StageDescriptor]:
    # Static inventory for v1 visibility. Do not probe endpoints over HTTP here.
    return [
        StageDescriptor(
            stage_number=1,
            stage_name="Master Admin Controls",
            stage_key="master_admin",
            implementation_status="present",
            backend_endpoint_family="/api/settings",
            frontend_route="/settings?tab=master_admin",
            recommended_operator_action="Review master settings before running workflow.",
            safety_notes=["Global workflow and execution control gates."],
            outputs=["runtime gates snapshot"],
            next_stage_keys=["session_router"],
        ),
        StageDescriptor(
            stage_number=2,
            stage_name="Data Intake & Quality",
            stage_key="data_intake_quality",
            implementation_status="partial_existing",
            backend_endpoint_family="/api/data-sources, /api/data-quality",
            frontend_route="/data-sources, /data-quality",
            recommended_operator_action="Confirm data sources and data quality before trading workflow.",
            safety_notes=["Upstream support services; no trading actions."],
            next_stage_keys=["session_router"],
        ),
        StageDescriptor(
            stage_number=3,
            stage_name="Session Router",
            stage_key="session_router",
            implementation_status="present",
            backend_endpoint_family="/api/session-router",
            frontend_route="/session-router",
            recommended_operator_action="Evaluate session (pre/market/post) before routing workflow.",
            outputs=["session evaluation"],
            next_stage_keys=["workflow_router"],
        ),
        StageDescriptor(
            stage_number=4,
            stage_name="Market Condition Scanner",
            stage_key="market_condition_scanner",
            implementation_status="partial_existing",
            backend_endpoint_family="/api/market-regime, /api/market-scanner",
            frontend_route="/market-regime",
            recommended_operator_action="Review market regime/scanner outputs for context.",
            next_stage_keys=["workflow_router"],
        ),
        StageDescriptor(
            stage_number=5,
            stage_name="Workflow Router",
            stage_key="workflow_router",
            implementation_status="present",
            backend_endpoint_family="/api/workflow-router",
            frontend_route="/workflow-router",
            recommended_operator_action="Route next workflow path based on session and constraints.",
            outputs=["workflow decision"],
            next_stage_keys=["strategy_eligibility"],
        ),
        StageDescriptor(
            stage_number=6,
            stage_name="Watchlist Builder",
            stage_key="watchlist_builder",
            implementation_status="partial_existing",
            backend_endpoint_family="/api/candidates, /api/watchlists, /api/live-watchlist",
            frontend_route="/candidate-engine, /live-watchlist",
            recommended_operator_action="Build/inspect candidate watchlists.",
            next_stage_keys=["strategy_eligibility"],
        ),
        StageDescriptor(
            stage_number=7,
            stage_name="Strategy Requirements & Eligibility",
            stage_key="strategy_eligibility",
            implementation_status="present",
            backend_endpoint_family="/api/strategy-eligibility",
            frontend_route="/strategy-eligibility",
            recommended_operator_action="Check strategy eligibility under current conditions.",
            outputs=["eligibility result"],
            next_stage_keys=["trigger_monitoring"],
        ),
        StageDescriptor(
            stage_number=8,
            stage_name="Trigger Monitoring",
            stage_key="trigger_monitoring",
            implementation_status="present",
            backend_endpoint_family="/api/trigger-monitoring",
            frontend_route="/trigger-monitoring",
            recommended_operator_action="Evaluate triggers; only proceed when fired and eligible.",
            outputs=["trigger evaluation"],
            next_stage_keys=["execution_planner"],
        ),
        StageDescriptor(
            stage_number=9,
            stage_name="Execution Planner",
            stage_key="execution_planner",
            implementation_status="present",
            backend_endpoint_family="/api/execution-planner",
            frontend_route="/execution-planner",
            recommended_operator_action="Create an execution plan preview (no broker submission).",
            outputs=["execution plan", "precheck handoff preview"],
            next_stage_keys=["trade_execution"],
        ),
        StageDescriptor(
            stage_number=10,
            stage_name="Execution Precheck / Execution Backend",
            stage_key="trade_execution",
            implementation_status="existing_gated",
            backend_endpoint_family="/api/execution",
            frontend_route="/auto-execution-monitor, /tradenow",
            recommended_operator_action="Use precheck/monitoring; do not assume any submit is enabled in v1.",
            safety_notes=[
                "Existing execution backend; not recreated here.",
                "Stage 9 handoff is precheck-preview only.",
                "Submission endpoints are gated by master admin settings.",
            ],
            next_stage_keys=["position_monitoring"],
        ),
        StageDescriptor(
            stage_number=11,
            stage_name="Position Monitoring",
            stage_key="position_monitoring",
            implementation_status="present",
            backend_endpoint_family="/api/position-monitoring",
            frontend_route="/position-monitoring",
            recommended_operator_action="Monitor position health and decide hold/reduce/exit_review.",
            outputs=["position evaluation"],
            next_stage_keys=["close_position"],
        ),
        StageDescriptor(
            stage_number=12,
            stage_name="Close Position Review",
            stage_key="close_position",
            implementation_status="present",
            backend_endpoint_family="/api/close-position",
            frontend_route="/close-position",
            recommended_operator_action="Prepare close/reduce preview only (no submission).",
            outputs=["close review preview"],
            next_stage_keys=["post_trade_evaluation"],
        ),
        StageDescriptor(
            stage_number=13,
            stage_name="Post-Trade Evaluation",
            stage_key="post_trade_evaluation",
            implementation_status="present",
            backend_endpoint_family="/api/post-trade-evaluation",
            frontend_route="/post-trade-evaluation",
            recommended_operator_action="Evaluate closed trade outcome and metrics.",
            outputs=["post-trade evaluation"],
            next_stage_keys=["learning_loop"],
        ),
        StageDescriptor(
            stage_number=14,
            stage_name="Learning Loop",
            stage_key="learning_loop",
            implementation_status="present",
            backend_endpoint_family="/api/learning-loop",
            frontend_route="/learning-loop",
            recommended_operator_action="Review metrics and promotion/demotion recommendations (no auto-promotion).",
            outputs=["learning decision"],
            next_stage_keys=[],
        ),
    ]


def build_stages() -> RunbookStagesResponse:
    return RunbookStagesResponse(
        status="ok",
        data_mode="stage_inventory_v1",
        updated_at=iso_utc_now(),
        stages=_stage_inventory(),
    )


def build_latest() -> RunbookLatestResponse:
    # Import latest getters (no HTTP calls, no evaluation triggers).
    from app.services.session_router.service import get_latest_session
    from app.services.workflow_router.service import get_latest_decision
    from app.services.strategy_eligibility.service import get_latest_check
    from app.services.trigger_monitoring.service import get_latest_evaluation as get_latest_trigger_eval
    from app.services.execution_planner.service import get_latest_plan, get_latest_handoff
    from app.services.position_monitoring.service import get_latest_evaluation as get_latest_position_eval
    from app.services.close_position.service import get_latest_review
    from app.services.post_trade_evaluation.service import get_latest_evaluation as get_latest_post_trade_eval
    from app.services.learning_loop.service import get_latest_decision as get_latest_learning_decision

    latest = {
        "session_router": get_latest_session().model_dump() if get_latest_session() else None,
        "workflow_router": get_latest_decision().model_dump() if get_latest_decision() else None,
        "strategy_eligibility": get_latest_check().model_dump() if get_latest_check() else None,
        "trigger_monitoring": get_latest_trigger_eval().model_dump() if get_latest_trigger_eval() else None,
        "execution_planner": get_latest_plan().model_dump() if get_latest_plan() else None,
        "execution_precheck_handoff": get_latest_handoff().model_dump() if get_latest_handoff() else None,
        "position_monitoring": get_latest_position_eval().model_dump() if get_latest_position_eval() else None,
        "close_position": get_latest_review().model_dump() if get_latest_review() else None,
        "post_trade_evaluation": get_latest_post_trade_eval().model_dump() if get_latest_post_trade_eval() else None,
        "learning_loop": get_latest_learning_decision().model_dump() if get_latest_learning_decision() else None,
    }

    return RunbookLatestResponse(
        status="ok",
        data_mode="latest_snapshot_v1",
        latest=latest,
        message="Latest snapshots are available after each stage is evaluated.",
    )


def build_status() -> RunbookStatusResponse:
    stages = _stage_inventory()
    gates = _master_gates()
    updated_at = iso_utc_now()

    critical_blockers: list[str] = []
    warnings: list[str] = []
    if not gates["workflow_enabled"]:
        warnings.append("workflow_disabled")
    if gates["live_trading_enabled"]:
        critical_blockers.append("live_trading_enabled_blocked_in_v1")
    if gates["emergency_stop"]:
        critical_blockers.append("emergency_stop_active")

    workflow_status = "visible_ready"
    if critical_blockers:
        workflow_status = "blocked"
    elif warnings:
        workflow_status = "partial"

    # Health list: indicates whether a "latest" snapshot exists (without triggering anything).
    latest = build_latest().latest
    stage_health: list[StageHealth] = []
    for st in stages:
        key = st.stage_key
        latest_key_map = {
            "session_router": "session_router",
            "workflow_router": "workflow_router",
            "strategy_eligibility": "strategy_eligibility",
            "trigger_monitoring": "trigger_monitoring",
            "execution_planner": "execution_planner",
            "position_monitoring": "position_monitoring",
            "close_position": "close_position",
            "post_trade_evaluation": "post_trade_evaluation",
            "learning_loop": "learning_loop",
        }
        latest_available = bool(latest.get(latest_key_map.get(key, ""), None)) if key in latest_key_map else True
        stage_health.append(
            StageHealth(
                stage_number=st.stage_number,
                stage_name=st.stage_name,
                stage_key=st.stage_key,
                backend_status="present" if st.implementation_status in {"present", "existing_gated"} else "partial",
                frontend_status="present" if st.implementation_status in {"present", "existing_gated", "partial_existing"} else "backlog",
                endpoint_family=st.backend_endpoint_family,
                ui_route=st.frontend_route,
                latest_available=latest_available,
                safety_role=(st.safety_notes[0] if st.safety_notes else "Workflow visibility stage."),
                next_action=st.recommended_operator_action,
            )
        )

    return RunbookStatusResponse(
        status="ok",
        data_mode="aggregated_status_v1",
        updated_at=updated_at,
        scope={
            "asset_class": "stock",
            "horizon": "day_trading",
            "mode": "paper_first",
            "llm_required": False,
            "live_trading_enabled": bool(gates["live_trading_enabled"]),
            "broker_submission_enabled": bool(gates["broker_execution_enabled"]) and bool(gates["execution_enabled"]),
        },
        summary={
            "workflow_name": "US Stock Day-Trading Paper Workflow v1",
            "workflow_status": workflow_status,
            "total_stages": 14,
            "implemented_stages": 11,
            "frontend_visible_stages": 10,
            "critical_blockers": critical_blockers,
            "warnings": warnings,
            "next_action": "Use Workflow Runbook UI to review each stage output and run sample path end-to-end.",
        },
        master_gates=gates,
        stage_health=stage_health,
    )

