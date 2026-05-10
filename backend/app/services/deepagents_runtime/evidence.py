"""Evidence pack construction for DeepAgents advisory reasoning."""

from __future__ import annotations

from typing import Any

from app.services.deepagents_runtime.schemas import EvidencePack, OwnerAuthority


def _resolve_owner_authority(workflow_state: dict[str, Any]) -> OwnerAuthority:
    """Resolve the owner authority granted to the agent runtime.

    Precedence:
    1. Explicit ``owner_authority`` block in ``workflow_state``.
    2. ``agent_capability_flags`` carried alongside the workflow state.
    3. Fallback to ``Settings.agent_capability_flags`` (already gated by
       LIVE_TRADING_ENABLED / BROKER_EXECUTION_ENABLED).
    4. Conservative ``read_only`` default.
    """
    explicit = workflow_state.get("owner_authority")
    if isinstance(explicit, OwnerAuthority):
        return explicit
    if isinstance(explicit, dict):
        try:
            return OwnerAuthority.model_validate(explicit)
        except Exception:
            pass

    flags = workflow_state.get("agent_capability_flags")
    if not isinstance(flags, dict):
        try:
            from app.core.settings import get_settings

            flags = get_settings().agent_capability_flags
        except Exception:
            flags = None

    if not isinstance(flags, dict):
        return OwnerAuthority.read_only()

    can_recommend = bool(flags.get("agent_can_recommend_trades"))
    can_paper_plan = bool(flags.get("agent_can_create_paper_plans"))
    can_approval = bool(flags.get("agent_can_create_approval_requests"))
    can_paper_submit = bool(flags.get("agent_can_submit_paper_orders"))
    can_live_submit = bool(flags.get("agent_can_submit_live_orders"))

    if can_live_submit:
        level = "live_submit"
    elif can_paper_submit:
        level = "paper_submit"
    elif can_paper_plan or can_approval:
        level = "paper_plan"
    elif can_recommend:
        level = "advise"
    else:
        level = "read_only"

    return OwnerAuthority(
        level=level,  # type: ignore[arg-type]
        can_recommend_trades=can_recommend,
        can_create_paper_plans=can_paper_plan,
        can_create_approval_requests=can_approval,
        can_submit_paper_orders=can_paper_submit,
        can_submit_live_orders=can_live_submit,
        require_human_approval=True,
    )


_PRICE_KEYS = (
    "last_price",
    "latest_price",
    "price",
    "close",
    "current_price",
    "bid",
    "ask",
    "entry",
    "stop",
    "target",
)

# Sources that must never feed the watchlist evidence pack.
# ``universe_selection``/``candidate_universe`` are pre-scan universe picks (not
# real scanner candidates); ``default``/``fallback`` are deterministic fallbacks
# that should never produce LLM-influenced trade decisions.
_FORBIDDEN_ROW_SOURCES = frozenset(
    {
        "universe_selection",
        "candidate_universe",
        "default",
        "fallback",
        "static_universe",
        "static_default",
    }
)

_FORBIDDEN_DATA_QUALITY = frozenset({"fail", "stale", "non_real", "synthetic", "fake", "mock"})


def _dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _symbol_from_row(row: dict[str, Any]) -> str:
    return str(row.get("symbol") or row.get("ticker") or "").strip().upper()


def _symbols_from_rows(rows: list[dict[str, Any]]) -> set[str]:
    return {symbol for row in rows if (symbol := _symbol_from_row(row))}


def _is_real_scanner_row(row: dict[str, Any]) -> bool:
    """Return True only for rows that represent a real, fresh, scanner-linked candidate.

    Rejects:
      * rows with no symbol
      * rows explicitly marked ``stale``/``is_stale``/``non_real``/``synthetic``
      * rows whose ``data_quality`` indicates failure/staleness/non-real data
      * rows whose ``source``/``source_type``/``candidate_source`` resolves to a
        forbidden universe-selection or fallback source
    """
    if not isinstance(row, dict):
        return False
    if not _symbol_from_row(row):
        return False
    for stale_key in ("stale", "is_stale", "non_real", "synthetic", "is_synthetic"):
        if bool(row.get(stale_key)):
            return False
    quality = str(row.get("data_quality") or "").strip().lower()
    if quality and quality in _FORBIDDEN_DATA_QUALITY:
        return False
    for source_key in ("source", "source_type", "candidate_source", "row_source"):
        value = str(row.get(source_key) or "").strip().lower()
        if value and value in _FORBIDDEN_ROW_SOURCES:
            return False
    return True


def _filter_real_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in rows if _is_real_scanner_row(row)]


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


def _known_prices(rows: list[dict[str, Any]]) -> dict[str, list[float]]:
    prices: dict[str, list[float]] = {}
    for row in rows:
        symbol = _symbol_from_row(row)
        if not symbol:
            continue
        bucket = prices.setdefault(symbol, [])
        for key in _PRICE_KEYS:
            raw = row.get(key)
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if value > 0 and value not in bucket:
                bucket.append(value)
    return {symbol: sorted(values) for symbol, values in prices.items() if values}


class EvidencePackBuilder:
    """Build a closed-world evidence pack without fetching data or symbols."""

    @staticmethod
    def build(workflow_state: dict[str, Any], agent_key: str = "watchlist_builder_agent") -> EvidencePack:
        scanner_diagnostics = workflow_state.get("scanner_diagnostics") if isinstance(workflow_state.get("scanner_diagnostics"), dict) else {}
        provider_status = workflow_state.get("provider_status") if isinstance(workflow_state.get("provider_status"), dict) else {}
        market_condition = workflow_state.get("market_context") or workflow_state.get("market_condition")
        if not isinstance(market_condition, dict):
            market_condition = {}
        market_session = workflow_state.get("market_session") if isinstance(workflow_state.get("market_session"), dict) else {}

        scanner_rows: list[dict[str, Any]] = []
        for key in ("scanner_candidates", "selected_candidates", "watchlist_candidates", "ranked_candidates", "watchlist"):
            scanner_rows.extend(_dict_list(workflow_state.get(key)))
        for key in ("selected_candidates", "watchlist_candidates"):
            scanner_rows.extend(_dict_list(scanner_diagnostics.get(key)))

        # Drop universe_selection / candidate_universe / fallback / stale / synthetic rows.
        scanner_rows = _filter_real_rows(scanner_rows)

        candidate_features = _dict_list(workflow_state.get("candidate_features")) or _dict_list(workflow_state.get("feature_rows"))
        candidate_features = _filter_real_rows(candidate_features)
        allowed_symbols = sorted(_symbols_from_rows(scanner_rows) | _symbols_from_rows(candidate_features))

        alpha = workflow_state.get("alpha_recommendation") if isinstance(workflow_state.get("alpha_recommendation"), dict) else {}
        alpha_symbol = str(alpha.get("symbol") or workflow_state.get("alpha_selected_symbol") or "").strip().upper()
        if alpha_symbol and alpha_symbol in allowed_symbols:
            allowed_symbols = sorted(set(allowed_symbols) | {alpha_symbol})

        all_rows = scanner_rows + candidate_features
        return EvidencePack(
            workflow_run_id=str(workflow_state.get("workflow_run_id") or "unknown"),
            orchestrator_run_id=str(workflow_state.get("orchestrator_run_id")) if workflow_state.get("orchestrator_run_id") else None,
            agent_key=agent_key,
            allowed_symbols=allowed_symbols,
            scanner_candidates=scanner_rows,
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
            provider_status={**provider_status, "provider_chain": _provider_chain_from_rows(all_rows, provider_status, scanner_diagnostics)},
            market_session=market_session,
            market_condition=market_condition,
            account_policy={
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
            },
            alpha_recommendation=alpha,
            strategy_registry={"selected_strategy_key": workflow_state.get("selected_strategy_key") or workflow_state.get("strategy_key")},
            model_registry={
                "selected_model_key": workflow_state.get("selected_model_key"),
                "selected_model_keys": workflow_state.get("selected_model_keys") or [],
            },
            risk_sizing_context={
                "latest_price": workflow_state.get("latest_price"),
                "spread_bps": workflow_state.get("spread_bps"),
                "avg_dollar_volume": workflow_state.get("avg_dollar_volume"),
                "planned_risk_dollars": workflow_state.get("planned_risk_dollars"),
                "max_risk_dollars": workflow_state.get("max_risk_dollars"),
                "max_daily_loss_dollars": workflow_state.get("max_daily_loss_dollars"),
                "small_account_decision": workflow_state.get("small_account_decision"),
                "small_account_blockers": workflow_state.get("small_account_blockers") or [],
                "small_account_warnings": workflow_state.get("small_account_warnings") or [],
            },
            execution_plan=workflow_state.get("execution_plan") if isinstance(workflow_state.get("execution_plan"), dict) else {},
            proof_evidence_status={
                "proof_status": workflow_state.get("proof_status"),
                "proof_id": workflow_state.get("proof_id"),
                "evidence_blockers": workflow_state.get("evidence_blockers") or [],
                "evidence_warnings": workflow_state.get("evidence_warnings") or [],
                "qlib_available": workflow_state.get("qlib_available"),
                "qlib_version": workflow_state.get("qlib_version"),
                "qlib_artifact_id": workflow_state.get("qlib_artifact_id"),
                "qlib_artifact_counts": workflow_state.get("qlib_artifact_counts") or {},
            },
            known_prices=_known_prices(all_rows),
            owner_authority=_resolve_owner_authority(workflow_state),
            hard_rules=[
                "DeepAgent may reason only over this evidence pack.",
                "Do not invent symbols, prices, features, indicators, backtests, models, or data.",
                "Do not use mock, synthetic, demo, or fake data.",
                "Do not recommend if no real candidate exists in allowed_symbols.",
                "Do not call brokers or submit orders.",
                "Do not mark strategy/model active or promote a strategy/model.",
                "LLM output is advisory only; deterministic gates remain final authority.",
                "Zero candidates must propagate as no_qualified_setup or data_unavailable.",
            ],
        )
