"""Merge Phase 3 glue (and related) agent outputs into orchestrator inputs for the next stage."""

from __future__ import annotations

from typing import Any

from app.services.agent_runtime.models import AgentRunResult
from app.services.agent_runtime.wrappers.glue_agents import GLUE_AGENT_KEYS
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState


def _tool_result(agent_result: AgentRunResult) -> dict[str, Any]:
    d = agent_result.decision
    if not isinstance(d, dict):
        return {}
    r = d.get("result")
    return r if isinstance(r, dict) else {}


def _append_strings(target: list[str], values: Any) -> None:
    if isinstance(values, list):
        for value in values:
            if value:
                target.append(str(value))


def _clean_symbols(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [str(s).strip().upper() for s in values if str(s).strip()]


def apply_stage_carryforward(*, agent_key: str, agent_result: AgentRunResult, state: WorkflowCarryForwardState) -> list[str]:
    """Carry typed workflow state forward for downstream agents. Returns advisory warnings."""
    warnings: list[str] = []
    state.submitted_order = False
    state.broker_called = False
    state.llm_used = False

    if agent_key not in GLUE_AGENT_KEYS:
        return warnings
    tr = _tool_result(agent_result)
    if not tr:
        return warnings

    if agent_key == "data_readiness_agent":
        _append_strings(warnings, tr.get("warnings"))
        _append_strings(state.warnings, tr.get("warnings"))
    elif agent_key == "market_condition_agent":
        mc = tr.get("market_context")
        if isinstance(mc, dict):
            state.market_context = dict(mc)
            if mc.get("regime"):
                state.regime = str(mc["regime"])
            # volatility_state and liquidity_state remain inside market_context.
    elif agent_key == "watchlist_builder_agent":
        syms = _clean_symbols(tr.get("symbols"))
        if syms:
            state.symbols = syms
        cand = tr.get("selected_candidate") or tr.get("selected_symbol") or tr.get("symbol")
        if cand:
            state.symbol = str(cand).strip().upper()
            state.selected_symbol = state.symbol
        elif state.symbols:
            state.symbol = str(state.symbols[0]).strip().upper()
            state.selected_symbol = state.symbol
    elif agent_key == "strategy_selection_agent":
        sk = tr.get("selected_strategy_key")
        if sk:
            state.strategy_key = str(sk)
            state.selected_strategy_key = str(sk)
        ps = tr.get("proof_status")
        if ps:
            state.proof_status = str(ps)
    elif agent_key == "model_selection_agent":
        smk = tr.get("selected_model_key")
        if smk:
            state.selected_model_key = str(smk)
        smks = tr.get("selected_model_keys")
        if isinstance(smks, list) and smks:
            state.selected_model_keys = [str(x) for x in smks if x]
        artifact = tr.get("qlib_artifact_id")
        if artifact:
            state.qlib_artifact_id = str(artifact)
    elif agent_key == "backtest_validation_agent":
        ps = tr.get("proof_status")
        if ps:
            state.proof_status = str(ps)
        proof_id = tr.get("proof_id")
        if proof_id:
            state.market_context = {**state.market_context, "proof_id": str(proof_id)}
    elif agent_key == "qlib_research_agent":
        if "qlib_available" in tr:
            state.qlib_available = bool(tr["qlib_available"])
        artifact = tr.get("qlib_artifact_id")
        if artifact:
            state.qlib_artifact_id = str(artifact)

    if state.strategy_key and not state.symbol and state.symbols:
        state.symbol = str(state.symbols[0]).strip().upper()
        state.selected_symbol = state.symbol

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
