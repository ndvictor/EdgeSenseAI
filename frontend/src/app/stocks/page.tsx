"use client";

import { useEffect, useState } from "react";
import { api, type MarketSnapshot, type ModelPipelineResult, type AccountFeasibilityResult, type RiskCheckResult } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function StocksPage() {
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
          eyebrow="stocks workflow"
          title="Stocks"
          description="Focused stock workflow for $1K-$10K accounts. A stock candidate must pass snapshot, feature, model pipeline, feasibility, and risk checks before it can become a Command Center top action."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
        {!snapshot || !pipeline || !feasibility || !risk ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading stock workflow...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Prototype Stock Candidate: {snapshot.symbol}</h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Current Price" value={`$${snapshot.current_price.toLocaleString()}`} accent />
                <MetricCard label="Day Change" value={`${snapshot.day_change_percent.toFixed(2)}%`} />
                <MetricCard label="RVOL" value={`${snapshot.relative_volume.toFixed(1)}x`} />
                <MetricCard label="Spread" value={`${snapshot.spread_percent.toFixed(2)}%`} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Feature Pipeline</h3>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <MetricCard label="Composite" value={pipeline.features.composite_feature_score} accent />
                  <MetricCard label="Momentum" value={pipeline.features.momentum_score} />
                  <MetricCard label="RVOL Score" value={pipeline.features.rvol_score} />
                  <MetricCard label="Spread Quality" value={pipeline.features.spread_quality_score} />
                </div>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Model Pipeline</h3>
                <div className="mt-3 space-y-3 text-sm text-slate-300">
                  <p>Directional bias: <span className="font-bold text-white">{pipeline.directional_bias}</span></p>
                  <p>Regime bias: <span className="font-bold text-white">{pipeline.regime_bias}</span></p>
                  <p>Volatility fit: <span className="font-bold text-white">{pipeline.volatility_fit}</span></p>
                  <p>Ranker score: <span className="font-bold text-emerald-300">{pipeline.ranker_score}</span></p>
                </div>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Account + Risk Fit</h3>
                <div className="mt-3 space-y-3 text-sm text-slate-300">
                  <p>Feasibility: <span className="font-bold text-white">{feasibility.feasibility.replace(/_/g, " ")}</span></p>
                  <p>Max risk: <span className="font-bold text-white">${feasibility.max_risk_dollars.toLocaleString()}</span></p>
                  <p>Risk status: <span className={risk.passed ? "font-bold text-emerald-300" : "font-bold text-amber-300"}>{risk.risk_status}</span></p>
                  <p>Reward/Risk: <span className="font-bold text-white">{risk.reward_risk_ratio.toFixed(1)}R</span></p>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Stock Strategy Lanes</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {[
                  ["Day Trade", "RVOL, VWAP deviation, spread quality, short momentum, breakout/reversion alerts."],
                  ["Swing", "Momentum, breakout confirmation, sector relative strength, sentiment, options confirmation."],
                  ["1 Month", "MA20/50 trend, relative strength, earnings revisions, macro regime, volatility forecast."],
                ].map(([title, body]) => (
                  <div key={title} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <h3 className="text-lg font-bold text-white">{title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
