from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.core.effective_runtime import effective_bool, effective_int
from app.services.agent_runtime.redis_runtime import get_active_workflow_state
from app.services.workflow_governance.models import WorkflowGovernanceCheckRequest, WorkflowGovernanceCheckResponse, WorkflowGovernanceStatusResponse, iso_utc_now

SUPPORTED_AUTONOMOUS_HORIZONS = ["day_trading"]
BLOCKED_AUTONOMOUS_HORIZONS = ["swing_trading", "swing", "multi_day", "overnight", "position_trade"]


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def get_governance_status() -> WorkflowGovernanceStatusResponse:
    return WorkflowGovernanceStatusResponse(
        updated_at=iso_utc_now(),
        summary={
            "workflow_enabled": effective_bool("WORKFLOW_ENABLED"),
            "execution_enabled": effective_bool("EXECUTION_ENABLED"),
            "emergency_stop": effective_bool("EMERGENCY_STOP"),
            "paper_trading_enabled": effective_bool("PAPER_TRADING_ENABLED"),
            "live_trading_enabled": effective_bool("LIVE_TRADING_ENABLED"),
            "broker_execution_enabled": effective_bool("BROKER_EXECUTION_ENABLED"),
            "require_human_approval": effective_bool("REQUIRE_HUMAN_APPROVAL"),
            "max_daily_agent_runs": effective_int("MAX_DAILY_AGENT_RUNS"),
        },
    )


def _count_today_runs() -> int:
    session = _db_session()
    if session is None:
        return 0
    try:
        from sqlalchemy import func, select

        from app.db.models import WorkflowOrchestratorRunRecord

        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        return int(
            session.execute(
                select(func.count()).select_from(WorkflowOrchestratorRunRecord).where(WorkflowOrchestratorRunRecord.created_at >= start)
            ).scalar()
            or 0
        )
    except Exception:
        return 0
    finally:
        session.close()


def check_governance(req: WorkflowGovernanceCheckRequest) -> WorkflowGovernanceCheckResponse:
    gates: dict[str, Any] = {}
    blockers: list[str] = []
    warnings: list[str] = []

    workflow_enabled = effective_bool("WORKFLOW_ENABLED")
    emergency_stop = effective_bool("EMERGENCY_STOP")
    paper_enabled = effective_bool("PAPER_TRADING_ENABLED")
    live_enabled = effective_bool("LIVE_TRADING_ENABLED")
    broker_exec_enabled = effective_bool("BROKER_EXECUTION_ENABLED")
    require_human = effective_bool("REQUIRE_HUMAN_APPROVAL")

    gates.update(
        {
            "workflow_enabled": workflow_enabled,
            "emergency_stop": emergency_stop,
            "paper_trading_enabled": paper_enabled,
            "live_trading_enabled": live_enabled,
            "broker_execution_enabled": broker_exec_enabled,
            "require_human_approval": require_human,
        }
    )

    if not workflow_enabled:
        blockers.append("workflow_disabled")
    if emergency_stop:
        blockers.append("emergency_stop_active")
    if not paper_enabled:
        blockers.append("paper_trading_disabled")
    if live_enabled:
        blockers.append("live_trading_blocked_v1")
    if broker_exec_enabled:
        blockers.append("broker_execution_blocked_v1")

    # Scope enforcement
    if str(req.asset_class).strip().lower() != "stock":
        blockers.append("asset_class_not_supported_v1")
    if str(req.horizon).strip().lower() != "day_trading":
        blockers.append("horizon_not_supported_for_autonomous_workflow")

    # Approval + submit enforcement
    if bool(req.allow_submit):
        blockers.append("allow_submit_blocked_v1")
    if bool(req.require_human_approval) and not require_human:
        warnings.append("request_requires_human_approval_but_runtime_is_false")

    # Limits (best-effort)
    max_daily_agent_runs = effective_int("MAX_DAILY_AGENT_RUNS")
    max_daily_workflow_runs = max(5, int(max_daily_agent_runs / 5))
    today = _count_today_runs()
    limits = {
        "max_daily_workflow_runs": max_daily_workflow_runs,
        "today_workflow_runs": today,
        "per_symbol_cooldown_seconds": 300,
        "supported_horizons": SUPPORTED_AUTONOMOUS_HORIZONS,
        "blocked_horizons": BLOCKED_AUTONOMOUS_HORIZONS,
    }
    if today >= max_daily_workflow_runs:
        blockers.append("max_daily_workflow_runs_exceeded")

    # Per-symbol cooldown (Redis hot state only; not authoritative)
    for sym in (req.symbols or [])[:10]:
        st = get_active_workflow_state(f"symbol:{sym.upper()}")
        if st and st.get("cooldown_until"):
            warnings.append(f"symbol_cooldown_active:{sym.upper()}")

    decision: str
    if blockers:
        decision = "blocked"
        next_action = "Resolve governance blockers (emergency stop, scope, submit flags, or limits)."
    elif warnings:
        decision = "warning"
        next_action = "Proceed with caution; review warnings."
    else:
        decision = "allowed"
        next_action = "Governance passed; orchestration may proceed."

    # Persist a lightweight governance check record best-effort
    session = _db_session()
    if session is not None:
        try:
            from app.db.models import WorkflowGovernanceCheckRecord

            session.merge(
                WorkflowGovernanceCheckRecord(
                    governance_check_id=f"gov_{uuid4().hex[:12]}",
                    workflow_run_id=req.workflow_run_id,
                    check_scope="pre_run",
                    status=decision,
                    gates=gates,
                    blockers=blockers,
                    warnings=warnings,
                    limits=limits,
                    metadata_json=req.metadata or {},
                    created_at=datetime.now(timezone.utc),
                )
            )
            session.commit()
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    return WorkflowGovernanceCheckResponse(
        decision=decision,  # type: ignore[arg-type]
        blockers=blockers,
        warnings=warnings,
        gates=gates,
        limits=limits,
        next_action=next_action,
        created_at=iso_utc_now(),
    )

