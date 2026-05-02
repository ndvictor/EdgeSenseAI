"use client";

import { useEffect, useState } from "react";
import { api, type MarketRegimeResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function MarketRegimePage() {
  const [data, setData] = useState<MarketRegimeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getMarketRegime().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="regime filter"
          title="Market Regime"
          description="Regime decides which strategies are allowed, reduced, or blocked before any signal becomes a recommendation."
        />

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading regime context...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <MetricCard label="Regime State" value={data.regime_state.replace(/_/g, " ")} accent />
                <MetricCard label="Confidence" value={`${Math.round(data.confidence * 100)}%`} />
                <MetricCard label="Strategy Bias" value={data.strategy_bias.replace(/_/g, " ")} />
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-emerald-500">Allowed Strategies</h2>
                <div className="space-y-2">
                  {data.allowed_strategies.map((strategy) => (
                    <div key={strategy} className="rounded-lg border border-emerald-800 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">{strategy}</div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-amber-800 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-amber-400">Blocked or Reduced</h2>
                <div className="space-y-2">
                  {data.blocked_strategies.map((strategy) => (
                    <div key={strategy} className="rounded-lg border border-amber-800 bg-amber-500/10 px-4 py-3 text-sm text-amber-300">{strategy}</div>
                  ))}
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Regime Factors</h2>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
                {data.factors.map((factor) => (
                  <div key={factor.name} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{factor.name}</p>
                    <h3 className="mt-2 text-lg font-bold text-white">{factor.value}</h3>
                    <p className="mt-2 text-sm text-emerald-400">Signal: {factor.signal}</p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-400">{factor.impact}</p>
                  </div>
                ))}
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Notes</h2>
              <div className="space-y-2">
                {data.notes.map((note) => (
                  <p key={note} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">{note}</p>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
