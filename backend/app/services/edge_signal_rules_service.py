from pydantic import BaseModel


class EdgeSignalRule(BaseModel):
    signal_key: str
    display_name: str
    signal_to_look_for: str
    validation_method: str
    condition_to_take_action: str
    required_metrics: list[str]
    supported_asset_classes: list[str]
    supported_timeframes: list[str]
    minimum_data_quality: str
    uses_llm: bool = False
    scan_interval_seconds: int
    enabled_by_default: bool


_RULES: list[EdgeSignalRule] = [
    EdgeSignalRule(signal_key="order_book_imbalance", display_name="Order Book Imbalance", signal_to_look_for="Bid/ask depth imbalance or aggressive volume proxy.", validation_method="deterministic_order_flow_metrics", condition_to_take_action="imbalance exceeds threshold and spread is acceptable", required_metrics=["bid", "ask", "volume"], supported_asset_classes=["crypto", "stock"], supported_timeframes=["intraday", "day_trade"], minimum_data_quality="warn", scan_interval_seconds=30, enabled_by_default=True),
    EdgeSignalRule(signal_key="low_float_breakout", display_name="Low Float Breakout", signal_to_look_for="High RVOL breakout on low-float stocks.", validation_method="deterministic_float_rvol_breakout", condition_to_take_action="rvol spike plus breakout confirmation", required_metrics=["volume", "average_volume", "current_price"], supported_asset_classes=["stock"], supported_timeframes=["intraday", "day_trade"], minimum_data_quality="warn", scan_interval_seconds=60, enabled_by_default=False),
    EdgeSignalRule(signal_key="rvol_spike", display_name="RVOL Spike", signal_to_look_for="Relative volume materially above baseline.", validation_method="volume_vs_average_volume", condition_to_take_action="relative_volume >= 1.5 or feature rvol score high", required_metrics=["volume", "average_volume"], supported_asset_classes=["stock", "crypto"], supported_timeframes=["intraday", "day_trade", "swing"], minimum_data_quality="warn", scan_interval_seconds=60, enabled_by_default=True),
    EdgeSignalRule(signal_key="mean_reversion_1_5_min", display_name="1-5 Min Mean Reversion", signal_to_look_for="Short-term stretch from VWAP with acceptable spread.", validation_method="price_vs_vwap_and_spread", condition_to_take_action="price extended from VWAP and spread pass", required_metrics=["price", "vwap", "bid_ask_spread"], supported_asset_classes=["stock", "crypto"], supported_timeframes=["intraday", "day_trade"], minimum_data_quality="warn", scan_interval_seconds=30, enabled_by_default=True),
    EdgeSignalRule(signal_key="retail_sentiment_spike", display_name="Retail Sentiment Spike", signal_to_look_for="Retail/news attention spike.", validation_method="sentiment_provider_metrics", condition_to_take_action="sentiment spike confirmed by price/volume", required_metrics=["sentiment_score", "volume"], supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "earnings"], minimum_data_quality="warn", scan_interval_seconds=300, enabled_by_default=False),
    EdgeSignalRule(signal_key="unusual_calls_puts", display_name="Unusual Calls / Puts", signal_to_look_for="Unusual option flow versus baseline.", validation_method="options_chain_flow_metrics", condition_to_take_action="premium/open-interest/volume anomaly and spread pass", required_metrics=["options_volume", "open_interest", "bid_ask_spread"], supported_asset_classes=["option"], supported_timeframes=["intraday", "day_trade", "swing", "earnings"], minimum_data_quality="warn", scan_interval_seconds=60, enabled_by_default=True),
    EdgeSignalRule(signal_key="etf_stock_lag_pairs", display_name="ETF / Stock Lag Pairs", signal_to_look_for="Lag between ETF and component stock move.", validation_method="pair_relative_performance", condition_to_take_action="lag confirmed and liquidity pass", required_metrics=["etf_snapshot", "stock_snapshot"], supported_asset_classes=["stock"], supported_timeframes=["day_trade", "swing", "one_month"], minimum_data_quality="warn", scan_interval_seconds=300, enabled_by_default=False),
    EdgeSignalRule(signal_key="short_term_momentum", display_name="Short-Term Momentum", signal_to_look_for="Positive price change with volume confirmation.", validation_method="change_percent_and_volume", condition_to_take_action="momentum and RVOL pass", required_metrics=["change_percent", "volume"], supported_asset_classes=["stock", "crypto"], supported_timeframes=["intraday", "day_trade", "swing"], minimum_data_quality="warn", scan_interval_seconds=60, enabled_by_default=True),
    EdgeSignalRule(signal_key="breakout", display_name="Breakout", signal_to_look_for="Price break above recent resistance.", validation_method="support_resistance_break", condition_to_take_action="breakout level confirmed with volume", required_metrics=["candles", "resistance_level", "volume"], supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], minimum_data_quality="warn", scan_interval_seconds=120, enabled_by_default=True),
    EdgeSignalRule(signal_key="advanced_options_flow", display_name="Advanced Options Flow", signal_to_look_for="Multi-factor options flow with IV and OI context.", validation_method="options_chain_iv_oi_flow", condition_to_take_action="flow anomaly plus IV/spread validation", required_metrics=["options_chain", "implied_volatility", "open_interest"], supported_asset_classes=["option"], supported_timeframes=["day_trade", "swing", "earnings"], minimum_data_quality="warn", scan_interval_seconds=120, enabled_by_default=True),
    EdgeSignalRule(signal_key="regime_shift", display_name="Regime Shift", signal_to_look_for="Market regime change affecting allowed strategies.", validation_method="regime_service_or_macro_features", condition_to_take_action="regime transition confirmed", required_metrics=["regime_state", "macro_snapshot"], supported_asset_classes=["stock", "option", "crypto"], supported_timeframes=["intraday", "day_trade", "swing", "one_month"], minimum_data_quality="warn", scan_interval_seconds=300, enabled_by_default=True),
]


def list_edge_signal_rules() -> list[EdgeSignalRule]:
    return _RULES


def get_rule(signal_key: str) -> EdgeSignalRule | None:
    return next((rule for rule in _RULES if rule.signal_key == signal_key), None)


def get_rules_for_signals(signal_keys: list[str]) -> list[EdgeSignalRule]:
    return [rule for rule in _RULES if rule.signal_key in signal_keys]
