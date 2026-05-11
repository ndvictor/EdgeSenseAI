"""Tests for ``DecisionAuditor`` — the DeepAgents output safety gate.

These tests verify:
- Unknown symbols in LLM output are rejected.
- Invented prices for allowed symbols are rejected.
- Broker / order-submission language is rejected.
- ``submitted_order`` and ``broker_called`` claims from the LLM are scrubbed.
- Recommendations against an empty evidence pack are downgraded.
"""

from __future__ import annotations

from app.services.deepagents_runtime import (
    DataUsed,
    DecisionAuditor,
    DeepAgentDecision,
    EvidencePack,
)


def _evidence(allowed: list[str], prices: dict[str, list[float]] | None = None) -> EvidencePack:
    return EvidencePack(
        workflow_run_id="wr_test",
        agent_key="watchlist_builder_agent",
        allowed_symbols=allowed,
        known_prices=prices or {},
        hard_rules=["Do not invent symbols or prices."],
    )


def _decision(**overrides) -> DeepAgentDecision:
    base = {
        "agent_key": "watchlist_builder_agent",
        "reasoning_status": "completed",
        "decision": "candidate_selected",
        "confidence": 0.7,
        "thesis": "Provider-backed thesis on TSLA.",
        "data_used": DataUsed(provider_chain=["alpaca"], symbols=["TSLA"]),
        "llm_used": True,
    }
    base.update(overrides)
    return DeepAgentDecision.model_validate(base)


# ---------- Unknown symbol ----------


def test_auditor_rejects_unknown_symbol_in_data_used():
    evidence = _evidence(["TSLA"])
    decision = _decision(
        thesis="No leaked symbol in prose.",
        data_used=DataUsed(provider_chain=["alpaca"], symbols=["NVDA"]),
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "blocked"
    assert any(b == "hallucinated_symbol:NVDA" for b in audited.hard_blockers)
    assert audited.submitted_order is False
    assert audited.broker_called is False
    assert audited.llm_used_for_trade_decision is False


def test_auditor_rejects_unknown_symbol_in_thesis_text():
    evidence = _evidence(["TSLA"])
    decision = _decision(thesis="NVDA looks strong but is not in the evidence pack.")

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert any(b.startswith("hallucinated_symbol:NVDA") for b in audited.hard_blockers)


# ---------- Invented price ----------


def test_auditor_rejects_invented_price_for_allowed_symbol():
    evidence = _evidence(["TSLA"], prices={"TSLA": [240.5]})
    decision = _decision(
        data_used=DataUsed(
            provider_chain=["alpaca"],
            symbols=["TSLA"],
            prices={"TSLA": 999.99},  # not present in known_prices
        )
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert any(b.startswith("invented_price:TSLA") for b in audited.hard_blockers)


def test_auditor_accepts_known_price_for_allowed_symbol():
    evidence = _evidence(["TSLA"], prices={"TSLA": [240.5]})
    decision = _decision(
        data_used=DataUsed(
            provider_chain=["alpaca"],
            symbols=["TSLA"],
            prices={"TSLA": 240.5},
        )
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "completed"
    assert audited.decision == "candidate_selected"
    assert audited.submitted_order is False
    assert audited.broker_called is False


# ---------- Forbidden / broker language ----------


def test_auditor_rejects_broker_submit_language():
    evidence = _evidence(["TSLA"])
    decision = _decision(
        agent_key="execution_planner_agent",
        decision="plan_only",
        thesis="Plan only, but submit_order should be rejected.",
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "blocked"
    assert any(b.startswith("forbidden_action:submit_order") for b in audited.hard_blockers)


def test_auditor_scrubs_broker_submit_claims_from_llm():
    evidence = _evidence(["TSLA"])
    decision = _decision(
        submitted_order=True,
        broker_called=True,
        llm_used_for_trade_decision=True,
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.submitted_order is False
    assert audited.broker_called is False
    assert audited.llm_used_for_trade_decision is False
    assert any("forbidden_broker_or_submit_claim" in b for b in audited.hard_blockers)


# ---------- Empty evidence pack ----------


def test_auditor_rejects_recommendation_when_evidence_is_empty():
    evidence = _evidence([])
    decision = _decision(
        thesis="Candidate selected even though evidence is empty.",
        data_used=DataUsed(provider_chain=["alpaca"], symbols=[]),
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "no_qualified_setup"
    assert "recommendation_with_zero_candidates" in audited.hard_blockers


# ---------- Mock / synthetic / demo language ----------


def test_auditor_rejects_synthetic_language():
    evidence = _evidence(["TSLA"])
    decision = _decision(thesis="Used SYNTHETIC backtest data to confirm.")

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert "reasoning_referenced_non_real_data" in audited.hard_blockers
