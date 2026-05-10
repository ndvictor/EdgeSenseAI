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


def _dict_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    return [dict(value) for value in values if isinstance(value, dict)]


def _scanner_context_snapshot(state: WorkflowCarryForwardState) -> dict[str, Any]:
    """Capture scanner-seeded fields before a stage may overwrite them."""
    return {
        "scanner_candidates": list(state.scanner_candidates or []),
        "feature_rows": list(state.feature_rows or []),
        "watchlist": list(state.watchlist or []),
        "usable_symbols": list(state.usable_symbols or []),
        "symbols": list(state.symbols or []),
        "symbol": state.symbol,
        "selected_symbol": state.selected_symbol,
        "candidate_source": state.candidate_source,
        "latest_price": state.latest_price,
        "spread_bps": state.spread_bps,
        "avg_dollar_volume": state.avg_dollar_volume,
        "feature_row_count": state.feature_row_count,
        "latest_snapshot_count": state.latest_snapshot_count,
        "provider_name": state.provider_name,
        "provider_status": dict(state.provider_status or {}),
        "feature_store_status": state.feature_store_status,
        "persistence_status": state.persistence_status,
        "freshness_status": state.freshness_status,
    }


def _reconcile_scanner_seeded_fields_after_data_readiness(state: WorkflowCarryForwardState, prior: dict[str, Any]) -> None:
    """Restore scanner context if data readiness cleared or nullified seeded values (glue-only, no new symbols)."""
    if not prior.get("scanner_candidates"):
        return
    if state.candidate_source == "universe_selection" and prior.get("candidate_source") not in (None, "universe_selection"):
        state.candidate_source = prior["candidate_source"]
    if not state.usable_symbols and prior.get("usable_symbols"):
        state.usable_symbols = list(prior["usable_symbols"])
    if (not state.symbols) and prior.get("symbols"):
        state.symbols = list(prior["symbols"])
    if not state.selected_symbol and prior.get("selected_symbol"):
        state.selected_symbol = prior["selected_symbol"]
        state.symbol = prior.get("symbol") or prior["selected_symbol"]
    if state.latest_price is None and prior.get("latest_price") is not None:
        state.latest_price = prior["latest_price"]
    if state.spread_bps is None and prior.get("spread_bps") is not None:
        state.spread_bps = prior["spread_bps"]
    if state.avg_dollar_volume is None and prior.get("avg_dollar_volume") is not None:
        state.avg_dollar_volume = prior["avg_dollar_volume"]
    if (state.feature_row_count or 0) == 0 and (prior.get("feature_row_count") or 0) > 0:
        state.feature_row_count = int(prior["feature_row_count"])
    if (state.latest_snapshot_count or 0) == 0 and (prior.get("latest_snapshot_count") or 0) > 0:
        state.latest_snapshot_count = int(prior["latest_snapshot_count"])
    if not state.feature_rows and prior.get("feature_rows"):
        state.feature_rows = list(prior["feature_rows"])
    if not state.scanner_candidates and prior.get("scanner_candidates"):
        state.scanner_candidates = list(prior["scanner_candidates"])
    if not state.watchlist and prior.get("watchlist"):
        state.watchlist = list(prior["watchlist"])
    if prior.get("provider_status"):
        merged_ps = dict(prior["provider_status"])
        merged_ps.update(state.provider_status or {})
        state.provider_status = merged_ps
    if prior.get("provider_name") and not state.provider_name:
        state.provider_name = prior["provider_name"]
    if prior.get("feature_store_status") == "scanner_enriched" and str(state.feature_store_status or "").lower() in {
        "",
        "unavailable",
    }:
        state.feature_store_status = prior["feature_store_status"]
    if prior.get("persistence_status") == "scanner_runtime" and not state.persistence_status:
        state.persistence_status = prior["persistence_status"]
    if prior.get("freshness_status") == "fresh" and not state.freshness_status:
        state.freshness_status = prior["freshness_status"]


def _enrich_alpha_recommendation_with_row(state: WorkflowCarryForwardState) -> None:
    if not isinstance(state.alpha_recommendation, dict) or not state.alpha_recommendation:
        return
    sym = state.alpha_selected_symbol or state.alpha_recommendation.get("symbol")
    if not sym:
        return
    sym_u = str(sym).strip().upper()
    row = _first_dict(state.feature_rows, sym_u) or _first_dict(state.scanner_candidates, sym_u)
    rec = dict(state.alpha_recommendation)
    ep = rec.get("entry_plan")
    ep_dict = ep if isinstance(ep, dict) else {}
    entry_val = _float_or_none(ep_dict.get("entry")) if ep_dict else None
    last_px = _float_or_none(row.get("last_price") or row.get("price")) if row else None
    if rec.get("latest_price") is None:
        rec["latest_price"] = last_px or entry_val
    if rec.get("spread_bps") is None and row:
        rec["spread_bps"] = _float_or_none(row.get("spread_bps"))
    for key in ("volume", "avg_volume", "relative_volume", "dollar_volume", "data_quality"):
        if row and rec.get(key) is None and row.get(key) is not None:
            rec[key] = row.get(key)
    if rec.get("dollar_volume") is None and row:
        lp = last_px or _float_or_none(row.get("last_price") or row.get("price"))
        vol = _float_or_none(row.get("volume"))
        if lp is not None and vol is not None:
            rec["dollar_volume"] = round(lp * vol, 2)
    if rec.get("market_session") is None and row:
        rec["market_session"] = row.get("session_state") or row.get("market_session")
    if rec.get("candidate_source") is None and state.candidate_source:
        rec["candidate_source"] = state.candidate_source
    if rec.get("provider_name") is None:
        rec["provider_name"] = (row or {}).get("provider_name") or state.provider_name
    state.alpha_recommendation = rec


def apply_stage_carryforward(*, agent_key: str, agent_result: AgentRunResult, state: WorkflowCarryForwardState) -> list[str]:
    """Carry typed workflow state forward for downstream agents. Returns advisory warnings."""
    warnings: list[str] = []
    state.submitted_order = False
    state.broker_called = False
    state.llm_used = False

    tr = _tool_result(agent_result)
    if agent_key == "account_owner_policy_agent" and isinstance(tr.get("gates"), dict):
        state.account_owner_gates = dict(tr["gates"])
        if "paper_trading_enabled" in tr["gates"]:
            state.paper_trading_enabled = bool(tr["gates"]["paper_trading_enabled"])
        if "live_trading_enabled" in tr["gates"]:
            state.live_trading_enabled = bool(tr["gates"]["live_trading_enabled"])
        if "broker_execution_enabled" in tr["gates"]:
            state.broker_execution_enabled = bool(tr["gates"]["broker_execution_enabled"])

    if agent_key not in GLUE_AGENT_KEYS:
        return warnings
    if not tr:
        return warnings

    if agent_key == "data_readiness_agent":
        prior_scanner = _scanner_context_snapshot(state)
        _append_strings(warnings, tr.get("warnings"))
        _append_strings(state.warnings, tr.get("warnings"))
        _append_strings(state.blockers, tr.get("blockers"))
        if isinstance(tr.get("provider_status"), dict):
            state.provider_status = {**dict(state.provider_status), **dict(tr["provider_status"])}
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
        if "using_non_real_data" in tr:
            state.using_non_real_data = bool(tr["using_non_real_data"])
        if "discovery_mode" in tr:
            state.discovery_mode = bool(tr["discovery_mode"])
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
        feature_rows = _dict_list(artifacts.get("feature_rows"))
        if feature_rows:
            state.feature_rows = feature_rows
        feature_row = _first_dict(artifacts.get("feature_rows"), state.selected_symbol or state.symbol)
        snapshot = _first_dict(artifacts.get("latest_snapshots"), state.selected_symbol or state.symbol)
        state.latest_price = _float_or_none(feature_row.get("last_price") or snapshot.get("price") or snapshot.get("last") or snapshot.get("close"))
        state.spread_bps = _float_or_none(feature_row.get("spread_bps"))
        volume = _float_or_none(feature_row.get("volume") or snapshot.get("volume"))
        if state.latest_price is not None and volume is not None:
            state.avg_dollar_volume = round(state.latest_price * volume, 2)
        _reconcile_scanner_seeded_fields_after_data_readiness(state, prior_scanner)
    elif agent_key == "market_condition_agent":
        mc = tr.get("market_context")
        if isinstance(mc, dict):
            state.market_context = dict(mc)
            if mc.get("regime"):
                state.regime = str(mc["regime"])
            # volatility_state and liquidity_state remain inside market_context.
    elif agent_key == "watchlist_builder_agent":
        prior_watchlist = _scanner_context_snapshot(state)
        syms = _clean_symbols(tr.get("symbols"))
        if syms:
            state.symbols = syms
            state.usable_symbols = syms
        usable = _clean_symbols(tr.get("usable_symbols"))
        if usable:
            state.usable_symbols = usable
            state.symbols = usable
        for attr in ("candidate_source",):
            if tr.get(attr) is not None:
                val = str(tr[attr])
                if (
                    val == "universe_selection"
                    and prior_watchlist.get("candidate_source") not in (None, "universe_selection")
                    and prior_watchlist.get("scanner_candidates")
                ):
                    continue
                setattr(state, attr, val)
        if tr.get("raw_candidate_count") is not None:
            state.raw_candidate_count = int(tr.get("raw_candidate_count") or 0)
        if tr.get("filtered_candidate_count") is not None:
            state.filtered_candidate_count = int(tr.get("filtered_candidate_count") or 0)
        _append_strings(state.blockers, tr.get("blockers"))
        _append_strings(state.warnings, tr.get("warnings"))
        for key in ("feature_rows", "scanner_candidates", "watchlist", "candidates", "ranked_candidates"):
            values = tr.get(key)
            if key == "feature_rows":
                rows = _dict_list(values)
                if rows:
                    state.feature_rows = rows
            elif key in {"scanner_candidates", "candidates", "ranked_candidates"}:
                rows = _dict_list(values)
                if rows:
                    state.scanner_candidates = rows
            elif isinstance(values, list) and values:
                state.watchlist = list(values)
        cand = tr.get("selected_candidate") or tr.get("selected_symbol") or tr.get("symbol")
        if cand:
            state.symbol = str(cand).strip().upper()
            state.selected_symbol = state.symbol
        elif state.symbols:
            state.symbol = str(state.symbols[0]).strip().upper()
            state.selected_symbol = state.symbol
        if prior_watchlist.get("scanner_candidates"):
            if state.latest_price is None and prior_watchlist.get("latest_price") is not None:
                state.latest_price = prior_watchlist["latest_price"]
            if state.spread_bps is None and prior_watchlist.get("spread_bps") is not None:
                state.spread_bps = prior_watchlist["spread_bps"]
            if state.avg_dollar_volume is None and prior_watchlist.get("avg_dollar_volume") is not None:
                state.avg_dollar_volume = prior_watchlist["avg_dollar_volume"]
            if not state.scanner_candidates and prior_watchlist.get("scanner_candidates"):
                state.scanner_candidates = list(prior_watchlist["scanner_candidates"])
            if not state.feature_rows and prior_watchlist.get("feature_rows"):
                state.feature_rows = list(prior_watchlist["feature_rows"])
            if (state.feature_row_count or 0) == 0 and (prior_watchlist.get("feature_row_count") or 0) > 0:
                state.feature_row_count = int(prior_watchlist["feature_row_count"])
    elif agent_key == "alpha_engine_agent":
        if isinstance(tr.get("alpha_recommendation"), dict):
            state.alpha_recommendation = dict(tr["alpha_recommendation"])
        if tr.get("alpha_status") is not None:
            state.alpha_status = str(tr["alpha_status"])
        if tr.get("alpha_selected_symbol"):
            state.alpha_selected_symbol = str(tr["alpha_selected_symbol"]).strip().upper()
            state.selected_symbol = state.alpha_selected_symbol
            state.symbol = state.alpha_selected_symbol
        if tr.get("alpha_strategy_key") is not None:
            state.alpha_strategy_key = str(tr["alpha_strategy_key"])
        if tr.get("alpha_score") is not None:
            state.alpha_score = _float_or_none(tr.get("alpha_score"))
        if tr.get("alpha_reason") is not None:
            state.alpha_reason = str(tr["alpha_reason"])
        state.alpha_blockers = [str(x) for x in (tr.get("alpha_blockers") or []) if x]
        state.alpha_warnings = [str(x) for x in (tr.get("alpha_warnings") or []) if x]
        _append_strings(state.warnings, tr.get("alpha_warnings"))
        _enrich_alpha_recommendation_with_row(state)
    elif agent_key == "strategy_selection_agent":
        sk = tr.get("selected_strategy_key")
        if sk:
            state.strategy_key = str(sk)
            state.selected_strategy_key = str(sk)
        if tr.get("selected_symbol"):
            state.selected_symbol = str(tr["selected_symbol"]).strip().upper()
            state.symbol = state.selected_symbol
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
        if tr.get("small_account_decision") is not None:
            state.small_account_decision = str(tr["small_account_decision"])
        elif tr.get("account_feasibility_decision") is not None:
            state.small_account_decision = str(tr["account_feasibility_decision"])
        elif tr.get("decision") is not None:
            leg = str(tr["decision"]).strip().lower()
            state.small_account_decision = {"pass": "feasible", "blocked": "blocked", "degraded": "degraded"}.get(leg, leg)
        if tr.get("account_feasibility_decision") is not None:
            state.account_feasibility_decision = str(tr["account_feasibility_decision"])
        elif state.small_account_decision is not None:
            state.account_feasibility_decision = state.small_account_decision
        if tr.get("account_equity") is not None:
            state.account_equity = float(tr["account_equity"])
        if tr.get("buying_power") is not None:
            state.buying_power = float(tr["buying_power"])
        if tr.get("fractional_trading_enabled") is not None:
            state.fractional_trading_enabled = bool(tr["fractional_trading_enabled"])
        if tr.get("max_risk_dollars") is not None:
            state.max_risk_dollars = float(tr["max_risk_dollars"])
        if tr.get("max_daily_loss_dollars") is not None:
            state.max_daily_loss_dollars = float(tr["max_daily_loss_dollars"])
        state.feasible_symbols = _clean_symbols(tr.get("feasible_symbols"))
        state.small_account_rejected_symbols = _clean_symbols(tr.get("rejected_symbols"))
        state.small_account_blockers = [str(x) for x in (tr.get("blockers") or []) if x]
        state.small_account_warnings = [str(x) for x in (tr.get("warnings") or []) if x]
        state.account_feasibility_blockers = [str(x) for x in (tr.get("account_feasibility_blockers") or tr.get("blockers") or []) if x]
        state.account_feasibility_warnings = [str(x) for x in (tr.get("account_feasibility_warnings") or tr.get("warnings") or []) if x]
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
