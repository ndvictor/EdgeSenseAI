"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type SignalFamilyStatus, type SignalsStatusResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";

function formatNumber(value: number | null | undefined) {
  if (value == null) return "—";
  return value.toLocaleString();
}

function statusBadge(status: string) {
  const v = status.toLowerCase();
  if (v === "ready" || v === "ok" || v === "pass") return "border-emerald-500/50 bg-emerald-500/10 text-emerald-300";
  if (v === "warning" || v === "warn" || v === "partial" || v === "degraded") return "border-amber-500/50 bg-amber-500/10 text-amber-200";
  if (v === "error" || v === "fail" || v === "failed" || v === "blocked") return "border-rose-500/50 bg-rose-500/10 text-rose-200";
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

export default function SignalEnginePage() {
  const [data, setData] = useState<SignalsStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSignalsStatus()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load signals status"));
  }, []);

  const families: SignalFamilyStatus[] = data?.signal_families ?? [];

  const computed = useMemo(() => {
    const signalFamilies = families.length;
    const activeSignals = families.reduce((acc, f) => acc + (f.active_count ?? 0), 0);
    const warnings = families.reduce((acc, f) => acc + (f.warnings?.length ?? 0), 0);
    const errors = families.reduce((acc, f) => acc + (f.errors?.length ?? 0), 0);
    return { signalFamilies, activeSignals, warnings, errors };
  }, [families]);

  const summary = data?.summary;
  const overallStatus = summary?.status ?? data?.status ?? "—";

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1500px] space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <PageHeader
            eyebrow="pipeline"
            title="Signal Engine"
            description="Converts feature-store outputs into edge signals such as RVOL spikes, VWAP reactions, breakouts, regime-aware momentum, and catalyst-confirmed setups."
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
          <div className="py-10 text-center text-sm text-slate-400">Loading signal engine status...</div>
        ) : (
          <>
            <section className={cardShell}>
              <p className="text-xs uppercase tracking-wide text-emerald-400">Pipeline position</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-200">
                {chip("Feature Store")}
                <span className="text-slate-500">→</span>
                {chip("Signals", true)}
                <span className="text-slate-500">→</span>
                {chip("Candidates")}
                <span className="text-slate-500">→</span>
                {chip("Recommendations")}
              </div>
              {data.updated_at ? <p className="mt-2 text-xs text-slate-500">Updated {new Date(data.updated_at).toLocaleString()}</p> : null}
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
              <MetricCard label="Status" value={overallStatus} accent />
              <MetricCard label="Signal Families" value={formatNumber(summary?.signal_families ?? computed.signalFamilies)} />
              <MetricCard label="Active Signals" value={formatNumber(summary?.active_signals ?? computed.activeSignals)} />
              <MetricCard label="Warnings" value={formatNumber(summary?.warnings ?? computed.warnings)} />
              <MetricCard label="Errors" value={formatNumber(summary?.errors ?? computed.errors)} />
            </section>

            <section className={cardShell}>
              <table className="w-full min-w-[1500px] text-left text-sm">
                <thead className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-emerald-400">
                  <tr>
                    <th className="px-4 py-3">Signal Family</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Description</th>
                    <th className="px-4 py-3">Input Stage</th>
                    <th className="px-4 py-3">Required Features</th>
                    <th className="px-4 py-3">Downstream Consumers</th>
                    <th className="px-4 py-3">Active Count</th>
                    <th className="px-4 py-3">Last Signal At</th>
                    <th className="px-4 py-3">Warnings</th>
                    <th className="px-4 py-3">Errors</th>
                    <th className="px-4 py-3">Next Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-950/40">
                  {families.length ? (
                    families.map((f) => (
                      <tr key={f.signal_family} className="align-top hover:bg-white/[0.03]">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{f.signal_family}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusBadge(f.status)}`}>
                            {f.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          <div className="max-w-[28rem] leading-relaxed">{f.description ?? "—"}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-300">{f.input_stage ?? "—"}</td>
                        <td className="px-4 py-3 text-slate-300">
                          {safeList(f.required_features).length ? safeList(f.required_features).slice(0, 12).join(", ") : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {safeList(f.downstream_consumers).length ? safeList(f.downstream_consumers).join(", ") : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(f.active_count)}</td>
                        <td className="px-4 py-3 text-slate-300">{f.last_signal_at ? new Date(f.last_signal_at).toLocaleString() : "—"}</td>
                        <td className="px-4 py-3">
                          {f.warnings?.length ? (
                            <ul className="space-y-1 text-xs text-amber-200">
                              {f.warnings.slice(0, 3).map((w: string) => (
                                <li key={w} className="max-w-[20rem] truncate">
                                  {w}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {f.errors?.length ? (
                            <ul className="space-y-1 text-xs text-rose-200">
                              {f.errors.slice(0, 3).map((e: string) => (
                                <li key={e} className="max-w-[20rem] truncate">
                                  {e}
                                </li>
                              ))}
                            </ul>
                          ) : (
                            <span className="text-slate-500">—</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          <div className="max-w-[26rem] leading-relaxed">{f.next_action ?? "—"}</div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="px-4 py-8 text-center text-sm text-slate-400" colSpan={11}>
                        No signal family status available.
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

