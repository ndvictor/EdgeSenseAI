"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Workflow } from "lucide-react";
import { api, getRunbookLatestBlob, type DataQualityStatusResponse, type WorkflowRunbookLatestResponse } from "@/lib/api";

const shell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-5 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur";
const card = "rounded-2xl border border-emerald-400/12 bg-[#070c12]/95 p-4 transition hover:border-emerald-400/25 hover:bg-white/[0.03]";

function chip(status: string | null | undefined): string {
  const s = String(status ?? "unknown").toLowerCase();
  if (["ok", "pass", "ready", "connected"].includes(s)) return "border-emerald-500/35 bg-emerald-500/10 text-emerald-200";
  if (["warn", "warning", "partial", "degraded"].includes(s)) return "border-amber-500/35 bg-amber-500/10 text-amber-100";
  if (["fail", "error", "blocked"].includes(s)) return "border-rose-500/35 bg-rose-500/10 text-rose-100";
  return "border-slate-600/60 bg-slate-800/40 text-slate-300";
}

function StatusPill({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-semibold uppercase ${chip(value)}`}>
      <span className="text-[10px] tracking-[0.22em] opacity-80">{label}</span>
      <span className="tracking-[0.12em]">{String(value ?? "unknown").replaceAll("_", " ")}</span>
    </div>
  );
}

function HubCard({
  title,
  href,
  description,
  meta,
}: {
  title: string;
  href: string;
  description: string;
  meta?: Array<{ label: string; value: string | number | null | undefined }>;
}) {
  return (
    <Link href={href} className={card}>
      <div className="text-sm font-semibold text-white">{title}</div>
      <div className="mt-1 text-xs leading-relaxed text-slate-400">{description}</div>
      {meta?.length ? (
        <div className="mt-3 space-y-1 text-[11px] text-slate-400">
          {meta.slice(0, 3).map((m) => (
            <div key={m.label} className="flex items-center justify-between gap-3">
              <span className="text-slate-500">{m.label}</span>
              <span className="font-medium text-slate-200">{String(m.value ?? "—")}</span>
            </div>
          ))}
        </div>
      ) : null}
      <div className="mt-3 text-[11px] font-semibold text-emerald-300/90">{href}</div>
    </Link>
  );
}

export default function StrategyWorkflowHubPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runbookLatest, setRunbookLatest] = useState<WorkflowRunbookLatestResponse | null>(null);
  const [dqStatus, setDqStatus] = useState<DataQualityStatusResponse | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [rb, dq] = await Promise.all([api.getWorkflowRunbookLatest().catch(() => null), api.getDataQualityStatus().catch(() => null)]);
        if (cancelled) return;
        setRunbookLatest(rb);
        setDqStatus(dq);
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message || "Failed to load Strategy Workflow sources.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const latestBlob = useMemo(() => (runbookLatest ? getRunbookLatestBlob(runbookLatest) : null), [runbookLatest]);
  const watchSummary = useMemo(() => {
    const b = latestBlob?.watchlist_builder;
    if (!b || typeof b !== "object") return null;
    const r = b as Record<string, unknown>;
    const s = r.summary;
    return s && typeof s === "object" ? (s as Record<string, unknown>) : null;
  }, [latestBlob]);

  const dqRollup = useMemo(() => {
    const s = dqStatus?.summary;
    return s?.rollup_status ?? s?.status ?? null;
  }, [dqStatus]);

  return (
    <div className="mx-auto w-full max-w-[1600px] p-4 lg:p-8">
      <header className="mb-6">
        <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
          <Workflow className="h-4 w-4" />
          14-stage autonomous workflow hub
        </div>
        <h1 className="text-3xl font-black tracking-[-0.03em] text-white lg:text-4xl">Strategy Workflow</h1>
        <p className="mt-2 max-w-5xl text-sm leading-relaxed text-slate-400">
          Runbook + stage visibility. Low-level workflow pages remain accessible here, but are not top-level sidebar items.
        </p>
      </header>

      <section className={`${shell} mb-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label="runbook" value={runbookLatest ? String(runbookLatest.status ?? "ok") : "unknown"} />
          <StatusPill label="data quality" value={dqRollup ? String(dqRollup) : "unknown"} />
          <StatusPill label="watchlist" value={watchSummary ? "present" : "unknown"} />
          <StatusPill label="market scan" value={latestBlob?.market_condition_scanner ? "present" : "unknown"} />
          {loading ? <span className="ml-1 text-xs text-slate-500">Loading sources…</span> : null}
          {error ? <span className="ml-1 text-xs text-rose-200/90">{error}</span> : null}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          These panels are sourced from <code className="text-emerald-200/80">/api/workflow-runbook/latest</code> and <code className="text-emerald-200/80">/api/data-quality/status</code>.
        </p>
      </section>

      <section className={shell}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <HubCard
            title="Workflow Runbook"
            href="/workflow-runbook"
            description="14-stage timeline + pipeline visibility panels."
            meta={[
              { label: "data_mode", value: runbookLatest ? String(runbookLatest.data_mode ?? "—") : "—" },
              { label: "watchlist rows", value: watchSummary ? String(watchSummary.row_count ?? "—") : "—" },
              { label: "updated", value: watchSummary ? String(watchSummary.last_updated ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Data Quality"
            href="/data-quality"
            description="Stage 2 data intake & quality diagnostics."
            meta={[
              { label: "rollup", value: dqRollup ? String(dqRollup) : "—" },
              { label: "sampled", value: dqStatus?.summary ? String(dqStatus.summary.symbols_sampled ?? dqStatus.summary.symbols_checked_today ?? "—") : "—" },
              { label: "blockers", value: dqStatus?.summary?.pipeline_blockers?.length ?? "—" },
            ]}
          />
          <HubCard
            title="Session Router"
            href="/session-router"
            description="Stage 3 session routing visibility."
            meta={[{ label: "latest", value: latestBlob?.session_router ? "present" : "—" }]}
          />
          <HubCard
            title="Workflow Router"
            href="/workflow-router"
            description="Stage 5 workflow routing visibility."
            meta={[{ label: "latest", value: latestBlob?.workflow_router ? "present" : "—" }]}
          />
          <HubCard
            title="Strategy Eligibility"
            href="/strategy-eligibility"
            description="Stage 7D requirements & eligibility checks."
            meta={[{ label: "latest", value: latestBlob?.strategy_eligibility ? "present" : "—" }]}
          />
          <HubCard
            title="Trigger Monitoring"
            href="/trigger-monitoring"
            description="Stage 8 trigger evaluation and gating."
            meta={[{ label: "latest", value: latestBlob?.trigger_monitoring ? "present" : "—" }]}
          />
          <HubCard
            title="Execution Planner"
            href="/execution-planner"
            description="Stage 9 plan + paper-first execution visibility."
            meta={[{ label: "latest", value: latestBlob?.execution_planner ? "present" : "—" }]}
          />
        </div>
      </section>
    </div>
  );
}

