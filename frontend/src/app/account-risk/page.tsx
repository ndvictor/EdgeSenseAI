"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Settings, AlertCircle, CheckCircle2, XCircle, Activity } from "lucide-react";
import { api, type AlpacaPaperSnapshot, type SettingsResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function AccountRiskPage() {
  const [alpaca, setAlpaca] = useState<AlpacaPaperSnapshot | null>(null);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"risk" | "portfolio" | "settings">("risk");

  useEffect(() => {
    api.getAlpacaPaperSnapshot()
      .then(setAlpaca)
      .catch((err) => setError(err.message));
    api.getSettings()
      .then(setSettings)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load settings"));
  }, []);

  if (error) {
    return (
      <div className="w-full min-h-full p-4 lg:p-8">
        <div className="mx-auto w-full max-w-[1600px] rounded-2xl border border-rose-500/35 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
          <PageHeader
            eyebrow="account-aware control"
            title="Account Risk Center"
            description="Display-only view of Alpaca paper account data."
          />
          <div className="mt-4 rounded-xl border border-rose-800 bg-rose-900/20 p-4 text-rose-300">
            <AlertCircle className="inline h-5 w-5 mr-2" />
            Error loading account data: {error}
          </div>
        </div>
      </div>
    );
  }

  if (!alpaca) return <div className="w-full min-h-full p-4 text-sm text-slate-400">Loading...</div>;

  const riskCards =
    settings?.risk
      ? ([
          ["Max risk / trade", `${settings.risk.max_risk_per_trade_percent}%`],
          ["Max daily loss", `${settings.risk.max_daily_loss_percent}%`],
          ["Max position size", `${settings.risk.max_position_size_percent}%`],
          ["Min reward:risk", `${settings.risk.min_reward_risk_ratio.toFixed(1)}R`],
        ] as const)
      : [];

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
        <div className="flex items-center justify-between">
          <PageHeader
            eyebrow="account-aware control"
            title="Account Risk Center"
            description="Display-only view of Alpaca paper account data. Values are sourced directly from your Alpaca account."
          />
          <Link 
            href="/settings?tab=risk" 
            className="flex items-center gap-2 rounded-lg border border-emerald-400/20 bg-black/30 px-4 py-2 text-sm text-emerald-300 hover:border-emerald-400/40 hover:bg-black/40"
          >
            <Settings className="h-4 w-4" />
            Configure in Settings
          </Link>
        </div>

        {/* Subtabs */}
        <div className="mt-4 border-b border-emerald-400/15 pb-2">
          <div className="flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {(
              [
                ["risk", "Risk Controls"],
                ["portfolio", "Portfolio"],
                ["settings", "Settings"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveTab(id)}
                className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  activeTab === id
                    ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                    : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Configured risk controls (from Settings) */}
        {activeTab === "risk" && (riskCards.length > 0 ? (
          <section className="mt-4 rounded-2xl border border-emerald-400/15 bg-black/30 p-4 backdrop-blur">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-emerald-400">Configured risk controls</h3>
              <Link href="/settings?tab=risk" className="text-xs text-slate-400 hover:text-emerald-400">
                Edit risk controls →
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {riskCards.map(([label, value]) => (
                <MetricCard key={label} label={label} value={value} />
              ))}
            </div>
          </section>
        ) : (
          <section className="mt-4 rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
            Risk controls are not loaded yet. If this persists, open Settings → Account risk and save values.
          </section>
        ))}

        {activeTab === "portfolio" && (
        <div className="mt-4 rounded-2xl border border-emerald-400/15 bg-black/30 p-4 backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-sm text-emerald-400">
            <AlertCircle className="h-4 w-4" />
            <span>Portfolio snapshot (Alpaca paper). For risk controls, use the Risk Controls tab.</span>
          </div>

          {alpaca.account ? (
            <>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard 
                  label="Buying Power" 
                  value={`$${alpaca.account.buying_power?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`} 
                  accent 
                />
                <MetricCard 
                  label="Account Equity" 
                  value={`$${alpaca.account.equity?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`} 
                />
                <MetricCard 
                  label="Cash" 
                  value={`$${alpaca.account.cash?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`} 
                />
                <MetricCard 
                  label="Portfolio Value" 
                  value={`$${alpaca.account.portfolio_value?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`} 
                />
              </div>

              <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4 text-sm">
                <DisplayField 
                  label="Account Number" 
                  value={alpaca.account.account_number ?? "N/A"} 
                />
                <DisplayField 
                  label="Status" 
                  value={alpaca.account.status ?? "N/A"} 
                />
                <DisplayField 
                  label="Day Trade Count" 
                  value={alpaca.account.daytrade_count?.toString() ?? "0"} 
                />
                <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_22px_rgba(0,0,0,0.18)] backdrop-blur">
                  <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400/80">PDT status</p>
                  <p className={`mt-2 text-sm font-bold ${alpaca.account.pattern_day_trader ? "text-amber-300" : "text-emerald-300"}`}>
                    {alpaca.account.pattern_day_trader ? "Flagged" : "Clear"}
                  </p>
                </div>
                <DisplayField 
                  label="Currency" 
                  value={alpaca.account.currency ?? "USD"} 
                />
                <DisplayField 
                  label="Last Equity" 
                  value={`$${alpaca.account.last_equity?.toLocaleString(undefined, { maximumFractionDigits: 2 }) ?? "N/A"}`} 
                />
                <DisplayField 
                  label="Trading Blocked" 
                  value={alpaca.account.trading_blocked ? "Yes" : "No"} 
                  warning={alpaca.account.trading_blocked === true}
                />
                <DisplayField 
                  label="Account Blocked" 
                  value={alpaca.account.account_blocked ? "Yes" : "No"} 
                  warning={alpaca.account.account_blocked === true}
                />
              </div>
            </>
          ) : (
            <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">
              <AlertCircle className="inline h-5 w-5 mr-2" />
              No Alpaca account data available. Please configure your Alpaca API keys in the backend .env file.
            </div>
          )}
        </div>
        )}

        {/* Settings Status Panel */}
        {activeTab === "settings" && settings && (
          <div className="mt-4 rounded-2xl border border-emerald-400/15 bg-black/30 p-4 backdrop-blur">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
                <Activity className="h-4 w-4" />
                Settings status (trade gates)
              </h3>
              <Link href="/settings?tab=trading" className="text-xs text-slate-400 hover:text-emerald-400">
                Open Settings →
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <SettingStatus label="Paper Trading" enabled={settings.trading.paper_trading_enabled} />
              <SettingStatus label="Live Trading" enabled={settings.trading.live_trading_enabled} />
              <SettingStatus label="Broker Execution" enabled={settings.trading.broker_execution_enabled} />
              <SettingStatus label="Human Approval" enabled={settings.trading.require_human_approval} />
              <SettingStatus label="Execution Agent" enabled={settings.trading.execution_agent_enabled} />
              <SettingStatus label="Alpaca Paper" enabled={settings.trading.alpaca_paper_trade} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function DisplayField({ label, value, warning = false }: { label: string; value: string; warning?: boolean }) {
  return (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_22px_rgba(0,0,0,0.18)] backdrop-blur">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400/80">{label}</p>
      <p className={`mt-2 truncate font-mono text-sm font-bold ${warning ? "text-amber-300" : "text-slate-100"}`}>{value}</p>
    </div>
  );
}

function SettingStatus({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
      enabled ? "border-emerald-800 bg-emerald-950/30" : "border-rose-800 bg-rose-950/30"
    }`}>
      {enabled ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <XCircle className="h-4 w-4 text-rose-500" />
      )}
      <span className={`text-sm font-medium ${enabled ? "text-emerald-400" : "text-rose-400"}`}>
        {label}
      </span>
    </div>
  );
}
