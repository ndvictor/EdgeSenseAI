"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type DataQualityCheckStatus, type DataQualityStatusResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";

function formatNumber(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString();
}

function statusBadge(status: string) {
  const v = status.toLowerCase();
  if (v === "pass" || v === "ready" || v === "ok") return "border-emerald-500/50 bg-emerald-500/10 text-emerald-300";
  if (v === "warn" || v === "warning" || v === "partial" || v === "degraded") return "border-amber-500/50 bg-amber-500/10 text-amber-200";
  if (v === "fail" || v === "failed" || v === "error" || v === "blocked") return "border-rose-500/50 bg-rose-500/10 text-rose-200";
  if (v === "disabled" || v === "skipped") return "border-slate-600 bg-slate-600/10 text-slate-300";
  return "border-slate-600 bg-slate-600/10 text-slate-300";
}

function chip(text: string, accent = false) {
  return (
    <span
      key={text}
      className={
        accent
          ? "rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]"
          : "rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[10px] font-bold uppercase text-slate-300"
      }
    >
      {text}
    </span>
  );
}

function safeList(value: unknown): string[] {
  if (Array.isArray(value)) return value.map((v) => String(v));
  return [];
}

export default function DataQualityPage() {
  const [data, setData] = useState<DataQualityStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getDataQualityStatus()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load data quality status"));
  }, []);

  const checks: DataQualityCheckStatus[] = data?.checks ?? [];

  const computed = useMemo(() => {
    const checksConfigured = checks.length;
    const pass = checks.reduce((acc, c) => acc + (c.pass_count ?? 0), 0);
    const warnings = checks.reduce((acc, c) => acc + (c.warn_count ?? 0), 0);
    const fails = checks.reduce((acc, c) => acc + (c.fail_count ?? 0), 0);
    const symbolsCheckedToday = pass + warnings + fails;
    return { checksConfigured, symbolsCheckedToday, pass, warnings, fails };
  }, [checks]);

  const summary = data?.summary;
  const overallStatus = summary?.status ?? data?.status ?? "—";

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1500px] space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <PageHeader
            eyebrow="pipeline"
            title="Data Quality"
            description="Validates freshness, completeness, spread quality, provider errors, and mock-data safety before features and signals are generated."
          />

          {data?.data_mode === "summary" ? (
            <span className="mt-1 w-fit rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-cyan-200">
              summary
            </span>
          ) : null}
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>
        ) : null}

        {!data ? (
          <div className="py-10 text-center text-sm text-slate-400">Loading data quality status...</div>
        ) : (
          <>
            <section className={cardShell}>
              <p className="text-xs uppercase tracking-wide text-emerald-400">Pipeline position</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-200">
                {chip("Normalization")}
                <span className="text-slate-500">→</span>
                {chip("Data Quality", true)}
                <span className="text-slate-500">→</span>
                {chip("Feature Store")}
                <span className="text-slate-500">→</span>
                {chip("Signals")}
              </div>
              {data.updated_at ? <p className="mt-2 text-xs text-slate-500">Updated {new Date(data.updated_at).toLocaleString()}</p> : null}
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
              <MetricCard label="Status" value={overallStatus} accent />
              <MetricCard label="Checks Configured" value={formatNumber(summary?.checks_configured ?? computed.checksConfigured)} />
              <MetricCard label="Symbols Checked Today" value={formatNumber(summary?.symbols_checked_today ?? computed.symbolsCheckedToday)} />
              <MetricCard label="Pass" value={formatNumber(summary?.pass ?? computed.pass)} />
              <MetricCard label="Warnings" value={formatNumber(summary?.warnings ?? computed.warnings)} />
              <MetricCard label="Fails" value={formatNumber(summary?.fails ?? computed.fails)} />
            </section>

            <section className={cardShell}>
              <table className="w-full min-w-[1500px] text-left text-sm">
                <thead className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-emerald-400">
                  <tr>
                    <th className="px-4 py-3">Check</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Description</th>
                    <th className="px-4 py-3">Input Stage</th>
                    <th className="px-4 py-3">Blocks Downstream</th>
                    <th className="px-4 py-3">Downstream Consumers</th>
                    <th className="px-4 py-3">Pass</th>
                    <th className="px-4 py-3">Warn</th>
                    <th className="px-4 py-3">Fail</th>
                    <th className="px-4 py-3">Last Checked</th>
                    <th className="px-4 py-3">Next Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-950/40">
                  {checks.length ? (
                    checks.map((c) => (
                      <tr key={c.check} className="align-top hover:bg-white/[0.03]">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{c.check}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusBadge(c.status)}`}>
                            {c.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          <div className="max-w-[28rem] leading-relaxed">{c.description ?? "—"}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-300">{c.input_stage ?? "—"}</td>
                        <td className="px-4 py-3 text-slate-300">{typeof c.blocks_downstream === "boolean" ? (c.blocks_downstream ? "Yes" : "No") : "—"}</td>
                        <td className="px-4 py-3 text-slate-300">
                          {safeList(c.downstream_consumers).length ? safeList(c.downstream_consumers).join(", ") : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(c.pass_count)}</td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(c.warn_count)}</td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(c.fail_count)}</td>
                        <td className="px-4 py-3 text-slate-300">
                          {c.last_checked ? new Date(c.last_checked).toLocaleString() : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          <div className="max-w-[26rem] leading-relaxed">{c.next_action ?? "—"}</div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="px-4 py-8 text-center text-sm text-slate-400" colSpan={11}>
                        No check status available.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </section>
          </>
        )}
      </div>
    </div>
  );
}

