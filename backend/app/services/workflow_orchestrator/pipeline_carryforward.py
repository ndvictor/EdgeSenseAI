"""Merge Phase 3 glue (and related) agent outputs into orchestrator inputs for the next stage."""

from __future__ import annotations

from typing import Any

from app.services.agent_runtime.models import AgentRunResult
from app.services.agent_runtime.wrappers.glue_agents import GLUE_AGENT_KEYS


def _tool_result(agent_result: AgentRunResult) -> dict[str, Any]:
    d = agent_result.decision
    if not isinstance(d, dict):
        return {}
    r = d.get("result")
    return r if isinstance(r, dict) else {}


def apply_stage_carryforward(*, agent_key: str, agent_result: AgentRunResult, req_inputs: dict[str, Any]) -> list[str]:
    """Mutate ``req_inputs`` with fields downstream agents need. Returns advisory warnings."""
    warnings: list[str] = []
    if agent_key not in GLUE_AGENT_KEYS:
        return warnings
    tr = _tool_result(agent_result)
    if not tr:
        return warnings

    if agent_key == "market_condition_agent":
        mc = tr.get("market_context")
        if isinstance(mc, dict):
            req_inputs["market_context"] = mc
            if mc.get("regime"):
                req_inputs["regime"] = str(mc["regime"])
    elif agent_key == "watchlist_builder_agent":
        syms = tr.get("symbols")
        if isinstance(syms, list) and syms:
            req_inputs["symbols"] = [str(s).strip().upper() for s in syms if s]
        cand = tr.get("selected_candidate")
        if cand:
            req_inputs["symbol"] = str(cand).strip().upper()
        elif req_inputs.get("symbols"):
            req_inputs["symbol"] = str(req_inputs["symbols"][0]).strip().upper()
    elif agent_key == "strategy_selection_agent":
        sk = tr.get("selected_strategy_key")
        if sk:
            req_inputs["strategy_key"] = str(sk)
    elif agent_key == "model_selection_agent":
        smk = tr.get("selected_model_key")
        if smk:
            req_inputs["selected_model_key"] = str(smk)
        smks = tr.get("selected_model_keys")
        if isinstance(smks, list) and smks:
            req_inputs["selected_model_keys"] = [str(x) for x in smks if x]
    elif agent_key == "backtest_validation_agent":
        ps = tr.get("proof_status")
        if ps:
            req_inputs["proof_status"] = str(ps)
    elif agent_key == "qlib_research_agent":
        if "qlib_available" in tr:
            req_inputs["qlib_available"] = bool(tr["qlib_available"])

    if req_inputs.get("strategy_key") and not req_inputs.get("symbol") and req_inputs.get("symbols"):
        req_inputs["symbol"] = str(req_inputs["symbols"][0]).strip().upper()

    return warnings


def advisory_glue_next_agent_mismatch(*, agent_key: str, agent_result: AgentRunResult, next_planned_agent: str | None) -> str | None:
    """If glue suggests a different successor than the fixed plan, surface a single warning string."""
    if agent_key not in GLUE_AGENT_KEYS or not next_planned_agent:
        return None
    want = agent_result.next_agent
    if not want:
        return None
    if want != next_planned_agent:
        return f"glue_suggested_next_agent={want}_but_plan_has={next_planned_agent}"
    return None
