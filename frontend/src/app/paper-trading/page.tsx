"use client";

import { useEffect, useState } from "react";
import { api, type CommandCenterResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

function money(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export default function PaperTradingPage() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCommandCenter().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="paper validation"
          title="Paper Trading"
          description="Paper trading validates whether recommendations are actually actionable before live execution is ever considered. Every paper trade starts from the Command Center contract."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading paper validation...</div>
        ) : !data.top_action ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-8 text-center text-sm text-amber-200">
            No source-backed paper candidate is available yet.
          </div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                <div>
                  <p className="text-xs uppercase tracking-wide text-emerald-500">Paper Candidate</p>
                  <h2 className="mt-1 text-3xl font-black text-white">{data.top_action.symbol} · {data.top_action.action_label}</h2>
                  <p className="mt-2 max-w-4xl text-sm leading-relaxed text-slate-300">{data.top_action.final_reason}</p>
                </div>
                <span className="w-fit rounded-full border border-amber-500 bg-amber-500/10 px-4 py-2 text-sm font-bold uppercase text-amber-300">
                  No live execution
                </span>
              </div>
              <div className="mt-5 grid grid-cols-2 gap-4 md:grid-cols-6">
                <MetricCard label="Entry low" value={money(data.top_action.price_plan.buy_zone_low)} accent />
                <MetricCard label="Entry high" value={money(data.top_action.price_plan.buy_zone_high)} />
                <MetricCard label="Stop" value={money(data.top_action.price_plan.stop_loss)} />
                <MetricCard label="Target" value={money(data.top_action.price_plan.target_price)} />
                <MetricCard label="Max risk" value={money(data.top_action.risk_plan.max_dollar_risk)} />
                <MetricCard label="Expected R" value={`${data.top_action.risk_plan.reward_risk_ratio.toFixed(1)}R`} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Paper Trade Checklist</h3>
                <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-300">
                  <li>• Enter only inside the buy zone.</li>
                  <li>• Record actual fill price and time.</li>
                  <li>• Respect the stop and max-dollar-risk plan.</li>
                  <li>• Track whether target hit before stop.</li>
                </ul>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Outcome Labels</h3>
                <ul className="mt-3 space-y-2 text-sm leading-relaxed text-slate-300">
                  <li>• Target before stop</li>
                  <li>• Stop before target</li>
                  <li>• Timed exit</li>
                  <li>• Invalidated before entry</li>
                </ul>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Learning Loop</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">
                  Paper outcomes should feed the Journal, backtesting labels, and future agent scorecards so the system learns which signals actually produce positive expectancy.
                </p>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Invalidation Rules</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {data.top_action.invalidation_rules.map((rule) => (
                  <div key={rule} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">{rule}</div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
