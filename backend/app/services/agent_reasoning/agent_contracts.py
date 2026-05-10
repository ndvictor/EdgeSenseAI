from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


ReasoningStatus = Literal["completed", "disabled", "llm_unavailable", "audit_rejected", "blocked"]
ReasoningDecision = Literal[
    "candidate_selected",
    "no_qualified_setup",
    "data_unavailable",
    "blocked",
    "needs_more_evidence",
    "plan_only",
]


class DataUsed(BaseModel):
    provider_chain: list[str] = Field(default_factory=list)
    feature_row_id: str | None = None
    scanner_diagnostics: dict[str, Any] = Field(default_factory=dict)
    worker_status: dict[str, Any] = Field(default_factory=dict)
    symbols: list[str] = Field(default_factory=list)


class AgentReasoningDecision(BaseModel):
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
    ) -> "AgentReasoningDecision":
        return cls(
            agent_key=agent_key,
            reasoning_status=reasoning_status,
            decision=decision,
            confidence=0.0,
            thesis=thesis or "AI reasoning unavailable or disabled. Deterministic workflow gates remain authoritative.",
            bull_case=[],
            bear_case=[],
            missing_evidence=missing_evidence or ["agent_reasoning_unavailable"],
            risk_notes=["No LLM reasoning was used for trade decision."],
            recommended_next_action="continue_deterministic_workflow",
            hard_blockers=[],
            soft_warnings=soft_warnings or [],
            data_used=DataUsed(provider_chain=["deterministic_workflow"]),
            llm_used=False,
        )


class EvidencePack(BaseModel):
    workflow_run_id: str
    orchestrator_run_id: str | None = None
    agent_key: str
    allowed_symbols: list[str]
    candidate_features: list[dict[str, Any]] = Field(default_factory=list)
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
    proof_evidence_status: dict[str, Any] = Field(default_factory=dict)
    hard_rules: list[str]
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().replace(microsecond=0).isoformat() + "Z")

    def has_candidates(self) -> bool:
        return bool(self.allowed_symbols)
