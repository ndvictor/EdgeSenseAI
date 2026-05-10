from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services.market_session_service import get_market_session_state
from app.services.session_router.models import SessionEvaluateRequest, SessionEvaluation, SessionRouterStatusResponse, iso_utc_now
from app.services.session_router.rules import SUPPORTED_SESSIONS

_LATEST_SESSION: SessionEvaluation | None = None


def _deterministic_session_id(evaluated_at_iso: str) -> str:
    compact = evaluated_at_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"sr_{compact}"


def _parse_requested_time(request: SessionEvaluateRequest) -> datetime | None:
    if request.use_current_time or not request.timestamp:
        return None
    dt = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(request.timezone or "America/Chicago"))
    return dt


def _legacy_session_name(market_session: str) -> str:
    if market_session == "regular_market":
        return "market_open"
    return market_session


def get_latest_session() -> SessionEvaluation | None:
    return _LATEST_SESSION


def build_status() -> SessionRouterStatusResponse:
    latest = get_latest_session()
    updated_at = iso_utc_now()
    return SessionRouterStatusResponse(
        status="ok",
        stage={"stage_number": 3, "stage_name": "Session Router", "stage_key": "session_router"},
        data_mode="rules_v1",
        updated_at=updated_at,
        summary={
            "router_status": "ready",
            "llm_required": False,
            "calendar_mode": "shared_market_session_service",
            "latest_session_id": (latest.session_id if latest else None),
            "next_action": "Evaluate current or supplied timestamp using shared MarketSessionService.",
        },
        supported_sessions=list(SUPPORTED_SESSIONS),
        checkers=[
            {"key": "market_session_service", "label": "Shared Market Session Service", "status": "ready", "uses_llm": False},
        ],
    )


def evaluate_session(request: SessionEvaluateRequest) -> dict[str, Any]:
    global _LATEST_SESSION

    market = (request.market or "").strip().lower()
    evaluated_at = iso_utc_now()
    if market != "us_equities":
        session = SessionEvaluation(
            session_id=_deterministic_session_id(evaluated_at),
            session="unknown",
            market="us_equities",
            timezone=request.timezone or "America/Chicago",
            evaluated_at=evaluated_at,
            market_date=evaluated_at[:10],
            is_trading_day=False,
            is_holiday=False,
            allowed_workflow_bias=[],
            blocked_workflow_bias=[{"workflow": "trade_execution", "reason": f"Unsupported market '{market}' in v1."}],
            session_notes=[f"Unsupported market '{market}' for session router v1."],
            next_action="Fix request market or extend session router market support.",
        )
        _LATEST_SESSION = session
        return {"status": "ok", "session": session.model_dump(), "market_session_state": {}}

    try:
        requested_time = _parse_requested_time(request)
        state = get_market_session_state(requested_time, prefer_alpaca=request.use_current_time)
    except Exception as exc:
        session = SessionEvaluation(
            session_id=_deterministic_session_id(evaluated_at),
            session="unknown",
            market="us_equities",
            timezone=request.timezone or "America/Chicago",
            evaluated_at=evaluated_at,
            market_date=evaluated_at[:10],
            is_trading_day=False,
            is_holiday=False,
            allowed_workflow_bias=[],
            blocked_workflow_bias=[{"workflow": "trade_execution", "reason": "Session evaluation failed."}],
            session_notes=[str(exc)],
            next_action="Verify market session service configuration.",
        )
        _LATEST_SESSION = session
        return {"status": "ok", "session": session.model_dump(), "market_session_state": {}}

    blocked = []
    allowed = ["observe_only_path", "backtest_queue_path"]
    notes = [f"Market session resolved by {state.clock_source}."]
    next_action = "Send session context to Stage 5 Workflow Router."
    if state.market_session == "regular_market":
        allowed = ["baseline_fast_path", "paper_only_path", "observe_only_path"]
    elif state.market_session == "pre_market":
        allowed = ["adjusted_research_path", "backtest_queue_path", "paper_only_path"]
        blocked = [{"workflow": "trade_execution", "reason": "Pre-market execution not enabled in v1."}]
    elif state.market_session == "post_market":
        allowed = ["adjusted_research_path", "backtest_queue_path", "learning_loop"]
        blocked = [{"workflow": "trade_execution", "reason": "Post-market execution not enabled in v1."}]
    else:
        blocked = [{"workflow": "trade_execution", "reason": "Market is closed."}]
        notes.append("Market is closed; worker scanner should not scan.")

    session = SessionEvaluation(
        session_id=_deterministic_session_id(evaluated_at),
        session=_legacy_session_name(state.market_session),
        market="us_equities",
        timezone="America/New_York",
        evaluated_at=evaluated_at,
        market_date=state.market_date,
        is_trading_day=state.is_trading_day,
        is_holiday=False,
        allowed_workflow_bias=allowed,
        blocked_workflow_bias=blocked,
        session_notes=notes + list(state.warnings or []),
        next_action=next_action,
    )
    _LATEST_SESSION = session
    return {"status": "ok", "session": session.model_dump(), "market_session_state": state.model_dump()}
