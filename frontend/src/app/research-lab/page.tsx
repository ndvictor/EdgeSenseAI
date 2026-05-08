"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FlaskConical } from "lucide-react";
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

export default function ResearchLabHubPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [qlibStatus, setQlibStatus] = useState<Record<string, unknown> | null>(null);
  const [qlibAutomation, setQlibAutomation] = useState<Record<string, unknown> | null>(null);
  const [proofStatus, setProofStatus] = useState<Record<string, unknown> | null>(null);
  const [modelEvidenceStatus, setModelEvidenceStatus] = useState<Record<string, unknown> | null>(null);
  const [modelRegistry, setModelRegistry] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [qs, qa, ps, me, mr] = await Promise.all([
          api.getQlibStatus().catch(() => null),
          api.getQlibAutomationStatus().catch(() => null),
          api.getProofRegistryStatus().catch(() => null),
          api.getModelEvidenceStatus().catch(() => null),
          api.getModelRunRegistry().catch(() => null),
        ]);
        if (cancelled) return;
        setQlibStatus(asRecord(qs));
        setQlibAutomation(asRecord(qa));
        setProofStatus(asRecord(ps));
        setModelEvidenceStatus(asRecord(me));
        setModelRegistry(asRecord(mr));
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message || "Failed to load Research Lab sources.");
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
          <FlaskConical className="h-4 w-4" />
          research visibility & evidence
        </div>
        <h1 className="text-3xl font-black tracking-[-0.03em] text-white lg:text-4xl">Research Lab</h1>
        <p className="mt-2 max-w-5xl text-sm leading-relaxed text-slate-400">
          Strategy/model research visibility: Qlib status & artifacts, proof/backtests, registries, and evidence.
        </p>
      </header>

      <section className={`${shell} mb-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label="qlib" value={String(qlibStatus?.status ?? "unknown")} />
          <StatusPill label="proof" value={String(proofStatus?.status ?? "unknown")} />
          <StatusPill label="model evidence" value={String(modelEvidenceStatus?.status ?? "unknown")} />
          <StatusPill label="registry" value={String(modelRegistry?.status ?? "unknown")} />
          {loading ? <span className="ml-1 text-xs text-slate-500">Loading sources…</span> : null}
          {error ? <span className="ml-1 text-xs text-rose-200/90">{error}</span> : null}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          These summaries are live API reads (Qlib/proof/evidence/registries). If a service is unavailable, the hub reports unknown/partial rather than inventing values.
        </p>
      </section>

      <section className={shell}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <HubCard
            title="Research Evidence"
            href="/research-evidence"
            description="Evidence registry and research artifacts."
            meta={[{ label: "status", value: "source-backed" }]}
          />
          <HubCard title="Backtesting" href="/backtesting" description="Backtesting evidence and status." meta={[{ label: "status", value: "source-backed" }]} />
          <HubCard title="Model Lab" href="/model/lab" description="Model lab and debug views." meta={[{ label: "status", value: "source-backed" }]} />
          <HubCard
            title="Model Registry"
            href="/model-registry"
            description="Registered models and readiness."
            meta={[
              { label: "status", value: modelRegistry ? String(modelRegistry.status ?? "ok") : "unknown" },
              { label: "runs", value: modelRegistry ? String((modelRegistry.runs as unknown[] | undefined)?.length ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Qlib Status"
            href="/workflow-runbook"
            description="Qlib visibility lives in workflow panels; this hub shows Qlib status sources."
            meta={[
              { label: "qlib", value: qlibStatus ? String(qlibStatus.status ?? "unknown") : "unknown" },
              { label: "automation", value: qlibAutomation ? String(qlibAutomation.status ?? "unknown") : "unknown" },
            ]}
          />
          <HubCard title="Lab Inventory" href="/lab" description="Internal inventory view for research/workflow components." />
        </div>
      </section>
    </div>
  );
}

