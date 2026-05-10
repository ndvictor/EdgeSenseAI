from __future__ import annotations

from typing import Any

from app.services.agent_reasoning.agent_contracts import EvidencePack


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _symbols_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    symbols: set[str] = set()
    for row in rows:
        symbol = str(row.get("symbol") or row.get("ticker") or "").strip().upper()
        if symbol:
            symbols.add(symbol)
    return symbols


def _provider_chain_from_rows(rows: list[dict[str, Any]], provider_status: dict[str, Any], scanner_diagnostics: dict[str, Any]) -> list[str]:
    providers: list[str] = []
    for row in rows:
        for key in ("provider_name", "provider_primary", "provider"):
            value = row.get(key)
            if value:
                providers.append(str(value))
        chain = row.get("provider_chain")
        if isinstance(chain, list):
            providers.extend(str(x) for x in chain if x)
    for source in (provider_status, scanner_diagnostics):
        if isinstance(source, dict):
            if source.get("provider_name"):
                providers.append(str(source["provider_name"]))
            chain = source.get("provider_priority") or source.get("provider_chain")
            if isinstance(chain, list):
                providers.extend(str(x) for x in chain if x)
    out: list[str] = []
    for provider in providers:
        key = provider.strip().lower()
        if key and key not in out:
            out.append(key)
    return out


class EvidencePackBuilder:
    """Builds a strict real-data evidence pack for advisory reasoning.

    This class never fetches market data and never creates fallback symbols. It only
    packages symbols/features that already exist in workflow state or current agent
    output.
    """

    @staticmethod
    def build(workflow_state: dict[str, Any], agent_key: str) -> EvidencePack:
        scanner_diagnostics = workflow_state.get("scanner_diagnostics") if isinstance(workflow_state.get("scanner_diagnostics"), dict) else {}
        provider_status = workflow_state.get("provider_status") if isinstance(workflow_state.get("provider_status"), dict) else {}
        market_condition = workflow_state.get("market_context") or workflow_state.get("market_condition")
        if not isinstance(market_condition, dict):
            market_condition = {}
        market_session = workflow_state.get("market_session") if isinstance(workflow_state.get("market_session"), dict) else {}

        scanner_rows: list[dict[str, Any]] = []
        for key in ("scanner_candidates", "selected_candidates", "watchlist_candidates", "candidate_features", "feature_rows", "watchlist"):
            scanner_rows.extend(_dict_list(workflow_state.get(key)))
        for key in ("selected_candidates", "watchlist_candidates"):
            scanner_rows.extend(_dict_list(scanner_diagnostics.get(key)))

        candidate_features = _dict_list(workflow_state.get("candidate_features")) or _dict_list(workflow_state.get("feature_rows"))
        allowed_symbols = sorted(_symbols_from_rows(scanner_rows) | _symbols_from_rows(candidate_features))

        alpha = workflow_state.get("alpha_recommendation") if isinstance(workflow_state.get("alpha_recommendation"), dict) else {}
        alpha_symbol = str(alpha.get("symbol") or workflow_state.get("alpha_selected_symbol") or "").strip().upper()
        if alpha_symbol and alpha_symbol in allowed_symbols:
            allowed_symbols = sorted(set(allowed_symbols) | {alpha_symbol})

        account_policy = {
            "account_equity": workflow_state.get("account_equity"),
            "buying_power": workflow_state.get("buying_power"),
            "fractional_trading_enabled": workflow_state.get("fractional_trading_enabled"),
            "max_risk_per_trade_percent": workflow_state.get("max_risk_per_trade_percent"),
            "max_daily_loss_percent": workflow_state.get("max_daily_loss_percent"),
            "max_open_positions": workflow_state.get("max_open_positions"),
            "max_trades_per_day": workflow_state.get("max_trades_per_day"),
            "paper_trading_enabled": True,
            "live_trading_enabled": False,
            "broker_execution_enabled": False,
            "require_human_approval": True,
        }
        risk_sizing_context = {
            "latest_price": workflow_state.get("latest_price"),
            "spread_bps": workflow_state.get("spread_bps"),
            "avg_dollar_volume": workflow_state.get("avg_dollar_volume"),
            "planned_risk_dollars": workflow_state.get("planned_risk_dollars"),
            "max_risk_dollars": workflow_state.get("max_risk_dollars"),
            "max_daily_loss_dollars": workflow_state.get("max_daily_loss_dollars"),
            "small_account_decision": workflow_state.get("small_account_decision"),
            "small_account_blockers": workflow_state.get("small_account_blockers") or [],
            "small_account_warnings": workflow_state.get("small_account_warnings") or [],
        }
        proof_evidence_status = {
            "proof_status": workflow_state.get("proof_status"),
            "proof_id": workflow_state.get("proof_id"),
            "evidence_blockers": workflow_state.get("evidence_blockers") or [],
            "evidence_warnings": workflow_state.get("evidence_warnings") or [],
            "qlib_available": workflow_state.get("qlib_available"),
            "qlib_version": workflow_state.get("qlib_version"),
            "qlib_artifact_id": workflow_state.get("qlib_artifact_id"),
            "qlib_artifact_counts": workflow_state.get("qlib_artifact_counts") or {},
        }

        return EvidencePack(
            workflow_run_id=str(workflow_state.get("workflow_run_id") or "unknown"),
            orchestrator_run_id=str(workflow_state.get("orchestrator_run_id")) if workflow_state.get("orchestrator_run_id") else None,
            agent_key=agent_key,
            allowed_symbols=allowed_symbols,
            candidate_features=candidate_features,
            scanner_diagnostics=scanner_diagnostics,
            worker_status_summary={
                "data_ingestion": workflow_state.get("data_ingestion_status"),
                "feature_pipeline": workflow_state.get("feature_pipeline_status"),
                "snapshot_count": workflow_state.get("latest_snapshot_count", 0),
                "feature_row_count": workflow_state.get("feature_row_count", 0),
                "persistence_status": workflow_state.get("persistence_status"),
                "freshness_status": workflow_state.get("freshness_status"),
            },
            provider_status={**provider_status, "provider_chain": _provider_chain_from_rows(scanner_rows + candidate_features, provider_status, scanner_diagnostics)},
            market_session=market_session,
            market_condition=market_condition,
            account_policy=account_policy,
            alpha_recommendation=alpha,
            strategy_registry={"selected_strategy_key": workflow_state.get("selected_strategy_key") or workflow_state.get("strategy_key")},
            model_registry={
                "selected_model_key": workflow_state.get("selected_model_key"),
                "selected_model_keys": workflow_state.get("selected_model_keys") or [],
            },
            risk_sizing_context=risk_sizing_context,
            proof_evidence_status=proof_evidence_status,
            hard_rules=[
                "Do not invent symbols, prices, or features.",
                "Do not use mock or synthetic data.",
                "Do not recommend if no real candidate exists in allowed_symbols.",
                "Do not submit orders or call broker.",
                "Do not mark strategy/model active.",
                "If evidence is missing, use missing_evidence and decision=no_qualified_setup or needs_more_evidence.",
                "Zero candidates must propagate as no_qualified_setup or data_unavailable.",
                "AI reasoning is advisory and cannot override deterministic gates.",
            ],
        )
