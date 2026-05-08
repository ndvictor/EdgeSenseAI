"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BriefcaseBusiness } from "lucide-react";
import { api } from "@/lib/api";

const shell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-5 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur";
const card = "rounded-2xl border border-emerald-400/12 bg-[#070c12]/95 p-4 transition hover:border-emerald-400/25 hover:bg-white/[0.03]";

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

function chip(status: string | null | undefined): string {
  const s = String(status ?? "unknown").toLowerCase();
  if (["ok", "pass", "ready", "connected", "true", "paper"].includes(s)) return "border-emerald-500/35 bg-emerald-500/10 text-emerald-200";
  if (["warn", "warning", "partial", "degraded", "unknown"].includes(s)) return "border-amber-500/35 bg-amber-500/10 text-amber-100";
  if (["fail", "error", "blocked", "false"].includes(s)) return "border-rose-500/35 bg-rose-500/10 text-rose-100";
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

export default function TradingDeskHubPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runtimePhase, setRuntimePhase] = useState<Record<string, unknown> | null>(null);
  const [paperSnap, setPaperSnap] = useState<Record<string, unknown> | null>(null);
  const [approvalStatus, setApprovalStatus] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [phase, paper, approvals] = await Promise.all([
          api.getRuntimePhase().catch(() => null),
          api.getAlpacaPaperSnapshot().catch(() => null),
          api.getApprovalQueueStatus().catch(() => null),
        ]);
        if (cancelled) return;
        setRuntimePhase(asRecord(phase));
        setPaperSnap(asRecord(paper));
        setApprovalStatus(asRecord(approvals));
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message || "Failed to load Trading Desk sources.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const liveAllowed = useMemo(() => {
    if (!runtimePhase) return null;
    return String(runtimePhase.live_trading_allowed ?? "unknown");
  }, [runtimePhase]);

  const humanApproval = useMemo(() => {
    if (!runtimePhase) return null;
    return String(runtimePhase.human_approval_required ?? "unknown");
  }, [runtimePhase]);

  const equity = useMemo(() => {
    const e = paperSnap?.equity;
    return typeof e === "number" ? `$${e.toLocaleString(undefined, { maximumFractionDigits: 2 })}` : null;
  }, [paperSnap]);

  return (
    <div className="mx-auto w-full max-w-[1600px] p-4 lg:p-8">
      <header className="mb-6">
        <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
          <BriefcaseBusiness className="h-4 w-4" />
          paper-first trade actions (gated)
        </div>
        <h1 className="text-3xl font-black tracking-[-0.03em] text-white lg:text-4xl">Trading Desk</h1>
        <p className="mt-2 max-w-5xl text-sm leading-relaxed text-slate-400">
          Paper-first trade action area: recommendations, paper trading lifecycle, and gated execution surfaces.
        </p>
      </header>

      <section className={`${shell} mb-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label="market phase" value={runtimePhase ? String(runtimePhase.market_phase ?? "unknown") : "unknown"} />
          <StatusPill label="paper" value={paperSnap ? String(paperSnap.status ?? "connected") : "unknown"} />
          <StatusPill label="live allowed" value={liveAllowed} />
          <StatusPill label="approval required" value={humanApproval} />
          {loading ? <span className="ml-1 text-xs text-slate-500">Loading sources…</span> : null}
          {error ? <span className="ml-1 text-xs text-rose-200/90">{error}</span> : null}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          These summaries are live API reads (runtime phase, paper broker snapshot, approvals). The hub does not fabricate trades, fills, or PnL.
        </p>
      </section>

      <section className={shell}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <HubCard title="Recommendations" href="/recommendations" description="Read-only recommendations and decision context." />
          <HubCard
            title="Paper Trading"
            href="/paper-trading"
            description="Paper lifecycle: positions, fills, and evaluation."
            meta={[
              { label: "broker", value: paperSnap ? String(paperSnap.broker ?? "alpaca_paper") : "—" },
              { label: "equity", value: equity ?? "—" },
              { label: "updated", value: paperSnap ? String(paperSnap.updated_at ?? paperSnap.timestamp ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="TradeNow (gated)"
            href="/tradenow"
            description="Execution surface; gated by runtime flags and human approval policy."
            meta={[
              { label: "live allowed", value: liveAllowed ?? "—" },
              { label: "approval required", value: humanApproval ?? "—" },
              { label: "market phase", value: runtimePhase ? String(runtimePhase.market_phase ?? "—") : "—" },
            ]}
          />
          <HubCard title="Position Monitoring" href="/position-monitoring" description="Simulated position monitoring visibility." />
          <HubCard title="Close Position Review" href="/close-position" description="Close review & exit decision visibility." />
          <HubCard
            title="Approval Queue"
            href="/approval-queue"
            description="Execution approvals and gating items."
            meta={[
              { label: "status", value: approvalStatus ? String(approvalStatus.status ?? "ok") : "unknown" },
              { label: "open", value: approvalStatus ? String(approvalStatus.open_count ?? "—") : "—" },
              { label: "updated", value: approvalStatus ? String(approvalStatus.updated_at ?? "—") : "—" },
            ]}
          />
        </div>
      </section>
    </div>
  );
}

