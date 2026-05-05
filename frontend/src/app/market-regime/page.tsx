"use client";

import { useEffect, useState } from "react";
import { api, type MarketRegimeResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

function SourceBadge({ label, value, danger = false }: { label: string; value: string | boolean | null | undefined; danger?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${danger ? "border-amber-500/40 bg-amber-500/10" : "border-slate-800 bg-slate-900"}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-bold ${danger ? "text-amber-300" : "text-slate-200"}`}>{String(value ?? "unknown")}</p>
    </div>
  );
}

export default function MarketRegimePage() {
  const [data, setData] = useState<MarketRegimeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getMarketRegime().then(setData).catch((err) => setError(err.message));
  }, []);

  const provenance = data as (MarketRegimeResponse & {
    data_source?: string;
    source_type?: string;
    source_detail?: string;
    provider?: string;
    model_used?: string;
    llm_used?: string;
    agent_used?: string;
    calculation_engine?: string;
    real_data_used?: boolean;
    generated_at?: string;
  }) | null;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
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
            <section className="rounded-xl border border-amber-500/40 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-amber-300">Source Truth</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-4 xl:grid-cols-8">
                <SourceBadge label="Data Source" value={provenance?.data_source ?? "hardcoded_prototype"} danger />
                <SourceBadge label="Source Type" value={provenance?.source_type ?? "static_placeholder"} danger />
                <SourceBadge label="Real Data Used" value={provenance?.real_data_used ?? false} danger />
                <SourceBadge label="Provider" value={provenance?.provider ?? "none"} />
                <SourceBadge label="Model" value={provenance?.model_used ?? "none"} />
                <SourceBadge label="LLM" value={provenance?.llm_used ?? "none"} />
                <SourceBadge label="Agent" value={provenance?.agent_used ?? "none"} />
                <SourceBadge label="Engine" value={provenance?.calculation_engine ?? "static_rule_placeholder"} />
              </div>
              <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm leading-relaxed text-amber-200">
                {provenance?.source_detail ?? "This market regime page is currently using static prototype values, not real provider-backed market data."}
              </p>
            </section>

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
                {data.factors.map((factor) => {
                  const factorSource = factor as typeof factor & { data_source?: string; source_detail?: string };
                  return (
                    <div key={factor.name} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                      <p className="text-xs uppercase tracking-wide text-slate-500">{factor.name}</p>
                      <h3 className="mt-2 text-lg font-bold text-white">{factor.value}</h3>
                      <p className="mt-2 text-sm text-emerald-400">Signal: {factor.signal}</p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-400">{factor.impact}</p>
                      <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                        Source: {factorSource.data_source ?? "hardcoded_prototype"}
                      </div>
                    </div>
                  );
                })}
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
