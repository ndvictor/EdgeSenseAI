"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  type SettingsResponse,
  type TradingSettingsUpdate,
  type MarketDataSettingsUpdate,
  type PlatformFeaturesUpdate,
  type NewsSettingsUpdate,
} from "@/lib/api";

type Props = {
  settings: SettingsResponse | null;
  bundleLoading: boolean;
  onAfterSave: () => void | Promise<void>;
};

export function OwnerRuntimeSettingsPanel({ settings, bundleLoading, onAfterSave }: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [priorityDraft, setPriorityDraft] = useState("");
  const [newsPriorityDraft, setNewsPriorityDraft] = useState("");

  useEffect(() => {
    if (settings?.market_data.market_data_provider_priority != null) {
      setPriorityDraft(settings.market_data.market_data_provider_priority);
    }
  }, [settings?.market_data.market_data_provider_priority]);

  useEffect(() => {
    if (settings?.news.news_provider_priority != null) {
      setNewsPriorityDraft(settings.news.news_provider_priority);
    }
  }, [settings?.news.news_provider_priority]);

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await fn();
      setMessage("Saved — backend runtime_settings.json updated.");
      await onAfterSave();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const toggleTrading = (patch: TradingSettingsUpdate) =>
    run(async () => {
      await api.updateSettings({ trading: patch });
    });

  const patchMarket = (patch: MarketDataSettingsUpdate) =>
    run(async () => {
      await api.updateSettings({ market_data: patch });
    });

  const patchPlatform = (patch: PlatformFeaturesUpdate) =>
    run(async () => {
      await api.updateSettings({ platform: patch });
    });

  const patchNews = (patch: NewsSettingsUpdate) =>
    run(async () => {
      await api.updateSettings({ news: patch });
    });

  const Toggle = ({
    label,
    description,
    enabled,
    onToggle,
    danger,
    disabled,
  }: {
    label: string;
    description: string;
    enabled: boolean;
    onToggle: () => void;
    danger?: boolean;
    disabled?: boolean;
  }) => (
    <div
      className={`rounded-xl border p-4 ${
        danger ? "border-rose-500/35 bg-rose-500/10" : "border-emerald-400/15 bg-black/35"
      } ${disabled ? "opacity-50" : ""}`}
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <h3 className={`text-sm font-semibold ${danger ? "text-rose-200" : "text-white"}`}>{label}</h3>
          <p className="mt-1 text-xs text-slate-400">{description}</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          disabled={disabled || busy}
          className={`relative inline-flex h-7 w-12 shrink-0 items-center rounded-full transition-colors ${
            enabled ? (danger ? "bg-rose-600" : "bg-emerald-600") : "bg-slate-700"
          } ${busy ? "cursor-wait" : "cursor-pointer"}`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );

  if (bundleLoading && !settings) {
    return <p className="text-sm text-slate-400">Loading /api/settings…</p>;
  }
  if (!settings) {
    return <p className="text-sm text-rose-200">Settings unavailable. Check API proxy and backend.</p>;
  }

  const d = busy || bundleLoading;

  return (
    <section className="mb-6 rounded-2xl border border-emerald-400/20 bg-black/40 p-6 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-emerald-300">Runtime switches</h2>
          <p className="mt-1 max-w-2xl text-sm text-slate-400">
            Same endpoint as Engineering{" "}
            <Link href="/settings" className="text-emerald-400 underline-offset-2 hover:underline">
              Settings
            </Link>
            : POST <code className="rounded bg-black/50 px-1 text-emerald-200/90">/api/settings</code> writes{" "}
            <code className="rounded bg-black/50 px-1 text-slate-300">runtime_settings.json</code> on the backend. Changes apply immediately to{" "}
            <code className="rounded bg-black/50 px-1 text-slate-300">effective_*</code> resolution.
          </p>
        </div>
        <Link
          href="/settings"
          className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-200 transition hover:bg-emerald-400/20"
        >
          Full settings UI
        </Link>
      </div>

      {error && <div className="mb-4 rounded-xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">{error}</div>}
      {message && <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-100">{message}</div>}

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2 xl:grid-cols-3">
        <Toggle
          label="Paper trading"
          description="Paper mode gate (runtime PAPER_TRADING_ENABLED)."
          enabled={settings.trading.paper_trading_enabled}
          onToggle={() => toggleTrading({ paper_trading_enabled: !settings.trading.paper_trading_enabled })}
          disabled={d}
        />
        <Toggle
          label="Live trading"
          description="Requires human approval + safety checks on server."
          danger
          enabled={settings.trading.live_trading_enabled}
          onToggle={() => toggleTrading({ live_trading_enabled: !settings.trading.live_trading_enabled })}
          disabled={d}
        />
        <Toggle
          label="Broker execution"
          description="Allow broker routing when gates pass."
          enabled={settings.trading.broker_execution_enabled}
          onToggle={() => toggleTrading({ broker_execution_enabled: !settings.trading.broker_execution_enabled })}
          disabled={d}
        />
        <Toggle
          label="Human approval"
          description="Require explicit approval for sensitive execution paths."
          enabled={settings.trading.require_human_approval}
          onToggle={() => toggleTrading({ require_human_approval: !settings.trading.require_human_approval })}
          disabled={d}
        />
        <Toggle
          label="Execution agent"
          description="Automation agent toggle (EXECUTION_AGENT_ENABLED)."
          enabled={settings.trading.execution_agent_enabled}
          onToggle={() => toggleTrading({ execution_agent_enabled: !settings.trading.execution_agent_enabled })}
          disabled={d}
        />
        <Toggle
          label="Alpaca paper session"
          description="Alpaca paper vs live keys surface."
          enabled={settings.trading.alpaca_paper_trade}
          onToggle={() => toggleTrading({ alpaca_paper_trade: !settings.trading.alpaca_paper_trade })}
          disabled={d}
        />
        <Toggle
          label="Alpaca market data"
          description="Use Alpaca data API when configured."
          enabled={settings.market_data.alpaca_market_data_enabled}
          onToggle={() =>
            patchMarket({ alpaca_market_data_enabled: !settings.market_data.alpaca_market_data_enabled })
          }
          disabled={d}
        />
        <Toggle
          label="Vector memory"
          description="VECTOR_MEMORY_ENABLED."
          enabled={settings.platform.vector_memory_enabled}
          onToggle={() => patchPlatform({ vector_memory_enabled: !settings.platform.vector_memory_enabled })}
          disabled={d}
        />
        <Toggle
          label="LangSmith tracing"
          description="LANGSMITH_TRACING."
          enabled={settings.platform.langsmith_tracing}
          onToggle={() => patchPlatform({ langsmith_tracing: !settings.platform.langsmith_tracing })}
          disabled={d}
        />
        <Toggle
          label="News provider"
          description="NEWS_PROVIDER_ENABLED."
          enabled={settings.news.news_provider_enabled}
          onToggle={() => patchNews({ news_provider_enabled: !settings.news.news_provider_enabled })}
          disabled={d}
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Primary market data provider</label>
          <p className="mb-2 text-xs text-slate-500">MARKET_DATA_PROVIDER — human primary; workflows with source auto use this first.</p>
          <select
            value={settings.market_data.market_data_provider}
            disabled={d}
            onChange={(e) => patchMarket({ market_data_provider: e.target.value })}
            className="w-full rounded-lg border border-emerald-400/25 bg-black/50 px-3 py-2 text-sm text-white"
          >
            <option value="yfinance">yfinance</option>
            <option value="alpaca">alpaca</option>
            <option value="polygon">polygon</option>
          </select>
        </div>
        <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
          <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Execution mode</label>
          <p className="mb-2 text-xs text-slate-500">EXECUTION_MODE</p>
          <select
            value={settings.trading.execution_mode}
            disabled={d}
            onChange={(e) => toggleTrading({ execution_mode: e.target.value })}
            className="w-full rounded-lg border border-emerald-400/25 bg-black/50 px-3 py-2 text-sm text-white"
          >
            <option value="dry_run">dry_run</option>
            <option value="paper">paper</option>
            <option value="live">live</option>
          </select>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-emerald-400/15 bg-black/35 p-4">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">Market — provider fallback order</label>
        <p className="mb-2 text-xs text-slate-500">MARKET_DATA_PROVIDER_PRIORITY — comma-separated (saved explicitly).</p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            value={priorityDraft}
            disabled={d}
            onChange={(e) => setPriorityDraft(e.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-emerald-400/25 bg-black/50 px-3 py-2 font-mono text-sm text-emerald-100"
          />
          <button
            type="button"
            disabled={
              d ||
              priorityDraft.trim() === (settings.market_data.market_data_provider_priority || "").trim()
            }
            onClick={() => patchMarket({ market_data_provider_priority: priorityDraft.trim() })}
            className="rounded-lg border border-emerald-400/40 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-200 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Save priority list
          </button>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-emerald-400/15 bg-black/35 p-4">
        <label className="text-xs font-semibold uppercase tracking-wide text-slate-500">News — provider fallback order</label>
        <p className="mb-2 text-xs text-slate-500">
          NEWS_PROVIDER_PRIORITY — feeds to try after NEWS_PROVIDER_PRIMARY (comma-separated: newsapi, finnhub, benzinga).
        </p>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <input
            type="text"
            value={newsPriorityDraft}
            disabled={d}
            onChange={(e) => setNewsPriorityDraft(e.target.value)}
            className="min-w-0 flex-1 rounded-lg border border-emerald-400/25 bg-black/50 px-3 py-2 font-mono text-sm text-cyan-100"
          />
          <button
            type="button"
            disabled={
              d || newsPriorityDraft.trim() === (settings.news.news_provider_priority || "").trim()
            }
            onClick={() => patchNews({ news_provider_priority: newsPriorityDraft.trim() })}
            className="rounded-lg border border-cyan-400/40 bg-cyan-500/15 px-4 py-2 text-sm font-semibold text-cyan-100 disabled:cursor-not-allowed disabled:opacity-40"
          >
            Save news priority
          </button>
        </div>
      </div>
    </section>
  );
}
