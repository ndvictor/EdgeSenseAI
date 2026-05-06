"""In-memory risk usage for execution (daily loss proxy, lockout). Not production ledger."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from threading import Lock

_LOCK = Lock()
_daily_loss_pct_used: float = 0.0
_lockout_until: datetime | None = None
_last_reset_utc_date: str = ""


def _ensure_day() -> None:
    global _daily_loss_pct_used, _lockout_until, _last_reset_utc_date
    today = date.today().isoformat()
    if _last_reset_utc_date != today:
        _daily_loss_pct_used = 0.0
        _lockout_until = None
        _last_reset_utc_date = today


def get_daily_loss_pct_used() -> float:
    with _LOCK:
        _ensure_day()
        return _daily_loss_pct_used


def record_loss_pct(pct: float) -> None:
    global _daily_loss_pct_used
    with _LOCK:
        _ensure_day()
        _daily_loss_pct_used += max(0.0, pct)


def is_risk_lockout() -> bool:
    with _LOCK:
        _ensure_day()
        if _lockout_until is None:
            return False
        return datetime.now(timezone.utc) < _lockout_until


def set_risk_lockout_minutes(minutes: int) -> None:
    global _lockout_until
    with _LOCK:
        _ensure_day()
        _lockout_until = datetime.now(timezone.utc) + timedelta(minutes=max(1, minutes))


def set_daily_loss_pct_for_tests(pct: float) -> None:
    """Test-only: force daily loss usage."""
    global _daily_loss_pct_used
    with _LOCK:
        _ensure_day()
        _daily_loss_pct_used = pct


def reset_execution_risk_state_for_tests() -> None:
    global _daily_loss_pct_used, _lockout_until, _last_reset_utc_date
    with _LOCK:
        _daily_loss_pct_used = 0.0
        _lockout_until = None
        _last_reset_utc_date = ""
