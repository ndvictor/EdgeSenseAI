"""Pydantic models for paper autonomy stores.

All records are simulation-only. ``broker_called`` is permanently ``False`` and
must never be flipped, even at construction time. Only ``submitted_order`` may
be ``True`` on a paper-route record after explicit authorization.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


PaperOrderStatus = Literal["paper_submitted", "paper_open", "paper_blocked", "paper_filled", "paper_cancelled"]
PaperPositionStatus = Literal["open", "closed"]
PaperSubmitRoute = Literal["none", "paper", "live"]


def iso_utc_now() -> str:
    """Timezone-aware UTC ISO timestamp truncated to seconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_paper_order_id() -> str:
    return f"po_{uuid4().hex[:12]}"


def new_paper_position_id() -> str:
    return f"pp_{uuid4().hex[:12]}"


class PaperOrderRecord(BaseModel):
    """Simulated paper order record. Never reaches a broker."""

    model_config = ConfigDict(protected_namespaces=())

    paper_order_id: str = Field(default_factory=new_paper_order_id)
    workflow_run_id: str
    orchestrator_run_id: str | None = None
    agent_run_id: str | None = None
    recommendation_id: str | None = None
    symbol: str
    strategy_key: str | None = None
    side: Literal["buy", "sell"] = "buy"
    order_type: Literal["limit", "market"] = "limit"
    time_in_force: Literal["day", "gtc"] = "day"
    entry: float
    stop: float
    target: float
    shares: float
    notional: float
    risk_dollars: float
    expected_profit_dollars: float | None = None
    expected_r_after_costs: float | None = None
    submit_route: PaperSubmitRoute = "paper"
    status: PaperOrderStatus = "paper_submitted"
    broker_called: Literal[False] = False
    submitted_order: bool = True
    source: Literal["paper_simulator"] = "paper_simulator"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=iso_utc_now)
    updated_at: str = Field(default_factory=iso_utc_now)


class PaperPositionRecord(BaseModel):
    """Simulated paper position. Mark-to-market against real quotes."""

    model_config = ConfigDict(protected_namespaces=())

    paper_position_id: str = Field(default_factory=new_paper_position_id)
    paper_order_id: str
    workflow_run_id: str
    orchestrator_run_id: str | None = None
    recommendation_id: str | None = None
    symbol: str
    strategy_key: str | None = None
    side: Literal["long"] = "long"
    entry_price: float
    stop_price: float
    target_price: float
    shares: float
    notional: float
    risk_dollars: float
    expected_profit_dollars: float | None = None
    expected_r_after_costs: float | None = None
    opened_at: str = Field(default_factory=iso_utc_now)
    status: PaperPositionStatus = "open"
    source: Literal["paper_simulator"] = "paper_simulator"
    broker_called: Literal[False] = False

    last_mark_price: float | None = None
    last_marked_at: str | None = None
    mfe: float = 0.0
    mae: float = 0.0
    closed_at: str | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    actual_return_pct: float | None = None
    actual_return_r: float | None = None
    hit_target: bool | None = None
    hit_stop: bool | None = None
    prediction_error_r: float | None = None


class PaperLearningOutcome(BaseModel):
    """Closed paper trade outcome record fed into learning_loop_agent."""

    trade_id: str
    paper_position_id: str | None = None
    workflow_run_id: str | None = None
    strategy_key: str
    symbol: str
    outcome_label: str
    outcome_status: str
    realized_pnl: float
    actual_return_r: float
    slippage_status: Literal["pass", "warn", "fail"] = "pass"
    rule_compliant: bool = True
    created_at: str = Field(default_factory=iso_utc_now)


def to_dict(record: BaseModel) -> dict[str, Any]:
    return record.model_dump(mode="python")
