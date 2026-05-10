from __future__ import annotations

import re
from copy import deepcopy

from app.services.agent_reasoning.agent_contracts import AgentReasoningDecision, EvidencePack


class DecisionAuditor:
    """Rejects reasoning output that attempts to invent facts or cross safety boundaries."""

    FORBIDDEN_ACTIONS = (
        "submit_order",
        "place_order",
        "send_order",
        "broker_called=true",
        "submitted_order=true",
        "live execution",
        "live_trade",
        "disable approval",
        "mark_active",
        "activate_strategy",
        "activate_model",
    )
    COMMON_NON_SYMBOL_WORDS = {
        "AI",
        "API",
        "ATR",
        "BUY",
        "CFO",
        "CEO",
        "CSV",
        "DATA",
        "ETF",
        "EV",
        "JSON",
        "LLM",
        "MACD",
        "NO",
        "OK",
        "RISK",
        "RSI",
        "SELL",
        "VWAP",
        "YES",
    }

    @staticmethod
    def audit(decision: AgentReasoningDecision, evidence: EvidencePack) -> AgentReasoningDecision:
        audited = deepcopy(decision)
        allowed = {symbol.upper() for symbol in evidence.allowed_symbols}
        text_parts = [
            audited.thesis or "",
            " ".join(audited.bull_case or []),
            " ".join(audited.bear_case or []),
            " ".join(audited.missing_evidence or []),
            " ".join(audited.risk_notes or []),
            " ".join(audited.soft_warnings or []),
            " ".join(audited.hard_blockers or []),
            audited.recommended_next_action or "",
            " ".join(audited.data_used.symbols or []),
        ]
        text_upper = " ".join(text_parts).upper()

        if not allowed and audited.decision == "candidate_selected":
            audited.hard_blockers.append("recommendation_with_zero_candidates")
            audited.reasoning_status = "audit_rejected"
            audited.decision = "no_qualified_setup"

        for symbol in audited.data_used.symbols or []:
            sym = str(symbol).upper().strip()
            if sym and sym not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{sym}")
                audited.reasoning_status = "audit_rejected"

        # Conservative ticker hallucination check. Only reject uppercase tokens that look like symbols
        # and are not common acronyms or already allowed.
        for sym in re.findall(r"\b[A-Z]{2,5}\b", text_upper):
            if sym in DecisionAuditor.COMMON_NON_SYMBOL_WORDS:
                continue
            if allowed and sym not in allowed:
                audited.hard_blockers.append(f"hallucinated_symbol:{sym}")
                audited.reasoning_status = "audit_rejected"

        if any(term in text_upper for term in ("MOCK", "SYNTHETIC", "FAKE", "DEMO DATA")):
            audited.hard_blockers.append("reasoning_referenced_non_real_data")
            audited.reasoning_status = "audit_rejected"

        for phrase in DecisionAuditor.FORBIDDEN_ACTIONS:
            if phrase.upper() in text_upper:
                audited.hard_blockers.append(f"forbidden_action:{phrase}")
                audited.reasoning_status = "audit_rejected"

        if audited.reasoning_status == "audit_rejected":
            audited.decision = "no_qualified_setup" if not allowed else "blocked"
            audited.confidence = 0.0
            audited.llm_used = bool(audited.llm_used)
            audited.hard_blockers = sorted(set(audited.hard_blockers))
            audited.soft_warnings = sorted(set(audited.soft_warnings + ["agent_reasoning_audit_rejected"]))
        return audited
