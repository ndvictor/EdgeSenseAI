"""Runtime gate config service.

Single source of truth for the **trading gates** exposed to the UI / API.

Conceptually it is a thin, audited facade over ``runtime_settings.json`` (already
managed by ``app/core/runtime_settings_store.py``) plus the effective-runtime
resolver. **Reads** use explicit process env first (Azure Portal / Container App
env), then ``runtime_settings.json``, then pydantic defaults. **Writes** persist
to ``runtime_settings.json``. It exists so:

1. The UI / API can read a *strictly-typed* gate snapshot without scanning
   the full legacy settings dict.
2. Mutations go through one validator that enforces hard safety invariants
   (e.g. live trading requires broker execution + human approval, agent
   live submission requires both LIVE_TRADING_ENABLED and BROKER_EXECUTION_ENABLED).
3. Every mutation writes an audit record (``updated_at``, ``updated_by_email``,
   ``change_reason``, prev/new values) so paper -> live transitions are
   recoverable from logs.

LOCKED CONVENTION
-----------------
Percent gates are stored as **human-readable percent** values (``0.5`` means
``0.5%``). Backend services convert to a fraction exactly once via
``_percent_to_fraction``. The UI MUST present and edit them as percent. Do not
multiply or divide by 100 here.

This module **never** calls a broker. It is config only.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.effective_runtime import (
    effective_bool,
    effective_float,
    effective_int,
    effective_str,
)
from app.core.runtime_settings_store import (
    load_runtime_settings,
    save_runtime_settings,
)
from app.core.settings import settings


# ---------------------------------------------------------------------------
# Authority levels & allowed combinations
# ---------------------------------------------------------------------------

OwnerAuthorityLevel = Literal[
    "view_only",
    "paper_manual",
    "paper_auto",
    "live_submit",
]

ALLOWED_AUTHORITY_LEVELS: tuple[str, ...] = (
    "view_only",
    "paper_manual",
    "paper_auto",
    "live_submit",
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class ReasoningGates(BaseModel):
    """Gates that decide whether DeepAgents reasoning runs at all."""

    model_config = ConfigDict(extra="forbid")

    workflow_enabled: bool
    agent_reasoning_enabled: bool


class PaperGates(BaseModel):
    """Gates that control paper trading simulation."""

    model_config = ConfigDict(extra="forbid")

    paper_trading_enabled: bool
    agent_can_create_paper_plans: bool
    agent_can_submit_paper_orders: bool
    agent_can_auto_submit_paper_orders: bool


class LiveGates(BaseModel):
    """Gates that control live broker execution.

    Defaults are ``False``. These can only be turned on through the gate
    update endpoint, with explicit owner confirmation handled at the route
    layer. ``agent_can_submit_live_orders`` is force-gated by
    ``live_trading_enabled`` and ``broker_execution_enabled`` in
    ``Settings.agent_capability_flags``.
    """

    model_config = ConfigDict(extra="forbid")

    live_trading_enabled: bool
    broker_execution_enabled: bool
    execution_agent_enabled: bool
    require_human_approval: bool
    owner_authority_level: OwnerAuthorityLevel
    agent_can_submit_live_orders: bool


class RiskGates(BaseModel):
    """Risk / account gates.

    All percent fields use the LOCKED PERCENT CONVENTION (``0.5`` = ``0.5%``).
    """

    model_config = ConfigDict(extra="forbid")

    max_risk_per_trade_pct: float = Field(ge=0.0, le=100.0)
    max_daily_loss_pct: float = Field(ge=0.0, le=100.0)
    max_position_notional_pct: float = Field(ge=0.0, le=100.0)
    max_open_positions: int = Field(ge=0, le=100)
    max_trades_per_day: int = Field(ge=0, le=500)
    min_expected_r_after_costs: float = Field(ge=0.0, le=100.0)
    max_liquidity_participation_pct: float = Field(ge=0.0, le=100.0)


class GateAudit(BaseModel):
    """Audit metadata for the most recent gate mutation."""

    model_config = ConfigDict(extra="forbid")

    updated_at: str | None = None
    updated_by_email: str | None = None
    change_reason: str | None = None


class TradingGatesSnapshot(BaseModel):
    """Strictly-typed gate snapshot returned to the UI."""

    model_config = ConfigDict(extra="forbid")

    reasoning: ReasoningGates
    paper: PaperGates
    live: LiveGates
    risk: RiskGates
    audit: GateAudit
    safety_warnings: list[str] = Field(default_factory=list)
    # Always-true on this endpoint surface: nothing here calls a broker.
    broker_called: Literal[False] = False


# ---------------------------------------------------------------------------
# Update payload
# ---------------------------------------------------------------------------


class TradingGatesUpdate(BaseModel):
    """Partial update for trading gates.

    Any field left ``None`` is left unchanged. Validation runs after the merge
    via :func:`_apply_and_validate` so cross-field invariants stay enforced
    (e.g. you cannot enable ``live_trading_enabled`` without
    ``broker_execution_enabled`` + ``require_human_approval``).
    """

    model_config = ConfigDict(extra="forbid")

    # Reasoning
    workflow_enabled: bool | None = None
    agent_reasoning_enabled: bool | None = None
    # Paper
    paper_trading_enabled: bool | None = None
    agent_can_create_paper_plans: bool | None = None
    agent_can_submit_paper_orders: bool | None = None
    agent_can_auto_submit_paper_orders: bool | None = None
    # Live
    live_trading_enabled: bool | None = None
    broker_execution_enabled: bool | None = None
    execution_agent_enabled: bool | None = None
    require_human_approval: bool | None = None
    owner_authority_level: OwnerAuthorityLevel | None = None
    agent_can_submit_live_orders: bool | None = None
    # Risk
    max_risk_per_trade_pct: float | None = None
    max_daily_loss_pct: float | None = None
    max_position_notional_pct: float | None = None
    max_open_positions: int | None = None
    max_trades_per_day: int | None = None
    min_expected_r_after_costs: float | None = None
    max_liquidity_participation_pct: float | None = None
    # Audit metadata
    change_reason: str | None = Field(default=None, max_length=500)
    confirm_live: bool | None = None

    @field_validator(
        "max_risk_per_trade_pct",
        "max_daily_loss_pct",
        "max_position_notional_pct",
        "min_expected_r_after_costs",
        "max_liquidity_participation_pct",
    )
    @classmethod
    def _percent_bounds(cls, value: float | None) -> float | None:
        if value is None:
            return value
        if value < 0.0 or value > 100.0:
            raise ValueError("percent fields must be between 0 and 100 (locked convention: 0.5 = 0.5%)")
        return value


# ---------------------------------------------------------------------------
# Read path
# ---------------------------------------------------------------------------


@dataclass
class _Merged:
    """Intermediate effective view used by both read and write paths."""

    runtime: dict[str, Any]
    safety_warnings: list[str] = field(default_factory=list)


def _parse_env_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_bool(key: str) -> bool | None:
    """Return bool when the process env explicitly sets ``key``, else None."""
    raw = os.getenv(key)
    if raw is None:
        return None
    return _parse_env_bool(raw)


def _coalesce_bool(runtime: dict[str, Any], key: str, settings_attr: str | None = None) -> bool:
    """Effective gate boolean: explicit env > runtime_settings.json > Settings default."""
    env_val = _env_bool(key)
    if env_val is not None:
        return env_val
    if key in runtime:
        return bool(runtime[key])
    return effective_bool(key)


def _coalesce_float(runtime: dict[str, Any], key: str, default: float) -> float:
    if key in runtime:
        try:
            return float(runtime[key])
        except (TypeError, ValueError):
            return default
    value = effective_float(key)
    if value == 0.0 and key not in {"MAX_RISK_PER_TRADE_PCT", "MAX_DAILY_LOSS_PCT"}:
        return default
    return value if value != 0.0 else default


def _coalesce_int(runtime: dict[str, Any], key: str, default: int) -> int:
    if key in runtime:
        try:
            return int(runtime[key])
        except (TypeError, ValueError):
            return default
    value = effective_int(key)
    return value or default


def _coalesce_str(runtime: dict[str, Any], key: str, default: str) -> str:
    env_val = os.getenv(key)
    if env_val is not None and str(env_val).strip():
        return str(env_val).strip()
    if key in runtime:
        raw = runtime[key]
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    value = effective_str(key)
    return value.strip() if value and value.strip() else default


def _resolve_authority_level(runtime: dict[str, Any]) -> OwnerAuthorityLevel:
    raw = _coalesce_str(runtime, "OWNER_AUTHORITY_LEVEL", "paper_manual").lower()
    if raw not in ALLOWED_AUTHORITY_LEVELS:
        return "paper_manual"
    return raw  # type: ignore[return-value]


def _compute_safety_warnings(snapshot: TradingGatesSnapshot) -> list[str]:
    warnings: list[str] = []
    paper = snapshot.paper
    live = snapshot.live

    if live.live_trading_enabled and not live.broker_execution_enabled:
        warnings.append("live_trading_enabled but broker_execution_enabled is false; live RUN will be blocked")
    if live.live_trading_enabled and not live.require_human_approval:
        warnings.append("live_trading_enabled without require_human_approval is unsafe")
    if live.agent_can_submit_live_orders and not (live.live_trading_enabled and live.broker_execution_enabled):
        warnings.append("agent_can_submit_live_orders is set but live gates are off; effective live submit is disabled")
    if paper.agent_can_auto_submit_paper_orders and not paper.agent_can_submit_paper_orders:
        warnings.append("agent_can_auto_submit_paper_orders requires agent_can_submit_paper_orders")
    if paper.agent_can_auto_submit_paper_orders and not paper.paper_trading_enabled:
        warnings.append("agent_can_auto_submit_paper_orders requires paper_trading_enabled")
    if live.owner_authority_level == "live_submit" and not live.live_trading_enabled:
        warnings.append("owner_authority_level=live_submit but live_trading_enabled is false")
    if live.owner_authority_level == "paper_auto" and not paper.agent_can_auto_submit_paper_orders:
        warnings.append("owner_authority_level=paper_auto but agent_can_auto_submit_paper_orders is false")
    return warnings


def get_trading_gates() -> TradingGatesSnapshot:
    """Return the strictly-typed effective trading gate snapshot."""
    runtime = load_runtime_settings()

    reasoning = ReasoningGates(
        workflow_enabled=_coalesce_bool(runtime, "WORKFLOW_ENABLED"),
        agent_reasoning_enabled=_coalesce_bool(runtime, "AGENT_REASONING_ENABLED"),
    )
    paper = PaperGates(
        paper_trading_enabled=_coalesce_bool(runtime, "PAPER_TRADING_ENABLED"),
        agent_can_create_paper_plans=_coalesce_bool(runtime, "AGENT_CAN_CREATE_PAPER_PLANS"),
        agent_can_submit_paper_orders=_coalesce_bool(runtime, "AGENT_CAN_SUBMIT_PAPER_ORDERS"),
        agent_can_auto_submit_paper_orders=_coalesce_bool(runtime, "AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS"),
    )
    live = LiveGates(
        live_trading_enabled=_coalesce_bool(runtime, "LIVE_TRADING_ENABLED"),
        broker_execution_enabled=_coalesce_bool(runtime, "BROKER_EXECUTION_ENABLED"),
        execution_agent_enabled=_coalesce_bool(runtime, "EXECUTION_AGENT_ENABLED"),
        require_human_approval=_coalesce_bool(runtime, "REQUIRE_HUMAN_APPROVAL"),
        owner_authority_level=_resolve_authority_level(runtime),
        agent_can_submit_live_orders=_coalesce_bool(runtime, "AGENT_CAN_SUBMIT_LIVE_ORDERS"),
    )
    risk = RiskGates(
        max_risk_per_trade_pct=_coalesce_float(runtime, "MAX_RISK_PER_TRADE_PCT", 0.5),
        max_daily_loss_pct=_coalesce_float(runtime, "MAX_DAILY_LOSS_PCT", 1.5),
        max_position_notional_pct=_coalesce_float(runtime, "MAX_POSITION_NOTIONAL_PCT", 20.0),
        max_open_positions=_coalesce_int(runtime, "MAX_OPEN_POSITIONS", 1),
        max_trades_per_day=_coalesce_int(runtime, "MAX_TRADES_PER_DAY", 3),
        min_expected_r_after_costs=_coalesce_float(runtime, "MIN_EXPECTED_R_AFTER_COSTS", 1.5),
        max_liquidity_participation_pct=_coalesce_float(runtime, "MAX_LIQUIDITY_PARTICIPATION_PCT", 1.0),
    )
    audit = GateAudit(
        updated_at=runtime.get("GATES_UPDATED_AT") or runtime.get("UPDATED_AT"),
        updated_by_email=runtime.get("GATES_UPDATED_BY_EMAIL") or runtime.get("LAST_UPDATED_BY"),
        change_reason=runtime.get("GATES_CHANGE_REASON"),
    )

    snapshot = TradingGatesSnapshot(
        reasoning=reasoning,
        paper=paper,
        live=live,
        risk=risk,
        audit=audit,
        safety_warnings=[],
    )
    snapshot.safety_warnings = _compute_safety_warnings(snapshot)
    return snapshot


# ---------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------


class GateValidationError(ValueError):
    """Raised when a gate update violates a hard safety invariant."""


def _apply_update(runtime: dict[str, Any], update: TradingGatesUpdate) -> None:
    """Mutate ``runtime`` in-place from ``update``. Audit fields handled separately."""
    if update.workflow_enabled is not None:
        runtime["WORKFLOW_ENABLED"] = bool(update.workflow_enabled)
        if not bool(update.workflow_enabled):
            runtime["WORKFLOW_RUNNING"] = False
    if update.agent_reasoning_enabled is not None:
        runtime["AGENT_REASONING_ENABLED"] = bool(update.agent_reasoning_enabled)

    if update.paper_trading_enabled is not None:
        runtime["PAPER_TRADING_ENABLED"] = bool(update.paper_trading_enabled)
    if update.agent_can_create_paper_plans is not None:
        runtime["AGENT_CAN_CREATE_PAPER_PLANS"] = bool(update.agent_can_create_paper_plans)
    if update.agent_can_submit_paper_orders is not None:
        runtime["AGENT_CAN_SUBMIT_PAPER_ORDERS"] = bool(update.agent_can_submit_paper_orders)
    if update.agent_can_auto_submit_paper_orders is not None:
        runtime["AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS"] = bool(update.agent_can_auto_submit_paper_orders)

    if update.live_trading_enabled is not None:
        runtime["LIVE_TRADING_ENABLED"] = bool(update.live_trading_enabled)
    if update.broker_execution_enabled is not None:
        runtime["BROKER_EXECUTION_ENABLED"] = bool(update.broker_execution_enabled)
    if update.execution_agent_enabled is not None:
        runtime["EXECUTION_AGENT_ENABLED"] = bool(update.execution_agent_enabled)
    if update.require_human_approval is not None:
        runtime["REQUIRE_HUMAN_APPROVAL"] = bool(update.require_human_approval)
    if update.owner_authority_level is not None:
        runtime["OWNER_AUTHORITY_LEVEL"] = str(update.owner_authority_level)
    if update.agent_can_submit_live_orders is not None:
        runtime["AGENT_CAN_SUBMIT_LIVE_ORDERS"] = bool(update.agent_can_submit_live_orders)

    if update.max_risk_per_trade_pct is not None:
        runtime["MAX_RISK_PER_TRADE_PCT"] = float(update.max_risk_per_trade_pct)
        runtime["MAX_RISK_PER_TRADE_PERCENT"] = float(update.max_risk_per_trade_pct)
    if update.max_daily_loss_pct is not None:
        runtime["MAX_DAILY_LOSS_PCT"] = float(update.max_daily_loss_pct)
        runtime["MAX_DAILY_LOSS_PERCENT"] = float(update.max_daily_loss_pct)
    if update.max_position_notional_pct is not None:
        runtime["MAX_POSITION_NOTIONAL_PCT"] = float(update.max_position_notional_pct)
        runtime["MAX_POSITION_SIZE_PERCENT"] = float(update.max_position_notional_pct)
    if update.max_open_positions is not None:
        runtime["MAX_OPEN_POSITIONS"] = int(update.max_open_positions)
    if update.max_trades_per_day is not None:
        runtime["MAX_TRADES_PER_DAY"] = int(update.max_trades_per_day)
    if update.min_expected_r_after_costs is not None:
        runtime["MIN_EXPECTED_R_AFTER_COSTS"] = float(update.min_expected_r_after_costs)
        runtime["MIN_REWARD_RISK_RATIO"] = float(update.min_expected_r_after_costs)
    if update.max_liquidity_participation_pct is not None:
        runtime["MAX_LIQUIDITY_PARTICIPATION_PCT"] = float(update.max_liquidity_participation_pct)


def _validate_invariants(runtime: dict[str, Any], update: TradingGatesUpdate) -> None:
    """Reject merged configurations that break hard safety rules.

    The safety rules are:

    - ``live_trading_enabled`` requires ``broker_execution_enabled``.
    - ``live_trading_enabled`` requires ``require_human_approval`` (UI workflow
      can satisfy this with explicit confirmation per RUN, not by disabling
      approval globally).
    - ``broker_execution_enabled`` requires ``require_human_approval``.
    - Enabling ``live_trading_enabled`` in this update requires
      ``update.confirm_live=True``. This is the gate-level confirmation; the
      RUN endpoint also re-checks it per workflow run.
    - ``agent_can_auto_submit_paper_orders`` requires
      ``agent_can_submit_paper_orders`` and ``paper_trading_enabled``.
    - ``owner_authority_level=='live_submit'`` requires ``live_trading_enabled``
      and ``broker_execution_enabled``.
    - ``EMERGENCY_STOP`` overrides everything: cannot enable execution while
      emergency stop is set.
    """
    if runtime.get("EMERGENCY_STOP"):
        if bool(update.live_trading_enabled) or bool(update.broker_execution_enabled):
            raise GateValidationError("emergency_stop is active; disable EMERGENCY_STOP before enabling execution gates")

    live_on = bool(runtime.get("LIVE_TRADING_ENABLED"))
    broker_on = bool(runtime.get("BROKER_EXECUTION_ENABLED"))
    approval_on = bool(runtime.get("REQUIRE_HUMAN_APPROVAL"))
    paper_on = bool(runtime.get("PAPER_TRADING_ENABLED"))
    paper_submit = bool(runtime.get("AGENT_CAN_SUBMIT_PAPER_ORDERS"))
    paper_auto = bool(runtime.get("AGENT_CAN_AUTO_SUBMIT_PAPER_ORDERS"))
    authority = str(runtime.get("OWNER_AUTHORITY_LEVEL") or "").lower()

    if live_on and not broker_on:
        raise GateValidationError("cannot enable live_trading_enabled without broker_execution_enabled")
    if live_on and not approval_on:
        raise GateValidationError("cannot enable live_trading_enabled without require_human_approval")
    if broker_on and not approval_on:
        raise GateValidationError("cannot enable broker_execution_enabled without require_human_approval")

    if update.live_trading_enabled is True and not bool(update.confirm_live):
        raise GateValidationError("enabling live_trading_enabled requires confirm_live=true in the same request")

    if paper_auto and not paper_submit:
        raise GateValidationError("agent_can_auto_submit_paper_orders requires agent_can_submit_paper_orders")
    if paper_auto and not paper_on:
        raise GateValidationError("agent_can_auto_submit_paper_orders requires paper_trading_enabled")

    if authority == "live_submit" and not (live_on and broker_on):
        raise GateValidationError("owner_authority_level=live_submit requires live_trading_enabled and broker_execution_enabled")


def _stamp_audit(runtime: dict[str, Any], update: TradingGatesUpdate, *, updated_by_email: str | None) -> None:
    now_iso = datetime.now(timezone.utc).isoformat()
    runtime["GATES_UPDATED_AT"] = now_iso
    runtime["UPDATED_AT"] = now_iso  # legacy field; keep in sync
    if updated_by_email:
        runtime["GATES_UPDATED_BY_EMAIL"] = updated_by_email[:200]
        runtime["LAST_UPDATED_BY"] = updated_by_email[:200]
    if update.change_reason and update.change_reason.strip():
        runtime["GATES_CHANGE_REASON"] = update.change_reason.strip()[:500]
    else:
        runtime["GATES_CHANGE_REASON"] = None


def update_trading_gates(
    update: TradingGatesUpdate,
    *,
    updated_by_email: str | None = None,
) -> TradingGatesSnapshot:
    """Apply a partial gate update with validation, audit, and persistence.

    Raises:
        GateValidationError: if the merged configuration violates a hard
            safety invariant.
    """
    runtime = load_runtime_settings()
    _apply_update(runtime, update)
    _validate_invariants(runtime, update)
    _stamp_audit(runtime, update, updated_by_email=updated_by_email)
    save_runtime_settings(runtime)
    return get_trading_gates()


# ---------------------------------------------------------------------------
# Helpers consumed by other services (e.g. workflow run)
# ---------------------------------------------------------------------------


def can_run_paper_workflow() -> tuple[bool, list[str]]:
    """Return (allowed, reasons). True iff the paper workflow may start."""
    gates = get_trading_gates()
    reasons: list[str] = []
    if not gates.reasoning.workflow_enabled:
        reasons.append("workflow_enabled is false")
    if not gates.paper.paper_trading_enabled:
        reasons.append("paper_trading_enabled is false")
    return (len(reasons) == 0, reasons)


def can_run_live_workflow() -> tuple[bool, list[str]]:
    """Return (allowed, reasons). True iff the live workflow may start.

    This only checks gate config. The RUN endpoint must *also* check the
    per-request owner confirmation field.
    """
    gates = get_trading_gates()
    reasons: list[str] = []
    if not gates.reasoning.workflow_enabled:
        reasons.append("workflow_enabled is false")
    if not gates.live.live_trading_enabled:
        reasons.append("live_trading_enabled is false")
    if not gates.live.broker_execution_enabled:
        reasons.append("broker_execution_enabled is false")
    if not gates.live.require_human_approval:
        reasons.append("require_human_approval is false")
    if gates.live.owner_authority_level != "live_submit":
        reasons.append("owner_authority_level is not live_submit")
    return (len(reasons) == 0, reasons)


__all__ = [
    "ALLOWED_AUTHORITY_LEVELS",
    "GateAudit",
    "GateValidationError",
    "LiveGates",
    "OwnerAuthorityLevel",
    "PaperGates",
    "ReasoningGates",
    "RiskGates",
    "TradingGatesSnapshot",
    "TradingGatesUpdate",
    "can_run_live_workflow",
    "can_run_paper_workflow",
    "get_trading_gates",
    "update_trading_gates",
]
