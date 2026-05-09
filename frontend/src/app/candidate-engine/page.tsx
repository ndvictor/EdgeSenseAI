"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type CandidateSourceStatus, type CandidatesStatusResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";
import UniversePage from "@/app/universe/page";
import CandidatesPage from "@/app/candidates/page";
import SignalsPage from "@/app/signals/page";

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

export default function CandidateEnginePage() {
  const [data, setData] = useState<CandidatesStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<"candidate_engine" | "universe" | "candidates" | "signals">("candidate_engine");

  useEffect(() => {
    api
      .getCandidatesStatus()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Failed to load candidates status"));
  }, []);

  const sources: CandidateSourceStatus[] = data?.candidate_sources ?? [];

  const computed = useMemo(() => {
    const candidateSources = sources.length;
    const activeCandidates = sources.reduce((acc, s) => acc + (s.active_count ?? 0), 0);
    const rankedCandidates = sources.reduce((acc, s) => acc + (s.ranked_count ?? 0), 0);
    const blockedCandidates = sources.reduce((acc, s) => acc + (s.blocked_count ?? 0), 0);
    return { candidateSources, activeCandidates, rankedCandidates, blockedCandidates };
  }, [sources]);

  const summary = data?.summary;
  const overallStatus = summary?.status ?? data?.status ?? "—";

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1500px] space-y-4">
        <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
          <PageHeader
            eyebrow="pipeline"
            title="Candidate Engine"
            description="Promotes qualified signals and watchlist symbols into a rankable trade candidate universe for recommendations, risk review, and execution readiness."
          />

          {data?.data_mode === "summary" ? (
            <span className="mt-1 w-fit rounded-full border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 text-[10px] font-bold uppercase text-cyan-200">
              summary
            </span>
          ) : null}
        </div>

        <div className="rounded-2xl border border-sky-400/20 bg-sky-500/10 px-4 py-3 text-sm text-sky-100">
          Candidate Universe is a manual research tool. Use Workflow Runbook to run the autonomous agent workflow.
        </div>

        <div className="flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          {[
            ["candidate_engine", "Candidate Engine"],
            ["universe", "Universe"],
            ["candidates", "Candidates"],
            ["signals", "Signals"],
          ].map(([key, label]) => (
            <button
              key={key}
              type="button"
              onClick={() => setTab(key as typeof tab)}
              className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                tab === key
                  ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                  : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>
        ) : null}

        {tab === "universe" ? (
          <UniversePage />
        ) : tab === "candidates" ? (
          <CandidatesPage />
        ) : tab === "signals" ? (
          <SignalsPage />
        ) : !data ? (
          <div className="py-10 text-center text-sm text-slate-400">Loading candidate engine status...</div>
        ) : (
          <>
            <section className={cardShell}>
              <p className="text-xs uppercase tracking-wide text-emerald-400">Pipeline position</p>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-slate-200">
                {chip("Signals")}
                <span className="text-slate-500">→</span>
                {chip("Candidates", true)}
                <span className="text-slate-500">→</span>
                {chip("Recommendations")}
                <span className="text-slate-500">→</span>
                {chip("Risk")}
              </div>
              {data.updated_at ? <p className="mt-2 text-xs text-slate-500">Updated {new Date(data.updated_at).toLocaleString()}</p> : null}
            </section>

            <section className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
              <MetricCard label="Status" value={overallStatus} accent />
              <MetricCard label="Candidate Sources" value={formatNumber(summary?.candidate_sources ?? computed.candidateSources)} />
              <MetricCard label="Active Candidates" value={formatNumber(summary?.active_candidates ?? computed.activeCandidates)} />
              <MetricCard label="Ranked Candidates" value={formatNumber(summary?.ranked_candidates ?? computed.rankedCandidates)} />
              <MetricCard label="Blocked Candidates" value={formatNumber(summary?.blocked_candidates ?? computed.blockedCandidates)} />
            </section>

            <section className={cardShell}>
              <table className="w-full min-w-[1500px] text-left text-sm">
                <thead className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-emerald-400">
                  <tr>
                    <th className="px-4 py-3">Candidate Source</th>
                    <th className="px-4 py-3">Status</th>
                    <th className="px-4 py-3">Description</th>
                    <th className="px-4 py-3">Input Stage</th>
                    <th className="px-4 py-3">Candidate Types</th>
                    <th className="px-4 py-3">Downstream Consumers</th>
                    <th className="px-4 py-3">Active</th>
                    <th className="px-4 py-3">Ranked</th>
                    <th className="px-4 py-3">Blocked</th>
                    <th className="px-4 py-3">Last Candidate At</th>
                    <th className="px-4 py-3">Warnings</th>
                    <th className="px-4 py-3">Errors</th>
                    <th className="px-4 py-3">Next Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-emerald-950/40">
                  {sources.length ? (
                    sources.map((s, index) => (
                      <tr key={`${s.candidate_source}-${index}`} className="align-top hover:bg-white/[0.03]">
                        <td className="px-4 py-3">
                          <div className="font-semibold text-white">{s.candidate_source}</div>
                        </td>
                        <td className="px-4 py-3">
                          <span className={`inline-flex rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusBadge(s.status)}`}>
                            {s.status}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          <div className="max-w-[28rem] leading-relaxed">{s.description ?? "—"}</div>
                        </td>
                        <td className="px-4 py-3 text-slate-300">{s.input_stage ?? "—"}</td>
                        <td className="px-4 py-3 text-slate-300">
                          {safeList(s.candidate_types).length ? safeList(s.candidate_types).join(", ") : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">
                          {safeList(s.downstream_consumers).length ? safeList(s.downstream_consumers).join(", ") : "—"}
                        </td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(s.active_count)}</td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(s.ranked_count)}</td>
                        <td className="px-4 py-3 text-slate-300">{formatNumber(s.blocked_count)}</td>
                        <td className="px-4 py-3 text-slate-300">{s.last_candidate_at ? new Date(s.last_candidate_at).toLocaleString() : "—"}</td>
                        <td className="px-4 py-3">
                          {s.warnings?.length ? (
                            <ul className="space-y-1 text-xs text-amber-200">
                              {s.warnings.slice(0, 3).map((w: string) => (
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
                          {s.errors?.length ? (
                            <ul className="space-y-1 text-xs text-rose-200">
                              {s.errors.slice(0, 3).map((e: string) => (
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
                          <div className="max-w-[26rem] leading-relaxed">{s.next_action ?? "—"}</div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td className="px-4 py-8 text-center text-sm text-slate-400" colSpan={13}>
                        No candidate source status available.
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

