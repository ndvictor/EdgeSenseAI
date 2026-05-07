from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.services.session_router.models import SessionEvaluateRequest, SessionEvaluation, SessionRouterStatusResponse, iso_utc_now
from app.services.session_router.rules import (
    CT_TZ,
    SUPPORTED_SESSIONS,
    evaluate_market_calendar_checker,
    evaluate_session_time_checker,
    session_rules_v1,
)

# In-memory latest evaluation (single-process; deterministic and test-friendly).
_LATEST_SESSION: SessionEvaluation | None = None


def _deterministic_session_id(evaluated_at_iso: str) -> str:
    compact = evaluated_at_iso.replace("-", "").replace(":", "").replace(".000", "").replace("Z", "Z")
    return f"sr_{compact}"


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
            "calendar_mode": "us_equities_basic",
            "latest_session_id": (latest.session_id if latest else None),
            "next_action": "Evaluate current or supplied timestamp to produce session context.",
        },
        supported_sessions=list(SUPPORTED_SESSIONS),
        checkers=[
            {"key": "session_time_checker", "label": "Session Time Checker", "status": "ready", "uses_llm": False},
            {"key": "market_calendar_checker", "label": "Market Calendar Checker", "status": "ready", "uses_llm": False},
        ],
    )


def _parse_timestamp_to_ct(request: SessionEvaluateRequest) -> tuple[datetime | None, str | None]:
    """
    Parse request timestamp and return datetime in Central Time, or (None, error_message).

    v1 supports:
    - use_current_time: server UTC -> Central
    - ISO-8601 timestamp with offset (preferred)
    - naive timestamps interpreted in provided timezone (default America/Chicago)
    """
    if request.use_current_time:
        return (datetime.now(tz=ZoneInfo("UTC")).astimezone(CT_TZ), None)

    if not request.timestamp:
        return (None, "No timestamp provided and use_current_time is false.")

    try:
        dt = datetime.fromisoformat(request.timestamp)
    except Exception as e:
        return (None, f"Failed to parse timestamp: {e}")

    try:
        if dt.tzinfo is None:
            tz = ZoneInfo(request.timezone or "America/Chicago")
            dt = dt.replace(tzinfo=tz)
        dt_ct = dt.astimezone(CT_TZ)
        return (dt_ct, None)
    except Exception as e:
        return (None, f"Failed to apply timezone conversion: {e}")


def evaluate_session(request: SessionEvaluateRequest) -> dict[str, Any]:
    """
    Deterministic Stage-3 session routing.

    This is an AI-Agent *without* an LLM:
    it observes time/session state, evaluates constraints, outputs a session context,
    and stores the latest state.
    """
    global _LATEST_SESSION

    # v1 market support
    market = (request.market or "").strip().lower()
    if market != "us_equities":
        evaluated_at = iso_utc_now()
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
        return {"status": "ok", "session": session.model_dump()}

    dt_ct, err = _parse_timestamp_to_ct(request)
    evaluated_at = iso_utc_now()
    if err or dt_ct is None:
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
            blocked_workflow_bias=[{"workflow": "trade_execution", "reason": "Session timestamp parsing failed."}],
            session_notes=[err or "Unknown parsing error."],
            next_action="Provide a valid ISO timestamp with timezone offset, or set use_current_time=true.",
        )
        _LATEST_SESSION = session
        return {"status": "ok", "session": session.model_dump()}

    # Checkers (kept simple in v1 but included for traceability)
    _ = evaluate_session_time_checker(dt_ct)
    _ = evaluate_market_calendar_checker(dt_ct)

    result = session_rules_v1(dt_ct)
    market_date = dt_ct.date().isoformat()

    session = SessionEvaluation(
        session_id=_deterministic_session_id(evaluated_at),
        session=result.session,
        market="us_equities",
        timezone="America/Chicago",
        evaluated_at=evaluated_at,
        market_date=market_date,
        is_trading_day=result.is_trading_day,
        is_holiday=result.is_holiday,
        allowed_workflow_bias=result.allowed_workflow_bias,
        blocked_workflow_bias=result.blocked_workflow_bias,
        session_notes=result.session_notes,
        next_action=result.next_action,
    )

    _LATEST_SESSION = session
    return {"status": "ok", "session": session.model_dump()}

