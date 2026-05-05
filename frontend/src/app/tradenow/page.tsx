"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { AlertTriangle, Bot, CheckCircle2, Play, Power, ShieldCheck, XCircle, Settings, Wallet } from "lucide-react";
import Link from "next/link";
import { MetricCard, PageHeader } from "@/components/Cards";
import { api, type AccountRiskProfile, type AlpacaPaperPosition, type AlpacaPaperSnapshot, type SettingsResponse } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8900";

type TradeTab = "stocks" | "options" | "etf" | "crypto";

const TAB_TO_ASSET: Record<TradeTab, "stock" | "option" | "etf" | "crypto"> = {
  stocks: "stock",
  options: "option",
  etf: "etf",
  crypto: "crypto",
};

const ETF_SYMBOLS = new Set([
  "SPY", "QQQ", "IWM", "DIA", "VOO", "VTI", "EFA", "EEM", "GLD", "SLV", "TLT", "HYG", "XLF", "XLE", "SMH", "ARKK", "SCHD", "VGT", "IVV", "IJH",
]);

function defaultSymbolForTab(tab: TradeTab): string {
  switch (tab) {
    case "crypto":
      return "BTC/USD";
    case "options":
      return "AAPL260116C00200000";
    case "etf":
      return "SPY";
    default:
      return "AAPL";
  }
}

/** Route Alpaca position rows into the same buckets as the trade tabs (best-effort without asset_class on position). */
function positionTab(symbol: string): TradeTab {
  const u = symbol.toUpperCase().trim();
  if (u.includes("/") || u.endsWith("USD")) return "crypto";
  if (/^[A-Z]{1,6}\d{6}[CP]\d{8}$/.test(u)) return "options";
  if (/^[A-Z]{1,5}\d+[CP]\d{3,}$/.test(u) && u.length >= 10) return "options";
  if (ETF_SYMBOLS.has(u)) return "etf";
  return "stocks";
}

type TradeNowConfig = {
  user_enabled: boolean;
  automatic_execution_user_enabled: boolean;
  execution_mode: "disabled" | "dry_run" | "paper" | "live";
  broker: string;
  paper_endpoint: string;
  live_endpoint: string;
  require_human_approval: boolean;
  live_trading_enabled_env: boolean;
  broker_execution_enabled_env: boolean;
  paper_trading_enabled_env: boolean;
  autonomous_execution_enabled_env: boolean;
  alpaca_keys_configured: boolean;
  alpaca_key_id_configured: boolean;
  alpaca_secret_key_configured: boolean;
  status: string;
  autonomous_status: string;
  blockers: string[];
  autonomous_blockers: string[];
  safety_notes: string[];
};

type TradeNowOrderResponse = {
  status: "blocked" | "dry_run" | "submitted" | "failed";
  execution_mode: string;
  order_id?: string | null;
  client_order_id: string;
  symbol: string;
  asset_class: "stock" | "etf" | "crypto" | "option";
  side: string;
  submitted_payload: Record<string, unknown>;
  broker_response?: Record<string, unknown> | null;
  request_id?: string | null;
  blockers: string[];
  warnings: string[];
  safety_notes: string[];
};

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

function StatusBadge({ value }: { value: string | boolean }) {
  const text = String(value);
  const positive = text === "true" || text.includes("ready") || text === "dry_run";
  const negative = text === "false" || text.includes("blocked") || text.includes("disabled") || text === "failed";
  return (
    <span
      className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${
        positive ? "border-emerald-500 bg-emerald-500/10 text-emerald-300" : negative ? "border-rose-500 bg-rose-500/10 text-rose-300" : "border-amber-500 bg-amber-500/10 text-amber-300"
      }`}
    >
      {text.replace(/_/g, " ")}
    </span>
  );
}

function EnvLine({ value }: { value: string }) {
  return <div className="rounded-lg border border-emerald-400/15 bg-black/40 px-2 py-1.5 font-mono text-[10px] text-slate-400">{value}</div>;
}

function SettingStatus({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div
      className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
        enabled ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" : "border-rose-500/30 bg-rose-500/10 text-rose-300"
      }`}
    >
      <span className="font-medium">{label}</span>
      <span className={`h-2 w-2 rounded-full ${enabled ? "bg-emerald-500" : "bg-rose-500"}`} />
    </div>
  );
}

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";

export default function TradeNowPage() {
  const [config, setConfig] = useState<TradeNowConfig | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [alpaca, setAlpaca] = useState<AlpacaPaperSnapshot | null>(null);
  const [riskProfile, setRiskProfile] = useState<AccountRiskProfile | null>(null);
  const [order, setOrder] = useState<TradeNowOrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TradeTab>("stocks");

  const [form, setForm] = useState({
    symbol: "AAPL",
    asset_class: "stock" as "stock" | "etf" | "crypto" | "option",
    side: "buy",
    qty: "1",
    limit_price: "",
    stop_price: "",
    type: "market",
    time_in_force: "day",
    dry_run: true,
    human_approval_confirmed: false,
  });

  const loadConfig = async () => {
    const next = await apiFetch<TradeNowConfig>("/api/tradenow/config");
    setConfig(next);
  };

  const loadSettings = async () => {
    const settingsData = await api.getSettings();
    setSettings(settingsData);
  };

  const loadAlpaca = useCallback(async () => {
    try {
      const snap = await api.getAlpacaPaperSnapshot();
      setAlpaca(snap);
    } catch {
      setAlpaca(null);
    }
  }, []);

  const loadRisk = useCallback(async () => {
    try {
      const p = await api.getAccountRisk();
      setRiskProfile(p);
    } catch {
      setRiskProfile(null);
    }
  }, []);

  useEffect(() => {
    loadConfig().catch((err) => setError(err.message));
    loadSettings().catch((err) => setError(err.message));
    loadAlpaca();
    loadRisk();
  }, [loadAlpaca, loadRisk]);

  const setTab = (tab: TradeTab) => {
    setActiveTab(tab);
    const ac = TAB_TO_ASSET[tab];
    setForm((f) => ({
      ...f,
      asset_class: ac,
      symbol: defaultSymbolForTab(tab),
      time_in_force: ac === "crypto" ? "gtc" : "day",
      type: ac === "option" && !["market", "limit"].includes(f.type) ? "limit" : f.type,
    }));
  };

  const updateConfig = async (patch: Partial<TradeNowConfig>) => {
    setSaving(true);
    setError(null);
    try {
      const next = await apiFetch<TradeNowConfig>("/api/tradenow/config", {
        method: "PUT",
        body: JSON.stringify({
          user_enabled: patch.user_enabled ?? config?.user_enabled ?? false,
          automatic_execution_user_enabled: patch.automatic_execution_user_enabled ?? config?.automatic_execution_user_enabled ?? false,
          execution_mode: patch.execution_mode ?? config?.execution_mode ?? "dry_run",
        }),
      });
      setConfig(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update TradeNow config");
    } finally {
      setSaving(false);
    }
  };

  const placeOrder = async () => {
    setSaving(true);
    setError(null);
    setOrder(null);
    try {
      const response = await apiFetch<TradeNowOrderResponse>("/api/tradenow/orders", {
        method: "POST",
        body: JSON.stringify({
          symbol: form.symbol,
          asset_class: form.asset_class,
          side: form.side,
          qty: Number(form.qty),
          type: form.type,
          time_in_force: form.time_in_force,
          limit_price: form.limit_price ? Number(form.limit_price) : null,
          stop_price: form.stop_price ? Number(form.stop_price) : null,
          dry_run: form.dry_run,
          human_approval_confirmed: form.human_approval_confirmed,
          approval_source: "human",
        }),
      });
      setOrder(response);
      await loadConfig();
      await loadAlpaca();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Order request failed");
    } finally {
      setSaving(false);
    }
  };

  const positions = alpaca?.positions ?? [];
  const tabPositions = useMemo(() => positions.filter((p) => positionTab(p.symbol) === activeTab), [positions, activeTab]);

  const tabHint = useMemo(() => {
    switch (activeTab) {
      case "crypto":
        return "Crypto uses slash pairs (e.g. BTC/USD), GTC/IOC, and fractional qty where supported.";
      case "options":
        return "Options use OCC symbols. Alpaca paper supports market/limit; stops may be limited — check blockers after submit.";
      case "etf":
        return "ETFs trade like equities on Alpaca; use standard stock-style day/GTC and share qty.";
      default:
        return "Equities: standard symbols, day session defaults, and share qty.";
    }
  }, [activeTab]);

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1500px] space-y-4">
        <PageHeader
          eyebrow="execution foundation"
          title="TradeNow"
          description="Alpaca execution adapter with dry-run default, paper endpoint support, human approval, env-only credentials, and live trading disabled unless explicitly enabled later."
        />

        {error && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

        {settings && (
          <section className={cardShell}>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings className="h-5 w-5 text-emerald-300" />
                <h2 className="text-lg font-black text-white">Settings routing to TradeNow</h2>
              </div>
              <Link href="/settings" className="text-sm text-emerald-400 underline hover:text-emerald-300">
                Edit in Settings →
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
              <SettingStatus label="Paper Trading" enabled={settings.trading.paper_trading_enabled} />
              <SettingStatus label="Live Trading" enabled={settings.trading.live_trading_enabled} />
              <SettingStatus label="Broker Execution" enabled={settings.trading.broker_execution_enabled} />
              <SettingStatus label="Human Approval" enabled={settings.trading.require_human_approval} />
              <SettingStatus label="Execution Agent" enabled={settings.trading.execution_agent_enabled} />
              <SettingStatus label="Alpaca Paper" enabled={settings.trading.alpaca_paper_trade} />
            </div>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded border border-emerald-400/20 bg-black/30 px-2 py-1 text-slate-400">
                Mode: <span className="text-emerald-400">{settings.trading.execution_mode}</span>
              </span>
              <span className="rounded border border-emerald-400/20 bg-black/30 px-2 py-1 text-slate-400">
                Broker: <span className="text-emerald-400">{settings.trading.broker_provider}</span>
              </span>
            </div>
          </section>
        )}

        {/* Portfolio snapshot (Alpaca + risk profile, similar to Account Risk Center) */}
        <section className={cardShell}>
          <div className="mb-3 flex items-center gap-2">
            <Wallet className="h-5 w-5 text-emerald-300" />
            <h2 className="text-lg font-black text-white">Current portfolio</h2>
            <Link href="/account-risk" className="ml-auto text-xs text-emerald-400/90 underline hover:text-emerald-300">
              Open Account Risk Center →
            </Link>
          </div>
          {alpaca?.account ? (
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <MetricCard
                label="Buying power"
                value={`$${alpaca.account.buying_power?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`}
                accent
              />
              <MetricCard
                label="Account equity"
                value={`$${alpaca.account.equity?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`}
              />
              <MetricCard
                label="Max risk / trade"
                value={riskProfile != null ? `${riskProfile.max_risk_per_trade_percent}%` : "—"}
              />
              <MetricCard
                label="Day trades / PDT"
                value={`${alpaca.account.daytrade_count ?? 0} / ${alpaca.account.pattern_day_trader ? "flagged" : "clear"}`}
              />
            </div>
          ) : (
            <p className="text-sm text-slate-400">
              {alpaca?.message ?? "Connect Alpaca paper keys in backend `.env` to load buying power and risk context."}
            </p>
          )}
        </section>

        {/* Compact execution configuration */}
        <section className={`${cardShell} p-3`}>
          <h3 className="mb-2 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">Execution configuration</h3>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div className="rounded-xl border border-emerald-400/10 bg-black/25 p-3">
              <div className="mb-2 flex items-center gap-2">
                <Power className="h-4 w-4 text-emerald-300" />
                <span className="text-xs font-bold text-white">Manual</span>
              </div>
              {config ? (
                <div className="space-y-2 text-[11px] text-slate-300">
                  <div className="flex flex-wrap gap-1">
                    <StatusBadge value={config.status} />
                    <StatusBadge value={config.execution_mode} />
                  </div>
                  <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2 py-1.5">
                    <span>UI enabled</span>
                    <input type="checkbox" checked={config.user_enabled} onChange={(e) => updateConfig({ user_enabled: e.target.checked })} />
                  </label>
                  <select
                    className="w-full rounded-lg border border-emerald-400/20 bg-black/40 px-2 py-1 text-[11px] text-white"
                    value={config.execution_mode}
                    onChange={(e) => updateConfig({ execution_mode: e.target.value as TradeNowConfig["execution_mode"] })}
                    disabled={saving}
                  >
                    <option value="dry_run">Dry run</option>
                    <option value="paper">Paper</option>
                    <option value="live">Live (gated)</option>
                    <option value="disabled">Disabled</option>
                  </select>
                  <div className="space-y-1 border-t border-white/10 pt-2">
                    <div className="flex justify-between"><span className="text-slate-500">Broker env</span><StatusBadge value={config.broker_execution_enabled_env} /></div>
                    <div className="flex justify-between"><span className="text-slate-500">Paper env</span><StatusBadge value={config.paper_trading_enabled_env} /></div>
                    <div className="flex justify-between"><span className="text-slate-500">Human approval</span><StatusBadge value={config.require_human_approval} /></div>
                  </div>
                </div>
              ) : (
                <p className="text-[11px] text-slate-500">Loading…</p>
              )}
            </div>

            <div className="rounded-xl border border-emerald-400/10 bg-black/25 p-3">
              <div className="mb-2 flex items-center gap-2">
                <Bot className="h-4 w-4 text-cyan-300" />
                <span className="text-xs font-bold text-white">Automatic</span>
              </div>
              {config ? (
                <div className="space-y-2 text-[11px] text-slate-300">
                  <div className="flex flex-wrap gap-1">
                    <StatusBadge value={config.autonomous_status} />
                    <StatusBadge value={`auto_env_${config.autonomous_execution_enabled_env}`} />
                  </div>
                  <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-white/[0.03] px-2 py-1.5">
                    <span>Auto paper (future)</span>
                    <input
                      type="checkbox"
                      checked={config.automatic_execution_user_enabled}
                      onChange={(e) => updateConfig({ automatic_execution_user_enabled: e.target.checked })}
                    />
                  </label>
                  <p className="leading-snug text-slate-500">Requires autonomous env + gates. See Safety for blockers.</p>
                  {config.autonomous_blockers?.length ? (
                    <ul className="max-h-24 space-y-1 overflow-y-auto text-amber-200/90">
                      {config.autonomous_blockers.slice(0, 4).map((b) => (
                        <li key={b} className="rounded border border-amber-500/20 bg-amber-500/5 px-2 py-1">
                          {b}
                        </li>
                      ))}
                    </ul>
                  ) : null}
                </div>
              ) : (
                <p className="text-[11px] text-slate-500">Loading…</p>
              )}
            </div>

            <div className="rounded-xl border border-amber-500/25 bg-black/25 p-3">
              <div className="mb-2 flex items-center gap-2">
                <ShieldCheck className="h-4 w-4 text-amber-300" />
                <span className="text-xs font-bold text-white">Safety</span>
              </div>
              {config?.blockers?.length ? (
                <ul className="mb-2 max-h-28 space-y-1 overflow-y-auto text-[11px] text-amber-200">
                  {config.blockers.map((blocker) => (
                    <li key={blocker} className="rounded border border-amber-500/25 bg-amber-500/5 px-2 py-1">
                      {blocker}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mb-2 text-[11px] text-emerald-200/90">No blockers for current mode.</p>
              )}
              <div className="border-t border-white/10 pt-2">
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-slate-500">Env reference</p>
                <div className="space-y-1">
                  <EnvLine value="ALPACA_API_KEY / ALPACA_SECRET_KEY" />
                  <EnvLine value="BROKER_EXECUTION_ENABLED / LIVE_TRADING_ENABLED" />
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Asset-class tabs */}
        <div className="flex flex-wrap gap-2 border-b border-emerald-400/15 pb-2">
          {(
            [
              ["stocks", "Stocks"],
              ["options", "Options"],
              ["etf", "ETF"],
              ["crypto", "Crypto"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`rounded-xl px-4 py-2 text-sm font-semibold transition ${
                activeTab === id
                  ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                  : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <p className="text-xs leading-relaxed text-slate-400">{tabHint}</p>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className={cardShell}>
            <h2 className="mb-3 text-lg font-black text-white">Manual order ticket</h2>
            <div className="mb-3 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs leading-relaxed text-emerald-100/90">
              Active class: <span className="font-bold uppercase text-emerald-300">{activeTab}</span>. Paper submission needs paper mode, broker env, dry-run off, and human approval when required.
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-300">
                Symbol
                <input
                  value={form.symbol}
                  onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                />
              </label>
              <label className="text-sm text-slate-300">
                Side
                <select
                  value={form.side}
                  onChange={(e) => setForm({ ...form, side: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                >
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </select>
              </label>
              <label className="text-sm text-slate-300">
                Quantity
                <input
                  value={form.qty}
                  onChange={(e) => setForm({ ...form, qty: e.target.value })}
                  type="number"
                  min="0"
                  step="0.0001"
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                />
              </label>
              <label className="text-sm text-slate-300">
                Order type
                <select
                  value={form.type}
                  onChange={(e) => setForm({ ...form, type: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                >
                  <option value="market">Market</option>
                  <option value="limit">Limit</option>
                  {form.asset_class !== "option" ? <option value="stop">Stop</option> : null}
                  {form.asset_class !== "option" ? <option value="stop_limit">Stop limit</option> : null}
                </select>
              </label>
              <label className="text-sm text-slate-300">
                Time in force
                <select
                  value={form.time_in_force}
                  onChange={(e) => setForm({ ...form, time_in_force: e.target.value })}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                >
                  {form.asset_class === "crypto" ? (
                    <>
                      <option value="gtc">GTC</option>
                      <option value="ioc">IOC</option>
                    </>
                  ) : (
                    <>
                      <option value="day">Day</option>
                      <option value="gtc">GTC</option>
                      <option value="opg">OPG</option>
                      <option value="cls">CLS</option>
                      <option value="ioc">IOC</option>
                      <option value="fok">FOK</option>
                    </>
                  )}
                </select>
              </label>
              <label className="text-sm text-slate-300">
                Limit price
                <input
                  value={form.limit_price}
                  onChange={(e) => setForm({ ...form, limit_price: e.target.value })}
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="For limit"
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white"
                />
              </label>
              <label className="text-sm text-slate-300">
                Stop price
                <input
                  value={form.stop_price}
                  onChange={(e) => setForm({ ...form, stop_price: e.target.value })}
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="For stop"
                  disabled={form.asset_class === "option"}
                  className="mt-1 w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-white disabled:opacity-50"
                />
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-300">
                <input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} />
                Dry run
              </label>
              <label className="flex items-center gap-2 rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">
                <input
                  type="checkbox"
                  checked={form.human_approval_confirmed}
                  onChange={(e) => setForm({ ...form, human_approval_confirmed: e.target.checked })}
                />
                Human approval
              </label>
            </div>
            <button
              onClick={placeOrder}
              disabled={saving}
              className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-bold uppercase text-emerald-300 hover:bg-emerald-500 hover:text-slate-950 disabled:opacity-50"
            >
              <Play className="h-4 w-4" /> Submit order
            </button>
          </div>

          <div className={cardShell}>
            <h2 className="mb-3 text-lg font-black text-white">Last order response</h2>
            {order ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={order.status} />
                  <StatusBadge value={order.execution_mode} />
                  <StatusBadge value={order.asset_class} />
                </div>
                {order.status === "submitted" ? (
                  <p className="flex items-center gap-2 text-sm text-emerald-300">
                    <CheckCircle2 className="h-4 w-4" /> Submitted to broker.
                  </p>
                ) : null}
                {order.status === "blocked" || order.status === "failed" ? (
                  <p className="flex items-center gap-2 text-sm text-rose-300">
                    <XCircle className="h-4 w-4" /> Not submitted.
                  </p>
                ) : null}
                {order.status === "dry_run" ? (
                  <p className="flex items-center gap-2 text-sm text-cyan-300">
                    <AlertTriangle className="h-4 w-4" /> Dry run only.
                  </p>
                ) : null}
                {order.request_id ? (
                  <p className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 font-mono text-[11px] text-cyan-200">X-Request-ID: {order.request_id}</p>
                ) : null}
                {order.blockers?.length ? (
                  <ul className="space-y-2 text-sm text-amber-200">
                    {order.blockers.map((b) => (
                      <li key={b} className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">
                        {b}
                      </li>
                    ))}
                  </ul>
                ) : null}
                <pre className="max-h-72 overflow-auto rounded-xl border border-emerald-400/15 bg-black/50 p-3 text-[11px] text-slate-300">{JSON.stringify(order, null, 2)}</pre>
              </div>
            ) : (
              <p className="text-sm text-slate-400">No order submitted yet for this session.</p>
            )}
          </div>
        </section>

        <section className={cardShell}>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-black text-white">Current holdings</h2>
            <span className="text-xs text-slate-500">
              {tabPositions.length} in {activeTab} (best-effort filter)
            </span>
          </div>
          {tabPositions.length === 0 ? (
            <p className="text-sm text-slate-400">No open positions classified as {activeTab} in this paper account.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-emerald-400/15">
              <table className="w-full min-w-[640px] text-left text-sm">
                <thead className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-emerald-400">
                  <tr>
                    <th className="px-3 py-2">Symbol</th>
                    <th className="px-3 py-2">Qty</th>
                    <th className="px-3 py-2">Market value</th>
                    <th className="px-3 py-2">Unrealized P/L</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-950/40">
                  {tabPositions.map((p: AlpacaPaperPosition) => (
                    <tr key={p.symbol} className="hover:bg-white/[0.03]">
                      <td className="px-3 py-2 font-mono text-white">{p.symbol}</td>
                      <td className="px-3 py-2 text-slate-300">{p.qty ?? "—"}</td>
                      <td className="px-3 py-2 text-slate-300">
                        {p.market_value != null ? `$${p.market_value.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-300">
                        {p.unrealized_pl != null ? `$${p.unrealized_pl.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
