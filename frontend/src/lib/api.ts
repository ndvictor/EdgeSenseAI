const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8900";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

export type DataSourceStatus = {
  name: string;
  key?: string | null;
  status: string;
  type: string;
  configured: boolean;
  used_for: string[];
  last_checked: string;
  message: string;
};

export type DataSourcesStatusResponse = {
  connected_sources: number;
  total_sources: number;
  sources: DataSourceStatus[];
};

export type MarketDataSource = "auto" | "yfinance" | "alpaca" | "mock";

export type AccountRiskProfile = {
  account_mode: "manual" | "paper";
  account_equity: number;
  buying_power: number;
  cash: number;
  max_risk_per_trade_percent: number;
  max_daily_loss_percent: number;
  max_position_size_percent: number;
  min_reward_risk_ratio: number;
  preferred_risk_style: string;
  paper_only: boolean;
  source: string;
  last_updated: string;
};

export type EdgeSignal = {
  symbol: string;
  asset_class: "stock" | "option" | "crypto";
  signal_name: string;
  signal_type: string;
  urgency: "low" | "medium" | "high" | "critical";
  time_decay: string;
  edge_score: number;
  confidence: number;
  spread_pass: boolean;
  liquidity_pass: boolean;
  regime_pass: boolean;
  account_fit: string;
  recommended_action: string;
  alert_status: string;
  reason: string;
  risk_factors: string[];
};

export type ModelVote = {
  model: string;
  status: "prototype" | "active" | "disabled";
  signal: "bullish" | "bearish" | "neutral" | "risk_off";
  confidence: number;
  explanation: string;
};

export type ModelStatus = {
  name: string;
  category: string;
  status: string;
  purpose: string;
  current_mode: string;
  next_step: string;
};

export type ModelStatusResponse = {
  data_mode: string;
  live_prediction_enabled: boolean;
  models: ModelStatus[];
};

export type MarketSnapshot = {
  symbol: string;
  asset_class: string;
  current_price: number;
  previous_close: number;
  day_change_percent: number;
  volume: number;
  relative_volume: number;
  bid: number;
  ask: number;
  spread_percent: number;
  vwap: number;
  volatility_proxy: number;
  data_mode: string;
};

export type MarketDataSnapshot = {
  symbol: string;
  price: number | null;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  day_high: number | null;
  day_low: number | null;
  volume: number | null;
  average_volume?: number | null;
  bid?: number | null;
  ask?: number | null;
  bid_ask_spread?: number | null;
  market_cap: number | null;
  fifty_two_week_high: number | null;
  fifty_two_week_low: number | null;
  sector: string | null;
  industry: string | null;
  provider: string | null;
  source?: string | null;
  is_mock: boolean;
  data_quality?: string | null;
  unavailable_fields?: string[];
  not_configured_fields?: string[];
  provider_statuses?: Array<Record<string, unknown>> | null;
  error?: string | null;
};

export type PriceHistory = {
  symbol: string;
  period: string;
  interval: string;
  data: Array<{ date: string; open: number | null; high: number | null; low: number | null; close: number | null; volume: number | null }>;
  provider: string | null;
  is_mock: boolean;
  data_quality?: string | null;
  error?: string | null;
};

export type MarketCandle = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type MarketCandlesResponse = {
  symbol: string;
  asset_class: string;
  interval: string;
  period: string;
  data_mode: string;
  candles: MarketCandle[];
};

export type EngineeredFeatures = {
  symbol: string;
  momentum_score: number;
  rvol_score: number;
  spread_quality_score: number;
  trend_vs_vwap_score: number;
  volatility_score: number;
  composite_feature_score: number;
  notes: string[];
};

export type ModelPipelineResult = {
  symbol: string;
  data_mode: string;
  features: EngineeredFeatures;
  directional_bias: string;
  regime_bias: string;
  volatility_fit: string;
  ranker_score: number;
  pipeline_notes: string[];
};

export type AccountFeasibilityResult = {
  symbol: string;
  feasibility: string;
  max_position_size_dollars: number;
  max_risk_dollars: number;
  suggested_expression: string;
  notes: string[];
};

export type RiskCheckResult = {
  passed: boolean;
  reward_risk_ratio: number;
  max_dollar_risk: number;
  stop_distance_percent: number;
  risk_status: string;
  blockers: string[];
};

export type RegimeFactor = {
  name: string;
  value: string;
  signal: string;
  impact: string;
};

export type MarketRegimeResponse = {
  regime_state: string;
  confidence: number;
  strategy_bias: string;
  allowed_strategies: string[];
  blocked_strategies: string[];
  factors: RegimeFactor[];
  notes: string[];
};

export type BacktestMetric = {
  name: string;
  value: string;
  status: string;
};

export type BacktestProfile = {
  profile_name: string;
  objective: string;
  horizon: string;
  status: string;
  metrics: BacktestMetric[];
  next_steps: string[];
};

export type BacktestingResponse = {
  mode: string;
  profiles: BacktestProfile[];
};

export type JournalEntry = {
  id: string;
  symbol: string;
  asset_class: string;
  setup: string;
  planned_action: string;
  entry_zone: string;
  stop: string;
  target: string;
  status: string;
  outcome_label: string;
  lesson: string;
};

export type JournalSummary = {
  mode: string;
  total_entries: number;
  pending_reviews: number;
  winning_labels: number;
  losing_labels: number;
  entries: JournalEntry[];
  next_steps: string[];
};

export type RankerScore = {
  symbol: string;
  score: number;
  rank: number;
  model_used: string;
  explanation: string;
};

export type ModelLabRunRequest = {
  data_source: "mock" | "yfinance";
  model: "xgboost_ranker" | "weighted_ranker";
  symbols: string[];
  train_split_percent: number;
  test_split_percent: number;
  feature_set: "prototype_v1";
};

export type ModelLabRunResponse = {
  workflow_status: string;
  data_source: string;
  model: string;
  feature_set: string;
  split: {
    total_rows: number;
    train_rows: number;
    test_rows: number;
    train_split_percent: number;
    test_split_percent: number;
  };
  features: Array<{
    symbol: string;
    asset_class: string;
    current_price: number;
    feature_score: number;
    momentum_score: number;
    rvol_score: number;
    spread_quality_score: number;
    trend_vs_vwap_score: number;
    volatility_score: number;
  }>;
  ranker_result: {
    model_name: string;
    model_available: boolean;
    rows_scored: number;
    scores: RankerScore[];
    notes: string[];
  };
  next_steps: string[];
};

export type PricePlan = {
  current_price: number;
  buy_zone_low: number;
  buy_zone_high: number;
  stop_loss: number;
  target_price: number;
  target_2_price?: number | null;
};

export type RiskPlan = {
  position_size_dollars: number;
  max_dollar_risk: number;
  max_loss_percent: number;
  expected_return_percent: number;
  reward_risk_ratio: number;
  account_fit: string;
};

export type TradeRecommendation = {
  symbol: string;
  asset_class: "stock" | "option" | "crypto";
  action: "buy" | "watch" | "avoid";
  action_label: string;
  horizon: "intraday" | "day_trade" | "swing" | "one_month";
  confidence: number;
  final_score: number;
  urgency: "low" | "medium" | "high" | "critical";
  price_plan: PricePlan;
  risk_plan: RiskPlan;
  model_votes: ModelVote[];
  final_reason: string;
  invalidation_rules: string[];
  risk_factors: string[];
  data_mode: "synthetic_prototype" | "paper" | "live" | "source_unavailable";
  execution_enabled: boolean;
  research_only: boolean;
};

export type Recommendation = {
  symbol: string;
  asset_class: "stock" | "option" | "crypto";
  horizon: string;
  final_decision: string;
  final_score: number;
  confidence: number;
  reward_risk_ratio: number;
  account_fit: string;
  model_stack: string[];
  reason: string;
  risk_factors: string[];
};

export type SourceDataStatus = {
  symbol: string;
  provider?: string | null;
  data_quality?: string | null;
  is_mock: boolean;
  error?: string | null;
};

export type CommandCenterResponse = {
  account_profile: AccountRiskProfile;
  top_action: TradeRecommendation | null;
  top_recommendations: Recommendation[];
  urgent_edge_alerts: EdgeSignal[];
  agents: { name: string; role: string; status: string; status_label: string; last_checked: string }[];
  source_data_status: SourceDataStatus[];
  dashboard_mode: string;
  cost_usage_message: string;
};

export type LiveWatchlistResponse = {
  mode: string;
  live_trading_enabled: boolean;
  execution_enabled: boolean;
  summary: {
    triggered_now: number;
    high_conviction: number;
    alerts_sent_today: number;
    average_priority_score: number;
    strongest_trigger: string;
    auto_refresh_interval: string;
    notify_enabled: boolean;
    last_updated: string;
  };
  agents: { name: string; role: string; status: string; status_label: string; last_checked: string }[];
  candidates: {
    symbol: string;
    asset: string;
    asset_class: "stock" | "option" | "crypto";
    horizon: string;
    trigger: string;
    trigger_type: string;
    priority_score: number;
    trigger_strength: number;
    account_fit: string;
    account_fit_label: string;
    suggested_expression: string;
    agent_status: string;
    notify_status: string;
    notify_label: string;
    data_quality: string;
    reason: string;
    risk_factors: string[];
  }[];
  disclaimer: string;
};

export const api = {
  getCommandCenter: () => request<CommandCenterResponse>("/api/command-center"),
  getAccountRisk: () => request<AccountRiskProfile>("/api/account-risk/profile"),
  updateAccountRisk: (payload: Partial<AccountRiskProfile>) => request<AccountRiskProfile>("/api/account-risk/profile", { method: "PUT", body: JSON.stringify(payload) }),
  getLiveWatchlist: () => request<LiveWatchlistResponse>("/api/live-watchlist/latest"),
  getEdgeSignals: () => request<{ last_updated: string; alerts_enabled: boolean; account_range: string; signals: EdgeSignal[] }>("/api/edge-signals/latest"),
  getModelStatus: () => request<ModelStatusResponse>("/api/models/status"),
  getDataSourcesStatus: () => request<DataSourcesStatusResponse>("/api/data-sources/status"),
  getMarketDataSnapshot: (symbol: string, source: MarketDataSource = "auto") => request<MarketDataSnapshot>(`/api/market-data/snapshot/${symbol}?source=${source}`),
  getMarketDataHistory: (symbol: string, period = "6mo", interval = "1d", source: MarketDataSource = "auto") => request<PriceHistory>(`/api/market-data/history/${symbol}?period=${period}&interval=${interval}&source=${source}`),
  getMarketSnapshots: () => request<MarketSnapshot[]>("/api/market/snapshots"),
  getMarketSnapshot: (symbol: string, provider = "mock") => request<MarketSnapshot>(`/api/market/${symbol}/snapshot?provider=${provider}`),
  getMarketCandles: (symbol: string, provider = "mock", period = "1mo", interval = "1d") => request<MarketCandlesResponse>(`/api/market/${symbol}/candles?provider=${provider}&period=${period}&interval=${interval}`),
  getFeatures: (symbol: string) => request<EngineeredFeatures>(`/api/features/${symbol}`),
  getModelPipeline: (symbol: string) => request<ModelPipelineResult>(`/api/model-pipeline/${symbol}`),
  getAccountFeasibility: (symbol: string) => request<AccountFeasibilityResult>(`/api/account-feasibility/${symbol}`),
  getRiskCheck: (symbol: string) => request<RiskCheckResult>(`/api/risk-check/${symbol}`),
  getMarketRegime: () => request<MarketRegimeResponse>("/api/market-regime"),
  getBacktestingSummary: () => request<BacktestingResponse>("/api/backtesting/summary"),
  getJournalSummary: () => request<JournalSummary>("/api/journal/summary"),
  runModelLab: (payload: ModelLabRunRequest) => request<ModelLabRunResponse>("/api/model-lab/run", { method: "POST", body: JSON.stringify(payload) }),
};
