from __future__ import annotations

from typing import Any

from app.services.agent_runtime.wrappers.backtest_validation_adapter import validate_backtest_or_proof
from app.services.agent_runtime.wrappers.data_readiness_adapter import evaluate_data_readiness
from app.services.agent_runtime.wrappers.market_condition_adapter import scan_market_condition
from app.services.agent_runtime.wrappers.model_selection_adapter import select_models
from app.services.agent_runtime.wrappers.qlib_adapter import qlib_research_snapshot
from app.services.agent_runtime.wrappers.small_account_feasibility_adapter import evaluate_small_account_inputs
from app.services.agent_runtime.wrappers.strategy_selection_adapter import select_strategy
from app.services.agent_runtime.wrappers.watchlist_adapter import build_watchlist
from app.services.agent_runtime.wrappers.safety import SafetyResult


GLUE_AGENT_KEYS = frozenset(
    {
        "data_readiness_agent",
        "market_condition_agent",
        "watchlist_builder_agent",
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
        out = evaluate_data_readiness(symbols=symbols, asset_class=asset_class, horizon=horizon, source=str(s.get("source", "auto")))
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
        include_mock = data_source == "mock"
        seed_symbols = [str(x).upper() for x in (s.get("usable_symbols") or symbols) if x]
        out = build_watchlist(
            asset_class=asset_class,
            horizon=horizon,
            max_symbols=int(s.get("max_symbols", 10)),
            seed_symbols=seed_symbols if orch else None,
            orchestrator_mode=orch,
            data_source=data_source,
            include_mock=include_mock,
        )
        tool = "universe_selection.run_universe_selection" if orch else "candidate_universe.list"
        return {
            "tool_name": tool,
            "tool_request": {"asset_class": asset_class, "horizon": horizon, "source": data_source, "seeds": seed_symbols if orch else None},
            "tool_response": out,
            "next_agent": "strategy_selection_agent" if out.get("symbols") else None,
            "safety": safety,
        }

    if agent_key == "strategy_selection_agent":
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
        out = evaluate_small_account_inputs(s)
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

