"use client";

import { useEffect, useState } from "react";
import {
  api,
  type AccountFeasibilityResult,
  type LiveWatchlistResponse,
  type MarketSnapshot,
  type ModelPipelineResult,
  type RiskCheckResult,
} from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

type ReadinessBySymbol = Record<
  string,
  {
    snapshot?: MarketSnapshot;
    pipeline?: ModelPipelineResult;
    feasibility?: AccountFeasibilityResult;
    risk?: RiskCheckResult;
  }
>;

export default function LiveWatchlistPage() {
  const [data, setData] = useState<LiveWatchlistResponse | null>(null);
  const [readiness, setReadiness] = useState<ReadinessBySymbol>({});
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const watchlist = await api.getLiveWatchlist();
    setData(watchlist);

    const snapshots = await api.getMarketSnapshots();
    const uniqueSymbols = Array.from(new Set(watchlist.candidates.map((candidate) => candidate.symbol)));
    const entries = await Promise.all(
      uniqueSymbols.map(async (symbol) => {
        const [pipeline, feasibility, risk] = await Promise.all([
          api.getModelPipeline(symbol),
          api.getAccountFeasibility(symbol),
          api.getRiskCheck(symbol),
        ]);
        return [
          symbol,
          {
            snapshot: snapshots.find((snapshot) => snapshot.symbol === symbol),
            pipeline,
            feasibility,
            risk,
          },
        ] as const;
      })
    );
    setReadiness(Object.fromEntries(entries));
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
    const timer = window.setInterval(() => {
      load().catch((err) => setError(err.message));
    }, 300000);
    return () => window.clearInterval(timer);
  }, []);

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="agent-driven monitoring"
          title="Live Watchlist"
          description="Candidates are no longer just signals. Each row is backed by market snapshot, feature pipeline, account feasibility, and risk-check readiness before it can become a trade recommendation."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
        {!data ? <div className="py-8 text-center text-sm text-slate-300">Loading...</div> : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <MetricCard label="Triggered now" value={data.summary.triggered_now} accent />
              <MetricCard label="High conviction" value={data.summary.high_conviction} />
              <MetricCard label="Alerts sent today" value={data.summary.alerts_sent_today} />
              <MetricCard label="Strongest trigger" value={data.summary.strongest_trigger} />
            </div>

            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Decision Readiness Pipeline</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">1. Market Snapshot</p>
                  <p className="mt-2 text-sm text-slate-300">Price, RVOL, spread, VWAP, and volatility proxy.</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">2. Feature Pipeline</p>
                  <p className="mt-2 text-sm text-slate-300">Momentum, spread quality, trend-vs-VWAP, volatility fit.</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">3. Account Fit</p>
                  <p className="mt-2 text-sm text-slate-300">Position size, risk dollars, and small-account expression routing.</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-slate-500">4. Risk Check</p>
                  <p className="mt-2 text-sm text-slate-300">Reward/risk, stop distance, blockers, and execution safety.</p>
                </div>
              </div>
            </section>

            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              {data.agents.map((agent) => (
                <div key={agent.role} className="rounded-xl border border-white/10 bg-slate-900/80 p-4">
                  <p className="truncate text-xs uppercase tracking-wide text-slate-500">{agent.role.replace(/_/g, " ")}</p>
                  <h3 className="mt-1 truncate text-base font-semibold text-white">{agent.name}</h3>
                  <p className="mt-2 text-sm text-emerald-300">● {agent.status_label}</p>
                </div>
              ))}
            </div>

            <div className="overflow-x-auto rounded-xl border border-white/10 bg-slate-900/80">
              <table className="w-full min-w-[1500px] text-left text-sm">
                <thead className="bg-white/5 text-xs uppercase tracking-wide text-slate-400">
                  <tr>
                    <th className="px-4 py-3">Symbol</th>
                    <th className="px-4 py-3">Trigger</th>
                    <th className="px-4 py-3">Priority</th>
                    <th className="px-4 py-3">Price / RVOL</th>
                    <th className="px-4 py-3">Feature Score</th>
                    <th className="px-4 py-3">Ranker</th>
                    <th className="px-4 py-3">Account Fit</th>
                    <th className="px-4 py-3">Risk Status</th>
                    <th className="px-4 py-3">Next Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {data.candidates.map((candidate) => {
                    const candidateReadiness = readiness[candidate.symbol];
                    return (
                      <tr key={`${candidate.symbol}-${candidate.horizon}`} className="hover:bg-white/[0.04]">
                        <td className="px-4 py-3">
                          <p className="font-bold text-cyan-300">{candidate.symbol}</p>
                          <p className="text-xs text-slate-500">{candidate.asset_class} · {candidate.horizon}</p>
                        </td>
                        <td className="px-4 py-3 text-slate-300">{candidate.trigger}</td>
                        <td className="px-4 py-3 font-bold text-emerald-300">{candidate.priority_score}</td>
                        <td className="px-4 py-3 text-slate-300">
                          {candidateReadiness?.snapshot ? (
                            <>
                              <p>${candidateReadiness.snapshot.current_price.toLocaleString()}</p>
                              <p className="text-xs text-slate-500">RVOL {candidateReadiness.snapshot.relative_volume.toFixed(1)}x</p>
                            </>
                          ) : "Loading"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {candidateReadiness?.pipeline ? candidateReadiness.pipeline.features.composite_feature_score : "Loading"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {candidateReadiness?.pipeline ? (
                            <>
                              <p className="font-bold text-emerald-300">{candidateReadiness.pipeline.ranker_score}</p>
                              <p className="text-xs text-slate-500">{candidateReadiness.pipeline.directional_bias}</p>
                            </>
                          ) : "Loading"}
                        </td>
                        <td className="px-4 py-3 text-amber-300">
                          {candidateReadiness?.feasibility?.feasibility ?? candidate.account_fit_label}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {candidateReadiness?.risk ? (
                            <>
                              <p className={candidateReadiness.risk.passed ? "font-bold text-emerald-300" : "font-bold text-amber-300"}>{candidateReadiness.risk.risk_status}</p>
                              <p className="text-xs text-slate-500">{candidateReadiness.risk.reward_risk_ratio.toFixed(1)}R</p>
                            </>
                          ) : "Loading"}
                        </td>
                        <td className="max-w-xl px-4 py-3 text-sm leading-relaxed text-slate-400">
                          {candidateReadiness?.feasibility?.suggested_expression ?? candidate.suggested_expression}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            <p className="text-sm leading-relaxed text-slate-300">{data.disclaimer}</p>
          </div>
        )}
      </div>
    </div>
  );
}
