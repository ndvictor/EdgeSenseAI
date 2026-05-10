from __future__ import annotations

from typing import Any

from app.services.agent_runtime.wrappers.alpha_engine_adapter import run_alpha_engine_selection
from app.services.agent_runtime.wrappers.backtest_validation_adapter import validate_backtest_or_proof
from app.services.agent_runtime.wrappers.data_readiness_adapter import evaluate_data_readiness
from app.services.agent_runtime.wrappers.market_condition_adapter import scan_market_condition
from app.services.agent_runtime.wrappers.model_selection_adapter import select_models
from app.services.agent_runtime.wrappers.qlib_adapter import qlib_research_snapshot
from app.services.agent_runtime.wrappers.small_account_feasibility_adapter import evaluate_small_account_inputs
from app.services.agent_runtime.wrappers.strategy_selection_adapter import select_strategy
from app.services.agent_runtime.wrappers.watchlist_adapter import build_watchlist, watchlist_from_workflow_scanner_rows
from app.services.agent_runtime.wrappers.safety import SafetyResult


GLUE_AGENT_KEYS = frozenset(
    {
        "data_readiness_agent",
        "market_condition_agent",
        "watchlist_builder_agent",
        "alpha_engine_agent",
        "strategy_selection_agent",
        "model_selection_agent",
        "backtest_validation_agent",
        "qlib_research_agent",
        "small_account_feasibility_agent",
    }
)


def run_glue_agent(*, agent_key: str, inputs: dict[str, Any], context: dict[str, Any], safety: SafetyResult) -> dict[str, Any]:
    s = safety.sanitized_inputs

    asset_class = str(s.get("asset_class", "stock"))
    horizon = str(s.get("horizon", "day_trading"))
    symbols = s.get("symbols") or [s.get("symbol")] if s.get("symbol") else []
    symbols = [str(x).upper() for x in symbols if x]

    if agent_key == "data_readiness_agent":
        sc = s.get("scanner_candidates")
        scanner_for_readiness = sc if isinstance(sc, list) else None
        out = evaluate_data_readiness(
            symbols=symbols,
            asset_class=asset_class,
            horizon=horizon,
            source=str(s.get("source", "auto")),
            scanner_candidates=scanner_for_readiness,
        )
        return {"tool_name": "feature_store.run", "tool_request": {"symbols": symbols, "asset_class": asset_class, "horizon": horizon}, "tool_response": out, "next_agent": out.get("next_agent"), "safety": safety}

    if agent_key == "market_condition_agent":
        if not symbols:
            out = {
                "decision": "discovery",
                "market_context": {"should_trigger_workflow": False, "regime": "unknown", "discovery_mode": True},
                "blockers": [],
                "warnings": ["market_condition_deferred_until_discovery_candidates"],
                "next_agent": "watchlist_builder_agent",
                "next_action": "Continue to watchlist discovery; no manual symbols were supplied.",
            }
            return {"tool_name": "market_scanner.scan", "tool_request": {"symbols": symbols}, "tool_response": out, "next_agent": "watchlist_builder_agent", "safety": safety}
        out = scan_market_condition(symbols=symbols, source=str(s.get("source", "auto")))
        mc = out["market_context"]
        next_agent = "workflow_router_agent" if mc.get("should_trigger_workflow") else "watchlist_builder_agent"
        return {"tool_name": "market_scanner.scan", "tool_request": {"symbols": symbols}, "tool_response": out, "next_agent": next_agent, "safety": safety}

    if agent_key == "watchlist_builder_agent":
        orch = context.get("source") == "workflow_orchestrator"
        data_source = str(s.get("source", "auto"))
        # Manual seeds = workflow HTTP body only (workflow_request_symbols). Never use state.symbols here:
        # data_readiness carryforward sets state.symbols from usable_symbols and would wrongly trigger universe_selection.
        req_syms = s.get("workflow_request_symbols")
        if not isinstance(req_syms, list):
            req_syms = []
        manual_seeds = [str(x).upper() for x in req_syms if x]
        discovery_symbols = [str(x).upper() for x in (s.get("usable_symbols") or []) if x]
        scanner_payload = s.get("scanner_candidates") if isinstance(s.get("scanner_candidates"), list) else []
        if orch and manual_seeds and scanner_payload:
            row_by = {
                str(r.get("symbol") or "").strip().upper(): r
                for r in scanner_payload
                if isinstance(r, dict) and r.get("symbol")
            }
            ordered_rows: list[dict[str, Any]] = []
            for m in manual_seeds:
                hit = row_by.get(m)
                if hit is None:
                    ordered_rows = []
                    break
                ordered_rows.append(hit)
            if ordered_rows and len(ordered_rows) == len(manual_seeds):
                cand_src = str(s.get("candidate_source") or "manual_request")
                out = watchlist_from_workflow_scanner_rows(
                    ordered_rows,
                    max_symbols=int(s.get("max_symbols", 10)),
                    candidate_source=cand_src,
                )
                tool = "watchlist_builder.scanner_runtime_prefill"
                return {
                    "tool_name": tool,
                    "tool_request": {
                        "asset_class": asset_class,
                        "horizon": horizon,
                        "source": data_source,
                        "manual_seeds": manual_seeds,
                        "prefill_rows": len(ordered_rows),
                    },
                    "tool_response": out,
                    "next_agent": "alpha_engine_agent" if out.get("symbols") or out.get("recommendation") else None,
                    "safety": safety,
                }
        out = build_watchlist(
            asset_class=asset_class,
            horizon=horizon,
            max_symbols=int(s.get("max_symbols", 10)),
            seed_symbols=manual_seeds if orch else None,
            discovery_symbols=discovery_symbols if orch else None,
            orchestrator_mode=orch,
            data_source=data_source,
        )
        used_univ = bool(manual_seeds) and orch and out.get("candidate_source") == "universe_selection"
        tool = "universe_selection.run_universe_selection" if used_univ else ("watchlist_builder.discovery" if orch else "candidate_universe.list")
        return {
            "tool_name": tool,
            "tool_request": {
                "asset_class": asset_class,
                "horizon": horizon,
                "source": data_source,
                "manual_seeds": manual_seeds if orch else None,
                "discovery_symbols": discovery_symbols if orch else None,
            },
            "tool_response": out,
            "next_agent": "alpha_engine_agent" if out.get("symbols") or out.get("recommendation") else None,
            "safety": safety,
        }

    if agent_key == "alpha_engine_agent":
        out = run_alpha_engine_selection(s, context)
        return {
            "tool_name": "alpha_engine.generate_alpha_recommendation",
            "tool_request": {
                "feature_rows": len(s.get("feature_rows") or []),
                "scanner_candidates": len(s.get("scanner_candidates") or []),
                "watchlist": len(s.get("watchlist") or []),
                "usable_symbols": len(s.get("usable_symbols") or []),
                "selected_symbol": s.get("selected_symbol") or s.get("symbol"),
            },
            "tool_response": out,
            "next_agent": "strategy_selection_agent",
            "safety": safety,
        }

    if agent_key == "strategy_selection_agent":
        alpha_status = str(s.get("alpha_status") or "")
        if alpha_status in {"candidate_selected", "watchlist_only", "needs_more_evidence"}:
            strat = s.get("alpha_strategy_key") or s.get("strategy_key") or s.get("selected_strategy_key")
            sym = s.get("alpha_selected_symbol") or s.get("selected_symbol") or s.get("symbol")
            out = {
                "selected_strategy_key": strat,
                "selected_symbol": sym,
                "proof_status": "unknown",
                "blockers": [],
                "warnings": list(s.get("alpha_warnings") or []),
                "next_agent": "model_selection_agent" if sym and strat else ("model_selection_agent" if sym else None),
                "next_action": "Use Alpha Engine selected strategy and symbol.",
            }
            return {
                "tool_name": "alpha_engine.strategy_selection",
                "tool_request": {
                    "alpha_status": alpha_status,
                    "alpha_selected_symbol": sym,
                    "alpha_strategy_key": strat,
                    "workflow_run_id": context.get("workflow_run_id"),
                    "orchestrator_run_id": context.get("orchestrator_run_id"),
                },
                "tool_response": out,
                "next_agent": out.get("next_agent"),
                "safety": safety,
            }
        if alpha_status in {"no_qualified_setup", "data_unavailable", "blocked"}:
            blockers = list(s.get("alpha_blockers") or [])
            if not blockers:
                blockers = [f"alpha_engine_{alpha_status}"]
            out = {
                "selected_strategy_key": None,
                "selected_symbol": None,
                "proof_status": "unknown",
                "blockers": blockers,
                "warnings": list(s.get("alpha_warnings") or []),
                "next_agent": None,
                "next_action": "No Alpha Engine candidate selected; strategy selection stopped.",
            }
            return {
                "tool_name": "alpha_engine.strategy_selection",
                "tool_request": {
                    "alpha_status": alpha_status,
                    "workflow_run_id": context.get("workflow_run_id"),
                    "orchestrator_run_id": context.get("orchestrator_run_id"),
                },
                "tool_response": out,
                "next_agent": None,
                "safety": safety,
            }
        out = select_strategy(
            market_phase=str(s.get("market_phase", "market_open")),
            active_loop=str(s.get("active_loop", "paper_first")),
            regime=str(s.get("regime", "risk_on")),
            horizon=horizon,
        )
        return {
            "tool_name": "strategy_ranking.run_strategy_ranking",
            "tool_request": {
                "market_phase": s.get("market_phase"),
                "active_loop": s.get("active_loop"),
                "regime": s.get("regime"),
                "workflow_run_id": context.get("workflow_run_id"),
                "orchestrator_run_id": context.get("orchestrator_run_id"),
            },
            "tool_response": out,
            "next_agent": "model_selection_agent" if out.get("selected_strategy_key") else None,
            "safety": safety,
        }

    if agent_key == "model_selection_agent":
        symbol = str(s.get("symbol") or (symbols[0] if symbols else ""))
        if not symbol:
            out = {
                "decision": "blocked",
                "selected_model_key": None,
                "selected_model_keys": [],
                "blockers": ["no_selected_symbol"],
                "warnings": [],
                "next_agent": None,
                "next_action": "Select a real provider-backed symbol before model selection.",
            }
            return {"tool_name": "model_orchestrator.run_model_orchestrator", "tool_request": {"symbol": None, "strategy_key": s.get("strategy_key")}, "tool_response": out, "next_agent": None, "safety": safety}
        out = select_models(symbol=symbol, asset_class=asset_class, horizon=horizon, strategy_key=str(s.get("strategy_key")) if s.get("strategy_key") else None)
        return {"tool_name": "model_orchestrator.run_model_orchestrator", "tool_request": {"symbol": symbol, "strategy_key": s.get("strategy_key")}, "tool_response": out, "next_agent": out.get("next_agent"), "safety": safety}

    if agent_key == "backtest_validation_agent":
        out = validate_backtest_or_proof(strategy_key=str(s.get("strategy_key", "stock_day_trading")), asset_class=asset_class, horizon=horizon)
        return {"tool_name": "proof_registry.lookup", "tool_request": {"strategy_key": s.get("strategy_key")}, "tool_response": out, "next_agent": "strategy_eligibility_agent" if out.get("proof_status") in {"proven", "paper_passed"} else None, "safety": safety}

    if agent_key == "qlib_research_agent":
        out = qlib_research_snapshot(limit=int(s.get("limit", 10)), horizon=horizon)
        return {"tool_name": "qlib.status_and_artifacts", "tool_request": {"limit": s.get("limit", 10)}, "tool_response": out, "next_agent": out.get("next_agent") or "small_account_feasibility_agent", "safety": safety}

    if agent_key == "small_account_feasibility_agent":
        merged_inputs: dict[str, Any] = dict(s)
        if merged_inputs.get("latest_price") is None:
            ar = merged_inputs.get("alpha_recommendation")
            if isinstance(ar, dict):
                ep = ar.get("entry_plan")
                if isinstance(ep, dict) and ep.get("entry") is not None:
                    merged_inputs["latest_price"] = ep.get("entry")
        if merged_inputs.get("avg_dollar_volume") is None:
            sc = merged_inputs.get("scanner_candidates")
            sel = str(merged_inputs.get("selected_symbol") or merged_inputs.get("symbol") or "").strip().upper()
            if isinstance(sc, list) and sel:
                for row in sc:
                    if not isinstance(row, dict):
                        continue
                    sym = str(row.get("symbol") or "").strip().upper()
                    if sym == sel and row.get("dollar_volume") is not None:
                        merged_inputs["avg_dollar_volume"] = row.get("dollar_volume")
                        break
        out = evaluate_small_account_inputs(merged_inputs)
        return {
            "tool_name": "small_account_feasibility.evaluate",
            "tool_request": {
                "account_equity": s.get("account_equity"),
                "selected_symbol": s.get("selected_symbol") or s.get("symbol"),
                "latest_price": s.get("latest_price"),
                "spread_bps": s.get("spread_bps"),
                "avg_dollar_volume": s.get("avg_dollar_volume"),
                "planned_risk_dollars": s.get("planned_risk_dollars"),
                "open_positions": s.get("open_positions", 0),
                "day_trades_used": s.get("day_trades_used", 0),
            },
            "tool_response": out,
            "next_agent": out.get("next_agent"),
            "safety": safety,
        }

    return {"tool_name": "not_implemented", "tool_request": s, "tool_response": {"status": "not_implemented", "message": "No glue agent wrapper."}, "next_agent": None, "safety": safety}

