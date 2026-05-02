"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type DataSourcesStatusResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

function statusClass(status: string) {
  if (status === "connected") return "border-emerald-500 bg-emerald-500/10 text-emerald-300";
  if (status === "partial") return "border-cyan-500 bg-cyan-500/10 text-cyan-300";
  if (status === "error" || status === "unavailable") return "border-rose-500 bg-rose-500/10 text-rose-300";
  return "border-amber-500 bg-amber-500/10 text-amber-300";
}

export default function DataSourcesPage() {
  const [data, setData] = useState<DataSourcesStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getDataSourcesStatus().then(setData).catch((err) => setError(err.message));
  }, []);

  const byType = useMemo(() => {
    if (!data) return {} as Record<string, typeof data.sources>;
    return data.sources.reduce<Record<string, typeof data.sources>>((acc, source) => {
      acc[source.type] = acc[source.type] ?? [];
      acc[source.type].push(source);
      return acc;
    }, {});
  }, [data]);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="platform truth layer"
          title="Data Sources"
          description="See which data sources are connected, partial, unavailable, or not configured. This keeps EdgeSenseAI honest before signals, features, models, and recommendations run."
        />

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading data source status...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Connected" value={data.connected_sources} accent />
                <MetricCard label="Total Sources" value={data.total_sources} />
                <MetricCard label="Not Configured" value={data.sources.filter((source) => source.status === "not_configured").length} />
                <MetricCard label="Partial/Error" value={data.sources.filter((source) => ["partial", "error", "unavailable"].includes(source.status)).length} />
              </div>
            </section>

            {Object.entries(byType).map(([type, sources]) => (
              <section key={type} className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold capitalize text-emerald-500">{type.replace(/_/g, " ")}</h2>
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                  {sources.map((source) => (
                    <article key={source.key ?? source.name} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-xs uppercase tracking-wide text-slate-500">{source.key}</p>
                          <h3 className="mt-1 text-xl font-black text-white">{source.name}</h3>
                        </div>
                        <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusClass(source.status)}`}>{source.status.replace(/_/g, " ")}</span>
                      </div>
                      <p className="mt-3 text-sm leading-relaxed text-slate-300">{source.message}</p>
                      <div className="mt-3 flex flex-wrap gap-2">
                        {source.used_for.map((usage) => (
                          <span key={usage} className="rounded-full border border-slate-700 bg-slate-950 px-3 py-1 text-xs text-slate-300">{usage.replace(/_/g, " ")}</span>
                        ))}
                      </div>
                      <p className="mt-3 text-xs text-slate-500">Last checked: {new Date(source.last_checked).toLocaleString()}</p>
                    </article>
                  ))}
                </div>
              </section>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
