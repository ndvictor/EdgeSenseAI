"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type JournalOutcomeSummary, type JournalOutcomeResponse, type SettingsResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";
import { BookOpen, XCircle, CheckCircle, MinusCircle, HelpCircle, CheckCircle2, XCircle as XIcon, Activity } from "lucide-react";

function outcomeIcon(label: string) {
  switch (label) {
    case "win": return <CheckCircle className="h-4 w-4 text-emerald-400" />;
    case "loss": return <XCircle className="h-4 w-4 text-red-400" />;
    case "breakeven": return <MinusCircle className="h-4 w-4 text-slate-400" />;
    default: return <HelpCircle className="h-4 w-4 text-slate-500" />;
  }
}

function outcomeBadge(label: string) {
  switch (label) {
    case "win": return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">Win</span>;
    case "loss": return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">Loss</span>;
    case "breakeven": return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">Breakeven</span>;
    case "avoided_loss": return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">Avoided Loss</span>;
    case "unknown": return <span className="rounded-full border border-slate-600 bg-slate-600/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-500">Unknown</span>;
    default: return <span className="rounded-full border border-slate-600 bg-slate-600/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-500">{label}</span>;
  }
}

function SettingStatus({ label, enabled }: { label: string; enabled: boolean }) {
  return (
    <div className={`flex items-center gap-2 rounded-lg border px-3 py-2 ${
      enabled ? "border-emerald-800 bg-emerald-950/30" : "border-rose-800 bg-rose-950/30"
    }`}>
      {enabled ? (
        <CheckCircle2 className="h-4 w-4 text-emerald-500" />
      ) : (
        <XIcon className="h-4 w-4 text-rose-500" />
      )}
      <span className={`text-sm font-medium ${enabled ? "text-emerald-400" : "text-rose-400"}`}>
        {label}
      </span>
    </div>
  );
}

export default function JournalPage() {
  const [data, setData] = useState<JournalOutcomeSummary | null>(null);
  const [entries, setEntries] = useState<JournalOutcomeResponse[]>([]);
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getJournalSummary().then(setData).catch((err) => setError(err.message));
    api.getJournalOutcomes({ limit: 20 }).then((res) => {
      if (Array.isArray(res)) setEntries(res);
    }).catch(() => {});
    api.getSettings()
      .then(setSettings)
      .catch(() => {});
  }, []);

  return (
    <div className="mx-auto max-w-6xl p-6">
      <PageHeader
        eyebrow="learning loop"
        title="Journal"
        description="Journal outcomes close the learning loop. Every recommendation should eventually become a labeled outcome for backtesting, scorecards, and ranker calibration."
      />

      {error && <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">{error}</div>}

      {/* Settings Status Panel */}
      {settings && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="flex items-center gap-2 text-sm font-semibold text-emerald-400">
              <Activity className="h-4 w-4" />
              Journal & Learning Loop Settings
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
              label="Execution Agent" 
              enabled={settings.trading.execution_agent_enabled} 
            />
            <SettingStatus 
              label="Human Approval" 
              enabled={settings.trading.require_human_approval} 
            />
            <SettingStatus 
              label="LangSmith Tracing" 
              enabled={settings.platform.langsmith_tracing} 
            />
          </div>
        </div>
      )}

      {!data ? (
        <div className="py-8 text-center text-sm text-slate-400">Loading journal...</div>
      ) : (
        <div className="space-y-6">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Total Entries" value={data.total_entries} accent />
            <MetricCard label="Wins" value={data.wins} />
            <MetricCard label="Losses" value={data.losses} />
            <MetricCard label="Win Rate" value={`${(data.win_rate * 100).toFixed(1)}%`} />
          </div>

          {/* Entries List */}
          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
              <BookOpen className="h-4 w-4" />
              Recent Outcomes
            </h3>
            {entries.length > 0 ? (
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {entries.map((entry) => (
                  <div key={entry.id} className="flex items-center justify-between rounded-lg bg-slate-800/50 p-3 text-sm">
                    <div className="flex items-center gap-3">
                      {outcomeIcon(entry.outcome_label)}
                      <div>
                        <div className="font-bold text-slate-300">{entry.symbol || "N/A"}</div>
                        <div className="text-xs text-slate-500">{entry.source_type}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <div className="text-slate-400">R: {entry.realized_r?.toFixed(2) || "N/A"}</div>
                        <div className="text-xs text-slate-600">
                          MFE: {entry.mfe_percent?.toFixed(1) || "N/A"}% / MAE: {entry.mae_percent?.toFixed(1) || "N/A"}%
                        </div>
                      </div>
                      {outcomeBadge(entry.outcome_label)}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-4 text-center text-sm text-slate-500">No journal entries yet. Create outcomes from paper trades or manually.</p>
            )}
          </div>

          {/* By Source / Strategy / Symbol */}
          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
              <h4 className="mb-2 text-xs font-bold uppercase text-slate-500">By Source Type</h4>
              {Object.entries(data.by_source_type).map(([source, count]) => (
                <div key={source} className="flex justify-between py-1 text-sm">
                  <span className="text-slate-400">{source}</span>
                  <span className="font-bold text-slate-300">{count}</span>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
              <h4 className="mb-2 text-xs font-bold uppercase text-slate-500">By Symbol</h4>
              {Object.entries(data.by_symbol).slice(0, 5).map(([symbol, count]) => (
                <div key={symbol} className="flex justify-between py-1 text-sm">
                  <span className="text-slate-400">{symbol}</span>
                  <span className="font-bold text-slate-300">{count}</span>
                </div>
              ))}
            </div>
            <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
              <h4 className="mb-2 text-xs font-bold uppercase text-slate-500">By Strategy</h4>
              {Object.entries(data.by_strategy).slice(0, 5).map(([strategy, count]) => (
                <div key={strategy} className="flex justify-between py-1 text-sm">
                  <span className="text-slate-400">{strategy}</span>
                  <span className="font-bold text-slate-300">{count}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
