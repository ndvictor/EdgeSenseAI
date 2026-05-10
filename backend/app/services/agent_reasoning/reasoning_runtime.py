from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from typing import Any

from app.services.agent_reasoning.agent_contracts import AgentReasoningDecision, EvidencePack
from app.services.agent_reasoning.decision_auditor import DecisionAuditor
from app.services.agent_reasoning.decision_parser import DecisionParser
from app.services.agent_reasoning.evidence_pack_builder import EvidencePackBuilder
from app.services.agent_reasoning.prompt_templates import PromptTemplates


_REASONING_AGENT_KEYS = {
    "market_condition_agent",
    "watchlist_builder_agent",
    "alpha_engine_agent",
    "strategy_selection_agent",
    "model_selection_agent",
    "small_account_feasibility_agent",
    "execution_planner_agent",
}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fallback_decision_for_evidence(evidence: EvidencePack) -> str:
    if not evidence.allowed_symbols:
        return "no_qualified_setup"
    return "needs_more_evidence"


class ReasoningRuntime:
    """Controlled advisory LLM reasoning over evidence packs.

    This runtime never fetches market data, never creates symbols, never submits
    orders, and cannot override deterministic workflow/risk gates.
    """

    @staticmethod
    def supported_agent(agent_key: str) -> bool:
        return agent_key in _REASONING_AGENT_KEYS

    @staticmethod
    def reason(agent_key: str, workflow_state: dict[str, Any]) -> AgentReasoningDecision:
        evidence = EvidencePackBuilder.build(workflow_state, agent_key)
        return ReasoningRuntime.reason_with_evidence(evidence)

    @staticmethod
    def reason_with_evidence(evidence: EvidencePack) -> AgentReasoningDecision:
        if not ReasoningRuntime.supported_agent(evidence.agent_key):
            return AgentReasoningDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),
                reasoning_status="disabled",
                thesis="Agent reasoning is not enabled for this agent key.",
                soft_warnings=["agent_reasoning_not_supported_for_agent"],
            )

        if not _env_bool("AGENT_REASONING_ENABLED", False):
            return AgentReasoningDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),
                reasoning_status="disabled",
                thesis="Agent reasoning is disabled by AGENT_REASONING_ENABLED=false. Deterministic workflow gates remain authoritative.",
                soft_warnings=["agent_reasoning_disabled"],
            )

        provider = os.getenv("AGENT_REASONING_PROVIDER", "lightllm").strip().lower()
        if provider != "lightllm":
            return AgentReasoningDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),
                reasoning_status="llm_unavailable",
                thesis="Configured reasoning provider is unavailable or unsupported.",
                missing_evidence=["supported_reasoning_provider"],
                soft_warnings=["agent_reasoning_provider_unavailable"],
            )

        base_url = (os.getenv("LIGHTLLM_BASE_URL") or "").rstrip("/")
        model = os.getenv("LIGHTLLM_MODEL") or ""
        if not base_url or not model:
            return AgentReasoningDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),
                reasoning_status="llm_unavailable",
                thesis="LightLLM is not configured. Set LIGHTLLM_BASE_URL and LIGHTLLM_MODEL to enable advisory reasoning.",
                missing_evidence=["LIGHTLLM_BASE_URL", "LIGHTLLM_MODEL"],
                soft_warnings=["lightllm_not_configured"],
            )

        system_prompt = PromptTemplates.get_system_prompt(evidence.agent_key)
        user_prompt = PromptTemplates.get_user_prompt(evidence)
        prompt_hash = _sha256(system_prompt + "\n" + user_prompt)
        timeout = float(os.getenv("AGENT_REASONING_TIMEOUT_SECONDS") or 10)
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "response_format": {"type": "json_object"},
        }
        try:
            request = urllib.request.Request(
                f"{base_url}/v1/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - URL comes from configured internal LightLLM endpoint.
                raw_response = response.read().decode("utf-8")
            response_payload = json.loads(raw_response)
            content = response_payload["choices"][0]["message"]["content"]
            output_hash = _sha256(str(content))
            decision = DecisionParser.parse(
                content,
                agent_key=evidence.agent_key,
                prompt_hash=prompt_hash,
                output_hash=output_hash,
                llm_model=model,
            )
            audited = DecisionAuditor.audit(decision, evidence)
            return audited
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError, ValueError, TypeError) as exc:
            return AgentReasoningDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),
                reasoning_status="llm_unavailable",
                thesis="LLM reasoning call failed. Deterministic workflow gates remain authoritative.",
                missing_evidence=["successful_llm_reasoning_call"],
                soft_warnings=[f"agent_reasoning_runtime_error:{type(exc).__name__}"],
            )
