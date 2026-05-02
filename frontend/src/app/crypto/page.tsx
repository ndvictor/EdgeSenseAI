"use client";

import { useEffect, useState } from "react";
import { api, type AccountFeasibilityResult, type MarketSnapshot, type ModelPipelineResult, type RiskCheckResult } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function CryptoPage() {
  const [snapshot, setSnapshot] = useState<MarketSnapshot | null>(null);
  const [pipeline, setPipeline] = useState<ModelPipelineResult | null>(null);
  const [feasibility, setFeasibility] = useState<AccountFeasibilityResult | null>(null);
  const [risk, setRisk] = useState<RiskCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getMarketSnapshots(),
      api.getModelPipeline("BTC-USD"),
      api.getAccountFeasibility("BTC-USD"),
      api.getRiskCheck("BTC-USD"),
    ])
      .then(([snapshots, pipelineResult, feasibilityResult, riskResult]) => {
        setSnapshot(snapshots.find((item) => item.symbol === "BTC-USD") ?? snapshots[0]);
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
          eyebrow="bitcoin and crypto workflow"
          title="Bitcoin / Crypto"
          description="Crypto signals are treated as high-volatility opportunities. BTC must pass volatility, liquidity, regime, account feasibility, and risk gates before being promoted."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}
        {!snapshot || !pipeline || !feasibility || !risk ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading crypto workflow...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">BTC Readiness Snapshot</h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="BTC Price" value={`$${snapshot.current_price.toLocaleString()}`} accent />
                <MetricCard label="Day Change" value={`${snapshot.day_change_percent.toFixed(2)}%`} />
                <MetricCard label="Vol Proxy" value={snapshot.volatility_proxy.toFixed(2)} />
                <MetricCard label="Risk Status" value={risk.risk_status.replace(/_/g, " ")} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-3">
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Crypto Model Pipeline</h3>
                <div className="mt-3 space-y-3 text-sm text-slate-300">
                  <p>Directional bias: <span className="font-bold text-white">{pipeline.directional_bias}</span></p>
                  <p>Regime bias: <span className="font-bold text-white">{pipeline.regime_bias}</span></p>
                  <p>Volatility fit: <span className="font-bold text-white">{pipeline.volatility_fit}</span></p>
                  <p>Ranker score: <span className="font-bold text-emerald-300">{pipeline.ranker_score}</span></p>
                </div>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Account Routing</h3>
                <p className="mt-3 text-sm leading-relaxed text-slate-300">{feasibility.suggested_expression}</p>
                <p className="mt-3 text-sm text-slate-400">Max risk: ${feasibility.max_risk_dollars.toLocaleString()}</p>
              </div>
              <div className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h3 className="text-lg font-semibold text-emerald-500">Risk Check</h3>
                <p className="mt-3 text-sm text-slate-300">Reward/Risk: <span className="font-bold text-white">{risk.reward_risk_ratio.toFixed(1)}R</span></p>
                <p className="mt-2 text-sm text-slate-300">Stop distance: <span className="font-bold text-white">{risk.stop_distance_percent.toFixed(2)}%</span></p>
                <p className="mt-2 text-sm text-slate-300">Status: <span className={risk.passed ? "font-bold text-emerald-300" : "font-bold text-amber-300"}>{risk.risk_status}</span></p>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Crypto Strategy Lanes</h2>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                {[
                  ["Intraday", "Volatility bursts, funding, liquidations, order book imbalance, volume, and BTC momentum."],
                  ["Swing", "Momentum, funding trend, open interest, exchange flows, sentiment, and macro risk context."],
                  ["One Month", "ETF flows, liquidity, BTC dominance, macro regime, and volatility regime."],
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
