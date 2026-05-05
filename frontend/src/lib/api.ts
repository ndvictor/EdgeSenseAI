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
  connected: boolean;
  used_for: string[];
  required_for?: string[];
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

export type AlpacaPaperAccount = {
  id?: string | null;
  account_number?: string | null;
  status?: string | null;
  currency?: string | null;
  cash?: number | null;
  buying_power?: number | null;
  portfolio_value?: number | null;
  equity?: number | null;
  last_equity?: number | null;
  daytrade_count?: number | null;
  pattern_day_trader?: boolean | null;
  trading_blocked?: boolean | null;
  transfers_blocked?: boolean | null;
  account_blocked?: boolean | null;
};

export type AlpacaPaperPosition = {
  symbol: string;
  qty?: number | null;
  side?: string | null;
  market_value?: number | null;
  cost_basis?: number | null;
  unrealized_pl?: number | null;
  unrealized_plpc?: number | null;
  current_price?: number | null;
  avg_entry_price?: number | null;
};

export type AlpacaPaperOrder = {
  id: string;
  client_order_id?: string | null;
  symbol: string;
  side?: string | null;
  type?: string | null;
  status?: string | null;
  qty?: number | null;
  notional?: number | null;
  filled_qty?: number | null;
  submitted_at?: string | null;
  filled_at?: string | null;
  limit_price?: number | null;
  stop_price?: number | null;
};

export type AlpacaPaperSnapshot = {
  provider: "alpaca";
  mode: "paper";
  status: "connected" | "not_configured" | "unavailable";
  endpoint: string;
  keys_configured: boolean;
  paper_trading_enabled: boolean;
  live_trading_enabled: boolean;
  broker_execution_enabled: boolean;
  account?: AlpacaPaperAccount;
  positions: AlpacaPaperPosition[];
  open_orders: AlpacaPaperOrder[];
  message: string;
  warnings: string[];
  last_checked?: string;
};

export type AlpacaPaperPortfolioHistory = {
  provider: "alpaca";
  mode: "paper";
  status: "connected" | "not_configured" | "unavailable";
  endpoint: string;
  keys_configured: boolean;
  period: string;
  timeframe: string;
  timestamps: number[];
  equity: number[];
  base_value?: number | null;
  message: string;
  warnings: string[];
  last_checked?: string;
};

// Settings API Types - Comprehensive Platform Settings
export type TradingSettings = {
  paper_trading_enabled: boolean;
  live_trading_enabled: boolean;
  broker_execution_enabled: boolean;
  require_human_approval: boolean;
  execution_mode: string;
  execution_agent_enabled: boolean;
  paper_starting_cash: number;
  broker_provider: string;
  alpaca_paper_trade: boolean;
};

export type LlmGatewaySettings = {
  llm_gateway_enable_paid_tests: boolean;
  llm_gateway_daily_budget: number;
  llm_gateway_default_cheap_model: string;
  llm_gateway_default_reasoning_model: string;
  llm_gateway_default_fallback_model: string;
  embeddings_enable_paid_calls: boolean;
};

export type MarketDataSettings = {
  market_data_provider: string;
  market_data_provider_priority: string;
  market_data_provider_timeout_seconds: number;
  alpaca_market_data_enabled: boolean;
};

export type NewsSettings = {
  news_provider_enabled: boolean;
  news_provider_primary: string;
  news_provider_timeout_seconds: number;
};

export type PlatformFeatures = {
  langsmith_tracing: boolean;
  vector_memory_enabled: boolean;
};

export type RateLimitSettings = {
  max_daily_llm_cost: number;
  max_daily_agent_runs: number;
};

export type RiskSettings = {
  max_risk_per_trade_percent: number;
  max_daily_loss_percent: number;
  max_position_size_percent: number;
  min_reward_risk_ratio: number;
};

export type SettingsResponse = {
  trading: TradingSettings;
  risk: RiskSettings;
  llm_gateway: LlmGatewaySettings;
  market_data: MarketDataSettings;
  news: NewsSettings;
  platform: PlatformFeatures;
  rate_limits: RateLimitSettings;
};

export type TradingSettingsUpdate = {
  paper_trading_enabled?: boolean;
  live_trading_enabled?: boolean;
  broker_execution_enabled?: boolean;
  require_human_approval?: boolean;
  execution_mode?: string;
  execution_agent_enabled?: boolean;
  paper_starting_cash?: number;
  broker_provider?: string;
  alpaca_paper_trade?: boolean;
};

export type LlmGatewaySettingsUpdate = {
  llm_gateway_enable_paid_tests?: boolean;
  llm_gateway_daily_budget?: number;
  llm_gateway_default_cheap_model?: string;
  llm_gateway_default_reasoning_model?: string;
  llm_gateway_default_fallback_model?: string;
  embeddings_enable_paid_calls?: boolean;
};

export type MarketDataSettingsUpdate = {
  market_data_provider?: string;
  market_data_provider_priority?: string;
  market_data_provider_timeout_seconds?: number;
  alpaca_market_data_enabled?: boolean;
};

export type NewsSettingsUpdate = {
  news_provider_enabled?: boolean;
  news_provider_primary?: string;
  news_provider_timeout_seconds?: number;
};

export type PlatformFeaturesUpdate = {
  langsmith_tracing?: boolean;
  vector_memory_enabled?: boolean;
};

export type RateLimitSettingsUpdate = {
  max_daily_llm_cost?: number;
  max_daily_agent_runs?: number;
};

export type RiskSettingsUpdate = {
  max_risk_per_trade_percent?: number;
  max_daily_loss_percent?: number;
  max_position_size_percent?: number;
  min_reward_risk_ratio?: number;
};

export type SettingsUpdateRequest = {
  trading?: TradingSettingsUpdate;
  risk?: RiskSettingsUpdate;
  llm_gateway?: LlmGatewaySettingsUpdate;
  market_data?: MarketDataSettingsUpdate;
  news?: NewsSettingsUpdate;
  platform?: PlatformFeaturesUpdate;
  rate_limits?: RateLimitSettingsUpdate;
};

// Paper Trading Order Types
export type PaperOrderRequest = {
  symbol: string;
  side: "buy" | "sell";
  qty: number;
  type?: "market" | "limit" | "stop" | "stop_limit";
  time_in_force?: "day" | "gtc" | "ioc";
  limit_price?: number | null;
  stop_price?: number | null;
  asset_class?: "stock" | "etf" | "crypto" | "option";
  human_approval_confirmed: boolean;
  dry_run: boolean;
};

export type PaperOrderResponse = {
  status: "blocked" | "dry_run" | "submitted" | "failed";
  broker: string;
  execution_mode: string;
  order_id: string | null;
  client_order_id: string;
  symbol: string;
  asset_class: string;
  side: string;
  submitted_payload: Record<string, unknown>;
  broker_response: Record<string, unknown> | null;
  request_id: string | null;
  blockers: string[];
  warnings: string[];
  safety_notes: string[];
  created_at: string;
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

export type DataSourceKind = "demo" | "placeholder" | "source_backed" | string;

export type AiOpsSummaryResponse = {
  data_source: DataSourceKind;
  status: string;
  generated_at?: string;
  orchestration?: Record<string, unknown>;
  agent_scorecards_available?: number;
  live_trading_allowed?: boolean;
  paper_trading_requires_approval?: boolean;
  postgres_persistence_status?: string;
  pgvector_status?: string;
  embedding_provider?: string;
  vector_memory_status?: string;
  recent_memory_count?: number;
  latest_workflow_memory?: Record<string, unknown> | null;
  latest_recommendation_memory?: Record<string, unknown> | null;
};

export type AiOpsWorkflow = {
  name?: string;
  workflow_name?: string;
  status?: string;
  trigger?: string;
  mode?: string;
  data_source?: DataSourceKind;
  agents?: string[] | number;
  last_run?: string | null;
  last_run_at?: string | null;
  next_step?: string;
  entrypoint?: string;
  live_trading_allowed?: boolean;
  langgraph?: Record<string, unknown>;
};

export type AiOpsWorkflowListResponse = {
  data_source: DataSourceKind;
  workflows: AiOpsWorkflow[];
};

export type AiOpsAgentScorecard = {
  agent_key?: string;
  agent_name?: string;
  name?: string;
  role?: string;
  status?: string;
  run_count?: number;
  success_rate?: number | null;
  average_latency_ms?: number | null;
  drift_status?: string;
  last_run_at?: string | null;
  scorecard_notes?: string[];
  notes?: string[];
  data_source?: DataSourceKind;
};

export type AiOpsAgentStatusResponse = {
  data_source: DataSourceKind;
  existing_scorecards?: AiOpsAgentScorecard[];
  foundation_agents?: AiOpsAgentScorecard[];
};

export type AiOpsLlmUsageRow = {
  provider?: string;
  model?: string;
  model_name?: string;
  agent?: string;
  workflow?: string;
  tokens?: number;
  estimated_tokens?: number;
  cost?: number;
  estimated_cost?: number;
  status?: string;
};

export type AiOpsLlmUsageResponse = {
  data_source: DataSourceKind;
  status: string;
  provider?: string;
  total_estimated_cost?: number;
  total_estimated_tokens?: number;
  cost_today?: number;
  cost_limit?: number;
  tokens_today?: number;
  models?: AiOpsLlmUsageRow[];
  usage?: AiOpsLlmUsageRow[];
  notes?: string[];
};

export type AiOpsSchedulerJob = {
  id: string;
  name?: string;
  trigger?: string;
  schedule?: string;
  workflow?: string;
  status?: string;
  last_run?: string | null;
  last_run_at?: string | null;
  next_run?: string | null;
  next_run_at?: string | null;
  description?: string;
  data_source?: DataSourceKind;
};

export type AiOpsSchedulerJobsResponse = {
  data_source: DataSourceKind;
  scheduler?: string;
  status: string;
  apscheduler_available?: boolean;
  auto_start_enabled?: boolean;
  jobs_configured?: number;
  running_jobs?: number;
  failed_jobs_today?: number;
  updated_at?: string;
  jobs: AiOpsSchedulerJob[];
};

export type AiOpsAuditEvent = {
  id?: string;
  time?: string;
  created_at?: string;
  event_type?: string;
  actor?: string;
  object?: string;
  status?: string;
  summary?: string;
  details?: string;
  severity?: string;
  data_source?: DataSourceKind;
};

export type AiOpsAuditEventsResponse = {
  data_source: DataSourceKind;
  events: AiOpsAuditEvent[];
  notes?: string[];
};

export type EdgeRadarRunRequest = {
  symbols: string[];
  asset_classes?: string[] | null;
  horizon: "intraday" | "day_trade" | "swing" | "one_month" | string;
  account_size?: number | null;
  max_risk_per_trade?: number | null;
  strategy_preference?: string | null;
  data_source: "auto" | "yfinance" | "mock" | string;
};

export type EdgeRadarTraceEvent = {
  run_id: string;
  workflow_name: string;
  agent_name: string;
  status: string;
  started_at: string;
  completed_at?: string | null;
  duration_ms?: number | null;
  confidence?: number | null;
  input_summary?: string | null;
  output_summary?: string | null;
  warnings: string[];
  errors: string[];
  metadata: Record<string, unknown>;
  data_source: DataSourceKind;
};

export type EdgeRadarRunResponse = {
  run_id: string;
  workflow_name: string;
  status: string;
  data_source: DataSourceKind;
  message: string;
  detected_signals: Array<Record<string, unknown>>;
  regime_context: Record<string, unknown>;
  risk_review: Record<string, unknown>;
  portfolio_manager_decision: Record<string, unknown>;
  approval_required: boolean;
  paper_trade_allowed: boolean;
  live_trading_allowed: boolean;
  cost_estimate: Record<string, unknown>;
  agent_trace: EdgeRadarTraceEvent[];
  warnings: string[];
  errors: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

export type DataQualityReport = {
  ticker: string;
  asset_class: string;
  provider?: string | null;
  data_source: DataSourceKind;
  quality_status: "pass" | "warn" | "fail" | string;
  freshness_status: string;
  missing_fields: string[];
  blockers: string[];
  warnings: string[];
  checked_at: string;
};

export type NormalizedMarketSnapshot = {
  ticker?: string;
  symbol?: string;
  asset_class?: string;
  timestamp?: string;
  provider?: string | null;
  source?: string | null;
  data_source?: DataSourceKind;
  price?: number | null;
  current_price?: number | null;
  previous_close?: number | null;
  change_percent?: number | null;
  day_high?: number | null;
  day_low?: number | null;
  volume?: number | null;
  average_volume?: number | null;
  bid?: number | null;
  ask?: number | null;
  bid_ask_spread?: number | null;
  spread_percent?: number | null;
  relative_volume?: number | null;
  vwap?: number | null;
  volatility_proxy?: number | null;
  data_quality?: string;
  is_mock?: boolean;
};

export type FeatureStoreRow = {
  id: string;
  ticker: string;
  asset_class: string;
  horizon: string;
  timestamp: string;
  data_source: DataSourceKind;
  data_quality: string;
  technical_score?: number | null;
  momentum_score?: number | null;
  volume_score?: number | null;
  rvol_score?: number | null;
  options_score?: number | null;
  sentiment_score?: number | null;
  volatility_score?: number | null;
  macro_score?: number | null;
  regime_score?: number | null;
  liquidity_score?: number | null;
  confidence?: number | null;
  feature_version: string;
  created_at: string;
};

export type FeatureStoreRunRequest = {
  symbol: string;
  asset_class: string;
  horizon: "intraday" | "day_trade" | "swing" | "one_month" | string;
  source: "auto" | "yfinance" | "mock" | string;
};

export type FeatureStoreRunResponse = {
  row: FeatureStoreRow;
  quality_report: DataQualityReport;
  normalized_snapshot?: NormalizedMarketSnapshot | null;
  storage_mode?: string;
  warnings?: string[];
};

export type ModelRegistryItem = {
  key: string;
  name?: string;
  status: string;
  should_run_when?: string[];
  data_source?: DataSourceKind;
};

export type ModelRegistryResponse = {
  data_source: DataSourceKind;
  models: ModelRegistryItem[];
  available_model_count?: number;
  placeholder_model_count?: number;
};

export type ModelRunPlanRequest = {
  symbols: string[];
  asset_class: string;
  horizon: "intraday" | "day_trade" | "swing" | "one_month" | string;
  source: "auto" | "yfinance" | "mock" | string;
  strategy_key?: string | null;
  feature_row_id?: string | null;
  selected_models?: string[] | null;
  feature_rows?: FeatureStoreRow[] | null;
};

export type PlannedModel = {
  key: string;
  status: string;
  should_run: boolean;
  reason: string;
  data_source?: DataSourceKind;
};

export type ModelRunPlanResponse = {
  data_source: DataSourceKind;
  models: PlannedModel[];
  feature_rows_used?: number;
  warnings?: string[];
};

export type ModelRunRequest = ModelRunPlanRequest;

export type ModelOutput = {
  model?: string;
  model_name?: string;
  model_type?: string;
  status?: string;
  prediction?: string | number | null;
  prediction_score?: number | null;
  probability?: number | null;
  probability_score?: number | null;
  expected_return_score?: number | null;
  expected_return_score_source?: string | null;
  volatility_adjusted_score?: number | null;
  rank_score?: number | null;
  confidence_score?: number | null;
  score?: number | null;
  confidence?: number | null;
  scores?: Array<Record<string, unknown>>;
  result?: Record<string, unknown>;
  notes?: string[];
  warnings?: string[];
  feature_contributions?: Array<Record<string, unknown>>;
  feature_importance?: Array<Record<string, unknown>> | Record<string, unknown> | null;
  data_source?: DataSourceKind;
  reason?: string;
  next_steps?: string[];
};

export type BlockedOrPlaceholderModel = {
  model?: string;
  model_name?: string;
  status: "placeholder_not_run" | "blocked" | "missing_inputs" | "not_configured" | string;
  reason?: string;
  needed_inputs?: string[];
  next_step?: string;
  data_source?: DataSourceKind;
};

export type ModelRunResponse = {
  status: string;
  data_source: DataSourceKind;
  plan?: ModelRunPlanResponse;
  feature_rows?: FeatureStoreRow[];
  results?: Array<ModelOutput | BlockedOrPlaceholderModel>;
  model_outputs?: Array<ModelOutput | BlockedOrPlaceholderModel>;
  completed_models?: ModelOutput[];
  blocked_models?: BlockedOrPlaceholderModel[];
  placeholder_models?: BlockedOrPlaceholderModel[];
  not_trained_models?: BlockedOrPlaceholderModel[];
  warnings?: string[];
  next_action?: string;
};

export type LlmProviderStatus = {
  provider: string;
  status: "configured" | "not_configured" | "placeholder" | "error" | string;
  configured: boolean;
  required_env_vars: string[];
  configured_env_vars: string[];
  message: string;
  data_source: DataSourceKind;
};

export type LlmModelConfig = {
  model_name: string;
  provider: string;
  role: string;
  context_window?: number | null;
  pricing_source: string;
  input_cost_per_1k_tokens: number;
  output_cost_per_1k_tokens: number;
  status: string;
  data_source: DataSourceKind;
};

export type LlmRoutingRule = {
  task_type: string;
  preferred_provider: string;
  preferred_model: string;
  fallback_model: string;
  max_cost_per_call: number;
  max_tokens: number;
  enabled: boolean;
  data_source: DataSourceKind;
};

export type LlmUsageRecord = {
  id: string;
  timestamp: string;
  provider: string;
  model: string;
  agent: string;
  workflow: string;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost: number;
  latency_ms?: number | null;
  status: string;
  dry_run: boolean;
  data_source: DataSourceKind;
};

export type LlmCostSummary = {
  data_source: DataSourceKind;
  cost_today: number;
  daily_budget: number;
  budget_remaining: number;
  tokens_today: number;
  calls_today: number;
  cost_by_provider: Record<string, number>;
  cost_by_model: Record<string, number>;
  cost_by_agent: Record<string, number>;
  cost_by_workflow: Record<string, number>;
  most_used_model?: string | null;
  most_expensive_agent?: string | null;
  pricing_source: string;
};

export type AgentModelMapping = {
  agent_name: string;
  default_model: string;
  fallback_model: string;
  max_daily_cost: number;
  max_calls_per_day: number;
  current_cost_today: number;
  calls_today: number;
  status: string;
  data_source: DataSourceKind;
};

export type LlmGatewayStatusResponse = {
  status: string;
  litellm_available: boolean;
  litellm_api_base_configured: boolean;
  litellm_master_key_configured: boolean;
  configured_providers_count: number;
  budget_status: string;
  daily_budget: number;
  cost_today: number;
  budget_remaining: number;
  data_source: DataSourceKind;
};

export type LlmCostEstimateRequest = {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
};

export type LlmCostEstimateResponse = {
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  estimated_cost: number;
  input_cost: number;
  output_cost: number;
  pricing_source: string;
  data_source: DataSourceKind;
};

export type LlmGatewayTestCallRequest = {
  provider: string;
  model: string;
  prompt: string;
  allow_paid_call: boolean;
};

export type LlmGatewayTestCallResponse = {
  id: string;
  provider: string;
  model: string;
  dry_run: boolean;
  paid_call_attempted: boolean;
  status: string;
  response_text: string;
  estimated_cost: number;
  data_source: DataSourceKind;
  warnings: string[];
};

export type CoreAgentRegistryItem = {
  agent_key: string;
  agent_name: string;
  category: string;
  purpose: string;
  supported_asset_classes: string[];
  supported_timeframes: string[];
  required_inputs: string[];
  output_fields: string[];
  status: "available" | "partial" | "placeholder" | "not_configured" | string;
  uses_llm: boolean;
  uses_models: boolean;
  safe_for_auto_run: boolean;
  notes: string[];
};

export type CoreAgentRegistryResponse = CoreAgentRegistryItem[];

export type StrategyConfig = {
  strategy_key: string;
  display_name: string;
  asset_class: string;
  timeframe: string;
  description: string;
  edge_signals: string[];
  required_agents: string[];
  optional_agents: string[];
  required_models: string[];
  optional_models: string[];
  required_data_sources: string[];
  validation_rules: string[];
  risk_rules: string[];
  action_rules: string[];
  default_weights: Record<string, number>;
  auto_run_supported: boolean;
  live_trading_supported: boolean;
  paper_trading_supported: boolean;
  requires_human_approval: boolean;
  metadata?: Record<string, unknown>;
  // New candidate/research strategy fields (all optional for backward compatibility)
  status?: "active" | "approved" | "candidate" | "paused" | "rejected";
  promotion_status?: "active" | "candidate" | "testing" | "paper_active" | "paused" | "rejected";
  claim_source?: string | null;
  claim_type?: "internal" | "vendor_claim" | "research_note" | "backtest" | "paper_result";
  best_regimes?: string[];
  bad_regimes?: string[];
  trigger_rules?: string[];
  risk_notes?: string[];
  small_account_fit?: boolean | null;
  drawdown_risk?: string | null;
  pdt_risk?: boolean | null;
  paper_research_only?: boolean;
  requires_backtest?: boolean;
  requires_owner_approval_for_promotion?: boolean;
  candidate_universe_examples?: string[];
  core_universe?: string[];
  optional_expansion?: string[];
  disabled_reason?: string | null;
  promotion_requirements?: string[];
};

export type StrategyRegistryResponse = StrategyConfig[];

export type StrategyRegistrySummary = {
  data_source: "strategy_registry";
  total_count: number;
  by_status: Record<string, number>;
  active_approved_count: number;
  candidate_count: number;
  production_ready_count: number;
  disabled_or_blocked_count: number;
};

export type PlatformReadinessCheck = {
  key: string;
  label: string;
  status: "pass" | "warn" | "fail";
  message: string;
  required_for: string;
};

export type PlatformReadinessResponse = {
  status: "ready" | "partial" | "not_ready";
  checks: PlatformReadinessCheck[];
  blockers: string[];
  warnings: string[];
  generated_at: string;
};

export type TracingStatusResponse = {
  enabled: boolean;
  configured: boolean;
  langsmith_installed: boolean;
  langsmith_tracing_env: boolean;
  api_key_configured: boolean;
  project_configured: boolean;
  mode: string;
};

export type TracingTestEventRequest = {
  name: string;
  metadata?: Record<string, unknown>;
};

export type TracingTestEventResponse = {
  tracing_enabled: boolean;
  event_sent: boolean;
  event_name: string;
  mode: string;
};

export type EdgeSignalRule = {
  signal_key: string;
  display_name: string;
  signal_to_look_for: string;
  validation_method: string;
  condition_to_take_action: string;
  required_metrics: string[];
  supported_asset_classes: string[];
  supported_timeframes: string[];
  minimum_data_quality: string;
  uses_llm: boolean;
  scan_interval_seconds: number;
  enabled_by_default: boolean;
};

export type EdgeSignalRulesResponse = EdgeSignalRule[];

export type AutoRunControlState = {
  auto_run_enabled: boolean;
  live_trading_enabled: boolean;
  paper_trading_enabled: boolean;
  require_human_approval: boolean;
  max_daily_agent_runs: number;
  max_daily_llm_cost: number;
  status: string;
  data_source: DataSourceKind;
};

export type AutoRunControlUpdate = Partial<Pick<AutoRunControlState, "auto_run_enabled" | "live_trading_enabled" | "paper_trading_enabled" | "require_human_approval" | "max_daily_agent_runs" | "max_daily_llm_cost">>;

export type MarketScannerSignal = {
  symbol: string;
  signal_key: string;
  display_name: string;
  status: string;
  reason: string;
  confidence?: number | null;
  data_source: DataSourceKind;
  metadata?: Record<string, unknown>;
};

export type MarketScannerRequest = {
  strategy_key: string;
  symbols: string[];
  data_source: "auto" | "yfinance" | "mock" | string;
  auto_run: boolean;
  trigger_type?: "manual" | "scheduled";
  trigger_workflow?: boolean;
  account_size?: number | null;
  max_risk_per_trade?: number | null;
};

export type MarketScannerResponse = {
  run_id: string;
  trigger_type: "manual" | "scheduled";
  strategy_key: string;
  symbols_scanned: string[];
  matched_signals: MarketScannerSignal[];
  skipped_signals: MarketScannerSignal[];
  should_trigger_workflow: boolean;
  recommended_workflow_key: string;
  workflow_trigger_status: string;
  workflow_run_id?: string | null;
  cooldown_remaining_seconds?: number | null;
  required_agents: string[];
  required_models: string[];
  safety_state: AutoRunControlState;
  next_action: string;
  data_source: DataSourceKind;
};

export type MarketScanRun = {
  run_id: string;
  trigger_type: "manual" | "scheduled";
  strategy_key: string;
  symbols: string[];
  data_source: DataSourceKind | string;
  auto_run_enabled: boolean;
  matched_signals_count: number;
  skipped_signals_count: number;
  should_trigger_workflow: boolean;
  recommended_workflow_key: string;
  workflow_trigger_status: string;
  workflow_run_id?: string | null;
  cooldown_remaining_seconds?: number | null;
  required_agents: string[];
  required_models: string[];
  safety_state: Record<string, unknown>;
  next_action: string;
  status: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  errors: string[];
  warnings: string[];
};

export type MarketScanRunSummary = {
  total_runs: number;
  scan_runs_today: number;
  latest_run?: MarketScanRun | null;
  runs: MarketScanRun[];
};

export type StrategyWorkflowTraceStep = {
  step_name: string;
  status: string;
  started_at: string;
  completed_at: string;
  duration_ms: number;
  summary: string;
  data_source: DataSourceKind;
  metadata?: Record<string, unknown>;
  warnings: string[];
  errors: string[];
};

export type StrategyWorkflowRunRequest = {
  strategy_key: string;
  symbol: string;
  asset_class?: string;
  horizon?: string;
  matched_signal_key?: string | null;
  matched_signal_name?: string | null;
  source_scan_run_id?: string | null;
  trigger_type?: "manual" | "scheduled" | "scanner_match";
  data_source?: string;
  account_size?: number | null;
  max_risk_per_trade?: number | null;
};

export type StrategyWorkflowRunResult = {
  workflow_run_id: string;
  source_scan_run_id?: string | null;
  trigger_type: "manual" | "scheduled" | "scanner_match";
  strategy_key: string;
  symbol: string;
  asset_class: string;
  horizon: string;
  matched_signal_key?: string | null;
  matched_signal_name?: string | null;
  required_agents: string[];
  required_models: string[];
  data_quality: Record<string, unknown>;
  feature_row: Record<string, unknown>;
  model_plan: Record<string, unknown>;
  model_outputs: Record<string, unknown>[];
  risk_review: Record<string, unknown>;
  portfolio_decision: Record<string, unknown>;
  recommendation: Record<string, unknown>;
  approval_required: boolean;
  paper_trade_allowed: boolean;
  live_trading_allowed: boolean;
  status: string;
  warnings: string[];
  errors: string[];
  trace: StrategyWorkflowTraceStep[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

export type StrategyWorkflowRunSummary = {
  total_runs: number;
  workflow_runs_today: number;
  latest_run?: StrategyWorkflowRunResult | null;
  runs: StrategyWorkflowRunResult[];
};

export type CandidateUniverseEntry = {
  id: string;
  symbol: string;
  asset_class: string;
  horizon: string;
  source_type: "manual" | "watchlist" | "scanner" | "stock_search" | "strategy_workflow";
  source_detail: string;
  priority_score: number;
  status: "active" | "paused" | "removed";
  created_at: string;
  updated_at: string;
  last_ranked_at?: string | null;
  notes: string;
};

export type CandidateUniverseResponse = {
  candidates: CandidateUniverseEntry[];
  summary: {
    total_candidates: number;
    active_count: number;
    paused_count: number;
    removed_count: number;
    active_symbols: string[];
    persistence_mode?: "postgres" | "memory";
  };
};

export type UniverseSelectionRequest = {
  symbols: string[];
  asset_class?: "stock" | "option" | "crypto";
  horizon?: "day_trade" | "swing" | "one_month";
  source?: "auto" | "yfinance" | "alpaca" | "polygon" | "mock";
  strategy_key?: string;
  max_candidates?: number;
  min_score?: number;
  account_equity?: number;
  buying_power?: number;
  max_risk_per_trade_percent?: number;
  include_mock?: boolean;
  promote_to_candidate_universe?: boolean;
};

export type UniverseSelectionCandidate = {
  symbol: string;
  asset_class: string;
  horizon: string;
  strategy_key?: string;
  rank: number;
  universe_score: number;
  priority_score: number;
  expected_direction: "long" | "short" | "neutral";
  assigned_strategy: string;
  trigger_condition: string;
  validation_condition: string;
  invalidation_condition: string;
  scan_interval_seconds: number;
  watchlist_ttl_minutes: number;
  account_fit: number;
  liquidity_score: number;
  spread_score: number;
  volatility_fit: number;
  trend_score: number;
  rvol_score: number;
  sector_strength_score?: number | null;
  data_quality: "excellent" | "good" | "fair" | "poor" | "unavailable";
  provider: string;
  source: string;
  reasons: string[];
  blockers: string[];
  expires_at: string | null;
};

export type CadencePlan = {
  scan_interval_seconds: number;
  strategy_refresh_minutes: number;
  universe_refresh_minutes: number;
  watchlist_ttl_minutes: number;
  llm_validation_policy: string;
  llm_budget_mode: string;
  scanner_depth: string;
};

export type UniverseSelectionResponse = {
  run_id: string;
  status: "completed" | "partial" | "failed" | "no_symbols";
  market_phase: string;
  active_loop: string;
  cadence_plan: CadencePlan;
  requested_symbols: string[];
  ranked_candidates: UniverseSelectionCandidate[];
  selected_watchlist: UniverseSelectionCandidate[];
  rejected_candidates: UniverseSelectionCandidate[];
  blockers: string[];
  warnings: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

export type DataFreshnessSymbolResult = {
  symbol: string;
  provider: string;
  data_quality: "excellent" | "good" | "fair" | "poor" | "unavailable";
  is_mock: boolean;
  quote_age_seconds: number | null;
  bar_age_seconds: number | null;
  has_price: boolean;
  has_volume: boolean;
  has_bid_ask: boolean;
  spread_percent: number | null;
  freshness_status: "fresh" | "stale" | "unknown";
  tradability_status: "pass" | "warn" | "fail" | "unknown";
  decision: "usable" | "degraded" | "blocked";
  blockers: string[];
  warnings: string[];
};

export type DataFreshnessSummary = {
  total_checked: number;
  usable_count: number;
  degraded_count: number;
  blocked_count: number;
  mock_blocked_count: number;
  unavailable_count: number;
};

export type DataFreshnessCheckResponse = {
  run_id: string;
  status: "pass" | "warn" | "fail";
  source: string;
  checked_at: string;
  results: DataFreshnessSymbolResult[];
  blockers: string[];
  warnings: string[];
  summary: DataFreshnessSummary;
};

export type MarketRegimeModelResponse = {
  run_id: string;
  status: "pass" | "warn" | "fail";
  regime: "risk_on" | "risk_off" | "chop" | "momentum" | "volatility_expansion" | "mean_reversion" | "unknown";
  trend_state: "uptrend" | "downtrend" | "sideways" | "mixed" | "unknown";
  volatility_state: "low" | "normal" | "elevated" | "high" | "extreme" | "unknown";
  breadth_proxy: string;
  sector_rotation_proxy: string;
  confidence: number;
  regime_score: number;
  allowed_strategy_families: string[];
  blocked_strategy_families: string[];
  inputs_used: Record<string, unknown>;
  blockers: string[];
  warnings: string[];
  checked_at: string;
};

export type StrategyArgument = {
  strategy_key: string;
  strategy_family: string;
  bull_case: string;
  bear_case: string;
  fit_score: number;
  allowed: boolean;
  disable_reason?: string | null;
  required_data_sources: string[];
  model_needs: string[];
};

export type StrategyDebateResponse = {
  run_id: string;
  status: "completed" | "partial" | "failed";
  market_phase: string;
  active_loop: string;
  regime: string;
  horizon: string;
  strategy_arguments: StrategyArgument[];
  recommended_strategy_keys: string[];
  disabled_strategy_keys: string[];
  warnings: string[];
  blockers: string[];
  created_at: string;
};

export type RankedStrategy = {
  strategy_key: string;
  strategy_family: string;
  rank: number;
  strategy_score: number;
  status: "active" | "conditional" | "disabled";
  model_stack_hint: string[];
  scanner_needs: string[];
  data_needs: string[];
  reason: string;
  blockers: string[];
  warnings: string[];
};

export type StrategyRankingResponse = {
  run_id: string;
  status: "completed" | "partial" | "failed";
  debate_run_id: string | null;
  market_phase: string;
  active_loop: string;
  regime: string;
  horizon: string;
  ranked_strategies: RankedStrategy[];
  active_strategies: string[];
  disabled_strategies: string[];
  top_strategy_key: string | null;
  warnings: string[];
  blockers: string[];
  created_at: string;
};

export type SelectedModel = {
  model_key: string;
  model_name: string;
  model_type: "scanner" | "scoring" | "validation" | "meta";
  selected: boolean;
  reason: string;
  skip_reason?: string | null;
};

export type ModelWeights = {
  weighted_ranker_v1_weight: number;
  xgboost_ranker_weight: number;
  historical_similarity_weight: number;
  liquidity_model_weight: number;
  regime_alignment_weight: number;
  confidence_threshold: number;
};

export type ModelSelectionResponse = {
  run_id: string;
  status: "completed" | "partial" | "failed";
  strategy_key: string;
  selected_scanner_models: SelectedModel[];
  selected_scoring_models: SelectedModel[];
  selected_validation_models: SelectedModel[];
  meta_model_weights: ModelWeights;
  skipped_models: SelectedModel[];
  llm_validation_policy: "strict" | "moderate" | "permissive" | "disabled";
  blockers: string[];
  warnings: string[];
  reason: string;
  created_at: string;
};

export type UpperWorkflowStage = {
  stage: string;
  status: "completed" | "skipped" | "failed" | "blocked";
  run_id?: string | null;
  blockers: string[];
  warnings: string[];
};

export type UniverseSelectionDataFreshnessSummary = {
  run_id: string;
  status: string;
  usable_count: number;
  degraded_count: number;
  blocked_count: number;
  total_checked: number;
};

export type HistoricalSimilarityMatch = {
  memory_id: string;
  title: string;
  memory_type: string;
  strategy_key?: string | null;
  regime?: string | null;
  similarity_score: number;
  outcome_label?: string | null;
  realized_r?: number | null;
  lesson?: string | null;
  source: string;
  created_at: string;
  metadata: Record<string, unknown>;
};

export type HistoricalSimilarityResponse = {
  run_id: string;
  status: "completed" | "unavailable" | "no_matches" | "degraded";
  symbol: string;
  strategy_key?: string | null;
  regime?: string | null;
  matches: HistoricalSimilarityMatch[];
  similarity_score?: number | null;
  outcome_summary: Record<string, unknown>;
  blockers: string[];
  warnings: string[];
  checked_at: string;
};

export type TriggerRule = {
  rule_id: string;
  symbol: string;
  asset_class: "stock" | "option" | "crypto";
  horizon: "day_trade" | "swing" | "one_month";
  strategy_key?: string | null;
  trigger_type: string;
  trigger_condition: string;
  validation_condition: string;
  invalidation_condition: string;
  ttl_minutes: number;
  scan_interval_seconds: number;
  cooldown_minutes: number;
  priority_score: number;
  expires_at: string;
  status: "active" | "expired" | "disabled" | "triggered";
  reasons: string[];
  created_from: string;
  source_run_id?: string | null;
};

export type TriggerRuleBuildResponse = {
  run_id: string;
  status: "completed" | "partial" | "no_candidates" | "failed";
  rules: TriggerRule[];
  active_rules: string[];
  expired_rules: string[];
  total_rules: number;
  blockers: string[];
  warnings: string[];
  created_at: string;
};

export type EventScannerMatchedEvent = {
  event_id: string;
  symbol: string;
  strategy_key?: string | null;
  trigger_rule_id?: string | null;
  trigger_type: string;
  raw_signal_score: number;
  event_confidence: number;
  event_data: Record<string, unknown>;
  reasons: string[];
  warnings: string[];
  detected_at: string;
};

export type EventScannerResponse = {
  run_id: string;
  status: "completed" | "partial" | "no_symbols" | "degraded" | "failed";
  scanned_symbols: string[];
  matched_events: EventScannerMatchedEvent[];
  skipped_symbols: Array<Record<string, unknown>>;
  source: string;
  data_freshness_run_id?: string | null;
  warnings: string[];
  blockers: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

export type ScoredSignal = {
  signal_id: string;
  symbol: string;
  strategy_key?: string | null;
  trigger_type: string;
  raw_signal_score: number;
  weighted_ranker_score: number;
  xgboost_score?: number | null;
  historical_similarity_score?: number | null;
  liquidity_score?: number | null;
  regime_alignment_score?: number | null;
  data_quality_score: number;
  signal_score: number;
  confidence: number;
  model_outputs: Record<string, unknown>;
  skipped_models: Array<Record<string, unknown>>;
  reasons: string[];
  blockers: string[];
  warnings: string[];
};

export type SignalScoringResponse = {
  run_id: string;
  status: "completed" | "partial" | "no_events" | "failed";
  scored_signals: ScoredSignal[];
  skipped_signals: Array<Record<string, unknown>>;
  blockers: string[];
  warnings: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

export type EnsembleSignal = {
  symbol: string;
  strategy_key?: string | null;
  trigger_type: string;
  final_signal_score: number;
  confidence: number;
  model_agreement: number;
  primary_reason: string;
  disagreement: string[];
  components: Array<Record<string, unknown>>;
  status: "pass" | "watch" | "blocked";
  blockers: string[];
  warnings: string[];
  scored_signal_id?: string | null;
};

export type MetaModelEnsembleResponse = {
  run_id: string;
  status: "completed" | "partial" | "no_signals" | "failed";
  ensemble_signals: EnsembleSignal[];
  passed_signals: string[];
  watch_signals: string[];
  blocked_signals: string[];
  model_weights_used: Record<string, number>;
  promoted_candidates: string[];
  blockers: string[];
  warnings: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

// LLM Budget Gate Types
export type LLMBudgetGateResponse = {
  run_id: string;
  status: "approved" | "skipped" | "blocked";
  llm_validation_policy: "disabled" | "deterministic_only" | "cheap_summary_allowed" | "strong_reasoning_allowed";
  selected_tier: "disabled" | "cheap" | "standard" | "strong";
  estimated_cost_usd: number;
  reason: string;
  blockers: string[];
  warnings: string[];
  checked_at: string;
};

// Agent Validation Types
export type SpecialistVote = {
  agent_key: string;
  vote: "pass" | "watch" | "block" | "abstain";
  score: number;
  reason: string;
};

export type AgentValidationResponse = {
  run_id: string;
  status: "pass" | "watch" | "blocked" | "skipped";
  symbol: string | null;
  specialist_votes: SpecialistVote[];
  validation_score: number;
  blockers: string[];
  warnings: string[];
  reason: string;
  checked_at: string;
};

// Risk Manager Types
export type OpenPosition = {
  symbol: string;
  side: "long" | "short";
  entry_price: number;
  quantity: number;
  unrealized_pnl: number;
};

export type RiskReviewResponse = {
  run_id: string;
  symbol: string;
  status: "approved" | "watch_only" | "paper_only" | "reduce_size" | "blocked";
  risk_score: number;
  hard_veto: boolean;
  veto_reasons: string[];
  max_dollar_risk: number;
  max_position_size_dollars: number;
  position_size_cap_dollars: number;
  required_reward_risk_ratio: number;
  approved_reward_risk_ratio: number | null;
  blockers: string[];
  warnings: string[];
  checked_at: string;
  live_trading_allowed: boolean;
};

// No-Trade Types
export type NoTradeResponse = {
  run_id: string;
  decision: "trade_allowed" | "watch_only" | "no_trade" | "reduce_cadence" | "preserve_capital";
  no_trade_reason: string;
  severity: "low" | "medium" | "high";
  blockers: string[];
  warnings: string[];
  checked_at: string;
};

// Capital Allocation Types
export type CapitalAllocationResponse = {
  run_id: string;
  symbol: string;
  status: "plan_created" | "watch_only" | "blocked";
  opportunity_score: number;
  capital_allocation_dollars: number;
  risk_dollars: number;
  position_size_units: number;
  entry_zone_low: number;
  entry_zone_high: number;
  stop_loss: number;
  invalidation: number;
  target_price: number;
  target_2_price: number | null;
  reward_risk_ratio: number;
  max_hold_minutes: number | null;
  timeout_rule: string;
  rotation_rule: string;
  approval_required: boolean;
  paper_trade_allowed: boolean;
  live_trading_allowed: boolean;
  blockers: string[];
  warnings: string[];
  created_at: string;
};

// Recommendation Pipeline Types
export type PipelineStage = {
  stage: string;
  status: "pending" | "running" | "completed" | "blocked" | "skipped";
  result: Record<string, unknown> | null;
  blockers: string[];
  warnings: string[];
};

export type PipelineRecommendation = {
  id: string;
  symbol: string;
  action_label: string;
  status: "pending_review" | "approved" | "rejected" | "paper_trade_created" | "expired";
  final_signal_score: number;
  confidence: number;
  risk_status: string;
  no_trade_decision: string;
  llm_policy: string;
  capital_allocation_dollars: number;
  position_size_units: number;
  entry_zone_low: number;
  entry_zone_high: number;
  stop_loss: number;
  target_price: number;
  reward_risk_ratio: number;
  paper_trade_allowed: boolean;
  live_trading_allowed: boolean;
  approval_required: boolean;
  reason: string;
};

export type RecommendationPipelineResponse = {
  run_id: string;
  status: "no_signal_available" | "llm_gate_skipped" | "agent_validation_blocked" | "risk_blocked" | "no_trade" | "capital_allocation_blocked" | "recommendation_created" | "completed";
  symbol: string | null;
  llm_budget_gate: LLMBudgetGateResponse | null;
  agent_validation: AgentValidationResponse | null;
  risk_review: RiskReviewResponse | null;
  no_trade: NoTradeResponse | null;
  capital_allocation: CapitalAllocationResponse | null;
  recommendation: PipelineRecommendation | null;
  stages: PipelineStage[];
  blockers: string[];
  warnings: string[];
  started_at: string;
  completed_at: string;
};

export type UpperWorkflowResponse = {
  run_id: string;
  status: "completed" | "partial" | "failed" | "blocked";
  market_phase: string;
  active_loop: string;
  stages: UpperWorkflowStage[];
  data_freshness: DataFreshnessCheckResponse | null;
  regime: MarketRegimeModelResponse | null;
  strategy_debate: StrategyDebateResponse | null;
  strategy_ranking: StrategyRankingResponse | null;
  model_selection: ModelSelectionResponse | null;
  universe_selection: UniverseSelectionResponse | null;
  trigger_rules: TriggerRuleBuildResponse | null;
  event_scanner: EventScannerResponse | null;
  signal_scoring: SignalScoringResponse | null;
  meta_model_ensemble: MetaModelEnsembleResponse | null;
  recommendation_pipeline: RecommendationPipelineResponse | null;
  promoted_candidates: string[];
  blockers: string[];
  warnings: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

export type RecommendationLifecycleRecord = {
  id: string;
  symbol: string;
  asset_class: string;
  horizon: string;
  source: string;
  feature_row_id?: string | null;
  score: number;
  confidence: number;
  action_label: string;
  status: "pending_review" | "approved" | "rejected" | "paper_trade_created" | "expired";
  reason: string;
  risk_factors: string[];
  created_at: string;
  updated_at: string;
  workflow_run_id?: string | null;
};

export type DecisionCandidate = {
  symbol: string;
  asset_class: string;
  horizon: string;
  source: string;
  provider?: string | null;
  data_quality: string;
  status: string;
  rank?: number | null;
  final_score: number;
  confidence: number;
  current_price?: number | null;
  buy_zone_low?: number | null;
  buy_zone_high?: number | null;
  stop_loss?: number | null;
  target_price?: number | null;
  reward_risk_ratio?: number | null;
  feature_row_id?: string | null;
  model_outputs: Array<Record<string, unknown>>;
  blockers: string[];
  warnings: string[];
  reason: string;
};

export type DecisionWorkflowRunResponse = {
  run_id: string;
  status: string;
  source: string;
  horizon: string;
  symbols_requested: string[];
  candidates: DecisionCandidate[];
  top_action?: TradeRecommendation | null;
  recommendations: Recommendation[];
  feature_runs: Array<Record<string, unknown>>;
  model_runs: Array<Record<string, unknown>>;
  blockers: string[];
  warnings: string[];
  started_at: string;
  completed_at: string;
  duration_ms: number;
};

// Learning Loop Types

export type JournalOutcomeResponse = {
  id: string;
  source_type: string;
  source_id: string | null;
  symbol: string | null;
  outcome_label: "win" | "loss" | "breakeven" | "avoided_loss" | "missed_opportunity" | "invalidated" | "unknown";
  /** How price resolved vs planned stop/target (learning-loop calibration). */
  resolution_path: "target_first" | "stop_first" | "timed_exit" | "invalidation_before_entry" | "unknown";
  mfe_percent: number | null;
  mae_percent: number | null;
  realized_r: number | null;
  time_to_result_minutes: number | null;
  followed_plan: boolean | null;
  confidence_error: number | null;
  expected_vs_actual: string | null;
  lessons: string[];
  created_at: string;
  updated_at: string;
};

export type JournalOutcomeSummary = {
  total_entries: number;
  wins: number;
  losses: number;
  breakeven: number;
  unknown: number;
  win_rate: number;
  average_realized_r: number | null;
  by_source_type: Record<string, number>;
  by_symbol: Record<string, number>;
  by_strategy: Record<string, number>;
  recent_entries: JournalOutcomeResponse[];
};

export type CalibrationBucket = {
  bucket: string;
  count: number;
  avg_confidence: number;
  observed_win_rate: number;
  avg_realized_r: number | null;
  calibration_error: number;
};

export type PerformanceDriftResponse = {
  run_id: string;
  status: "pass" | "warn" | "fail" | "insufficient_data";
  sample_count: number;
  calibration_buckets: CalibrationBucket[];
  false_positive_rate: number | null;
  win_rate: number | null;
  average_realized_r: number | null;
  confidence_error: number | null;
  affected_models: string[];
  affected_strategies: string[];
  recommended_actions: string[];
  blockers: string[];
  warnings: string[];
  checked_at: string;
};

export type ResearchTask = {
  task_id: string;
  priority_rank: number;
  priority_score: number;
  task_type: "backtest" | "model_evaluation" | "strategy_review" | "feature_review" | "risk_filter_review" | "data_quality_review" | "retraining_request";
  title: string;
  description: string;
  linked_strategy_key: string | null;
  linked_model: string | null;
  evidence: string[];
  suggested_next_step: string;
  status: "open" | "in_progress" | "completed" | "rejected";
};

export type ResearchPriorityResponse = {
  run_id: string;
  status: "generated" | "insufficient_evidence" | "empty";
  tasks: ResearchTask[];
  blockers: string[];
  warnings: string[];
  created_at: string;
};

export type StrategyWeightUpdate = {
  strategy_key: string;
  current_weight: number | null;
  proposed_weight: number;
  action: "keep" | "reduce" | "increase" | "pause" | "collect_more_data";
  reason: string;
  evidence: string[];
};

export type ModelWeightUpdate = {
  model_name: string;
  current_weight: number | null;
  proposed_weight: number;
  action: "keep" | "reduce" | "increase" | "pause" | "collect_more_data";
  reason: string;
  evidence: string[];
};

export type RetrainingRequest = {
  model_name: string;
  reason: string;
  required_data_points: number;
  current_data_points: number;
};

export type ModelStrategyUpdateResponse = {
  run_id: string;
  status: "proposed" | "insufficient_data" | "no_changes";
  strategy_weight_updates: StrategyWeightUpdate[];
  model_weight_updates: ModelWeightUpdate[];
  paused_strategies: string[];
  retraining_requests: RetrainingRequest[];
  evaluation_jobs: Array<Record<string, unknown>>;
  blockers: string[];
  warnings: string[];
  created_at: string;
};

export type MemoryUpdateResponse = {
  run_id: string;
  status: "stored" | "skipped" | "unavailable";
  memory_id: string | null;
  source_type: string;
  warnings: string[];
  blockers: string[];
  created_at: string;
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
  // Re-export for compatibility
  getJournalSummaryLegacy: () => request<JournalOutcomeSummary>("/api/journal/outcomes/summary"),
  runModelLab: (payload: ModelLabRunRequest) => request<ModelLabRunResponse>("/api/model-lab/run", { method: "POST", body: JSON.stringify(payload) }),
  getAiOpsSummary: () => request<AiOpsSummaryResponse>("/api/ai-ops/summary"),
  getAiOpsWorkflows: () => request<AiOpsWorkflowListResponse>("/api/ai-ops/workflows"),
  getAiOpsAgentStatus: () => request<AiOpsAgentStatusResponse>("/api/ai-ops/agents/status"),
  getAiOpsLlmUsage: () => request<AiOpsLlmUsageResponse>("/api/ai-ops/llm-usage"),
  getAiOpsSchedulerJobs: () => request<AiOpsSchedulerJobsResponse>("/api/ai-ops/scheduler/jobs"),
  getAiOpsAuditEvents: () => request<AiOpsAuditEventsResponse>("/api/ai-ops/audit-events"),
  runEdgeRadar: (payload: EdgeRadarRunRequest) => request<EdgeRadarRunResponse>("/api/agents/edge-radar/run", { method: "POST", body: JSON.stringify(payload) }),
  getDataQuality: (symbol: string, assetClass = "stock", source: MarketDataSource | string = "auto") =>
    request<DataQualityReport>(`/api/data-quality/${symbol}?asset_class=${assetClass}&source=${source}`),
  runFeatureStore: (payload: FeatureStoreRunRequest) =>
    request<FeatureStoreRunResponse>("/api/feature-store/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestFeatureStoreRows: () => request<FeatureStoreRow[]>("/api/feature-store/latest"),
  getFeatureStoreRowsBySymbol: (symbol: string) => request<FeatureStoreRow[]>(`/api/feature-store/${symbol}`),
  getModelRunRegistry: () => request<ModelRegistryResponse>("/api/model-runs/registry"),
  planModelRun: (payload: ModelRunPlanRequest) => request<ModelRunPlanResponse>("/api/model-runs/plan", { method: "POST", body: JSON.stringify(payload) }),
  runModelRun: (payload: ModelRunRequest) => request<ModelRunResponse>("/api/model-runs/run", { method: "POST", body: JSON.stringify(payload) }),
  getLlmGatewayStatus: () => request<LlmGatewayStatusResponse>("/api/llm-gateway/status"),
  getLlmGatewayProviders: () => request<LlmProviderStatus[]>("/api/llm-gateway/providers"),
  getLlmGatewayModels: () => request<LlmModelConfig[]>("/api/llm-gateway/models"),
  getLlmGatewayRoutingRules: () => request<LlmRoutingRule[]>("/api/llm-gateway/routing-rules"),
  getLlmGatewayUsage: () => request<LlmUsageRecord[]>("/api/llm-gateway/usage"),
  getLlmGatewayCosts: () => request<LlmCostSummary>("/api/llm-gateway/costs"),
  getLlmGatewayAgentModelMap: () => request<AgentModelMapping[]>("/api/llm-gateway/agent-model-map"),
  estimateLlmCost: (payload: LlmCostEstimateRequest) => request<LlmCostEstimateResponse>("/api/llm-gateway/estimate", { method: "POST", body: JSON.stringify(payload) }),
  testLlmGatewayCall: (payload: LlmGatewayTestCallRequest) => request<LlmGatewayTestCallResponse>("/api/llm-gateway/test-call", { method: "POST", body: JSON.stringify(payload) }),
  getAgentRegistry: () => request<CoreAgentRegistryResponse>("/api/agents/registry"),
  getStrategies: () => request<StrategyRegistryResponse>("/api/strategies"),
  getStrategyRegistrySummary: () => request<StrategyRegistrySummary>("/api/strategies/summary"),
  getCandidateStrategies: () => request<StrategyRegistryResponse>("/api/strategies/candidates"),
  getActiveStrategies: () => request<StrategyRegistryResponse>("/api/strategies/active"),
  getStrategy: (strategyKey: string) => request<StrategyConfig>(`/api/strategies/${strategyKey}`),
  getStrategyPlaybook: (strategyKey: string) => request<Record<string, unknown>>(`/api/strategies/${strategyKey}/playbook`),
  getEdgeSignalRules: () => request<EdgeSignalRulesResponse>("/api/edge-signal-rules"),
  scanMarketConditions: (payload: MarketScannerRequest) => request<MarketScannerResponse>("/api/market-scanner/scan", { method: "POST", body: JSON.stringify(payload) }),
  getMarketScanRuns: (limit = 25) => request<MarketScanRun[]>(`/api/market-scanner/runs?limit=${limit}`),
  getLatestMarketScanRun: () => request<MarketScanRun | null>("/api/market-scanner/runs/latest"),
  getMarketScanRun: (runId: string) => request<MarketScanRun>(`/api/market-scanner/runs/${runId}`),
  runScheduledMarketScanOnce: () => request<Record<string, unknown>>("/api/market-scanner/run-scheduled-once", { method: "POST" }),
  getStrategyWorkflowRuns: (limit = 25) => request<StrategyWorkflowRunResult[]>(`/api/strategy-workflows/runs?limit=${limit}`),
  getLatestStrategyWorkflowRun: () => request<StrategyWorkflowRunResult | null>("/api/strategy-workflows/runs/latest"),
  getStrategyWorkflowRun: (id: string) => request<StrategyWorkflowRunResult>(`/api/strategy-workflows/runs/${id}`),
  runStrategyWorkflow: (payload: StrategyWorkflowRunRequest) => request<StrategyWorkflowRunResult>("/api/strategy-workflows/run", { method: "POST", body: JSON.stringify(payload) }),
  getAutoRunStatus: () => request<AutoRunControlState>("/api/auto-run/status"),
  updateAutoRunStatus: (payload: AutoRunControlUpdate) => request<AutoRunControlState>("/api/auto-run/status", { method: "PUT", body: JSON.stringify(payload) }),

  // Candidate Universe APIs
  getCandidateUniverse: () => request<CandidateUniverseResponse>("/api/candidate-universe"),
  addCandidate: (payload: { symbol: string; asset_class?: string; horizon?: string; source_type?: string; source_detail?: string; priority_score?: number; notes?: string }) =>
    request<{ success: boolean; message: string; candidate: CandidateUniverseEntry }>("/api/candidate-universe/add", { method: "POST", body: JSON.stringify(payload) }),
  bulkAddCandidates: (payload: { symbols: string[]; asset_class?: string; horizon?: string; source_type?: string; source_detail?: string; priority_score?: number; notes?: string }) =>
    request<{ success: boolean; message: string; candidates: CandidateUniverseEntry[] }>("/api/candidate-universe/bulk-add", { method: "POST", body: JSON.stringify(payload) }),
  removeCandidate: (symbol: string) =>
    request<{ success: boolean; message: string }>("/api/candidate-universe/remove", { method: "POST", body: JSON.stringify({ symbol }) }),
  clearCandidates: () =>
    request<{ success: boolean; message: string }>("/api/candidate-universe/clear", { method: "POST" }),

  // Decision Workflow APIs
  getLatestDecisionWorkflowRun: () => request<DecisionWorkflowRunResponse | null>("/api/decision-workflows/runs/latest"),
  listDecisionWorkflowRuns: (limit = 20) => request<DecisionWorkflowRunResponse[]>(`/api/decision-workflows/runs?limit=${limit}`),
  runDecisionWorkflow: (payload: { symbols: string[]; asset_class?: string; horizon?: string; source?: string; max_candidates?: number; allow_mock?: boolean }) =>
    request<DecisionWorkflowRunResponse>("/api/decision-workflows/run", { method: "POST", body: JSON.stringify(payload) }),
  runDecisionWorkflowDefault: () => request<DecisionWorkflowRunResponse>("/api/decision-workflows/run-default", { method: "POST" }),
  runCandidateUniverseWorkflow: () => request<DecisionWorkflowRunResponse>("/api/decision-workflows/run-candidate-universe", { method: "POST" }),

  // Scanner Promotion API
  promoteScannerToCandidates: (payload?: { min_score?: number; max_candidates?: number; horizon?: string }) =>
    request<{ success: boolean; message: string; added: Array<Record<string, unknown>>; skipped: Array<Record<string, unknown>>; total_added: number; total_skipped: number }>("/api/market-scanner/promote-to-candidates", { method: "POST", body: JSON.stringify(payload || {}) }),

  // Watchlist Promotion API
  promoteWatchlistToCandidates: (payload?: { watchlist_id?: string; symbols?: string[]; horizon?: string; priority_score?: number }) =>
    request<{ success: boolean; message: string; added: Array<Record<string, unknown>>; skipped: Array<Record<string, unknown>>; total_added: number; total_skipped: number }>("/api/watchlists/promote-to-candidates", { method: "POST", body: JSON.stringify(payload || {}) }),

  // Recommendation Lifecycle APIs
  getRecommendationLifecycleList: (status?: string, symbol?: string, limit?: number) =>
    request<RecommendationLifecycleRecord[]>(`/api/recommendation-lifecycle?${status ? `status=${status}&` : ""}${symbol ? `symbol=${symbol}&` : ""}${limit ? `limit=${limit}` : ""}`),
  // Alias for compatibility
  getRecommendationLifecycle: (status?: string, symbol?: string, limit?: number) =>
    request<RecommendationLifecycleRecord[]>(`/api/recommendation-lifecycle?${status ? `status=${status}&` : ""}${symbol ? `symbol=${symbol}&` : ""}${limit ? `limit=${limit}` : ""}`),
  getRecommendationLifecycleSummary: () => request<Record<string, unknown>>("/api/recommendation-lifecycle/summary"),
  approveRecommendation: (id: string) => request<{ success: boolean; recommendation: Record<string, unknown> | null; message: string }>("/api/recommendation-lifecycle/approve", { method: "POST", body: JSON.stringify({ id }) }),
  rejectRecommendation: (id: string) => request<{ success: boolean; recommendation: Record<string, unknown> | null; message: string }>("/api/recommendation-lifecycle/reject", { method: "POST", body: JSON.stringify({ id }) }),
  expireRecommendation: (id: string) => request<{ success: boolean; recommendation: Record<string, unknown> | null; message: string }>("/api/recommendation-lifecycle/expire", { method: "POST", body: JSON.stringify({ id }) }),

  // Command Center Run API
  runCommandCenter: () => request<CommandCenterResponse>("/api/command-center/run", { method: "POST" }),

  // Universe Selection APIs
  runUniverseSelection: (payload: UniverseSelectionRequest) =>
    request<UniverseSelectionResponse>("/api/universe-selection/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestUniverseSelection: () => request<UniverseSelectionResponse | { message: string; status: string }>("/api/universe-selection/runs/latest"),
  getUniverseSelectionRuns: (limit = 20) => request<{ runs: UniverseSelectionResponse[]; count: number; total_available: number }>(`/api/universe-selection/runs?limit=${limit}`),
  promoteLatestUniverseSelectionToCandidates: () =>
    request<{ success: boolean; message: string; promoted_count: number; promoted_symbols: string[]; source_run_id?: string }>("/api/universe-selection/promote-latest-to-candidates", { method: "POST" }),

  // Runtime/Timing APIs
  getRuntimePhase: () => request<{ market_phase: string; current_time_et: string; is_trading_day: boolean; live_trading_allowed: boolean; human_approval_required: boolean; timestamp: string }>("/api/runtime/phase"),
  getRuntimeCadence: () => request<{ market_phase: string; active_loop: string; cadence_plan: CadencePlan; live_trading_allowed: boolean; human_approval_required: boolean; timestamp: string }>("/api/runtime/cadence"),

  // Data Freshness APIs
  runDataFreshnessCheck: (payload: { symbols: string[]; asset_class?: string; source?: string; horizon?: string; allow_mock?: boolean }) =>
    request<DataFreshnessCheckResponse>("/api/data-freshness/check", { method: "POST", body: JSON.stringify(payload) }),
  getLatestDataFreshness: () => request<DataFreshnessCheckResponse | { message: string; status: string }>("/api/data-freshness/latest"),

  // Market Regime APIs
  runMarketRegime: (payload: { source?: string; horizon?: string; allow_mock?: boolean }) =>
    request<MarketRegimeModelResponse>("/api/market-regime/model/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestMarketRegime: () => request<MarketRegimeModelResponse | { message: string; status: string }>("/api/market-regime/model/latest"),

  // Strategy Debate APIs
  runStrategyDebate: (payload: { market_phase: string; active_loop: string; regime: string; horizon: string; account_equity?: number; buying_power?: number }) =>
    request<StrategyDebateResponse>("/api/strategy-debate/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestStrategyDebate: () => request<StrategyDebateResponse | { message: string; status: string }>("/api/strategy-debate/latest"),

  // Strategy Ranking APIs
  runStrategyRanking: (payload: { market_phase: string; active_loop: string; regime: string; horizon: string; account_equity?: number; buying_power?: number }) =>
    request<StrategyRankingResponse>("/api/strategy-ranking/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestStrategyRanking: () => request<StrategyRankingResponse | { message: string; status: string }>("/api/strategy-ranking/latest"),
  // Note: getActiveStrategies is defined above for strategy registry

  // Model Selection APIs
  runModelSelection: (payload: { strategy_key: string; market_phase: string; active_loop: string; regime: string; horizon: string; llm_budget_mode?: string }) =>
    request<ModelSelectionResponse>("/api/model-selection/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestModelSelection: () => request<ModelSelectionResponse | { message: string; status: string }>("/api/model-selection/latest"),
  getModelRegistry: () => request<Record<string, unknown>>("/api/model-selection/registry"),

  // Upper Workflow API
  runUpperWorkflow: (payload: { symbols: string[]; horizon?: string; source?: string; asset_class?: string; account_equity?: number; buying_power?: number; allow_mock?: boolean; promote_to_candidate_universe?: boolean; build_trigger_rules?: boolean; run_event_scanner?: boolean; run_signal_scoring?: boolean; run_meta_model?: boolean; run_recommendation_pipeline?: boolean }) =>
    request<UpperWorkflowResponse>("/api/upper-workflow/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestUpperWorkflow: () => request<UpperWorkflowResponse | { message: string; status: string }>("/api/upper-workflow/latest"),

  // Historical Similarity APIs
  runHistoricalSimilarity: (payload: { symbol: string; asset_class?: string; horizon?: string; strategy_key?: string; regime?: string; max_results?: number; min_similarity?: number }) =>
    request<HistoricalSimilarityResponse>("/api/historical-similarity/search", { method: "POST", body: JSON.stringify(payload) }),
  getLatestHistoricalSimilarity: () => request<HistoricalSimilarityResponse | { message: string; status: string }>("/api/historical-similarity/latest"),

  // Trigger Rules APIs
  buildTriggerRules: (payload: { symbols?: string[]; strategy_key?: string; horizon?: string; market_phase?: string; active_loop?: string; use_latest_watchlist?: boolean }) =>
    request<TriggerRuleBuildResponse>("/api/trigger-rules/build", { method: "POST", body: JSON.stringify(payload) }),
  getLatestTriggerRules: () => request<TriggerRuleBuildResponse | { message: string; status: string }>("/api/trigger-rules/latest"),
  getActiveTriggerRules: () => request<{ rules: TriggerRule[]; count: number; status: string }>("/api/trigger-rules/active"),
  expireTriggerRules: (allRules?: boolean, ruleId?: string) =>
    request<{ expired_count: number; status: string; message: string }>("/api/trigger-rules/expire", { method: "POST", body: JSON.stringify({ all_rules: allRules, rule_id: ruleId }) }),

  // Event Scanner APIs
  runEventScanner: (payload: { symbols?: string[]; use_latest_watchlist?: boolean; use_active_trigger_rules?: boolean; source?: string; horizon?: string; allow_mock?: boolean; max_symbols?: number }) =>
    request<EventScannerResponse>("/api/event-scanner/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestEventScan: () => request<EventScannerResponse | { message: string; status: string }>("/api/event-scanner/runs/latest"),
  getEventScanRuns: (limit = 20) => request<{ runs: EventScannerResponse[]; count: number }>(`/api/event-scanner/runs?limit=${limit}`),

  // Signal Scoring APIs
  runSignalScoring: (payload: { events?: unknown[]; use_latest_events?: boolean; source?: string; horizon?: string; strategy_key?: string; allow_mock?: boolean }) =>
    request<SignalScoringResponse>("/api/signal-scoring/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestSignalScoring: () => request<SignalScoringResponse | { message: string; status: string }>("/api/signal-scoring/runs/latest"),
  getSignalScoringRuns: (limit = 20) => request<{ runs: SignalScoringResponse[]; count: number }>(`/api/signal-scoring/runs?limit=${limit}`),

  // Meta-Model Ensemble APIs
  runMetaModelEnsemble: (payload: { scored_signals?: unknown[]; use_latest_scored_signals?: boolean; regime?: string; strategy_key?: string; horizon?: string; promote_to_candidates?: boolean; include_watch?: boolean }) =>
    request<MetaModelEnsembleResponse>("/api/meta-model/ensemble/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestMetaModelEnsemble: () => request<MetaModelEnsembleResponse | { message: string; status: string }>("/api/meta-model/ensemble/latest"),
  getMetaModelEnsembleRuns: (limit = 20) => request<{ runs: MetaModelEnsembleResponse[]; count: number }>(`/api/meta-model/ensemble/runs?limit=${limit}`),
  promotePassingSignalsToCandidates: (includeWatch?: boolean, minScore?: number) =>
    request<{ success: boolean; promoted_count: number; promoted_symbols: string[]; source_run_id?: string }>("/api/meta-model/ensemble/promote-passing-to-candidates", { method: "POST", body: JSON.stringify({ include_watch: includeWatch, min_score: minScore }) }),

  // LLM Budget Gate APIs
  evaluateLLMBudgetGate: (payload: { symbol?: string; final_signal_score?: number; confidence?: number; allow_paid_llm?: boolean; dry_run?: boolean; requested_model_tier?: string }) =>
    request<LLMBudgetGateResponse>("/api/llm-budget-gate/evaluate", { method: "POST", body: JSON.stringify(payload) }),
  getLatestLLMBudgetGate: () => request<LLMBudgetGateResponse | { message: string; status: string }>("/api/llm-budget-gate/latest"),

  // Agent Validation APIs
  runAgentValidation: (payload: { ensemble_signal?: Record<string, unknown>; symbol?: string; strategy_key?: string; final_signal_score?: number; confidence?: number; llm_policy?: string; dry_run?: boolean }) =>
    request<AgentValidationResponse>("/api/agent-validation/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestAgentValidation: () => request<AgentValidationResponse | { message: string; status: string }>("/api/agent-validation/latest"),

  // Risk Manager APIs
  reviewRisk: (payload: { symbol: string; asset_class?: string; horizon?: string; current_price?: number; final_signal_score?: number; confidence?: number; account_equity?: number; buying_power?: number; data_quality?: string; spread_percent?: number; liquidity_score?: number }) =>
    request<RiskReviewResponse>("/api/risk-manager/review", { method: "POST", body: JSON.stringify(payload) }),
  getLatestRiskReview: () => request<RiskReviewResponse | { message: string; status: string }>("/api/risk-manager/latest"),

  // No-Trade APIs
  evaluateNoTrade: (payload: { regime?: string; data_freshness_status?: string; final_signal_score?: number; confidence?: number; risk_status?: string; buying_power?: number; account_equity?: number; warnings?: string[]; blockers?: string[] }) =>
    request<NoTradeResponse>("/api/no-trade/evaluate", { method: "POST", body: JSON.stringify(payload) }),
  getLatestNoTrade: () => request<NoTradeResponse | { message: string; status: string }>("/api/no-trade/latest"),

  // Capital Allocation APIs
  createCapitalAllocationPlan: (payload: { symbol: string; current_price: number; final_signal_score: number; confidence: number; risk_status: string; account_equity?: number; buying_power?: number; max_risk_per_trade_percent?: number; max_position_size_percent?: number; min_reward_risk_ratio?: number }) =>
    request<CapitalAllocationResponse>("/api/capital-allocation/plan", { method: "POST", body: JSON.stringify(payload) }),
  getLatestCapitalAllocation: () => request<CapitalAllocationResponse | { message: string; status: string }>("/api/capital-allocation/latest"),

  // Recommendation Pipeline APIs
  runRecommendationPipeline: (payload: { use_latest_ensemble?: boolean; ensemble_signal?: Record<string, unknown>; symbol?: string; account_equity?: number; buying_power?: number; allow_paid_llm?: boolean; dry_run?: boolean }) =>
    request<RecommendationPipelineResponse>("/api/recommendation-pipeline/run", { method: "POST", body: JSON.stringify(payload) }),
  getLatestRecommendationPipeline: () => request<RecommendationPipelineResponse | { message: string; status: string }>("/api/recommendation-pipeline/latest"),

  // Journal Outcomes APIs
  createJournalOutcome: (payload: { source_type?: string; symbol?: string; entry_price?: number; exit_price?: number; stop_loss?: number; target_price?: number; max_favorable_price?: number; max_adverse_price?: number; opened_at?: string; closed_at?: string; notes?: string }) =>
    request<JournalOutcomeResponse>("/api/journal/outcomes", { method: "POST", body: JSON.stringify(payload) }),
  getJournalOutcomes: (filters?: { source_type?: string; symbol?: string; outcome_label?: string; limit?: number }) =>
    request<JournalOutcomeResponse[]>(`/api/journal/outcomes?${filters?.source_type ? `source_type=${filters.source_type}&` : ""}${filters?.symbol ? `symbol=${filters.symbol}&` : ""}${filters?.outcome_label ? `outcome_label=${filters.outcome_label}&` : ""}${filters?.limit ? `limit=${filters.limit}` : ""}`),
  getJournalOutcome: (entryId: string) => request<JournalOutcomeResponse>(`/api/journal/outcomes/${entryId}`),
  getJournalSummary: () => request<JournalOutcomeSummary>("/api/journal/outcomes/summary"),
  labelFromPaperTrade: (payload: { paper_trade_id: string; symbol: string; entry_price: number; exit_price?: number; stop_loss: number; target_price: number; opened_at: string; closed_at?: string; outcome_notes?: string }) =>
    request<JournalOutcomeResponse>("/api/journal/outcomes/label-from-paper-trade", { method: "POST", body: JSON.stringify(payload) }),

  // Alpaca Paper Account APIs
  getAlpacaPaperSnapshot: () => request<AlpacaPaperSnapshot>("/api/paper-trading/alpaca"),
  getAlpacaPaperPortfolioHistory: (period = "3M", timeframe = "1D") =>
    request<AlpacaPaperPortfolioHistory>(`/api/paper-trading/alpaca/portfolio-history?period=${period}&timeframe=${timeframe}`),

  // Performance Drift APIs
  runPerformanceDrift: (payload?: { lookback_days?: number; strategy_key?: string; model_name?: string; min_samples?: number; source?: string }) =>
    request<PerformanceDriftResponse>("/api/performance-drift/run", { method: "POST", body: JSON.stringify(payload || {}) }),
  getLatestPerformanceDrift: () => request<PerformanceDriftResponse | { message: string; status: string }>("/api/performance-drift/latest"),
  getPerformanceDriftHistory: (limit?: number) => request<PerformanceDriftResponse[]>(`/api/performance-drift/history?limit=${limit || 20}`),

  // Research Priority APIs
  runResearchPriority: (payload?: { lookback_days?: number; include_drift?: boolean; include_journal?: boolean; include_no_trade?: boolean; max_tasks?: number }) =>
    request<ResearchPriorityResponse>("/api/research-priority/run", { method: "POST", body: JSON.stringify(payload || {}) }),
  getLatestResearchPriority: () => request<ResearchPriorityResponse | { message: string; status: string }>("/api/research-priority/latest"),
  getResearchTasks: (status?: string) => request<ResearchTask[]>(`/api/research-priority/tasks${status ? `?status=${status}` : ""}`),
  updateResearchTask: (taskId: string, status: string) => request<{ success: boolean; task: ResearchTask }>(`/api/research-priority/tasks/${taskId}/update`, { method: "POST", body: JSON.stringify({ status }) }),

  // Model/Strategy Update APIs
  proposeModelStrategyUpdate: (payload?: { research_run_id?: string; drift_run_id?: string; dry_run?: boolean }) =>
    request<ModelStrategyUpdateResponse>("/api/model-strategy-update/propose", { method: "POST", body: JSON.stringify(payload || {}) }),
  getLatestModelStrategyUpdate: () => request<ModelStrategyUpdateResponse | { message: string; status: string }>("/api/model-strategy-update/latest"),
  getModelStrategyUpdateHistory: (limit?: number) => request<ModelStrategyUpdateResponse[]>(`/api/model-strategy-update/history?limit=${limit || 20}`),

  // Memory Update APIs
  storeMemory: (payload: { source_type: string; title: string; content: string; metadata?: Record<string, unknown>; dry_run?: boolean }) =>
    request<MemoryUpdateResponse>("/api/memory-update/store", { method: "POST", body: JSON.stringify(payload) }),
  storeLatestJournalToMemory: () => request<MemoryUpdateResponse>("/api/memory-update/from-journal-latest", { method: "POST" }),
  storeLatestResearchToMemory: () => request<MemoryUpdateResponse>("/api/memory-update/from-research-latest", { method: "POST" }),
  getLatestMemoryUpdate: () => request<MemoryUpdateResponse | { message: string; status: string }>("/api/memory-update/latest"),

  // Platform Readiness APIs
  getPlatformReadiness: () => request<PlatformReadinessResponse>("/api/platform-readiness"),

  // Settings APIs
  getSettings: () => request<SettingsResponse>("/api/settings"),
  updateSettings: (payload: SettingsUpdateRequest) =>
    request<SettingsResponse>("/api/settings", { method: "POST", body: JSON.stringify(payload) }),
  resetSettings: () => request<SettingsResponse>("/api/settings/reset", { method: "POST" }),
  
  // Paper Trading Order API
  placePaperOrder: (payload: PaperOrderRequest) =>
    request<PaperOrderResponse>("/api/paper-trading/order", { method: "POST", body: JSON.stringify(payload) }),

  // Tracing APIs
  getTracingStatus: () => request<TracingStatusResponse>("/api/tracing/status"),
  sendTracingTestEvent: (payload: TracingTestEventRequest) =>
    request<TracingTestEventResponse>("/api/tracing/test-event", { method: "POST", body: JSON.stringify(payload) }),
};
