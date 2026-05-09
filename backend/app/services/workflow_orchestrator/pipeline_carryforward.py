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


def _first_dict(values: Any, symbol: str | None = None) -> dict[str, Any]:
    if not isinstance(values, list):
        return {}
    for value in values:
        if not isinstance(value, dict):
            continue
        if symbol is None or str(value.get("symbol", "")).strip().upper() == symbol:
            return value
    return {}


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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
        _append_strings(state.blockers, tr.get("blockers"))
        if isinstance(tr.get("provider_status"), dict):
            state.provider_status = dict(tr["provider_status"])
        for attr in (
            "provider_name",
            "source_mode",
            "latest_snapshot_status",
            "feature_store_status",
            "persistence_status",
            "freshness_status",
            "kafka_status",
        ):
            if tr.get(attr) is not None:
                setattr(state, attr, str(tr[attr]))
        if "using_mock_data" in tr:
            state.using_mock_data = bool(tr["using_mock_data"])
        state.usable_symbols = _clean_symbols(tr.get("usable_symbols"))
        state.rejected_symbols = _clean_symbols(tr.get("rejected_symbols"))
        if state.usable_symbols:
            state.symbols = state.usable_symbols
            state.symbol = state.usable_symbols[0]
            state.selected_symbol = state.symbol
        if tr.get("latest_snapshot_count") is not None:
            state.latest_snapshot_count = int(tr.get("latest_snapshot_count") or 0)
        if tr.get("feature_row_count") is not None:
            state.feature_row_count = int(tr.get("feature_row_count") or 0)
        artifacts = tr.get("artifacts") if isinstance(tr.get("artifacts"), dict) else {}
        feature_row = _first_dict(artifacts.get("feature_rows"), state.selected_symbol or state.symbol)
        snapshot = _first_dict(artifacts.get("latest_snapshots"), state.selected_symbol or state.symbol)
        state.latest_price = _float_or_none(feature_row.get("last_price") or snapshot.get("price") or snapshot.get("last") or snapshot.get("close"))
        state.spread_bps = _float_or_none(feature_row.get("spread_bps"))
        volume = _float_or_none(feature_row.get("volume") or snapshot.get("volume"))
        if state.latest_price is not None and volume is not None:
            state.avg_dollar_volume = round(state.latest_price * volume, 2)
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
        _append_strings(state.evidence_blockers, tr.get("blockers"))
        _append_strings(state.evidence_warnings, tr.get("warnings"))
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
        _append_strings(state.evidence_blockers, tr.get("blockers"))
        _append_strings(state.evidence_warnings, tr.get("warnings"))
    elif agent_key == "backtest_validation_agent":
        ps = tr.get("proof_status")
        if ps:
            state.proof_status = str(ps)
        proof_id = tr.get("proof_id")
        if proof_id:
            state.proof_id = str(proof_id)
            state.market_context = {**state.market_context, "proof_id": str(proof_id)}
        artifact = tr.get("qlib_artifact_id")
        if artifact:
            state.qlib_artifact_id = str(artifact)
        _append_strings(state.evidence_blockers, tr.get("blockers"))
        _append_strings(state.evidence_warnings, tr.get("warnings"))
    elif agent_key == "qlib_research_agent":
        if "qlib_available" in tr:
            state.qlib_available = bool(tr["qlib_available"])
        if tr.get("qlib_version") is not None:
            state.qlib_version = str(tr["qlib_version"])
        artifact = tr.get("qlib_artifact_id")
        if artifact:
            state.qlib_artifact_id = str(artifact)
        if isinstance(tr.get("qlib_artifact_counts"), dict):
            state.qlib_artifact_counts = {str(k): int(v or 0) for k, v in tr["qlib_artifact_counts"].items()}
        _append_strings(state.evidence_blockers, tr.get("blockers"))
        _append_strings(state.evidence_warnings, tr.get("warnings"))
    elif agent_key == "small_account_feasibility_agent":
        if tr.get("decision") is not None:
            state.small_account_decision = str(tr["decision"])
        if tr.get("account_equity") is not None:
            state.account_equity = float(tr["account_equity"])
        if tr.get("max_risk_dollars") is not None:
            state.max_risk_dollars = float(tr["max_risk_dollars"])
        if tr.get("max_daily_loss_dollars") is not None:
            state.max_daily_loss_dollars = float(tr["max_daily_loss_dollars"])
        state.feasible_symbols = _clean_symbols(tr.get("feasible_symbols"))
        state.small_account_rejected_symbols = _clean_symbols(tr.get("rejected_symbols"))
        state.small_account_blockers = [str(x) for x in (tr.get("blockers") or []) if x]
        state.small_account_warnings = [str(x) for x in (tr.get("warnings") or []) if x]
        _append_strings(state.blockers, tr.get("blockers"))
        _append_strings(state.warnings, tr.get("warnings"))

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
