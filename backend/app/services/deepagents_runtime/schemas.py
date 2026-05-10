"""Pydantic schemas for the DeepAgents advisory runtime."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ReasoningStatus = Literal["completed", "disabled", "llm_unavailable", "audit_rejected", "blocked"]
ReasoningDecision = Literal[
    "candidate_selected",
    "candidates_selected",
    "no_qualified_setup",
    "data_unavailable",
    "blocked",
    "needs_more_evidence",
    "plan_only",
    "feasible",
    "infeasible",
    "degraded",
]
OwnerAuthorityLevel = Literal["read_only", "advise", "paper_plan", "paper_submit", "live_submit"]


class OwnerAuthority(BaseModel):
    """Owner-policy authority granted to the agent runtime.

    This is the *resolved* capability surface (already gated by global trading
    flags); DeepAgents never escalates beyond it. The supervisor itself is
    advisory only; broker calls and order submission belong to the deterministic
    workflow paths and require ``can_submit_paper_orders`` /
    ``can_submit_live_orders`` to be ``True``.
    """

    level: OwnerAuthorityLevel = "advise"
    can_recommend_trades: bool = False
    can_create_paper_plans: bool = False
    can_create_approval_requests: bool = False
    can_submit_paper_orders: bool = False
    can_submit_live_orders: bool = False
    require_human_approval: bool = True

    @classmethod
    def read_only(cls) -> "OwnerAuthority":
        return cls(
            level="read_only",
            can_recommend_trades=False,
            can_create_paper_plans=False,
            can_create_approval_requests=False,
            can_submit_paper_orders=False,
            can_submit_live_orders=False,
            require_human_approval=True,
        )


class DataUsed(BaseModel):
    provider_chain: list[str] = Field(default_factory=list)
    feature_row_id: str | None = None
    scanner_diagnostics: dict[str, Any] = Field(default_factory=dict)
    worker_status: dict[str, Any] = Field(default_factory=dict)
    symbols: list[str] = Field(default_factory=list)
    prices: dict[str, float] = Field(default_factory=dict)


class DeepAgentToolSpec(BaseModel):
    """Declarative description of a tool callable by the supervisor or a subagent."""

    name: str
    description: str = ""
    json_schema: dict[str, Any] = Field(default_factory=dict)


class DeepAgentRunContext(BaseModel):
    """Immutable-enough context passed through a deep-agent run."""

    workflow_run_id: str | None = None
    orchestrator_run_id: str | None = None
    trace_id: str | None = None
    mode: Literal["dry_run", "paper", "live_shadow"] = "dry_run"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidencePack(BaseModel):
    """Real-data-only evidence available to DeepAgents.

    The pack is intentionally closed-world: DeepAgents may reason only about
    symbols, prices, and fields represented here.
    """

    model_config = {"protected_namespaces": ()}

    workflow_run_id: str
    orchestrator_run_id: str | None = None
    agent_key: str
    allowed_symbols: list[str]
    scanner_candidates: list[dict[str, Any]] = Field(default_factory=list)
    candidate_features: list[dict[str, Any]] = Field(default_factory=list)
    candidate_rankings: list[dict[str, Any]] = Field(default_factory=list)
    scanner_diagnostics: dict[str, Any] = Field(default_factory=dict)
    worker_status_summary: dict[str, Any] = Field(default_factory=dict)
    provider_status: dict[str, Any] = Field(default_factory=dict)
    market_session: dict[str, Any] = Field(default_factory=dict)
    market_condition: dict[str, Any] = Field(default_factory=dict)
    account_policy: dict[str, Any] = Field(default_factory=dict)
    alpha_recommendation: dict[str, Any] = Field(default_factory=dict)
    strategy_registry: dict[str, Any] = Field(default_factory=dict)
    model_registry: dict[str, Any] = Field(default_factory=dict)
    risk_sizing_context: dict[str, Any] = Field(default_factory=dict)
    tool_result: dict[str, Any] = Field(default_factory=dict)
    execution_plan: dict[str, Any] = Field(default_factory=dict)
    proof_evidence_status: dict[str, Any] = Field(default_factory=dict)
    known_prices: dict[str, list[float]] = Field(default_factory=dict)
    owner_authority: OwnerAuthority = Field(default_factory=OwnerAuthority.read_only)
    hard_rules: list[str]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().replace(microsecond=0).isoformat() + "Z")

    def has_candidates(self) -> bool:
        return bool(self.allowed_symbols)


class DeepAgentDecision(BaseModel):
    model_config = {"protected_namespaces": ()}

    agent_key: str
    reasoning_status: ReasoningStatus
    decision: ReasoningDecision
    confidence: float = Field(ge=0.0, le=1.0)
    thesis: str
    bull_case: list[str] = Field(default_factory=list)
    bear_case: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    risk_notes: list[str] = Field(default_factory=list)
    recommended_next_action: str | None = None
    hard_blockers: list[str] = Field(default_factory=list)
    soft_warnings: list[str] = Field(default_factory=list)
    data_used: DataUsed = Field(default_factory=DataUsed)
    llm_used: bool = False
    llm_model: str | None = None
    prompt_hash: str | None = None
    output_hash: str | None = None
    # Watchlist agentic-decision fields (optional; populated for
    # ``watchlist_builder_agent`` only). Other agent keys leave these empty.
    usable_symbols: list[str] = Field(default_factory=list)
    rejected_symbols: list[dict[str, Any]] = Field(default_factory=list)
    candidate_rankings: list[dict[str, Any]] = Field(default_factory=list)
    candidate_source: str | None = None
    # Alpha Engine agentic-decision fields (optional; populated for
    # ``alpha_engine_agent`` only). These mirror the deterministic Alpha
    # recommendation shape so an accepted audited decision can replace the
    # alpha output without touching broker/execution code.
    symbol: str | None = None
    strategy_key: str | None = None
    setup_type: str | None = None
    scanner_score: float | None = None
    model_score: float | None = None
    evidence_score: float | None = None
    small_account_score: float | None = None
    strategy_fit_score: float | None = None
    final_score: float | None = None
    entry_plan: dict[str, Any] = Field(default_factory=dict)
    recommendation_id: str | None = None
    predicted_return_pct: float | None = None
    predicted_return_r: float | None = None
    predicted_win_probability: float | None = None
    predicted_expected_value_r: float | None = None
    prediction_horizon_minutes: int | None = None
    prediction_model_key: str | None = None
    prediction_reason: str | None = None
    # Account / portfolio feasibility agent fields (optional; populated for
    # ``small_account_feasibility_agent`` only). The deterministic
    # ``evaluate_account_feasibility`` tool result is the source of truth for
    # the numeric sizing fields; the DeepAgent may explain feasibility but
    # cannot override the math (auditor enforces consistency within tolerance).
    account_feasibility_decision: str | None = None
    small_account_decision: str | None = None
    fractional_feasible: bool | None = None
    fractional_trading_enabled: bool | None = None
    position_size_shares: float | None = None
    position_size_notional: float | None = None
    risk_dollars: float | None = None
    risk_per_share: float | None = None
    max_loss_if_stopped: float | None = None
    expected_profit_dollars: float | None = None
    expected_value_dollars: float | None = None
    notional_usage_pct: float | None = None
    buying_power_usage_pct: float | None = None
    liquidity_participation_pct: float | None = None
    spread_cost_estimate: float | None = None
    slippage_cost_estimate: float | None = None
    expected_r_after_costs: float | None = None
    feasible_symbols: list[str] = Field(default_factory=list)
    infeasible_symbols: list[str] = Field(default_factory=list)
    submitted_order: bool = False
    broker_called: bool = False
    llm_used_for_trade_decision: bool = False

    @field_validator("confidence")
    @classmethod
    def round_confidence(cls, value: float) -> float:
        return round(float(value), 4)

    @classmethod
    def safe_fallback(
        cls,
        *,
        agent_key: str,
        decision: ReasoningDecision = "no_qualified_setup",
        reasoning_status: ReasoningStatus = "llm_unavailable",
        thesis: str | None = None,
        missing_evidence: list[str] | None = None,
        soft_warnings: list[str] | None = None,
        hard_blockers: list[str] | None = None,
    ) -> "DeepAgentDecision":
        return cls(
            agent_key=agent_key,
            reasoning_status=reasoning_status,
            decision=decision,
            confidence=0.0,
            thesis=thesis or "DeepAgent reasoning unavailable or disabled. Deterministic workflow gates remain authoritative.",
            bull_case=[],
            bear_case=[],
            missing_evidence=missing_evidence or ["deepagent_reasoning_unavailable"],
            risk_notes=["No LLM reasoning was used for trade decision."],
            recommended_next_action="continue_deterministic_workflow",
            hard_blockers=hard_blockers or [],
            soft_warnings=soft_warnings or [],
            data_used=DataUsed(provider_chain=["deterministic_workflow"]),
            llm_used=False,
            submitted_order=False,
            broker_called=False,
            llm_used_for_trade_decision=False,
        )
