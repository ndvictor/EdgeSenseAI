"""Foundation tests for the DeepAgents advisory runtime.

Step 1 only: foundation correctness. The watchlist_builder_agent integration is
exercised in a separate suite in step 2.

Verifies:
- Evidence pack includes allowed symbols only (no invented tickers).
- Evidence pack includes hard rules forbidding mocks, broker calls, and
  symbol/price/feature invention.
- DecisionAuditor rejects unknown symbols in LLM output.
- DecisionAuditor rejects invented price claims for allowed symbols.
- DecisionAuditor rejects broker / order-submission language.
- Owner authority level is represented on the evidence pack.
- Reasoning disabled returns a safe ``DeepAgentDecision`` (no LLM,
  no broker calls, no order submission, advisory only).
"""

from __future__ import annotations

from app.services.deepagents_runtime import (
    DataUsed,
    DecisionAuditor,
    DeepAgentDecision,
    DeepAgentSupervisor,
    EvidencePack,
    EvidencePackBuilder,
    OwnerAuthority,
)


# ---------- Evidence pack: allowed symbols ----------


def test_evidence_pack_includes_allowed_symbols_only_from_real_rows():
    """Evidence pack must only surface symbols backed by real provider rows.

    Symbols requested in the workflow body without backing scanner / feature
    rows must NOT appear in ``allowed_symbols``.
    """
    workflow_state = {
        "workflow_run_id": "wr_test_foundation",
        "scanner_candidates": [
            {"symbol": "TSLA", "provider_name": "alpaca", "last_price": 240.5},
        ],
        "feature_rows": [
            {"symbol": "TSLA", "last_price": 240.5, "volume": 1000, "provider_name": "alpaca"},
        ],
        # Requested-but-unbacked symbol must not become evidence.
        "symbols": ["FAKE_TICKER"],
        "workflow_request_symbols": ["FAKE_TICKER"],
    }

    evidence = EvidencePackBuilder.build(workflow_state, "watchlist_builder_agent")

    assert evidence.allowed_symbols == ["TSLA"]
    assert "FAKE_TICKER" not in evidence.allowed_symbols
    assert evidence.has_candidates() is True
    assert evidence.provider_status["provider_chain"] == ["alpaca"]


def test_evidence_pack_with_zero_real_rows_has_empty_allowed_symbols():
    workflow_state = {"workflow_run_id": "wr_test_foundation", "scanner_candidates": [], "feature_rows": []}

    evidence = EvidencePackBuilder.build(workflow_state, "watchlist_builder_agent")

    assert evidence.allowed_symbols == []
    assert evidence.has_candidates() is False


# ---------- Evidence pack: hard rules ----------


def test_evidence_pack_includes_hard_rules():
    """Hard rules must explicitly forbid invention and broker / submit actions."""
    evidence = EvidencePackBuilder.build({"workflow_run_id": "wr_test_foundation"}, "watchlist_builder_agent")

    rules = " ".join(evidence.hard_rules).lower()
    assert evidence.hard_rules, "hard_rules must not be empty"
    assert "invent" in rules
    assert "mock" in rules and "synthetic" in rules
    assert "broker" in rules or "submit" in rules
    assert "advisory" in rules
    assert "deterministic" in rules


# ---------- DecisionAuditor: unknown symbol ----------


def _allowed_evidence(symbols: list[str], known_prices: dict[str, list[float]] | None = None) -> EvidencePack:
    return EvidencePack(
        workflow_run_id="wr_test_foundation",
        agent_key="watchlist_builder_agent",
        allowed_symbols=symbols,
        known_prices=known_prices or {},
        hard_rules=["Do not invent symbols, prices, or features."],
    )


def _decision(**overrides) -> DeepAgentDecision:
    base = {
        "agent_key": "watchlist_builder_agent",
        "reasoning_status": "completed",
        "decision": "candidate_selected",
        "confidence": 0.6,
        "thesis": "Provider-backed thesis on TSLA.",
        "data_used": DataUsed(provider_chain=["alpaca"], symbols=["TSLA"]),
        "llm_used": True,
    }
    base.update(overrides)
    return DeepAgentDecision.model_validate(base)


def test_decision_auditor_rejects_unknown_symbol_in_data_used():
    evidence = _allowed_evidence(["TSLA"])
    decision = _decision(
        thesis="Reasonable provider-backed thesis.",
        data_used=DataUsed(provider_chain=["alpaca"], symbols=["NVDA"]),
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "blocked"
    assert any(b == "hallucinated_symbol:NVDA" for b in audited.hard_blockers)
    assert audited.submitted_order is False
    assert audited.broker_called is False
    assert audited.llm_used_for_trade_decision is False


def test_decision_auditor_rejects_unknown_symbol_in_thesis_prose():
    evidence = _allowed_evidence(["TSLA"])
    decision = _decision(thesis="NVDA looks strong but is not in the evidence pack.")

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert any(b.startswith("hallucinated_symbol:NVDA") for b in audited.hard_blockers)


# ---------- DecisionAuditor: invented price ----------


def test_decision_auditor_rejects_invented_price_for_allowed_symbol():
    evidence = _allowed_evidence(["TSLA"], known_prices={"TSLA": [240.5]})
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


def test_decision_auditor_accepts_known_price_for_allowed_symbol():
    evidence = _allowed_evidence(["TSLA"], known_prices={"TSLA": [240.5]})
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


# ---------- DecisionAuditor: broker / order submit ----------


def test_decision_auditor_rejects_broker_submit_attempt_in_prose():
    evidence = _allowed_evidence(["TSLA"])
    decision = _decision(
        agent_key="execution_planner_agent",
        decision="plan_only",
        thesis="Plan only, but submit_order should be rejected.",
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.decision == "blocked"
    assert any(b.startswith("forbidden_action:submit_order") for b in audited.hard_blockers)


def test_decision_auditor_scrubs_broker_submit_claims_from_llm_payload():
    evidence = _allowed_evidence(["TSLA"])
    decision = _decision(
        submitted_order=True,
        broker_called=True,
        llm_used_for_trade_decision=True,
    )

    audited = DecisionAuditor.audit(decision, evidence)

    assert audited.reasoning_status == "audit_rejected"
    assert audited.submitted_order is False
    assert audited.broker_called is False
    assert audited.llm_used_for_trade_decision is False
    assert any("forbidden_broker_or_submit_claim" in b for b in audited.hard_blockers)


# ---------- Owner authority ----------


def test_owner_authority_level_is_represented_on_evidence_pack():
    """Owner authority must appear on the evidence pack and gate broker access."""
    workflow_state = {
        "workflow_run_id": "wr_test_foundation",
        "agent_capability_flags": {
            "agent_reasoning_enabled": True,
            "agent_can_recommend_trades": True,
            "agent_can_create_paper_plans": True,
            "agent_can_create_approval_requests": True,
            "agent_can_submit_paper_orders": True,
            "agent_can_submit_live_orders": False,
        },
    }

    evidence = EvidencePackBuilder.build(workflow_state, "watchlist_builder_agent")

    assert isinstance(evidence.owner_authority, OwnerAuthority)
    assert evidence.owner_authority.level == "paper_submit"
    assert evidence.owner_authority.can_recommend_trades is True
    assert evidence.owner_authority.can_create_paper_plans is True
    assert evidence.owner_authority.can_submit_paper_orders is True
    assert evidence.owner_authority.can_submit_live_orders is False
    assert evidence.owner_authority.require_human_approval is True


def test_owner_authority_defaults_to_read_only_without_capability_flags():
    """Without explicit owner policy, the agent runtime must default to read_only."""
    workflow_state = {
        "workflow_run_id": "wr_test_foundation",
        "agent_capability_flags": {},
    }

    evidence = EvidencePackBuilder.build(workflow_state, "watchlist_builder_agent")

    auth = evidence.owner_authority
    assert auth.level == "read_only"
    assert auth.can_recommend_trades is False
    assert auth.can_create_paper_plans is False
    assert auth.can_submit_paper_orders is False
    assert auth.can_submit_live_orders is False


def test_owner_authority_explicit_block_in_workflow_state_takes_precedence():
    workflow_state = {
        "workflow_run_id": "wr_test_foundation",
        "owner_authority": {
            "level": "advise",
            "can_recommend_trades": True,
            "can_create_paper_plans": False,
            "can_create_approval_requests": False,
            "can_submit_paper_orders": False,
            "can_submit_live_orders": False,
            "require_human_approval": True,
        },
        "agent_capability_flags": {
            # These should NOT win — explicit block above is the source of truth.
            "agent_can_submit_live_orders": True,
        },
    }

    evidence = EvidencePackBuilder.build(workflow_state, "watchlist_builder_agent")

    assert evidence.owner_authority.level == "advise"
    assert evidence.owner_authority.can_submit_live_orders is False


# ---------- Reasoning disabled ----------


def test_reasoning_disabled_returns_safe_status(monkeypatch):
    """With AGENT_REASONING_ENABLED=false the supervisor must not call any LLM."""
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "false")

    evidence = EvidencePack(
        workflow_run_id="wr_test_foundation",
        agent_key="watchlist_builder_agent",
        allowed_symbols=["TSLA"],
        hard_rules=["Do not invent symbols"],
    )
    decision = DeepAgentSupervisor().reason(evidence=evidence)

    assert decision.reasoning_status == "disabled"
    assert decision.llm_used is False
    assert decision.submitted_order is False
    assert decision.broker_called is False
    assert decision.llm_used_for_trade_decision is False
    # Non-empty allowed_symbols downgrades to ``needs_more_evidence`` (advisory only).
    assert decision.decision == "needs_more_evidence"


def test_reasoning_disabled_with_zero_candidates_returns_no_qualified_setup(monkeypatch):
    monkeypatch.setenv("AGENT_REASONING_ENABLED", "false")

    evidence = EvidencePack(
        workflow_run_id="wr_test_foundation",
        agent_key="watchlist_builder_agent",
        allowed_symbols=[],
        hard_rules=["Zero candidates must propagate as no_qualified_setup"],
    )
    decision = DeepAgentSupervisor().reason(evidence=evidence)

    assert decision.reasoning_status == "disabled"
    assert decision.decision == "no_qualified_setup"
    assert decision.submitted_order is False
    assert decision.broker_called is False
    assert decision.llm_used_for_trade_decision is False
