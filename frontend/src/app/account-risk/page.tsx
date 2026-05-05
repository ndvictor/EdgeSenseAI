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

  useEffect(() => {
    api.getAlpacaPaperSnapshot()
      .then(setAlpaca)
      .catch((err) => setError(err.message));
    api.getSettings()
      .then(setSettings)
      .catch(() => {});
  }, []);

  if (error) {
    return (
      <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
        <div className="mx-auto w-full max-w-[1600px] rounded-xl border border-rose-800 bg-slate-950 p-4 shadow-sm">
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

  if (!alpaca) return <div className="min-h-screen bg-slate-500 p-4 text-sm text-slate-300">Loading...</div>;

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px] rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <PageHeader
            eyebrow="account-aware control"
            title="Account Risk Center"
            description="Display-only view of Alpaca paper account data. Values are sourced directly from your Alpaca account."
          />
          <Link 
            href="/settings" 
            className="flex items-center gap-2 rounded-lg border border-emerald-700 bg-emerald-900/30 px-4 py-2 text-sm text-emerald-400 hover:bg-emerald-900/50"
          >
            <Settings className="h-4 w-4" />
            Configure in Settings
          </Link>
        </div>

        {/* Settings Status Panel */}
        {settings && (
          <div className="mt-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
                <Activity className="h-4 w-4" />
                Account Risk Settings Status
              </h3>
              <Link 
                href="/settings" 
                className="text-xs text-slate-400 hover:text-emerald-400"
              >
                Configure in Settings →
              </Link>
            </div>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <SettingStatus 
                label="Paper Trading" 
                enabled={settings.trading.paper_trading_enabled} 
              />
              <SettingStatus 
                label="Live Trading" 
                enabled={settings.trading.live_trading_enabled} 
              />
              <SettingStatus 
                label="Broker Execution" 
                enabled={settings.trading.broker_execution_enabled} 
              />
              <SettingStatus 
                label="Human Approval" 
                enabled={settings.trading.require_human_approval} 
              />
              <SettingStatus 
                label="Execution Agent" 
                enabled={settings.trading.execution_agent_enabled} 
              />
              <SettingStatus 
                label="Alpaca Paper" 
                enabled={settings.trading.alpaca_paper_trade} 
              />
            </div>
          </div>
        )}

        <div className="mt-4 rounded-xl border border-emerald-800 bg-slate-900 p-4">
          <div className="mb-4 flex items-center gap-2 text-sm text-emerald-400">
            <AlertCircle className="h-4 w-4" />
            <span>Display-only mode. To change settings, go to Settings tab.</span>
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
                <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
                  <span className="text-slate-500">PDT Status:</span>
                  <span className={`ml-2 ${alpaca.account.pattern_day_trader ? "text-amber-400" : "text-emerald-400"}`}>
                    {alpaca.account.pattern_day_trader ? "Flagged" : "Clear"}
                  </span>
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
                  warning={alpaca.account.trading_blocked}
                />
                <DisplayField 
                  label="Account Blocked" 
                  value={alpaca.account.account_blocked ? "Yes" : "No"} 
                  warning={alpaca.account.account_blocked}
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
      </div>
    </div>
  );
}

function DisplayField({ label, value, warning = false }: { label: string; value: string; warning?: boolean }) {
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="text-slate-500">{label}:</span>
      <span className={`ml-2 font-mono ${warning ? "text-amber-400" : "text-slate-300"}`}>{value}</span>
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
