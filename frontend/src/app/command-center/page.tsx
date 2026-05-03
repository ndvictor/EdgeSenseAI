"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type CommandCenterResponse } from "@/lib/api";
import { EdgeSignalGrid, MetricCard, PageHeader, RecommendationTable } from "@/components/Cards";
import { Users, TrendingUp, AlertTriangle, Play, Clock } from "lucide-react";

function money(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function CommandCenterPage() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const loadData = async () => {
    try {
      const response = await api.getCommandCenter();
      setData(response);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunWorkflow = async () => {
    setIsRunning(true);
    setError(null);
    try {
      const response = await api.runCommandCenter();
      setData(response);
    } catch (err) {
      setError("Failed to run workflow");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="decision intelligence cockpit"
          title="Command Center"
          description="Source-backed dashboard. No hardcoded trade numbers are shown as recommendations. If real source data is unavailable, the platform shows no-action status instead of fake buy/target/stop data."
        />

        {error && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            {error}
          </div>
        )}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading dashboard...</div>
        ) : (
          <div className="space-y-4">
            {data.dashboard_mode === "no_symbols_selected" ? (
              <section className="rounded-2xl border border-amber-500 bg-slate-950 p-5 shadow-sm">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-amber-400" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-400">No candidates selected</p>
                    <h2 className="mt-1 text-2xl font-black text-white">Add symbols before running ranking</h2>
                  </div>
                </div>
                <p className="mt-4 max-w-5xl text-sm leading-relaxed text-slate-300">
                  The Command Center requires a candidate universe to rank. Add symbols from Stocks search, Watchlist, Scanner, or the Candidate Universe page before running the decision workflow.
                </p>

                {/* Navigation Cards */}
                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Link
                    href="/stocks"
                    className="flex items-center gap-4 rounded-xl border border-emerald-800 bg-slate-900 p-4 transition-colors hover:border-emerald-500 hover:bg-slate-800"
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                      <TrendingUp className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white">Stocks</h3>
                      <p className="text-sm text-slate-400">Search tickers and add them to candidate universe</p>
                    </div>
                  </Link>

                  <Link
                    href="/candidates"
                    className="flex items-center gap-4 rounded-xl border border-emerald-800 bg-slate-900 p-4 transition-colors hover:border-emerald-500 hover:bg-slate-800"
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                      <Users className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white">Candidate Universe</h3>
                      <p className="text-sm text-slate-400">Manage candidates and run decision workflow</p>
                    </div>
                  </Link>
                </div>
              </section>
            ) : data.dashboard_mode === "candidates_ready_not_ranked" ? (
              <section className="rounded-2xl border border-cyan-500 bg-slate-950 p-5 shadow-sm">
                <div className="flex items-center gap-3">
                  <Clock className="h-8 w-8 text-cyan-400" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-400">Candidates Ready</p>
                    <h2 className="mt-1 text-2xl font-black text-white">Workflow not yet run</h2>
                  </div>
                </div>
                <p className="mt-4 max-w-5xl text-sm leading-relaxed text-slate-300">
                  {data.cost_usage_message}
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    onClick={handleRunWorkflow}
                    disabled={isRunning}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
                      isRunning
                        ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                        : "border border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
                    }`}
                  >
                    {isRunning ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Run Decision Workflow
                      </>
                    )}
                  </button>

                  <Link
                    href="/candidates"
                    className="flex items-center gap-2 rounded-xl border border-cyan-500 bg-slate-900 px-4 py-2 text-sm font-bold uppercase text-cyan-400 transition-all hover:bg-cyan-500 hover:text-slate-950"
                  >
                    <Users className="h-4 w-4" />
                    Go to Candidates
                  </Link>
                </div>
              </section>
            ) : !data.top_action || data.top_recommendations.length === 0 ? (
              <section className="rounded-2xl border border-amber-500 bg-slate-950 p-5 shadow-sm">
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-amber-400" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-400">No actionable recommendations</p>
                    <h2 className="mt-1 text-2xl font-black text-white">Candidates exist but none passed all gates</h2>
                  </div>
                </div>
                <p className="mt-4 max-w-5xl text-sm leading-relaxed text-slate-300">
                  Candidates were ranked but none passed the quality, model score, and risk gates required for actionable status.
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    onClick={handleRunWorkflow}
                    disabled={isRunning}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
                      isRunning
                        ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                        : "border border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
                    }`}
                  >
                    {isRunning ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Re-run Workflow
                      </>
                    )}
                  </button>

                  <Link
                    href="/candidates"
                    className="flex items-center gap-2 rounded-xl border border-cyan-500 bg-slate-900 px-4 py-2 text-sm font-bold uppercase text-cyan-400 transition-all hover:bg-cyan-500 hover:text-slate-950"
                  >
                    <Users className="h-4 w-4" />
                    Manage Candidates
                  </Link>
                </div>

                {/* Show source data status if available */}
                {data.source_data_status.length > 0 && (
                  <div className="mt-6">
                    <p className="mb-3 text-sm font-semibold text-slate-400">Source data status:</p>
                    <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
                      {data.source_data_status.map((source) => (
                        <div key={source.symbol} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                          <p className="text-lg font-black text-white">{source.symbol}</p>
                          <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">Provider</p>
                          <p className="text-sm font-bold text-slate-300">{source.provider ?? "none"}</p>
                          <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">Quality</p>
                          <p className="text-sm font-bold text-amber-300">{source.data_quality ?? "unavailable"}</p>
                          {source.error && <p className="mt-2 text-xs leading-relaxed text-slate-400">{source.error}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            ) : (
              <>
                <section className="rounded-2xl border border-emerald-500 bg-slate-950 p-5 shadow-sm">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-500">Top Source-Backed Watch Candidate</p>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <h2 className="text-4xl font-black text-white">{data.top_action.symbol}</h2>
                        <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-4 py-1 text-sm font-bold uppercase text-emerald-300">
                          {data.top_action.action_label}
                        </span>
                        <span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-4 py-1 text-sm font-bold uppercase text-cyan-300">
                          {data.top_action.data_mode.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p className="mt-3 max-w-5xl text-sm leading-relaxed text-slate-300">{data.top_action.final_reason}</p>
                    </div>

                    <div className="rounded-xl border border-emerald-800 bg-slate-900 px-6 py-4 text-center">
                      <p className="text-xs uppercase tracking-wide text-emerald-500">Confidence</p>
                      <p className="mt-1 text-4xl font-black text-white">{percent(data.top_action.confidence)}</p>
                      <p className="mt-1 text-sm text-slate-400">Score {data.top_action.final_score}/100</p>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-6">
                    <MetricCard label="Current" value={money(data.top_action.price_plan.current_price)} accent />
                    <MetricCard label="Watch low" value={money(data.top_action.price_plan.buy_zone_low)} />
                    <MetricCard label="Watch high" value={money(data.top_action.price_plan.buy_zone_high)} />
                    <MetricCard label="Risk level" value={money(data.top_action.price_plan.stop_loss)} />
                    <MetricCard label="Target ref" value={money(data.top_action.price_plan.target_price)} />
                    <MetricCard label="Reward/Risk" value={`${data.top_action.risk_plan.reward_risk_ratio.toFixed(1)}R`} />
                  </div>
                </section>

                <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                  <h2 className="mb-3 text-lg font-semibold text-emerald-500">Evidence Status</h2>
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
                    {data.top_action.model_votes.map((vote) => (
                      <div key={vote.model} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                        <h3 className="text-sm font-bold text-white">{vote.model}</h3>
                        <p className="mt-2 text-2xl font-black text-emerald-500">{percent(vote.confidence)}</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-400">{vote.explanation}</p>
                        <p className="mt-3 text-xs uppercase tracking-wide text-amber-300">Status: {vote.status}</p>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            )}

            <section className="rounded-xl border border-emerald-600 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Portfolio Snapshot</h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Buying Power" value={`$${data.account_profile.buying_power.toLocaleString()}`} accent />
                <MetricCard label="Account Equity" value={`$${data.account_profile.account_equity.toLocaleString()}`} />
                <MetricCard label="Risk / Trade" value={`${data.account_profile.max_risk_per_trade_percent}%`} />
                <MetricCard label="Min Reward/Risk" value={`${data.account_profile.min_reward_risk_ratio}R`} />
              </div>
            </section>

            {data.top_recommendations.length > 0 && (
              <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-emerald-500">Source-Backed Watch Candidates</h2>
                <RecommendationTable recommendations={data.top_recommendations} />
              </section>
            )}

            {data.urgent_edge_alerts.length > 0 && (
              <section className="rounded-xl border border-emerald-900 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-emerald-500">Urgent Edge Alerts</h2>
                <EdgeSignalGrid signals={data.urgent_edge_alerts} />
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
