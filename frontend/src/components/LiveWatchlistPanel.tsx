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

export function LiveWatchlistPanel({
  showHeader = true,
  mode = "watchlist",
}: {
  showHeader?: boolean;
  mode?: "watchlist" | "agents";
}) {
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
    <div className="w-full min-h-full">
      {showHeader && (
        <PageHeader
          eyebrow="agent-driven monitoring"
          title="Live Watchlist"
          description="Candidates are no longer just signals. Each row is backed by market snapshot, feature pipeline, account feasibility, and risk-check readiness before it can become a trade recommendation."
        />
      )}

      {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
      {!data ? (
        <div className="py-8 text-center text-sm text-slate-300">Loading...</div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Triggered now" value={data.summary.triggered_now} accent />
            <MetricCard label="High conviction" value={data.summary.high_conviction} />
            <MetricCard label="Alerts sent today" value={data.summary.alerts_sent_today} />
            <MetricCard label="Strongest trigger" value={data.summary.strongest_trigger} />
          </div>

          {mode === "agents" ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
                <h2 className="mb-3 text-lg font-semibold text-emerald-300">Agents</h2>
                <p className="text-sm text-slate-400">Status view for the core decision-readiness agents.</p>
              </div>

              <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                {data.agents.map((agent) => (
                  <div key={agent.role} className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 shadow-[0_0_28px_rgba(0,0,0,0.2)] backdrop-blur">
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">{agent.role.replace(/_/g, " ")}</p>
                    <h3 className="mt-2 text-lg font-bold text-white">{agent.name}</h3>
                    <p className="mt-3 text-sm text-emerald-300">● {agent.status_label}</p>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <>
              <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
                <h2 className="mb-3 text-lg font-semibold text-emerald-300">Decision Readiness Pipeline</h2>
                <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                  {[
                    ["1. Data Quality Agent", "Checking source quality"],
                    ["2. Feature Store Agent", "Building feature rows"],
                    ["3. Model Orchestrator", "Running eligible models"],
                    ["4. Risk Agent", "Risk gate required"],
                  ].map(([title, body]) => (
                    <div key={title} className="rounded-xl border border-emerald-400/10 bg-white/[0.03] p-4">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
                      <p className="mt-2 text-sm text-slate-300">{body}</p>
                    </div>
                  ))}
                </div>
              </section>

              <div className="overflow-x-auto rounded-xl border border-emerald-400/15 bg-black/35 shadow-[0_0_28px_rgba(0,0,0,0.2)] backdrop-blur">
                <table className="w-full min-w-[1500px] text-left text-sm">
                  <thead className="bg-white/[0.02] text-xs uppercase tracking-wide text-slate-400">
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
                  <tbody className="divide-y divide-emerald-950/50">
                    {data.candidates.map((candidate) => {
                      const candidateReadiness = readiness[candidate.symbol];
                      return (
                        <tr key={`${candidate.symbol}-${candidate.horizon}`} className="hover:bg-white/[0.04]">
                          <td className="px-4 py-3">
                            <p className="font-bold text-cyan-300">{candidate.symbol}</p>
                            <p className="text-xs text-slate-500">
                              {candidate.asset_class} · {candidate.horizon}
                            </p>
                          </td>
                          <td className="px-4 py-3 text-slate-300">{candidate.trigger}</td>
                          <td className="px-4 py-3 font-bold text-emerald-300">{candidate.priority_score}</td>
                          <td className="px-4 py-3 text-slate-300">
                            {candidateReadiness?.snapshot ? (
                              <>
                                <p>${candidateReadiness.snapshot.current_price.toLocaleString()}</p>
                                <p className="text-xs text-slate-500">RVOL {candidateReadiness.snapshot.relative_volume.toFixed(1)}x</p>
                              </>
                            ) : (
                              "Loading"
                            )}
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
                            ) : (
                              "Loading"
                            )}
                          </td>
                          <td className="px-4 py-3 text-amber-300">{candidateReadiness?.feasibility?.feasibility ?? candidate.account_fit_label}</td>
                          <td className="px-4 py-3 text-slate-300">
                            {candidateReadiness?.risk ? (
                              <>
                                <p className={candidateReadiness.risk.passed ? "font-bold text-emerald-300" : "font-bold text-amber-300"}>
                                  {candidateReadiness.risk.risk_status}
                                </p>
                                <p className="text-xs text-slate-500">{candidateReadiness.risk.reward_risk_ratio.toFixed(1)}R</p>
                              </>
                            ) : (
                              "Loading"
                            )}
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
            </>
          )}
        </div>
      )}
    </div>
  );
}

