"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api, type MarketRegimeResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

type MarketRegimeProvenance = MarketRegimeResponse & {
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
};

function SourceBadge({ label, value, danger = false }: { label: string; value: string | boolean | null | undefined; danger?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${danger ? "border-amber-500/40 bg-amber-500/10" : "border-emerald-400/10 bg-white/[0.03]"}`}>
      <p className="text-[10px] font-bold uppercase tracking-wide text-slate-500">{label}</p>
      <p className={`mt-1 text-sm font-bold ${danger ? "text-amber-200" : "text-slate-200"}`}>{String(value ?? "unknown")}</p>
    </div>
  );
}

export function MarketRegimeShell({
  active,
}: {
  active: "source-truth" | "allowed-strategies" | "regime-factors";
}) {
  const [data, setData] = useState<MarketRegimeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getMarketRegime().then(setData).catch((err) => setError(err.message));
  }, []);

  const provenance: MarketRegimeProvenance | null = useMemo(() => {
    return data as MarketRegimeProvenance | null;
  }, [data]);

  const tabs = [
    { key: "source-truth", label: "Source Truth", href: "/market-regime/source-truth" },
    { key: "allowed-strategies", label: "Allowed Strategies", href: "/market-regime/allowed-strategies" },
    { key: "regime-factors", label: "Regime Factors", href: "/market-regime/regime-factors" },
  ] as const;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-4">
        <PageHeader
          eyebrow="regime filter"
          title="Market Regime"
          description="Regime decides which strategies are allowed, reduced, or blocked before any signal becomes a recommendation."
        />

        <div className="flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {tabs.map((t) => (
            <Link
              key={t.key}
              href={t.href}
              className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                active === t.key
                  ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                  : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {t.label}
            </Link>
          ))}
        </div>

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading regime context...</div>
        ) : active === "source-truth" ? (
          <div className="space-y-4">
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-emerald-300">Source Truth</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-4 xl:grid-cols-8">
                <SourceBadge label="Data Source" value={provenance?.data_source ?? "source_unavailable"} danger />
                <SourceBadge label="Source Type" value={provenance?.source_type ?? "not_configured"} danger />
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

            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <MetricCard label="Regime State" value={data.regime_state.replace(/_/g, " ")} accent />
                <MetricCard label="Confidence" value={`${Math.round(data.confidence * 100)}%`} />
                <MetricCard label="Strategy Bias" value={data.strategy_bias.replace(/_/g, " ")} />
              </div>
            </section>
          </div>
        ) : active === "allowed-strategies" ? (
          <section className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-emerald-300">Allowed Strategies</h2>
              <div className="space-y-2">
                {data.allowed_strategies.map((strategy) => (
                  <div key={strategy} className="rounded-lg border border-emerald-400/15 bg-white/[0.03] px-4 py-3 text-sm text-emerald-200">
                    {strategy}
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-amber-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-amber-300">Blocked or Reduced</h2>
              <div className="space-y-2">
                {data.blocked_strategies.map((strategy) => (
                  <div key={strategy} className="rounded-lg border border-amber-400/15 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                    {strategy}
                  </div>
                ))}
              </div>
            </div>
          </section>
        ) : (
          <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur">
            <h2 className="mb-3 text-lg font-semibold text-emerald-300">Regime Factors</h2>
            <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
              {data.factors.map((factor) => {
                const factorSource = factor as typeof factor & { data_source?: string; source_detail?: string };
                return (
                  <div key={factor.name} className="rounded-xl border border-emerald-400/10 bg-white/[0.03] p-4">
                    <p className="text-xs uppercase tracking-wide text-slate-500">{factor.name}</p>
                    <h3 className="mt-2 text-lg font-bold text-white">{factor.value}</h3>
                    <p className="mt-2 text-sm text-emerald-300">Signal: {factor.signal}</p>
                    <p className="mt-2 text-sm leading-relaxed text-slate-400">{factor.impact}</p>
                    <div className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                      Source: {factorSource.data_source ?? "source_unavailable"}
                    </div>
                  </div>
                );
              })}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

