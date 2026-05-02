from typing import Any

from pydantic import BaseModel, Field

from app.services.auto_run_control_service import AutoRunControlState, get_auto_run_state
from app.services.edge_signal_rules_service import EdgeSignalRule, get_rules_for_signals
from app.services.market_data_service import MarketDataService
from app.strategies.registry import StrategyConfig, get_strategy


class MarketScannerRequest(BaseModel):
    strategy_key: str
    symbols: list[str] = Field(default_factory=lambda: ["AMD"])
    data_source: str = "auto"
    auto_run: bool = False
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
    strategy_key: str
    symbols_scanned: list[str]
    matched_signals: list[MarketScannerSignal]
    skipped_signals: list[MarketScannerSignal]
    should_trigger_workflow: bool
    recommended_workflow_key: str
    required_agents: list[str]
    required_models: list[str]
    safety_state: AutoRunControlState
    next_action: str
    data_source: str


_MARKET_DATA = MarketDataService()


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
    strategy = get_strategy(request.strategy_key)
    if strategy is None:
        safety_state = get_auto_run_state()
        return MarketScannerResponse(strategy_key=request.strategy_key, symbols_scanned=request.symbols, matched_signals=[], skipped_signals=[], should_trigger_workflow=False, recommended_workflow_key="none", required_agents=[], required_models=[], safety_state=safety_state, next_action="Unknown strategy. Select a configured strategy before scanning.", data_source="placeholder")

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
    can_auto_trigger = bool(request.auto_run and safety_state.auto_run_enabled and strategy.auto_run_supported and safety_state.paper_trading_enabled and safety_state.require_human_approval)
    should_trigger = bool(matched) and can_auto_trigger
    if not matched:
        next_action = "No deterministic edge signal matched. Continue monitoring."
    elif not can_auto_trigger:
        next_action = "Matched signals require manual paper/research review before workflow trigger."
    else:
        next_action = "Trigger paper/research workflow with human approval gate."
    data_source = "source_backed" if "source_backed" in sources else "demo" if "demo" in sources else "placeholder"
    return MarketScannerResponse(
        strategy_key=strategy.strategy_key,
        symbols_scanned=[symbol.upper() for symbol in request.symbols],
        matched_signals=matched,
        skipped_signals=skipped,
        should_trigger_workflow=should_trigger,
        recommended_workflow_key=_recommended_workflow(strategy),
        required_agents=strategy.required_agents,
        required_models=strategy.required_models,
        safety_state=safety_state,
        next_action=next_action,
        data_source=data_source,
    )
