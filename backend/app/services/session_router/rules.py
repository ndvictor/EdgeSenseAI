from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from zoneinfo import ZoneInfo

from app.services.session_router.models import SessionKey


@dataclass(frozen=True)
class CheckerEval:
    status: str  # pass | warn | fail (kept simple for v1)
    message: str


@dataclass(frozen=True)
class SessionRuleResult:
    session: SessionKey
    is_trading_day: bool
    is_holiday: bool
    allowed_workflow_bias: list[str]
    blocked_workflow_bias: list[dict]
    session_notes: list[str]
    next_action: str


SUPPORTED_SESSIONS: list[SessionKey] = [
    "pre_market",
    "market_open",
    "post_market",
    "after_hours",
    "closed",
    "holiday",
    "unknown",
]


CT_TZ = ZoneInfo("America/Chicago")


def evaluate_session_time_checker(dt_ct: datetime) -> CheckerEval:
    if dt_ct.tzinfo is None:
        return CheckerEval("fail", "Timestamp is not timezone-aware.")
    return CheckerEval("pass", "Timestamp parsed and converted to session timezone.")


def evaluate_market_calendar_checker(dt_ct: datetime) -> CheckerEval:
    # v1 intentionally does not use external market calendar APIs.
    # We only apply a deterministic weekend rule and mark holidays as not implemented.
    if dt_ct.weekday() >= 5:
        return CheckerEval("pass", "Weekend detected by deterministic calendar rule.")
    return CheckerEval("pass", "Weekday detected by deterministic calendar rule (holidays not implemented in v1).")


def _in_range(t: time, start: time, end: time) -> bool:
    """Inclusive range where start <= end (same-day interval)."""
    return start <= t <= end


def _is_weekend(dt_ct: datetime) -> bool:
    return dt_ct.weekday() >= 5


def session_rules_v1(dt_ct: datetime) -> SessionRuleResult:
    """
    US equities basic session rules v1 using Central Time.

    No external holiday calendar in v1. Holidays are reported as false.
    """
    t = dt_ct.timetz()

    # A) Weekend rule
    if _is_weekend(dt_ct):
        return SessionRuleResult(
            session="closed",
            is_trading_day=False,
            is_holiday=False,
            allowed_workflow_bias=["adjusted_research_path", "backtest_queue_path", "observe_only_path"],
            blocked_workflow_bias=[
                {"workflow": "trade_execution", "reason": "Market is closed on weekend."},
            ],
            session_notes=["Market is closed (weekend). Focus on research, review, and preparation workflows."],
            next_action="Send session context to Stage 5 Workflow Router.",
        )

    # Time windows (Central Time)
    pre_market_start = time(3, 0)
    pre_market_end = time(8, 29)
    market_open_start = time(8, 30)
    market_open_end = time(15, 0)
    post_market_start = time(15, 1)
    post_market_end = time(19, 0)

    # B) Market open
    if _in_range(t, market_open_start, market_open_end):
        return SessionRuleResult(
            session="market_open",
            is_trading_day=True,
            is_holiday=False,
            allowed_workflow_bias=["baseline_fast_path", "paper_only_path", "observe_only_path"],
            blocked_workflow_bias=[],
            session_notes=["Market is open. Fast-path workflow may be allowed if downstream checks pass."],
            next_action="Send session context to Stage 5 Workflow Router.",
        )

    # C) Pre-market
    if _in_range(t, pre_market_start, pre_market_end):
        return SessionRuleResult(
            session="pre_market",
            is_trading_day=True,
            is_holiday=False,
            allowed_workflow_bias=["adjusted_research_path", "backtest_queue_path", "paper_only_path"],
            blocked_workflow_bias=[
                {"workflow": "trade_execution", "reason": "Pre-market execution not enabled in v1."},
            ],
            session_notes=["Pre-market session. Prefer preparation and validation workflows."],
            next_action="Send session context to Stage 5 Workflow Router.",
        )

    # D) Post-market
    if _in_range(t, post_market_start, post_market_end):
        return SessionRuleResult(
            session="post_market",
            is_trading_day=True,
            is_holiday=False,
            allowed_workflow_bias=["adjusted_research_path", "backtest_queue_path", "learning_loop"],
            blocked_workflow_bias=[
                {"workflow": "trade_execution", "reason": "Post-market execution not enabled in v1."},
            ],
            session_notes=["Post-market session. Prefer review, learning loop, and preparation workflows."],
            next_action="Send session context to Stage 5 Workflow Router.",
        )

    # E) After-hours (all other weekday times)
    return SessionRuleResult(
        session="after_hours",
        is_trading_day=True,
        is_holiday=False,
        allowed_workflow_bias=["adjusted_research_path", "backtest_queue_path", "learning_loop", "observe_only_path"],
        blocked_workflow_bias=[
            {"workflow": "trade_execution", "reason": "Outside regular market session."},
        ],
        session_notes=["After-hours session. Avoid execution; focus on research/backtest/prep."],
        next_action="Send session context to Stage 5 Workflow Router.",
    )

