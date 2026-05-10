"""DeepAgents supervisor for advisory reasoning over an evidence pack."""

from __future__ import annotations

import hashlib
import json
import os
from typing import Any

from app.services.deepagents_runtime.schemas import DataUsed, DeepAgentDecision, DeepAgentRunContext, EvidencePack
from app.services.deepagents_runtime.safety import DecisionAuditor
from app.services.deepagents_runtime.subagents import SubagentRegistry, default_subagent_registry
from app.services.deepagents_runtime.tools import DeepAgentToolRegistry, default_tool_registry

_SUPPORTED_AGENT_KEYS = {"watchlist_builder_agent", "alpha_engine_agent"}


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _reasoning_enabled() -> bool:
    """Resolve the reasoning flag from the OS environment only.

    The supervisor intentionally reads ``os.getenv`` rather than
    :class:`app.core.settings.Settings` so that the LLM call only happens when
    operators explicitly export ``AGENT_REASONING_ENABLED`` via their
    deployment system (systemd, docker-compose ``env_file``, k8s ConfigMap,
    etc.). pydantic-settings only loads ``.env`` into the ``Settings`` object,
    not into ``os.environ`` — pytest runs therefore never accidentally
    activate the LLM path even when ``Settings.agent_reasoning_enabled`` is
    true. Settings still surfaces the configured intent for status endpoints.
    """
    raw = os.getenv("AGENT_REASONING_ENABLED")
    if raw is None:
        return False
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _fallback_decision_for_evidence(evidence: EvidencePack) -> str:
    return "no_qualified_setup" if not evidence.allowed_symbols else "needs_more_evidence"


def _load_create_deep_agent():
    try:
        from deepagents import create_deep_agent

        return create_deep_agent
    except Exception:
        return None


def _decision_from_raw(raw: Any, *, evidence: EvidencePack, prompt_hash: str, output_hash: str, model: str | None) -> DeepAgentDecision:
    payload: Any = raw
    if isinstance(raw, dict) and "messages" in raw and isinstance(raw["messages"], list) and raw["messages"]:
        last = raw["messages"][-1]
        payload = getattr(last, "content", None) or (last.get("content") if isinstance(last, dict) else last)
    elif hasattr(raw, "content"):
        payload = raw.content
    if isinstance(payload, str):
        text = payload.strip()
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:].strip()
        payload = json.loads(text)
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("agent_key", evidence.agent_key)
    payload.setdefault("reasoning_status", "completed")
    payload.setdefault("decision", "needs_more_evidence")
    payload.setdefault("confidence", 0.0)
    payload.setdefault("thesis", "No thesis provided by DeepAgent.")
    payload.setdefault("bull_case", [])
    payload.setdefault("bear_case", [])
    payload.setdefault("missing_evidence", [])
    payload.setdefault("risk_notes", [])
    payload.setdefault("hard_blockers", [])
    payload.setdefault("soft_warnings", [])
    payload.setdefault("data_used", {})
    if not isinstance(payload["data_used"], dict):
        payload["data_used"] = {}
    payload["data_used"] = DataUsed.model_validate(payload["data_used"]).model_dump()
    payload.setdefault("usable_symbols", [])
    payload.setdefault("rejected_symbols", [])
    payload.setdefault("candidate_rankings", [])
    payload.setdefault("candidate_source", None)
    payload.setdefault("symbol", None)
    payload.setdefault("strategy_key", None)
    payload.setdefault("setup_type", None)
    payload.setdefault("scanner_score", None)
    payload.setdefault("model_score", None)
    payload.setdefault("evidence_score", None)
    payload.setdefault("small_account_score", None)
    payload.setdefault("strategy_fit_score", None)
    payload.setdefault("final_score", None)
    payload.setdefault("entry_plan", {})
    payload.setdefault("recommendation_id", None)
    payload.setdefault("predicted_return_pct", None)
    payload.setdefault("predicted_return_r", None)
    payload.setdefault("predicted_win_probability", None)
    payload.setdefault("predicted_expected_value_r", None)
    payload.setdefault("prediction_horizon_minutes", None)
    payload.setdefault("prediction_model_key", None)
    payload.setdefault("prediction_reason", None)
    payload["llm_used"] = True
    payload["llm_model"] = payload.get("llm_model") or model
    payload["prompt_hash"] = payload.get("prompt_hash") or prompt_hash
    payload["output_hash"] = payload.get("output_hash") or output_hash
    payload["submitted_order"] = False
    payload["broker_called"] = False
    payload["llm_used_for_trade_decision"] = False
    return DeepAgentDecision.model_validate(payload)


class DeepAgentSupervisor:
    """Coordinates a single DeepAgents advisory turn."""

    def __init__(
        self,
        *,
        tools: DeepAgentToolRegistry | None = None,
        subagents: SubagentRegistry | None = None,
        create_deep_agent_fn: Any | None = None,
    ) -> None:
        self.tools = tools
        self.subagents = subagents or default_subagent_registry()
        self.create_deep_agent_fn = create_deep_agent_fn

    @staticmethod
    def supported_agent(agent_key: str) -> bool:
        return agent_key in _SUPPORTED_AGENT_KEYS

    def reason(self, *, evidence: EvidencePack, context: DeepAgentRunContext | None = None, objective: str | None = None) -> DeepAgentDecision:
        """Run controlled advisory reasoning. Deterministic gates remain final."""
        if not self.supported_agent(evidence.agent_key):
            return DeepAgentDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),  # type: ignore[arg-type]
                reasoning_status="disabled",
                thesis="DeepAgents reasoning is currently integrated only with watchlist_builder_agent and alpha_engine_agent.",
                soft_warnings=["deepagent_not_integrated_for_agent"],
            )
        if not _reasoning_enabled():
            return DeepAgentDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),  # type: ignore[arg-type]
                reasoning_status="disabled",
                thesis="DeepAgents reasoning is disabled by AGENT_REASONING_ENABLED=false. Deterministic workflow gates remain authoritative.",
                soft_warnings=["deepagent_reasoning_disabled"],
            )
        if not evidence.allowed_symbols:
            return DeepAgentDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision="no_qualified_setup",
                reasoning_status="blocked",
                thesis="No provider-backed candidates are available in the evidence pack.",
                hard_blockers=["no_scanner_candidates_passed_filters"],
            )

        create_deep_agent = self.create_deep_agent_fn or _load_create_deep_agent()
        if create_deep_agent is None:
            return DeepAgentDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),  # type: ignore[arg-type]
                reasoning_status="llm_unavailable",
                thesis="deepagents is not installed or could not be imported.",
                missing_evidence=["deepagents.create_deep_agent"],
                soft_warnings=["deepagents_import_unavailable"],
            )

        registry = self.tools or default_tool_registry(evidence)
        system_prompt = (
            f"You are {evidence.agent_key} inside EdgeSenseAI. Reason only over the supplied Evidence Pack. "
            "Never invent symbols, prices, features, providers, strategies, models, or broker state. "
            "Never submit orders, call brokers, or promote strategies/models. Return JSON only."
        )
        user_prompt = json.dumps(
            {
                "objective": objective or "Provide advisory reasoning for the existing deterministic workflow output.",
                "context": (context or DeepAgentRunContext()).model_dump(),
                "evidence_pack": evidence.model_dump(),
                "required_output": {
                    "agent_key": evidence.agent_key,
                    "reasoning_status": "completed",
                    "decision": "candidate_selected | candidates_selected | no_qualified_setup | data_unavailable | blocked | needs_more_evidence | plan_only",
                    "confidence": "number between 0 and 1",
                    "thesis": "short evidence-based thesis",
                    "bull_case": [],
                    "bear_case": [],
                    "missing_evidence": [],
                    "risk_notes": [],
                    "recommended_next_action": "safe next workflow action",
                    "hard_blockers": [],
                    "soft_warnings": [],
                    "data_used": {"provider_chain": [], "feature_row_id": None, "scanner_diagnostics": {}, "worker_status": {}, "symbols": [], "prices": {}},
                    # Watchlist-specific structured decision (only for watchlist_builder_agent).
                    "usable_symbols": "subset of allowed_symbols only — never invent",
                    "rejected_symbols": [{"symbol": "...", "reason": "..."}],
                    "candidate_rankings": [{"symbol": "...", "score": "0..1", "reason": "..."}],
                    "candidate_source": "scanner | worker_output_scanner | manual_request | none",
                    # Alpha-specific structured recommendation (only for alpha_engine_agent).
                    "symbol": "single selected symbol from allowed_symbols, or null",
                    "strategy_key": "must be present in strategy_registry / Alpha evidence, or null",
                    "setup_type": "evidence-backed setup label, or null",
                    "scanner_score": "number or null",
                    "model_score": "number or null",
                    "evidence_score": "number or null",
                    "small_account_score": "number or null",
                    "strategy_fit_score": "number or null",
                    "final_score": "number or null",
                    "entry_plan": {
                        "entry": "evidence-backed price or null",
                        "stop": "evidence-backed/derived price or null",
                        "target": "evidence-backed/derived price or null",
                        "risk_per_share": "number or null",
                        "risk_dollars": "number or null",
                        "expected_r": "number or null",
                        "position_size_estimate": "number or null",
                        "plan_type": "string or null",
                        "notes": [],
                    },
                    "recommendation_id": "string or null",
                    "predicted_return_pct": "number or null",
                    "predicted_return_r": "number or null",
                    "predicted_win_probability": "number or null",
                    "predicted_expected_value_r": "number or null",
                    "prediction_horizon_minutes": "integer or null",
                    "prediction_model_key": "heuristic/model key or null",
                    "prediction_reason": "string or null",
                    "llm_used": True,
                    "submitted_order": False,
                    "broker_called": False,
                    "llm_used_for_trade_decision": False,
                },
            },
            sort_keys=True,
            default=str,
        )
        prompt_hash = _sha256(system_prompt + "\n" + user_prompt)
        model = os.getenv("AGENT_REASONING_MODEL") or os.getenv("LIGHTLLM_MODEL") or None
        try:
            tool_handlers = registry.list_handlers()
            subagents: list[dict[str, Any]] = []
            for key in self.subagents.list_keys():
                descriptor = self.subagents.get(key)
                if descriptor is None:
                    continue
                subagents.append(
                    {
                        "name": descriptor.key,
                        "description": descriptor.description or descriptor.key,
                        "system_prompt": (
                            f"You are the advisory subagent {descriptor.key}. "
                            "Reason only over the supplied evidence pack. "
                            "Never invent symbols, prices, or providers. Never submit orders."
                        ),
                        "tools": tool_handlers,
                    }
                )
            agent = create_deep_agent(tools=tool_handlers, system_prompt=system_prompt, subagents=subagents)
            raw = agent.invoke({"messages": [{"role": "user", "content": user_prompt}]})
            output_hash = _sha256(json.dumps(raw, sort_keys=True, default=str))
            decision = _decision_from_raw(raw, evidence=evidence, prompt_hash=prompt_hash, output_hash=output_hash, model=model)
            return DecisionAuditor.audit(decision, evidence)
        except Exception as exc:
            return DeepAgentDecision.safe_fallback(
                agent_key=evidence.agent_key,
                decision=_fallback_decision_for_evidence(evidence),  # type: ignore[arg-type]
                reasoning_status="llm_unavailable",
                thesis="DeepAgents reasoning call failed. Deterministic workflow gates remain authoritative.",
                missing_evidence=["successful_deepagents_reasoning_call"],
                soft_warnings=[f"deepagents_runtime_error:{type(exc).__name__}"],
            )

    def turn(self, *, objective: str, context: DeepAgentRunContext, inputs: dict[str, Any]) -> dict[str, Any]:
        evidence = EvidencePack.model_validate(inputs["evidence_pack"]) if "evidence_pack" in inputs else EvidencePack.model_validate(inputs)
        return self.reason(evidence=evidence, context=context, objective=objective).model_dump()


def run_supervisor_turn(
    *,
    objective: str,
    context: DeepAgentRunContext,
    inputs: dict[str, Any],
    supervisor: DeepAgentSupervisor | None = None,
) -> dict[str, Any]:
    svc = supervisor or DeepAgentSupervisor()
    return svc.turn(objective=objective, context=context, inputs=inputs)
