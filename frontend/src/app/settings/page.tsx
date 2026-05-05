"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { 
  api, 
  type SettingsResponse, 
  type TradingSettingsUpdate,
  type LlmGatewaySettingsUpdate,
  type MarketDataSettingsUpdate,
  type NewsSettingsUpdate,
  type PlatformFeaturesUpdate,
  type RateLimitSettingsUpdate,
  type AlpacaPaperSnapshot
} from "@/lib/api";
import { PageHeader } from "@/components/Cards";
import { 
  WalletCards, Zap, BookOpen, Globe, Brain, Radar, Target, Users, 
  BrainCircuit, Gauge, BellRing, Activity, FlaskConical, ShieldCheck, 
  DatabaseZap, TrendingUp, LineChart, Bitcoin, BarChart3, ClipboardList,
  Settings as SettingsIcon, Activity as ActivityIcon
} from "lucide-react";

export default function SettingsPage() {
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [alpaca, setAlpaca] = useState<AlpacaPaperSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadSettings = () => {
    api.getSettings()
      .then(setSettings)
      .catch((err) => setError(err.message));
  };

  const loadAlpaca = () => {
    api.getAlpacaPaperSnapshot()
      .then(setAlpaca)
      .catch((err) => console.error("Failed to load Alpaca data:", err));
  };

  useEffect(() => {
    loadSettings();
    loadAlpaca();
  }, []);

  const updateTrading = async (updates: TradingSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ trading: updates });
      setSettings(updated);
      setMessage("Trading settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateLlmGateway = async (updates: LlmGatewaySettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ llm_gateway: updates });
      setSettings(updated);
      setMessage("LLM Gateway settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateMarketData = async (updates: MarketDataSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ market_data: updates });
      setSettings(updated);
      setMessage("Market Data settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateNews = async (updates: NewsSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ news: updates });
      setSettings(updated);
      setMessage("News settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updatePlatform = async (updates: PlatformFeaturesUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ platform: updates });
      setSettings(updated);
      setMessage("Platform settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateRateLimits = async (updates: RateLimitSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ rate_limits: updates });
      setSettings(updated);
      setMessage("Rate limits updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const resetSettings = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const updated = await api.resetSettings();
      setSettings(updated);
      setMessage("Settings reset to defaults");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset settings");
    } finally {
      setLoading(false);
    }
  };

  const ToggleSwitch = ({ 
    label, 
    description, 
    enabled, 
    onToggle, 
    danger = false,
    disabled = false
  }: { 
    label: string; 
    description: string; 
    enabled: boolean; 
    onToggle: () => void;
    danger?: boolean;
    disabled?: boolean;
  }) => (
    <div className={`rounded-xl border p-4 ${danger ? "border-red-800 bg-red-950/20" : "border-emerald-400/15 bg-black/35 backdrop-blur"} ${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className={`font-semibold ${danger ? "text-red-400" : "text-white"}`}>{label}</h3>
          <p className="text-sm text-slate-400">{description}</p>
        </div>
        <button
          onClick={onToggle}
          disabled={loading || disabled}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            enabled 
              ? danger ? "bg-red-600" : "bg-emerald-600"
              : "bg-slate-700"
          } ${loading ? "cursor-wait" : "cursor-pointer"}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );

  const NumberInput = ({
    label,
    description,
    value,
    onChange,
    min,
    max,
    step = 1
  }: {
    label: string;
    description: string;
    value: number;
    onChange: (val: number) => void;
    min?: number;
    max?: number;
    step?: number;
  }) => (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
      <div>
        <h3 className="font-semibold text-white">{label}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={loading}
        className="mt-3 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
      />
    </div>
  );

  const TextInput = ({
    label,
    description,
    value,
    onChange,
    placeholder
  }: {
    label: string;
    description: string;
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
  }) => (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
      <div>
        <h3 className="font-semibold text-white">{label}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={loading}
        className="mt-3 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
      />
    </div>
  );

  const SelectInput = ({
    label,
    description,
    value,
    onChange,
    options
  }: {
    label: string;
    description: string;
    value: string;
    onChange: (val: string) => void;
    options: { value: string; label: string }[];
  }) => (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
      <div>
        <h3 className="font-semibold text-white">{label}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="mt-3 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="Platform Configuration"
          title="Settings"
          description="Manage platform runtime settings. Values are saved to runtime_settings.json on the backend and drive trading gates, LLM policy, market data selection, and integrations. Live trading stays locked unless human approval is required."
        />

        {error && (
          <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-100">Dismiss</button>
          </div>
        )}

        {/* Tab-specific Settings Cards */}
        {settings && (
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {/* Account Risk Center Card */}
            <SettingsCard 
              title="Account Risk Center" 
              href="/account-risk" 
              icon={WalletCards}
              settings={[
                { label: "Paper Trading", enabled: settings.trading.paper_trading_enabled },
                { label: "Live Trading", enabled: settings.trading.live_trading_enabled },
                { label: "Broker Execution", enabled: settings.trading.broker_execution_enabled },
                { label: "Human Approval", enabled: settings.trading.require_human_approval },
              ]}
            />

            {/* TradeNow Card */}
            <SettingsCard 
              title="TradeNow" 
              href="/tradenow" 
              icon={Zap}
              settings={[
                { label: "Paper Trading", enabled: settings.trading.paper_trading_enabled },
                { label: "Live Trading", enabled: settings.trading.live_trading_enabled },
                { label: "Broker Execution", enabled: settings.trading.broker_execution_enabled },
                { label: "Execution Agent", enabled: settings.trading.execution_agent_enabled },
              ]}
            />

            {/* Trading & Market Data Card */}
            <SettingsCard 
              title="Trading & Market Data" 
              href="/paper-trading" 
              icon={TrendingUp}
              settings={[
                { label: "Paper Trading", enabled: settings.trading.paper_trading_enabled },
                { label: "Broker Execution", enabled: settings.trading.broker_execution_enabled },
                { label: "Alpaca Paper", enabled: settings.trading.alpaca_paper_trade },
                { label: "Market Data", enabled: settings.market_data.alpaca_market_data_enabled },
              ]}
            />

            {/* Strategies & Universe Card */}
            <SettingsCard 
              title="Strategies & Universe" 
              href="/strategies" 
              icon={Brain}
              settings={[
                { label: "Execution agent", enabled: settings.trading.execution_agent_enabled },
                { label: "Vector memory", enabled: settings.platform.vector_memory_enabled },
                { label: "LLM paid tests", enabled: settings.llm_gateway.llm_gateway_enable_paid_tests },
                { label: "LangSmith tracing", enabled: settings.platform.langsmith_tracing },
              ]}
            />

            {/* Signals & Recommendations Card */}
            <SettingsCard 
              title="Signals & Recommendations" 
              href="/signals" 
              icon={Radar}
              settings={[
                { label: "Alpaca market data", enabled: settings.market_data.alpaca_market_data_enabled },
                { label: "Execution agent", enabled: settings.trading.execution_agent_enabled },
                { label: "LLM paid tests", enabled: settings.llm_gateway.llm_gateway_enable_paid_tests },
                { label: "News provider", enabled: settings.news.news_provider_enabled },
              ]}
            />

            {/* AI & Models Card */}
            <SettingsCard 
              title="AI & Models" 
              href="/ai-ops" 
              icon={BrainCircuit}
              settings={[
                { label: "LLM paid tests", enabled: settings.llm_gateway.llm_gateway_enable_paid_tests },
                { label: "Embedding paid calls", enabled: settings.llm_gateway.embeddings_enable_paid_calls },
                { label: "Vector memory", enabled: settings.platform.vector_memory_enabled },
                { label: "LangSmith tracing", enabled: settings.platform.langsmith_tracing },
              ]}
            />

            {/* Data & Integrations Card */}
            <SettingsCard 
              title="Data & Integrations" 
              href="/data-sources" 
              icon={DatabaseZap}
              settings={[
                { label: "Alpaca market data", enabled: settings.market_data.alpaca_market_data_enabled },
                { label: "News provider", enabled: settings.news.news_provider_enabled },
                { label: "LLM paid tests", enabled: settings.llm_gateway.llm_gateway_enable_paid_tests },
                { label: "Vector memory", enabled: settings.platform.vector_memory_enabled },
              ]}
            />

            {/* Journal & Learning Card */}
            <SettingsCard 
              title="Journal & Learning" 
              href="/journal" 
              icon={BookOpen}
              settings={[
                { label: "Paper Trading", enabled: settings.trading.paper_trading_enabled },
                { label: "Execution Agent", enabled: settings.trading.execution_agent_enabled },
                { label: "Human Approval", enabled: settings.trading.require_human_approval },
                { label: "LangSmith Tracing", enabled: settings.platform.langsmith_tracing },
              ]}
            />
          </div>
        )}

        {message && (
          <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            {message}
            <button onClick={() => setMessage(null)} className="ml-2 text-emerald-300 hover:text-emerald-100">Dismiss</button>
          </div>
        )}

        {!settings ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading settings...</div>
        ) : (
          <div className="space-y-6">
            {/* Trading Settings */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <h2 className="mb-4 text-xl font-semibold text-emerald-400">Trading Configuration</h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ToggleSwitch
                  label="Paper Trading"
                  description="Enable Alpaca paper trading simulation"
                  enabled={settings.trading.paper_trading_enabled}
                  onToggle={() => updateTrading({ paper_trading_enabled: !settings.trading.paper_trading_enabled })}
                />
                <ToggleSwitch
                  label="Live Trading"
                  description="⚠️ Enable live trading with real money"
                  enabled={settings.trading.live_trading_enabled}
                  onToggle={() => updateTrading({ live_trading_enabled: !settings.trading.live_trading_enabled })}
                  danger
                  disabled={!settings.trading.require_human_approval}
                />
                <ToggleSwitch
                  label="Broker Execution"
                  description="Send orders to broker (Alpaca)"
                  enabled={settings.trading.broker_execution_enabled}
                  onToggle={() => updateTrading({ broker_execution_enabled: !settings.trading.broker_execution_enabled })}
                  danger={settings.trading.broker_execution_enabled}
                />
                <ToggleSwitch
                  label="Require Human Approval"
                  description="All trades require manual confirmation"
                  enabled={settings.trading.require_human_approval}
                  onToggle={() => updateTrading({ require_human_approval: !settings.trading.require_human_approval })}
                />
                <ToggleSwitch
                  label="Execution Agent"
                  description="Enable autonomous trade execution agent"
                  enabled={settings.trading.execution_agent_enabled}
                  onToggle={() => updateTrading({ execution_agent_enabled: !settings.trading.execution_agent_enabled })}
                  danger
                />
                <ToggleSwitch
                  label="Alpaca Paper Trade"
                  description="Use Alpaca paper trading environment"
                  enabled={settings.trading.alpaca_paper_trade}
                  onToggle={() => updateTrading({ alpaca_paper_trade: !settings.trading.alpaca_paper_trade })}
                />
              </div>
              
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <SelectInput
                  label="Execution Mode"
                  description="Current trading execution mode"
                  value={settings.trading.execution_mode}
                  onChange={(val) => updateTrading({ execution_mode: val })}
                  options={[
                    { value: "dry_run", label: "Dry Run (No orders)" },
                    { value: "paper", label: "Paper Trading" },
                    { value: "live", label: "Live Trading" }
                  ]}
                />
                <SelectInput
                  label="Broker Provider"
                  description="Primary broker for order execution"
                  value={settings.trading.broker_provider}
                  onChange={(val) => updateTrading({ broker_provider: val })}
                  options={[
                    { value: "alpaca", label: "Alpaca" },
                    { value: "interactive_brokers", label: "Interactive Brokers" },
                    { value: "td_ameritrade", label: "TD Ameritrade" }
                  ]}
                />
                <NumberInput
                  label="Paper Starting Cash"
                  description="Initial cash for paper trading account"
                  value={settings.trading.paper_starting_cash}
                  onChange={(val) => updateTrading({ paper_starting_cash: val })}
                  min={0}
                  step={1000}
                />
              </div>
            </section>

            {/* LLM Gateway Settings */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <h2 className="mb-4 text-xl font-semibold text-emerald-400">LLM Gateway</h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ToggleSwitch
                  label="Enable Paid Tests"
                  description="Allow paid LLM API calls for testing"
                  enabled={settings.llm_gateway.llm_gateway_enable_paid_tests}
                  onToggle={() => updateLlmGateway({ llm_gateway_enable_paid_tests: !settings.llm_gateway.llm_gateway_enable_paid_tests })}
                />
                <ToggleSwitch
                  label="Embeddings Paid Calls"
                  description="Enable paid embedding API calls"
                  enabled={settings.llm_gateway.embeddings_enable_paid_calls}
                  onToggle={() => updateLlmGateway({ embeddings_enable_paid_calls: !settings.llm_gateway.embeddings_enable_paid_calls })}
                />
              </div>
              
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <NumberInput
                  label="Daily Budget ($)"
                  description="Maximum daily spend on LLM APIs"
                  value={settings.llm_gateway.llm_gateway_daily_budget}
                  onChange={(val) => updateLlmGateway({ llm_gateway_daily_budget: val })}
                  min={0}
                  step={1}
                />
                <TextInput
                  label="Cheap Model"
                  description="Default cheap/fast model for simple tasks"
                  value={settings.llm_gateway.llm_gateway_default_cheap_model}
                  onChange={(val) => updateLlmGateway({ llm_gateway_default_cheap_model: val })}
                  placeholder="gpt-4o-mini"
                />
                <TextInput
                  label="Reasoning Model"
                  description="Default model for complex reasoning"
                  value={settings.llm_gateway.llm_gateway_default_reasoning_model}
                  onChange={(val) => updateLlmGateway({ llm_gateway_default_reasoning_model: val })}
                  placeholder="gpt-4o"
                />
                <TextInput
                  label="Fallback Model"
                  description="Fallback when primary models fail"
                  value={settings.llm_gateway.llm_gateway_default_fallback_model}
                  onChange={(val) => updateLlmGateway({ llm_gateway_default_fallback_model: val })}
                  placeholder="local-placeholder"
                />
              </div>
            </section>

            {/* Market Data Settings */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <h2 className="mb-4 text-xl font-semibold text-emerald-400">Market Data</h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ToggleSwitch
                  label="Alpaca Market Data"
                  description="Use Alpaca for market data feeds"
                  enabled={settings.market_data.alpaca_market_data_enabled}
                  onToggle={() => updateMarketData({ alpaca_market_data_enabled: !settings.market_data.alpaca_market_data_enabled })}
                />
              </div>
              
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <SelectInput
                  label="Market Data Provider"
                  description="Primary market data source"
                  value={settings.market_data.market_data_provider}
                  onChange={(val) => updateMarketData({ market_data_provider: val })}
                  options={[
                    { value: "mock", label: "Mock Data" },
                    { value: "alpaca", label: "Alpaca" },
                    { value: "polygon", label: "Polygon.io" },
                    { value: "yfinance", label: "YFinance" }
                  ]}
                />
                <TextInput
                  label="Provider Priority"
                  description="Fallback order (comma-separated)"
                  value={settings.market_data.market_data_provider_priority}
                  onChange={(val) => updateMarketData({ market_data_provider_priority: val })}
                  placeholder="alpaca,yfinance,mock"
                />
                <NumberInput
                  label="Timeout (seconds)"
                  description="API request timeout"
                  value={settings.market_data.market_data_provider_timeout_seconds}
                  onChange={(val) => updateMarketData({ market_data_provider_timeout_seconds: val })}
                  min={1}
                  max={60}
                />
              </div>
            </section>

            {/* News Settings */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <h2 className="mb-4 text-xl font-semibold text-emerald-400">News & Sentiment</h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ToggleSwitch
                  label="News Provider"
                  description="Enable news feed integration"
                  enabled={settings.news.news_provider_enabled}
                  onToggle={() => updateNews({ news_provider_enabled: !settings.news.news_provider_enabled })}
                />
              </div>
              
              <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <SelectInput
                  label="Primary News Source"
                  description="Main news data provider"
                  value={settings.news.news_provider_primary}
                  onChange={(val) => updateNews({ news_provider_primary: val })}
                  options={[
                    { value: "none", label: "None" },
                    { value: "newsapi", label: "NewsAPI" },
                    { value: "finnhub", label: "Finnhub" },
                    { value: "benzinga", label: "Benzinga" }
                  ]}
                />
                <NumberInput
                  label="Timeout (seconds)"
                  description="News API request timeout"
                  value={settings.news.news_provider_timeout_seconds}
                  onChange={(val) => updateNews({ news_provider_timeout_seconds: val })}
                  min={1}
                  max={60}
                />
              </div>
            </section>

            {/* Platform Features */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <h2 className="mb-4 text-xl font-semibold text-emerald-400">Platform Features</h2>
              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                <ToggleSwitch
                  label="LangSmith Tracing"
                  description="Send traces to LangSmith for debugging"
                  enabled={settings.platform.langsmith_tracing}
                  onToggle={() => updatePlatform({ langsmith_tracing: !settings.platform.langsmith_tracing })}
                />
                <ToggleSwitch
                  label="Vector Memory"
                  description="Enable pgvector-based memory storage"
                  enabled={settings.platform.vector_memory_enabled}
                  onToggle={() => updatePlatform({ vector_memory_enabled: !settings.platform.vector_memory_enabled })}
                />
              </div>
            </section>

            {/* Rate Limits */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <h2 className="mb-4 text-xl font-semibold text-emerald-400">Rate Limits & Safety</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
                <NumberInput
                  label="Max Daily LLM Cost ($)"
                  description="Daily spending limit on LLM APIs"
                  value={settings.rate_limits.max_daily_llm_cost}
                  onChange={(val) => updateRateLimits({ max_daily_llm_cost: val })}
                  min={0}
                  step={1}
                />
                <NumberInput
                  label="Max Daily Agent Runs"
                  description="Maximum agent executions per day"
                  value={settings.rate_limits.max_daily_agent_runs}
                  onChange={(val) => updateRateLimits({ max_daily_agent_runs: val })}
                  min={1}
                  step={10}
                />
              </div>
            </section>

            {/* Account Risk Center - Display Only with Alpaca Data */}
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <div className="mb-4 flex items-center justify-between">
                <h2 className="text-xl font-semibold text-emerald-400">Account Risk Center</h2>
                <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-300">
                  Alpaca Paper Account
                </span>
              </div>
              <p className="mb-4 text-sm text-slate-400">
                Live account data from Alpaca paper trading. This section is display-only; values are sourced directly from your Alpaca account.
              </p>
              
              {alpaca?.account ? (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
                  <div className="rounded-xl border border-emerald-400/15 bg-white/[0.03] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Buying Power</p>
                    <p className="mt-1 text-xl font-semibold text-emerald-400">
                      ${alpaca.account.buying_power?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}
                    </p>
                    <p className="text-xs text-slate-500">Available for trading</p>
                  </div>
                  <div className="rounded-xl border border-emerald-400/15 bg-white/[0.03] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Account Equity</p>
                    <p className="mt-1 text-xl font-semibold text-emerald-400">
                      ${alpaca.account.equity?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}
                    </p>
                    <p className="text-xs text-slate-500">Total portfolio value</p>
                  </div>
                  <div className="rounded-xl border border-emerald-400/15 bg-white/[0.03] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Cash</p>
                    <p className="mt-1 text-xl font-semibold text-emerald-400">
                      ${alpaca.account.cash?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}
                    </p>
                    <p className="text-xs text-slate-500">Unsettled cash</p>
                  </div>
                  <div className="rounded-xl border border-emerald-400/15 bg-white/[0.03] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">Portfolio Value</p>
                    <p className="mt-1 text-xl font-semibold text-emerald-400">
                      ${alpaca.account.portfolio_value?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}
                    </p>
                    <p className="text-xs text-slate-500">Positions + cash</p>
                  </div>
                </div>
              ) : (
                <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
                  <p className="text-sm">No Alpaca account data available. Please configure your Alpaca API keys in the backend .env file.</p>
                </div>
              )}
              
              {alpaca?.account && (
                <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4 text-sm">
                  <div className="rounded-lg border border-emerald-400/15 bg-white/[0.03] px-3 py-2">
                    <span className="text-slate-500">Account #:</span>
                    <span className="ml-2 text-slate-300 font-mono">{alpaca.account.account_number ?? "N/A"}</span>
                  </div>
                  <div className="rounded-lg border border-emerald-400/15 bg-white/[0.03] px-3 py-2">
                    <span className="text-slate-500">Status:</span>
                    <span className="ml-2 text-slate-300">{alpaca.account.status ?? "N/A"}</span>
                  </div>
                  <div className="rounded-lg border border-emerald-400/15 bg-white/[0.03] px-3 py-2">
                    <span className="text-slate-500">Day Trades:</span>
                    <span className="ml-2 text-slate-300">{alpaca.account.daytrade_count ?? 0}</span>
                  </div>
                  <div className="rounded-lg border border-emerald-400/15 bg-white/[0.03] px-3 py-2">
                    <span className="text-slate-500">PDT Status:</span>
                    <span className={`ml-2 ${alpaca.account.pattern_day_trader ? "text-amber-400" : "text-emerald-400"}`}>
                      {alpaca.account.pattern_day_trader ? "Flagged" : "Clear"}
                    </span>
                  </div>
                </div>
              )}
            </section>

            {/* Actions */}
            <section className="flex gap-4">
              <button
                onClick={resetSettings}
                disabled={loading}
                className="rounded-lg border border-white/15 bg-white/[0.06] px-4 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-50"
              >
                Reset to Defaults
              </button>
              <button
                onClick={loadSettings}
                disabled={loading}
                className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
              >
                Refresh Settings
              </button>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

// Settings Card Component for Tab-specific Settings Display
function SettingsCard({ 
  title, 
  href, 
  icon: Icon, 
  settings 
}: { 
  title: string; 
  href: string; 
  icon: typeof WalletCards; 
  settings: { label: string; enabled: boolean }[];
}) {
  return (
    <Link 
      href={href}
      className="group rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur transition hover:border-emerald-400/40 hover:bg-white/[0.05]"
    >
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-5 w-5 text-emerald-400" />
        <h3 className="font-semibold text-emerald-300">{title}</h3>
      </div>
      <div className="space-y-2">
        {settings.map((setting) => (
          <div key={setting.label} className="flex items-center justify-between text-sm">
            <span className="text-slate-400">{setting.label}</span>
            <span className={`flex items-center gap-1 ${setting.enabled ? "text-emerald-400" : "text-rose-400"}`}>
              {setting.enabled ? (
                <>
                  <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                  On
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                  Off
                </>
              )}
            </span>
          </div>
        ))}
      </div>
    </Link>
  );
}
