from datetime import datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.services.auto_run_control_service import AutoRunControlState, get_auto_run_state
from app.services.edge_signal_rules_service import EdgeSignalRule, get_rules_for_signals
from app.services.market_data_service import MarketDataService
from app.services.market_scan_run_service import record_scan_run, update_scan_run_workflow_result
from app.services.strategy_workflow_run_service import StrategyWorkflowRunRequest, run_strategy_workflow_from_signal
from app.strategies.registry import StrategyConfig, get_strategy


class MarketScannerRequest(BaseModel):
    strategy_key: str
    symbols: list[str] = Field(default_factory=list)
    data_source: str = "auto"
    auto_run: bool = False
    trigger_type: Literal["manual", "scheduled"] = "manual"
    trigger_workflow: bool = False
    account_size: float | None = None
    max_risk_per_trade: float | None = None


class MarketScannerSignal(BaseModel):
    symbol: str
    signal_key: str
    display_name: str
    status: str
    reason: str
    confidence: float
    data_source: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class MarketScannerResponse(BaseModel):
    run_id: str
    trigger_type: Literal["manual", "scheduled"] = "manual"
    strategy_key: str
    symbols_scanned: list[str]
    matched_signals: list[MarketScannerSignal]
    skipped_signals: list[MarketScannerSignal]
    should_trigger_workflow: bool
    recommended_workflow_key: str
    workflow_trigger_status: str = "not_triggered"
    workflow_run_id: str | None = None
    cooldown_remaining_seconds: int | None = None
    required_agents: list[str]
    required_models: list[str]
    safety_state: AutoRunControlState
    next_action: str
    data_source: str


_MARKET_DATA = MarketDataService()
_WORKFLOW_TRIGGER_COOLDOWNS: dict[tuple[str, str, str], datetime] = {}
_DEFAULT_WORKFLOW_TRIGGER_COOLDOWN_SECONDS = 15 * 60


def _workflow_cooldown_key(strategy_key: str, symbol: str, matched_signal_key: str) -> tuple[str, str, str]:
    return (strategy_key, symbol.upper(), matched_signal_key)


def _workflow_cooldown_remaining_seconds(strategy_key: str, symbol: str, matched_signal_key: str, checked_at: datetime | None = None) -> int | None:
    now = checked_at or datetime.utcnow()
    key = _workflow_cooldown_key(strategy_key, symbol, matched_signal_key)
    expires_at = _WORKFLOW_TRIGGER_COOLDOWNS.get(key)
    if expires_at is None:
        return None
    remaining = int((expires_at - now).total_seconds())
    if remaining <= 0:
        _WORKFLOW_TRIGGER_COOLDOWNS.pop(key, None)
        return None
    return remaining


def _mark_workflow_cooldown(strategy_key: str, symbol: str, matched_signal_key: str, checked_at: datetime | None = None) -> None:
    now = checked_at or datetime.utcnow()
    _WORKFLOW_TRIGGER_COOLDOWNS[_workflow_cooldown_key(strategy_key, symbol, matched_signal_key)] = now + timedelta(seconds=_DEFAULT_WORKFLOW_TRIGGER_COOLDOWN_SECONDS)


def _source_label(snapshot: dict[str, Any]) -> str:
    if snapshot.get("is_mock"):
        return "demo"
    if snapshot.get("provider") and snapshot.get("data_quality") not in {"unavailable", "not_configured"}:
        return "source_backed"
    return "placeholder"


def _relative_volume(snapshot: dict[str, Any]) -> float | None:
    volume = snapshot.get("volume")
    average = snapshot.get("average_volume")
    if volume and average:
        return float(volume) / float(average)
    return snapshot.get("relative_volume")


def _spread_present(snapshot: dict[str, Any]) -> bool:
    return snapshot.get("bid_ask_spread") is not None or (snapshot.get("bid") is not None and snapshot.get("ask") is not None)


def _evaluate_rule(symbol: str, rule: EdgeSignalRule, snapshot: dict[str, Any]) -> MarketScannerSignal:
    data_source = _source_label(snapshot)
    price = snapshot.get("price") or snapshot.get("current_price")
    rvol = _relative_volume(snapshot)
    change_percent = float(snapshot.get("change_percent") or 0)
    vwap = snapshot.get("vwap")
    spread_ok = _spread_present(snapshot)

    if rule.signal_key == "rvol_spike":
        matched = bool(rvol and rvol >= 1.5)
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="matched" if matched else "skipped", reason=f"RVOL={round(rvol, 2) if rvol else 'unavailable'}; threshold=1.5.", confidence=0.72 if matched else 0.35, data_source=data_source, metadata={"relative_volume": rvol})
    if rule.signal_key in {"short_term_momentum", "low_float_breakout"}:
        matched = change_percent >= 1 and bool(snapshot.get("volume"))
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="matched" if matched else "skipped", reason=f"Change percent={round(change_percent, 2)}; volume {'present' if snapshot.get('volume') else 'missing'}.", confidence=0.68 if matched else 0.35, data_source=data_source, metadata={"change_percent": change_percent})
    if rule.signal_key == "mean_reversion_1_5_min":
        matched = bool(price and vwap and abs((float(price) - float(vwap)) / float(vwap)) >= 0.01 and spread_ok)
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="matched" if matched else "skipped", reason="VWAP extension and spread check evaluated when fields are available.", confidence=0.62 if matched else 0.3, data_source=data_source, metadata={"price": price, "vwap": vwap, "spread_present": spread_ok})
    if rule.signal_key in {"unusual_calls_puts", "advanced_options_flow"}:
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="placeholder", reason="Options chain data is not available in this scanner pass.", confidence=0.0, data_source="placeholder")
    if rule.signal_key == "breakout":
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="placeholder", reason="Support/resistance levels are not available yet.", confidence=0.0, data_source="placeholder")
    if rule.signal_key == "regime_shift":
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="placeholder", reason="Regime shift detection requires regime feature pipeline.", confidence=0.0, data_source="placeholder")
    if rule.signal_key in {"retail_sentiment_spike", "etf_stock_lag_pairs", "order_book_imbalance"}:
        return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="placeholder", reason="Required sentiment, pair, or order-book inputs are not wired yet.", confidence=0.0, data_source="placeholder")
    return MarketScannerSignal(symbol=symbol, signal_key=rule.signal_key, display_name=rule.display_name, status="skipped", reason="Rule has no deterministic evaluator yet.", confidence=0.0, data_source="placeholder")


def _recommended_workflow(strategy: StrategyConfig) -> str:
    if strategy.strategy_key in {"stock_day_trading", "stock_swing", "crypto_intraday", "crypto_swing"}:
        return "small_account_edge_radar"
    return "manual_research_review"


def run_market_condition_scan(request: MarketScannerRequest) -> MarketScannerResponse:
    started_at = datetime.utcnow()
    strategy = get_strategy(request.strategy_key)
    if strategy is None:
        safety_state = get_auto_run_state()
        next_action = "Unknown strategy. Select a configured strategy before scanning."
        run = record_scan_run(
            trigger_type=request.trigger_type,
            strategy_key=request.strategy_key,
            symbols=request.symbols,
            data_source="placeholder",
            auto_run_enabled=safety_state.auto_run_enabled,
            matched_signals_count=0,
            skipped_signals_count=0,
            should_trigger_workflow=False,
            recommended_workflow_key="none",
            required_agents=[],
            required_models=[],
            safety_state=safety_state.model_dump(),
            next_action=next_action,
            status="failed",
            started_at=started_at,
            errors=[f"Unknown strategy: {request.strategy_key}"],
        )
        return MarketScannerResponse(run_id=run.run_id, trigger_type=request.trigger_type, strategy_key=request.strategy_key, symbols_scanned=request.symbols, matched_signals=[], skipped_signals=[], should_trigger_workflow=False, recommended_workflow_key="none", workflow_trigger_status="failed", required_agents=[], required_models=[], safety_state=safety_state, next_action=next_action, data_source="placeholder")

    rules = get_rules_for_signals(strategy.edge_signals)
    matched: list[MarketScannerSignal] = []
    skipped: list[MarketScannerSignal] = []
    sources: set[str] = set()
    for symbol in request.symbols:
        snapshot = _MARKET_DATA.get_market_snapshot(symbol, source=request.data_source)
        sources.add(_source_label(snapshot))
        for rule in rules:
            if strategy.asset_class not in rule.supported_asset_classes and "option" not in rule.supported_asset_classes:
                skipped.append(MarketScannerSignal(symbol=symbol.upper(), signal_key=rule.signal_key, display_name=rule.display_name, status="skipped", reason=f"Rule does not support {strategy.asset_class}.", confidence=0.0, data_source="placeholder"))
                continue
            result = _evaluate_rule(symbol.upper(), rule, snapshot)
            if result.status == "matched":
                matched.append(result)
            else:
                skipped.append(result)

    safety_state = get_auto_run_state()
    can_auto_trigger = bool(request.auto_run and safety_state.auto_run_enabled and not safety_state.live_trading_enabled and strategy.auto_run_supported and safety_state.paper_trading_enabled and safety_state.require_human_approval)
    can_manual_trigger = bool(request.trigger_workflow and not safety_state.live_trading_enabled and safety_state.paper_trading_enabled and safety_state.require_human_approval)
    should_trigger = bool(matched) and (can_auto_trigger or can_manual_trigger)
    if not matched:
        next_action = "No deterministic edge signal matched. Continue monitoring."
    elif not can_auto_trigger:
        next_action = "Matched signals require manual paper/research review before workflow trigger."
    else:
        next_action = "Trigger paper/research workflow with human approval gate."
    data_source = "source_backed" if "source_backed" in sources else "demo" if "demo" in sources else "placeholder"
    run_status = "trigger_ready" if should_trigger else "completed"
    warnings: list[str] = []
    if matched and not should_trigger:
        warnings.append("Matched signals require manual paper/research review; no automatic execution was run.")
    run = record_scan_run(
        trigger_type=request.trigger_type,
        strategy_key=strategy.strategy_key,
        symbols=request.symbols,
        data_source=data_source,
        auto_run_enabled=safety_state.auto_run_enabled,
        matched_signals_count=len(matched),
        skipped_signals_count=len(skipped),
        should_trigger_workflow=should_trigger,
        recommended_workflow_key=_recommended_workflow(strategy),
        workflow_trigger_status="not_triggered" if not should_trigger else "pending",
        required_agents=strategy.required_agents,
        required_models=strategy.required_models,
        safety_state=safety_state.model_dump(),
        next_action=next_action,
        status=run_status,
        started_at=started_at,
        warnings=warnings,
    )
    workflow_trigger_status = "not_triggered"
    workflow_run_id: str | None = None
    cooldown_remaining_seconds: int | None = None
    if matched and request.auto_run and not safety_state.auto_run_enabled:
        workflow_trigger_status = "skipped_auto_run_disabled"
    elif should_trigger:
        top_signal = matched[0]
        cooldown_remaining_seconds = _workflow_cooldown_remaining_seconds(strategy.strategy_key, top_signal.symbol, top_signal.signal_key)
        if cooldown_remaining_seconds is not None:
            workflow_trigger_status = "skipped_cooldown_active"
        else:
            try:
                workflow_run = run_strategy_workflow_from_signal(
                    StrategyWorkflowRunRequest(
                        strategy_key=strategy.strategy_key,
                        symbol=top_signal.symbol,
                        asset_class=strategy.asset_class,
                        horizon=strategy.timeframe,
                        matched_signal_key=top_signal.signal_key,
                        matched_signal_name=top_signal.display_name,
                        source_scan_run_id=run.run_id,
                        trigger_type="scanner_match",
                        data_source=request.data_source,
                        account_size=request.account_size,
                        max_risk_per_trade=request.max_risk_per_trade,
                    )
                )
                workflow_trigger_status = "triggered"
                workflow_run_id = workflow_run.workflow_run_id
                _mark_workflow_cooldown(strategy.strategy_key, top_signal.symbol, top_signal.signal_key)
            except Exception as exc:
                workflow_trigger_status = "failed"
                warnings.append(f"Strategy workflow trigger failed: {exc}")
        update_scan_run_workflow_result(run.run_id, workflow_trigger_status, workflow_run_id, cooldown_remaining_seconds)
    else:
        update_scan_run_workflow_result(run.run_id, workflow_trigger_status, workflow_run_id)
    return MarketScannerResponse(
        run_id=run.run_id,
        trigger_type=request.trigger_type,
        strategy_key=strategy.strategy_key,
        symbols_scanned=[symbol.upper() for symbol in request.symbols],
        matched_signals=matched,
        skipped_signals=skipped,
        should_trigger_workflow=should_trigger,
        recommended_workflow_key=_recommended_workflow(strategy),
        workflow_trigger_status=workflow_trigger_status,
        workflow_run_id=workflow_run_id,
        cooldown_remaining_seconds=cooldown_remaining_seconds,
        required_agents=strategy.required_agents,
        required_models=strategy.required_models,
        safety_state=safety_state,
        next_action=next_action,
        data_source=data_source,
    )
