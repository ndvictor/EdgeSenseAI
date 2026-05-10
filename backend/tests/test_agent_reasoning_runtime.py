from __future__ import annotations

from app.services.agent_reasoning.agent_contracts import AgentReasoningDecision, DataUsed, EvidencePack
from app.services.agent_reasoning.decision_auditor import DecisionAuditor
from app.services.agent_reasoning.evidence_pack_builder import EvidencePackBuilder
from app.services.agent_reasoning.reasoning_runtime import ReasoningRuntime


def test_evidence_pack_contains_only_real_workflow_symbols():
    state = {
        "workflow_run_id": "wr_test",
        "scanner_candidates": [{"symbol": "TSLA", "provider_name": "alpaca", "data_quality": "real"}],
        "feature_rows": [{"symbol": "TSLA", "last_price": 100.0, "volume": 1000, "provider_name": "alpaca"}],
        "symbols": ["FAKE"],  # request symbols alone must not become evidence unless backed by rows
    }

    evidence = EvidencePackBuilder.build(state, "alpha_engine_agent")

    assert evidence.allowed_symbols == ["TSLA"]
    assert evidence.provider_status["provider_chain"] == ["alpaca"]


def test_reasoning_disabled_returns_safe_fallback(monkeypatch):
    monkeypatch.delenv("AGENT_REASONING_ENABLED", raising=False)
    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="alpha_engine_agent",
        allowed_symbols=["TSLA"],
        hard_rules=["Do not invent symbols"],
    )

    decision = ReasoningRuntime.reason_with_evidence(evidence)

    assert decision.reasoning_status == "disabled"
    assert decision.llm_used is False
    assert decision.decision == "needs_more_evidence"


def test_reasoning_disabled_zero_candidates_returns_no_qualified_setup(monkeypatch):
    monkeypatch.delenv("AGENT_REASONING_ENABLED", raising=False)
    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="alpha_engine_agent",
        allowed_symbols=[],
        hard_rules=["Zero candidates must propagate as no_qualified_setup"],
    )

    decision = ReasoningRuntime.reason_with_evidence(evidence)

    assert decision.reasoning_status == "disabled"
    assert decision.decision == "no_qualified_setup"


def test_auditor_rejects_unknown_symbol():
    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="alpha_engine_agent",
        allowed_symbols=["TSLA"],
        hard_rules=["Do not invent symbols"],
    )
    decision = AgentReasoningDecision(
        agent_key="alpha_engine_agent",
        reasoning_status="completed",
        decision="candidate_selected",
        confidence=0.7,
        thesis="NVDA looks strong, but it is not in evidence.",
        data_used=DataUsed(provider_chain=["alpaca"], symbols=["NVDA"]),
        llm_used=True,
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "blocked"
    assert any("hallucinated_symbol:NVDA" == x for x in audited.hard_blockers)


def test_auditor_rejects_recommendation_with_zero_candidates():
    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="alpha_engine_agent",
        allowed_symbols=[],
        hard_rules=["Zero candidates must propagate as no_qualified_setup"],
    )
    decision = AgentReasoningDecision(
        agent_key="alpha_engine_agent",
        reasoning_status="completed",
        decision="candidate_selected",
        confidence=0.8,
        thesis="Candidate selected even though evidence is empty.",
        data_used=DataUsed(provider_chain=["alpaca"], symbols=[]),
        llm_used=True,
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "no_qualified_setup"
    assert "recommendation_with_zero_candidates" in audited.hard_blockers


def test_auditor_rejects_broker_submit_language():
    evidence = EvidencePack(
        workflow_run_id="wr_test",
        agent_key="execution_planner_agent",
        allowed_symbols=["TSLA"],
        hard_rules=["Do not submit orders"],
    )
    decision = AgentReasoningDecision(
        agent_key="execution_planner_agent",
        reasoning_status="completed",
        decision="plan_only",
        confidence=0.8,
        thesis="Plan only, but submit_order should be rejected.",
        data_used=DataUsed(provider_chain=["alpaca"], symbols=["TSLA"]),
        llm_used=True,
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "blocked"
    assert any(x.startswith("forbidden_action:submit_order") for x in audited.hard_blockers)
