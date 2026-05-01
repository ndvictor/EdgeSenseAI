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
    <div className="p-6">
      <PageHeader
        eyebrow="agent-driven monitoring"
        title="Live Watchlist"
        description="Agents continuously monitor stocks, options, and Bitcoin/Crypto, rank triggered assets, and queue alerts when candidates pass small-account filters. Auto-refreshes every 5 minutes."
      />
      {error && <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">{error}</div>}
      {!data ? <div className="text-slate-400">Loading...</div> : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
            <MetricCard label="Triggered now" value={data.summary.triggered_now} accent />
            <MetricCard label="High conviction" value={data.summary.high_conviction} />
            <MetricCard label="Alerts sent today" value={data.summary.alerts_sent_today} />
            <MetricCard label="Strongest trigger" value={data.summary.strongest_trigger} />
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
            {data.agents.map((agent) => (
              <div key={agent.role} className="rounded-2xl border border-white/10 bg-slate-900/80 p-4">
                <p className="text-xs uppercase tracking-wide text-slate-500">{agent.role.replace(/_/g, " ")}</p>
                <h3 className="mt-1 font-black text-white">{agent.name}</h3>
                <p className="mt-2 text-sm text-emerald-300">● {agent.status_label}</p>
              </div>
            ))}
          </div>

          <div className="overflow-x-auto rounded-2xl border border-white/10 bg-slate-900/80">
            <table className="w-full min-w-[1000px] text-left text-sm">
              <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-4 py-3">Symbol</th>
                  <th className="px-4 py-3">Asset</th>
                  <th className="px-4 py-3">Horizon</th>
                  <th className="px-4 py-3">Trigger</th>
                  <th className="px-4 py-3">Priority</th>
                  <th className="px-4 py-3">Account Fit</th>
                  <th className="px-4 py-3">Notify</th>
                  <th className="px-4 py-3">Reason</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/10">
                {data.candidates.map((candidate) => (
                  <tr key={`${candidate.symbol}-${candidate.horizon}`} className="hover:bg-white/[0.04]">
                    <td className="px-4 py-3 font-black text-cyan-300">{candidate.symbol}</td>
                    <td className="px-4 py-3 text-slate-300">{candidate.asset}</td>
                    <td className="px-4 py-3 text-slate-300">{candidate.horizon}</td>
                    <td className="px-4 py-3 text-slate-300">{candidate.trigger}</td>
                    <td className="px-4 py-3 font-bold text-emerald-300">{candidate.priority_score}</td>
                    <td className="px-4 py-3 text-amber-300">{candidate.account_fit_label}</td>
                    <td className="px-4 py-3 text-slate-300">{candidate.notify_label}</td>
                    <td className="max-w-xl px-4 py-3 text-xs text-slate-400">{candidate.reason}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-500">{data.disclaimer}</p>
        </div>
      )}
    </div>
  );
}
