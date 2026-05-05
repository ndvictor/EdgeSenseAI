"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Bot, CheckCircle2, Play, Power, ShieldCheck, XCircle, Settings } from "lucide-react";
import Link from "next/link";
import { PageHeader } from "@/components/Cards";
import { api, type SettingsResponse } from "@/lib/api";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8900";

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
    <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${positive ? "border-emerald-500 bg-emerald-500/10 text-emerald-300" : negative ? "border-rose-500 bg-rose-500/10 text-rose-300" : "border-amber-500 bg-amber-500/10 text-amber-300"}`}>
      {text.replace(/_/g, " ")}
    </span>
  );
}

function EnvLine({ value }: { value: string }) {
  return <div className="rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400">{value}</div>;
}

function SettingStatus({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className={`flex items-center justify-between rounded-lg border px-3 py-2 text-sm ${
      enabled 
        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-300" 
        : "border-rose-500/30 bg-rose-500/10 text-rose-300"
    }`}>
      <span className="font-medium">{label}</span>
      <span className={`h-2 w-2 rounded-full ${enabled ? "bg-emerald-500" : "bg-rose-500"}`} />
    </div>
  );
}

export default function TradeNowPage() {
  const [config, setConfig] = useState<TradeNowConfig | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [order, setOrder] = useState<TradeNowOrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
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

  useEffect(() => {
    loadConfig().catch((err) => setError(err.message));
    loadSettings().catch((err) => setError(err.message));
  }, []);

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
    } catch (err) {
      setError(err instanceof Error ? err.message : "Order request failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1500px] space-y-4">
        <PageHeader
          eyebrow="execution foundation"
          title="TradeNow"
          description="Alpaca execution adapter with dry-run default, paper endpoint support, human approval, env-only credentials, and live trading disabled unless explicitly enabled later."
        />

        {error && <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}

        {/* Settings Status Panel */}
        {settings && (
          <section className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Settings className="h-5 w-5 text-emerald-300" />
                <h2 className="text-lg font-black text-white">Settings Routing to TradeNow</h2>
              </div>
              <Link href="/settings" className="text-sm text-emerald-400 hover:text-emerald-300 underline">
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
              <span className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-400">
                Mode: <span className="text-emerald-400">{settings.trading.execution_mode}</span>
              </span>
              <span className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-slate-400">
                Broker: <span className="text-emerald-400">{settings.trading.broker_provider}</span>
              </span>
            </div>
          </section>
        )}

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-4 flex items-center gap-3">
              <Power className="h-5 w-5 text-emerald-300" />
              <h2 className="text-lg font-black text-white">Manual Execution Control</h2>
            </div>
            {config ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={config.status} />
                  <StatusBadge value={config.execution_mode} />
                  <StatusBadge value={`keys_${config.alpaca_keys_configured}`} />
                </div>
                <label className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
                  <span className="text-sm font-semibold text-slate-200">Manual TradeNow UI Toggle</span>
                  <input type="checkbox" checked={config.user_enabled} onChange={(e) => updateConfig({ user_enabled: e.target.checked })} />
                </label>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-500">Manual Execution Mode</label>
                  <select
                    className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white"
                    value={config.execution_mode}
                    onChange={(e) => updateConfig({ execution_mode: e.target.value as TradeNowConfig["execution_mode"] })}
                    disabled={saving}
                  >
                    <option value="dry_run">Dry Run</option>
                    <option value="paper">Alpaca Paper</option>
                    <option value="live">Live, blocked unless env enabled</option>
                    <option value="disabled">Disabled</option>
                  </select>
                </div>
                <div className="grid grid-cols-1 gap-2 text-sm text-slate-300">
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Broker execution env</span><StatusBadge value={config.broker_execution_enabled_env} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Paper env</span><StatusBadge value={config.paper_trading_enabled_env} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Live env</span><StatusBadge value={config.live_trading_enabled_env} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Human approval</span><StatusBadge value={config.require_human_approval} /></div>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-400">Loading config...</p>
            )}
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-4 flex items-center gap-3">
              <Bot className="h-5 w-5 text-cyan-300" />
              <h2 className="text-lg font-black text-white">Automatic Execution Control</h2>
            </div>
            {config ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={config.autonomous_status} />
                  <StatusBadge value={`auto_env_${config.autonomous_execution_enabled_env}`} />
                </div>
                <p className="text-sm leading-relaxed text-slate-300">
                  Future scanner/orchestrator-to-broker execution is separated from manual order tickets. It can be staged for Alpaca paper once backend env flags, risk gates, execution readiness, and human approval metadata are all present.
                </p>
                <label className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
                  <span className="text-sm font-semibold text-slate-200">Future automatic paper execution toggle</span>
                  <input type="checkbox" checked={config.automatic_execution_user_enabled} onChange={(e) => updateConfig({ automatic_execution_user_enabled: e.target.checked })} />
                </label>
                <div className="grid grid-cols-1 gap-2 text-sm text-slate-300">
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Automatic UI toggle</span><StatusBadge value={config.automatic_execution_user_enabled} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Autonomous env</span><StatusBadge value={config.autonomous_execution_enabled_env} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Broker submission env</span><StatusBadge value={config.broker_execution_enabled_env} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Live env</span><StatusBadge value={config.live_trading_enabled_env} /></div>
                  <div className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 px-3 py-2"><span>Human approval required</span><StatusBadge value={config.require_human_approval} /></div>
                </div>
                <div className="rounded-xl border border-cyan-500/20 bg-cyan-500/10 px-3 py-2 text-xs leading-relaxed text-cyan-100">
                  This toggle is only one gate. Automatic paper orders still require AUTONOMOUS_EXECUTION_ENABLED=true, BROKER_EXECUTION_ENABLED=true, Paper mode, risk gate, execution readiness, and human approval metadata.
                </div>
                {config.autonomous_blockers?.length ? (
                  <ul className="space-y-2 text-sm text-amber-200">
                    {config.autonomous_blockers.map((blocker) => <li key={blocker} className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">{blocker}</li>)}
                  </ul>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-slate-400">Loading config...</p>
            )}
          </div>

          <div className="rounded-2xl border border-amber-500/40 bg-slate-950 p-4">
            <div className="mb-4 flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-amber-300" />
              <h2 className="text-lg font-black text-white">Safety Blockers</h2>
            </div>
            {config?.blockers?.length ? (
              <ul className="space-y-2 text-sm text-amber-200">
                {config.blockers.map((blocker) => <li key={blocker} className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">{blocker}</li>)}
              </ul>
            ) : (
              <p className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-200">No current blockers for selected mode.</p>
            )}
            <div className="mt-4 border-t border-slate-800 pt-4">
              <h3 className="mb-2 text-sm font-black uppercase tracking-wide text-white">Backend Alpaca credential notes</h3>
              <p className="mb-3 text-xs leading-relaxed text-slate-300">
                Add keys only to backend `.env`. The browser does not store Alpaca keys. The backend currently accepts these variable names.
              </p>
              <div className="space-y-2">
                <EnvLine value="ALPACA_API_KEY=your_key_id_here" />
                <EnvLine value="ALPACA_SECRET_KEY=your_secret_key_here" />
                <EnvLine value="ALPACA_PAPER_TRADING_BASE_URL=https://paper-api.alpaca.markets" />
                <EnvLine value="BROKER_EXECUTION_ENABLED=false" />
                <EnvLine value="LIVE_TRADING_ENABLED=false" />
              </div>
            </div>
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <h2 className="mb-4 text-lg font-black text-white">Manual Order Ticket</h2>
            <div className="mb-4 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs leading-relaxed text-emerald-100">
              Alpaca paper ticket supports stocks, ETFs, crypto, and options. Submission requires Paper mode, broker env enabled, dry-run unchecked, and the human approval checkbox.
            </div>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-300">Asset Class<select value={form.asset_class} onChange={(e) => {
                const assetClass = e.target.value as typeof form.asset_class;
                setForm({
                  ...form,
                  asset_class: assetClass,
                  symbol: assetClass === "crypto" ? "BTC/USD" : assetClass === "etf" ? "SPY" : assetClass === "option" ? "AAPL260116C00200000" : "AAPL",
                  time_in_force: assetClass === "crypto" ? "gtc" : "day",
                  type: assetClass === "option" && !["market", "limit"].includes(form.type) ? "limit" : form.type,
                });
              }} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"><option value="stock">Stock</option><option value="etf">ETF</option><option value="crypto">Crypto</option><option value="option">Option Contract</option></select></label>
              <label className="text-sm text-slate-300">Symbol<input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white" /></label>
              <label className="text-sm text-slate-300">Side<select value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
              <label className="text-sm text-slate-300">Quantity<input value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} type="number" min="0" step="0.0001" className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white" /></label>
              <label className="text-sm text-slate-300">Order Type<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"><option value="market">Market</option><option value="limit">Limit</option>{form.asset_class !== "option" ? <option value="stop">Stop</option> : null}{form.asset_class !== "option" ? <option value="stop_limit">Stop Limit</option> : null}</select></label>
              <label className="text-sm text-slate-300">Time in Force<select value={form.time_in_force} onChange={(e) => setForm({ ...form, time_in_force: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white">{form.asset_class === "crypto" ? <><option value="gtc">GTC</option><option value="ioc">IOC</option></> : <><option value="day">Day</option><option value="gtc">GTC</option><option value="opg">OPG</option><option value="cls">CLS</option><option value="ioc">IOC</option><option value="fok">FOK</option></>}</select></label>
              <label className="text-sm text-slate-300">Limit Price<input value={form.limit_price} onChange={(e) => setForm({ ...form, limit_price: e.target.value })} type="number" min="0" step="0.01" placeholder="Required for limit" className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white" /></label>
              <label className="text-sm text-slate-300">Stop Price<input value={form.stop_price} onChange={(e) => setForm({ ...form, stop_price: e.target.value })} type="number" min="0" step="0.01" placeholder="Required for stop" disabled={form.asset_class === "option"} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white disabled:opacity-50" /></label>
              <label className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300"><input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} /> Dry run this request</label>
              <label className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200"><input type="checkbox" checked={form.human_approval_confirmed} onChange={(e) => setForm({ ...form, human_approval_confirmed: e.target.checked })} /> Human approval: I approve this paper request</label>
            </div>
            <button onClick={placeOrder} disabled={saving} className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold uppercase text-emerald-300 hover:bg-emerald-500 hover:text-slate-950 disabled:opacity-50">
              <Play className="h-4 w-4" /> Submit Order Request
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <h2 className="mb-4 text-lg font-black text-white">Latest Order Response</h2>
            {order ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2"><StatusBadge value={order.status} /><StatusBadge value={order.execution_mode} /><StatusBadge value={order.asset_class} /></div>
                {order.status === "submitted" ? <p className="flex items-center gap-2 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Submitted to broker.</p> : null}
                {order.status === "blocked" || order.status === "failed" ? <p className="flex items-center gap-2 text-sm text-rose-300"><XCircle className="h-4 w-4" /> Request did not submit to broker.</p> : null}
                {order.status === "dry_run" ? <p className="flex items-center gap-2 text-sm text-cyan-300"><AlertTriangle className="h-4 w-4" /> Dry run only. No broker call was made.</p> : null}
                {order.request_id ? <p className="rounded-lg border border-cyan-500/30 bg-cyan-500/10 px-3 py-2 text-xs font-mono text-cyan-200">Alpaca X-Request-ID: {order.request_id}</p> : null}
                {order.blockers?.length ? <ul className="space-y-2 text-sm text-amber-200">{order.blockers.map((b) => <li key={b} className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2">{b}</li>)}</ul> : null}
                <pre className="max-h-96 overflow-auto rounded-xl border border-slate-800 bg-slate-900 p-3 text-xs text-slate-300">{JSON.stringify(order, null, 2)}</pre>
              </div>
            ) : (
              <p className="text-sm text-slate-400">No order request submitted yet.</p>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
