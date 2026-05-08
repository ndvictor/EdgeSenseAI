"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";

/** Matches GET /api/normalization/status (feed → normalized shapes → quality → feature store). */
type DataFeedStatusPayload = {
  status: string;
  data_mode?: string;
  updated_at?: string;
  summary?: {
    normalization_status?: string;
    supported_payloads?: number;
    records_normalized_today?: number;
    warning_count?: number;
    error_count?: number;
    last_normalized_at?: string | null;
    next_action?: string;
  };
  payload_types?: Array<{
    key: string;
    label: string;
    status: string;
    input_source: string;
    output_schema: string;
    required_fields: string[];
    optional_fields: string[];
    downstream_consumers: string[];
    records_normalized_today: number;
    last_normalized_at: string | null;
    warnings: string[];
    errors: string[];
    next_action: string;
  }>;
  pipeline_position?: {
    previous_stage: string;
    current_stage: string;
    next_stage: string;
    downstream_stage: string;
  };
};

export default function DataFeedPage() {
  const [data, setData] = useState<DataFeedStatusPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getNormalizationStatus()
      .then((raw) => setData(raw as unknown as DataFeedStatusPayload))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load data feed status"));
  }, []);

  const pos = data?.pipeline_position;
  const summary = data?.summary;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-6">
        <PageHeader
          eyebrow="market data feed"
          title="Data feed"
          description="Where provider quotes and bars enter the stack: ingestion, shaping into common snapshot schemas, then data quality and the feature store. Same path exercised by data readiness when you run a symbol through the pipeline."
        />

        <p className="text-sm text-slate-400">
          Run a symbol end-to-end:{" "}
          <Link href="/feature-pipeline" className="text-emerald-300 underline-offset-2 hover:underline">
            Feature pipeline
          </Link>
          {" · "}
          <Link href="/data-quality" className="text-emerald-300 underline-offset-2 hover:underline">
            Data validation
          </Link>
        </p>

        {error ? <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div> : null}

        {!data ? (
          <div className="py-10 text-center text-sm text-slate-400">Loading data feed status...</div>
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

            <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Feed / normalize status" value={summary?.normalization_status ?? "—"} accent />
              <MetricCard label="Payload types" value={summary?.supported_payloads ?? "—"} />
              <MetricCard label="Records today" value={summary?.records_normalized_today ?? "—"} />
              <MetricCard label="Warnings / errors" value={`${summary?.warning_count ?? 0} / ${summary?.error_count ?? 0}`} />
            </section>

            {summary?.next_action ? <p className="text-sm text-slate-300">{summary.next_action}</p> : null}

            <section className={cardShell}>
              <h2 className="mb-3 text-lg font-semibold text-emerald-400">Payload coverage</h2>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[800px] text-left text-sm">
                  <thead className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Key</th>
                      <th className="py-2 pr-3">Label</th>
                      <th className="py-2 pr-3">Status</th>
                      <th className="py-2 pr-3">Schema</th>
                      <th className="py-2">Next action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data.payload_types ?? []).map((p) => (
                      <tr key={p.key} className="border-b border-white/5 text-slate-200">
                        <td className="py-2 pr-3 font-mono text-emerald-200/90">{p.key}</td>
                        <td className="py-2 pr-3">{p.label}</td>
                        <td className="py-2 pr-3">{p.status}</td>
                        <td className="py-2 pr-3 font-mono text-xs text-slate-400">{p.output_schema}</td>
                        <td className="py-2 text-xs text-slate-400">{p.next_action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
