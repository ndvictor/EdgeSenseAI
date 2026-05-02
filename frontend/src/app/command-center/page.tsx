"use client";

import { useEffect, useState } from "react";
import { api, type CommandCenterResponse } from "@/lib/api";
import { EdgeSignalGrid, MetricCard, PageHeader, RecommendationTable } from "@/components/Cards";

function money(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function CommandCenterPage() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCommandCenter().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="decision intelligence cockpit"
          title="Command Center"
          description="The platform should produce a specific action plan: confidence, buy zone, stop, target, reward/risk, model evidence, and invalidation rules. Research mode only until live market data is connected."
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
            <section className="rounded-2xl border border-emerald-500 bg-slate-950 p-5 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-500">Top Action Right Now</p>
                  <div className="mt-2 flex flex-wrap items-center gap-3">
                    <h2 className="text-4xl font-black text-white">{data.top_action.symbol}</h2>
                    <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-4 py-1 text-sm font-bold uppercase text-emerald-300">
                      {data.top_action.action_label}
                    </span>
                    <span className="rounded-full border border-amber-500 bg-amber-500/10 px-4 py-1 text-sm font-bold uppercase text-amber-300">
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
                <MetricCard label="Buy zone low" value={money(data.top_action.price_plan.buy_zone_low)} />
                <MetricCard label="Buy zone high" value={money(data.top_action.price_plan.buy_zone_high)} />
                <MetricCard label="Stop loss" value={money(data.top_action.price_plan.stop_loss)} />
                <MetricCard label="Target" value={money(data.top_action.price_plan.target_price)} />
                <MetricCard label="Reward/Risk" value={`${data.top_action.risk_plan.reward_risk_ratio.toFixed(1)}R`} />
              </div>

              <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-3">
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <h3 className="text-lg font-semibold text-emerald-500">Account Risk Plan</h3>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                    <div>
                      <p className="text-slate-500">Position Size</p>
                      <p className="text-lg font-bold text-white">{money(data.top_action.risk_plan.position_size_dollars)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Max Risk</p>
                      <p className="text-lg font-bold text-white">{money(data.top_action.risk_plan.max_dollar_risk)}</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Max Loss</p>
                      <p className="text-lg font-bold text-white">{data.top_action.risk_plan.max_loss_percent.toFixed(1)}%</p>
                    </div>
                    <div>
                      <p className="text-slate-500">Expected Return</p>
                      <p className="text-lg font-bold text-white">{data.top_action.risk_plan.expected_return_percent.toFixed(1)}%</p>
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4 lg:col-span-2">
                  <h3 className="text-lg font-semibold text-emerald-500">Invalidation Rules</h3>
                  <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-300">
                    {data.top_action.invalidation_rules.map((rule) => (
                      <li key={rule} className="rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">{rule}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Statistical Model Evidence</h2>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
                {data.top_action.model_votes.map((vote) => (
                  <div key={vote.model} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="text-sm font-bold text-white">{vote.model}</h3>
                      <span className="rounded-full bg-cyan-500/10 px-2 py-1 text-xs font-bold uppercase text-cyan-300">{vote.signal}</span>
                    </div>
                    <p className="mt-2 text-2xl font-black text-emerald-500">{percent(vote.confidence)}</p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-400">{vote.explanation}</p>
                    <p className="mt-3 text-xs uppercase tracking-wide text-amber-300">Status: {vote.status}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-emerald-600 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Portfolio Snapshot</h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Buying Power" value={`$${data.account_profile.buying_power.toLocaleString()}`} accent />
                <MetricCard label="Account Equity" value={`$${data.account_profile.account_equity.toLocaleString()}`} />
                <MetricCard label="Risk / Trade" value={`${data.account_profile.max_risk_per_trade_percent}%`} />
                <MetricCard label="Min Reward/Risk" value={`${data.account_profile.min_reward_risk_ratio}R`} />
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Alternative Candidates</h2>
              <RecommendationTable recommendations={data.top_recommendations} />
            </section>

            <section className="rounded-xl border border-emerald-900 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Urgent Edge Alerts</h2>
              <EdgeSignalGrid signals={data.urgent_edge_alerts} />
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
