"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";

const shell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-5 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur";
const card = "rounded-2xl border border-emerald-400/12 bg-[#070c12]/95 p-4 transition hover:border-emerald-400/25 hover:bg-white/[0.03]";

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

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

export default function PerformanceGovernanceHubPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<Record<string, unknown> | null>(null);
  const [auditStatus, setAuditStatus] = useState<Record<string, unknown> | null>(null);
  const [govStatus, setGovStatus] = useState<Record<string, unknown> | null>(null);
  const [cadence, setCadence] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [appr, audit, gov, cad] = await Promise.all([
          api.getApprovalQueueStatus().catch(() => null),
          api.getAuditLogStatus().catch(() => null),
          api.getWorkflowGovernanceStatus().catch(() => null),
          api.getRuntimeCadence().catch(() => null),
        ]);
        if (cancelled) return;
        setApprovalStatus(asRecord(appr));
        setAuditStatus(asRecord(audit));
        setGovStatus(asRecord(gov));
        setCadence(asRecord(cad));
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message || "Failed to load governance sources.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="mx-auto w-full max-w-[1600px] p-4 lg:p-8">
      <header className="mb-6">
        <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
          <ShieldCheck className="h-4 w-4" />
          safety, review, audit, learning
        </div>
        <h1 className="text-3xl font-black tracking-[-0.03em] text-white lg:text-4xl">Performance & Governance</h1>
        <p className="mt-2 max-w-5xl text-sm leading-relaxed text-slate-400">
          Workflow safety surfaces: approvals, audit trail, governance, execution monitor, and post-trade learning.
        </p>
      </header>

      <section className={`${shell} mb-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label="approvals" value={String(approvalStatus?.status ?? "unknown")} />
          <StatusPill label="audit" value={String(auditStatus?.status ?? "unknown")} />
          <StatusPill label="governance" value={String(govStatus?.status ?? "unknown")} />
          <StatusPill label="cadence" value={cadence ? String(cadence.market_phase ?? cadence.active_loop ?? "unknown") : "unknown"} />
          {loading ? <span className="ml-1 text-xs text-slate-500">Loading sources…</span> : null}
          {error ? <span className="ml-1 text-xs text-rose-200/90">{error}</span> : null}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          Live read-only sources: approval queue, audit log, governance status, runtime cadence. No synthetic compliance metrics.
        </p>
      </section>

      <section className={shell}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <HubCard
            title="Approval Queue"
            href="/approval-queue"
            description="Execution approval and gating queue."
            meta={[
              { label: "open", value: approvalStatus ? String(approvalStatus.open_count ?? "—") : "—" },
              { label: "updated", value: approvalStatus ? String(approvalStatus.updated_at ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Audit Log"
            href="/audit-log"
            description="Operational audit trail and events."
            meta={[
              { label: "events", value: auditStatus ? String(auditStatus.event_count ?? "—") : "—" },
              { label: "updated", value: auditStatus ? String(auditStatus.updated_at ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Workflow Governance"
            href="/workflow-governance"
            description="Governance state, policies, and readiness."
            meta={[
              { label: "status", value: govStatus ? String(govStatus.status ?? "unknown") : "unknown" },
              { label: "updated", value: govStatus ? String(govStatus.updated_at ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Auto-Execution Monitor"
            href="/auto-execution-monitor"
            description="Visibility into gated execution automation."
            meta={[
              { label: "live allowed", value: cadence ? String(cadence.live_trading_allowed ?? "—") : "—" },
              { label: "approval required", value: cadence ? String(cadence.human_approval_required ?? "—") : "—" },
            ]}
          />
          <HubCard title="Post-Trade Evaluation" href="/post-trade-evaluation" description="Evaluation and scoring after paper trade closes." />
          <HubCard title="Learning Loop" href="/learning-loop" description="Learning decisions and promotion controls." />
        </div>
      </section>
    </div>
  );
}

