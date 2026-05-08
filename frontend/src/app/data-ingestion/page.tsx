"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, type DataIngestionStatusResponse, type DataIngestionSourceStatus } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";
const cardInner = "rounded-xl border border-emerald-400/15 bg-black/30 p-4 backdrop-blur";
const miniField = "rounded-lg border border-emerald-400/15 bg-black/35 px-3 py-2";
const pill = "rounded-full border border-emerald-400/15 bg-black/35 px-3 py-1 text-xs text-slate-300";

function statusClass(status: string) {
  if (status === "ready") return "border-emerald-500 bg-emerald-500/10 text-emerald-300";
  if (status === "disabled") return "border-slate-600 bg-slate-600/10 text-slate-300";
  if (status === "error") return "border-rose-500 bg-rose-500/10 text-rose-300";
  return "border-amber-500 bg-amber-500/10 text-amber-200";
}

export default function DataIngestionPage() {
  const [data, setData] = useState<DataIngestionStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDataIngestionStatus()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load data ingestion status"));
  }, []);

  const pos = data?.pipeline_position;
  const summary = data?.summary;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-6">
        <PageHeader
          eyebrow="pull / stream / persist"
          title="Data ingestion"
          description="Readiness across market, news, options, and account feeds. This view summarizes configured sources and suggested next actions; it does not start batch jobs by itself. Configure credentials on Data source, then run Feature pipeline to exercise a symbol end-to-end."
        />

        <p className="text-sm text-slate-400">
          <Link href="/datasource" className="text-emerald-300 underline-offset-2 hover:underline">
            Data source
          </Link>
          {" · "}
          <Link href="/data-feed" className="text-emerald-300 underline-offset-2 hover:underline">
            Data feed
          </Link>
          {" · "}
          <Link href="/feature-pipeline" className="text-emerald-300 underline-offset-2 hover:underline">
            Feature pipeline
          </Link>
        </p>

        {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div> : null}

        {!data ? (
          <div className="py-10 text-center text-sm text-slate-400">Loading data ingestion status...</div>
        ) : (
          <>
            {pos ? (
              <section className={cardShell}>
                <p className="text-xs uppercase tracking-wide text-emerald-400">Pipeline position</p>
                <div className="mt-3 flex flex-wrap gap-2 text-sm text-slate-200">
                  <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 font-mono text-xs">{pos.previous_stage}</span>
                  <span className="text-slate-500">→</span>
                  <span className="rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 font-mono text-xs text-emerald-200">{pos.current_stage}</span>
                  <span className="text-slate-500">→</span>
                  <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 font-mono text-xs">{pos.next_stage}</span>
                  <span className="text-slate-500">→</span>
                  <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 font-mono text-xs">{pos.downstream_stage}</span>
                </div>
                {data.updated_at ? <p className="mt-3 text-xs text-slate-500">Updated {new Date(data.updated_at).toLocaleString()}</p> : null}
              </section>
            ) : null}

            <section className={cardShell}>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4 lg:grid-cols-7">
                <MetricCard label="Total sources" value={summary?.total_sources ?? "—"} accent />
                <MetricCard label="Active" value={summary?.active_sources ?? "—"} />
                <MetricCard label="Warnings" value={summary?.warning_sources ?? "—"} />
                <MetricCard label="Errors" value={summary?.error_sources ?? "—"} />
                <MetricCard label="Ingested today" value={summary?.records_ingested_today ?? "—"} />
                <MetricCard label="Last ingest" value={summary?.last_ingested_at ? new Date(summary.last_ingested_at).toLocaleString() : "—"} />
                <MetricCard label="Mode" value={data.data_mode} />
              </div>
              {summary?.next_action ? <p className="mt-4 text-sm text-slate-300">{summary.next_action}</p> : null}
            </section>

            <section className={cardShell}>
              <h2 className="mb-3 text-lg font-semibold text-emerald-400">Ingestion lanes</h2>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {data.sources.map((source: DataIngestionSourceStatus) => (
                  <article key={source.key} className={cardInner}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-xs uppercase tracking-wide text-slate-500">{source.key}</p>
                        <h3 className="mt-1 text-xl font-black text-white">{source.name}</h3>
                      </div>
                      <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusClass(source.status)}`}>{source.status}</span>
                    </div>
                    <p className="mt-3 text-sm text-slate-400">
                      <span className="text-slate-500">Mode:</span> {source.ingestion_mode} · <span className="text-slate-500">Type:</span> {source.provider_type}
                    </p>
                    <p className="mt-3 text-sm leading-relaxed text-slate-300">{source.next_action}</p>
                    <div className="mt-3 grid grid-cols-2 gap-2 text-xs md:grid-cols-4">
                      <div className={miniField}>
                        <p className="uppercase tracking-wide text-slate-500">Symbols tracked</p>
                        <p className="font-mono text-emerald-200/90">{source.symbols_tracked}</p>
                      </div>
                      <div className={miniField}>
                        <p className="uppercase tracking-wide text-slate-500">Records today</p>
                        <p className="font-mono text-emerald-200/90">{source.records_ingested_today}</p>
                      </div>
                      <div className={miniField}>
                        <p className="uppercase tracking-wide text-slate-500">Freshness (s)</p>
                        <p className="font-mono text-slate-300">{source.freshness_seconds ?? "—"}</p>
                      </div>
                      <div className={miniField}>
                        <p className="uppercase tracking-wide text-slate-500">Latency (ms)</p>
                        <p className="font-mono text-slate-300">{source.latency_ms ?? "—"}</p>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {source.data_types.map((t) => (
                        <span key={t} className={pill}>
                          {t.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                    {source.errors.length > 0 ? (
                      <p className="mt-3 text-xs text-rose-300">{source.errors.join("; ")}</p>
                    ) : null}
                  </article>
                ))}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
