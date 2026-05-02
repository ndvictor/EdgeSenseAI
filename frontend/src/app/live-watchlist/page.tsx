"use client";

import { useEffect, useState } from "react";
import { api, type LiveWatchlistResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function LiveWatchlistPage() {
  const [data, setData] = useState<LiveWatchlistResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getLiveWatchlist().then(setData).catch((err) => setError(err.message));
    const timer = window.setInterval(() => {
      api.getLiveWatchlist().then(setData).catch((err) => setError(err.message));
    }, 300000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-2 lg:p-3">
      <div className="mx-auto max-w-7xl">
        <PageHeader
          eyebrow="agent-driven monitoring"
          title="Live Watchlist"
          description="Agents continuously monitor stocks, options, and Bitcoin/Crypto, rank triggered assets, and queue alerts when candidates pass small-account filters. Auto-refreshes every 5 minutes."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">{error}</div>}
        {!data ? <div className="py-6 text-center text-xs text-slate-300">Loading...</div> : (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              <MetricCard label="Triggered now" value={data.summary.triggered_now} accent />
              <MetricCard label="High conviction" value={data.summary.high_conviction} />
              <MetricCard label="Alerts sent today" value={data.summary.alerts_sent_today} />
              <MetricCard label="Strongest trigger" value={data.summary.strongest_trigger} />
            </div>

            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              {data.agents.map((agent) => (
                <div key={agent.role} className="rounded-xl border border-white/10 bg-slate-900/80 p-3">
                  <p className="truncate text-[10px] uppercase tracking-wide text-slate-500">{agent.role.replace(/_/g, " ")}</p>
                  <h3 className="mt-0.5 truncate text-sm font-semibold text-white">{agent.name}</h3>
                  <p className="mt-1 text-xs text-emerald-300">● {agent.status_label}</p>
                </div>
              ))}
            </div>

            <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900/80">
              <table className="w-full min-w-[1000px] text-left text-xs">
                <thead className="bg-white/5 text-[10px] uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-2 py-2">Symbol</th>
                    <th className="px-2 py-2">Asset</th>
                    <th className="px-2 py-2">Horizon</th>
                    <th className="px-2 py-2">Trigger</th>
                    <th className="px-2 py-2">Priority</th>
                    <th className="px-2 py-2">Account Fit</th>
                    <th className="px-2 py-2">Notify</th>
                    <th className="px-2 py-2">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {data.candidates.map((candidate) => (
                    <tr key={`${candidate.symbol}-${candidate.horizon}`} className="hover:bg-white/[0.04]">
                      <td className="px-2 py-1.5 font-bold text-cyan-300">{candidate.symbol}</td>
                      <td className="px-2 py-1.5 text-slate-300">{candidate.asset}</td>
                      <td className="px-2 py-1.5 text-slate-300">{candidate.horizon}</td>
                      <td className="px-2 py-1.5 text-slate-300">{candidate.trigger}</td>
                      <td className="px-2 py-1.5 font-bold text-emerald-300">{candidate.priority_score}</td>
                      <td className="px-2 py-1.5 text-amber-300">{candidate.account_fit_label}</td>
                      <td className="px-2 py-1.5 text-slate-300">{candidate.notify_label}</td>
                      <td className="max-w-xl px-2 py-1.5 text-[11px] leading-snug text-slate-400">{candidate.reason}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="text-[11px] leading-snug text-slate-300">{data.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
}
