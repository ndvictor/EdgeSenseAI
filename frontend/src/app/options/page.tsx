"use client";

import { useEffect, useState } from "react";
import { api, type AccountFeasibilityResult, type MarketSnapshot, type ModelPipelineResult, type RiskCheckResult } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function OptionsPage() {
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [pipeline, setPipeline] = useState<ModelPipelineResult | null>(null);
  const [feasibility, setFeasibility] = useState<AccountFeasibilityResult | null>(null);
  const [risk, setRisk] = useState<RiskCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getMarketSnapshots(),
      api.getModelPipeline("AMD"),
      api.getAccountFeasibility("AMD"),
      api.getRiskCheck("AMD"),
    ])
      .then(([snapshots, pipelineResult, feasibilityResult, riskResult]) => {
        setSnapshot(snapshots.find((item) => item.symbol === "AMD") ?? snapshots[0]);
        setPipeline(pipelineResult);
        setFeasibility(feasibilityResult);
        setRisk(riskResult);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="options workflow"
          title="Options"
          description="Options are only promoted when the underlying, IV context, spread quality, account feasibility, and defined-risk structure align. The platform should avoid naked speculation and wide-spread contracts."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
        {!snapshot || !pipeline || !feasibility || !risk ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading options workflow...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Underlying Readiness: {snapshot.symbol}</h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Underlying" value={`$${snapshot.current_price.toLocaleString()}`} accent />
                <MetricCard label="Ranker Score" value={pipeline.ranker_score} />
                <MetricCard label="Reward/Risk" value={`${risk.reward_risk_ratio.toFixed(1)}R`} />
                <MetricCard label="Risk Status" value={risk.risk_status.replace(/_/g, " ")} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              {[
                ["Day Trade Options", "Unusual flow, IV change, delta/gamma flow, spread quality, underlying momentum, and bid/ask validation."],
                ["Swing Options", "IV rank, skew, term structure, put/call ratio, OI change, and underlying trend confirmation."],
                ["Earnings Plays", "Expected move, IV crush risk, event history, gap risk, and defined-risk premium sizing."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                  <h3 className="text-xl font-bold text-white">{title}</h3>
                  <p className="mt-3 text-sm leading-relaxed text-slate-300">{body}</p>
                </div>
              ))}
            </section>

            <section className="rounded-xl border border-amber-800 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-amber-400">Small Account Options Rules</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
                {[
                  "Prefer defined-risk debit spreads or small premium structures.",
                  "Reject wide bid/ask spreads and low open interest contracts.",
                  "Size premium risk from account-risk settings, not conviction alone.",
                  "Avoid IV crush setups unless expected move and structure justify the risk.",
                ].map((rule) => (
                  <div key={rule} className="rounded-xl border border-slate-800 bg-slate-900 p-4 text-sm leading-relaxed text-slate-300">{rule}</div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Current Routing</h2>
              <p className="text-sm leading-relaxed text-slate-300">{feasibility.suggested_expression}</p>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">Prototype note: actual option selection requires options-chain provider data for IV, OI, volume, greeks, and spread quality.</p>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
