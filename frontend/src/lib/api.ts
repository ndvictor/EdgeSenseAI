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
  data_mode: "synthetic_prototype" | "paper" | "live";
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

export type CommandCenterResponse = {
  account_profile: AccountRiskProfile;
  top_action: TradeRecommendation;
  top_recommendations: Recommendation[];
  urgent_edge_alerts: EdgeSignal[];
  agents: { name: string; role: string; status: string; status_label: string; last_checked: string }[];
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
  getMarketSnapshots: () => request<MarketSnapshot[]>("/api/market/snapshots"),
  getFeatures: (symbol: string) => request<EngineeredFeatures>(`/api/features/${symbol}`),
  getModelPipeline: (symbol: string) => request<ModelPipelineResult>(`/api/model-pipeline/${symbol}`),
  getAccountFeasibility: (symbol: string) => request<AccountFeasibilityResult>(`/api/account-feasibility/${symbol}`),
  getRiskCheck: (symbol: string) => request<RiskCheckResult>(`/api/risk-check/${symbol}`),
};
