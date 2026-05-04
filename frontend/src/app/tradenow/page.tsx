"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, KeyRound, Play, Power, ShieldCheck, XCircle } from "lucide-react";
import { PageHeader } from "@/components/Cards";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8900";

type TradeNowConfig = {
  user_enabled: boolean;
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
  blockers: string[];
  safety_notes: string[];
};

type TradeNowOrderResponse = {
  status: "blocked" | "dry_run" | "submitted" | "failed";
  execution_mode: string;
  order_id?: string | null;
  client_order_id: string;
  symbol: string;
  side: string;
  submitted_payload: Record<string, unknown>;
  broker_response?: Record<string, unknown> | null;
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

export default function TradeNowPage() {
  const [config, setConfig] = useState<TradeNowConfig | null>(null);
  const [order, setOrder] = useState<TradeNowOrderResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    symbol: "AAPL",
    side: "buy",
    qty: "1",
    type: "market",
    time_in_force: "day",
    dry_run: true,
    human_approval_confirmed: false,
  });

  const loadConfig = async () => {
    const next = await apiFetch<TradeNowConfig>("/api/tradenow/config");
    setConfig(next);
  };

  useEffect(() => {
    loadConfig().catch((err) => setError(err.message));
  }, []);

  const updateConfig = async (patch: Partial<TradeNowConfig>) => {
    setSaving(true);
    setError(null);
    try {
      const next = await apiFetch<TradeNowConfig>("/api/tradenow/config", {
        method: "PUT",
        body: JSON.stringify({
          user_enabled: patch.user_enabled ?? config?.user_enabled ?? false,
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
          side: form.side,
          qty: Number(form.qty),
          type: form.type,
          time_in_force: form.time_in_force,
          dry_run: form.dry_run,
          human_approval_confirmed: form.human_approval_confirmed,
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

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-4 flex items-center gap-3">
              <Power className="h-5 w-5 text-emerald-300" />
              <h2 className="text-lg font-black text-white">Execution Control</h2>
            </div>
            {config ? (
              <div className="space-y-4">
                <div className="flex flex-wrap gap-2">
                  <StatusBadge value={config.status} />
                  <StatusBadge value={config.execution_mode} />
                  <StatusBadge value={`keys_${config.alpaca_keys_configured}`} />
                </div>
                <label className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-900 px-4 py-3">
                  <span className="text-sm font-semibold text-slate-200">TradeNow UI Toggle</span>
                  <input type="checkbox" checked={config.user_enabled} onChange={(e) => updateConfig({ user_enabled: e.target.checked })} />
                </label>
                <div>
                  <label className="text-xs font-bold uppercase text-slate-500">Execution Mode</label>
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
              <KeyRound className="h-5 w-5 text-cyan-300" />
              <h2 className="text-lg font-black text-white">Alpaca API Keys</h2>
            </div>
            <p className="mb-4 text-sm leading-relaxed text-slate-300">
              Add these to the backend `.env` when ready. Keys are not stored from the browser.
            </p>
            <div className="space-y-3">
              <input readOnly value="ALPACA_API_KEY=your_key_id_here" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400" />
              <input readOnly value="ALPACA_SECRET_KEY=your_secret_key_here" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400" />
              <input readOnly value="BROKER_EXECUTION_ENABLED=false" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400" />
              <input readOnly value="LIVE_TRADING_ENABLED=false" className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs text-slate-400" />
            </div>
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
          </div>
        </section>

        <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <h2 className="mb-4 text-lg font-black text-white">Manual Order Ticket</h2>
            <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-300">Symbol<input value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value.toUpperCase() })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white" /></label>
              <label className="text-sm text-slate-300">Side<select value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"><option value="buy">Buy</option><option value="sell">Sell</option></select></label>
              <label className="text-sm text-slate-300">Quantity<input value={form.qty} onChange={(e) => setForm({ ...form, qty: e.target.value })} type="number" min="0" step="0.0001" className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white" /></label>
              <label className="text-sm text-slate-300">Order Type<select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-2 text-white"><option value="market">Market</option><option value="limit">Limit</option><option value="stop">Stop</option><option value="stop_limit">Stop Limit</option></select></label>
              <label className="flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-300"><input type="checkbox" checked={form.dry_run} onChange={(e) => setForm({ ...form, dry_run: e.target.checked })} /> Dry run this request</label>
              <label className="flex items-center gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-sm text-amber-200"><input type="checkbox" checked={form.human_approval_confirmed} onChange={(e) => setForm({ ...form, human_approval_confirmed: e.target.checked })} /> I approve this request</label>
            </div>
            <button onClick={placeOrder} disabled={saving} className="mt-4 flex items-center gap-2 rounded-xl border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold uppercase text-emerald-300 hover:bg-emerald-500 hover:text-slate-950 disabled:opacity-50">
              <Play className="h-4 w-4" /> Submit Order Request
            </button>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <h2 className="mb-4 text-lg font-black text-white">Latest Order Response</h2>
            {order ? (
              <div className="space-y-3">
                <div className="flex flex-wrap gap-2"><StatusBadge value={order.status} /><StatusBadge value={order.execution_mode} /></div>
                {order.status === "submitted" ? <p className="flex items-center gap-2 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" /> Submitted to broker.</p> : null}
                {order.status === "blocked" || order.status === "failed" ? <p className="flex items-center gap-2 text-sm text-rose-300"><XCircle className="h-4 w-4" /> Request did not submit to broker.</p> : null}
                {order.status === "dry_run" ? <p className="flex items-center gap-2 text-sm text-cyan-300"><AlertTriangle className="h-4 w-4" /> Dry run only. No broker call was made.</p> : null}
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
