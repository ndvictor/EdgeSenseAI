"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Radar } from "lucide-react";
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

export default function MarketRadarHubPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [marketRegime, setMarketRegime] = useState<Record<string, unknown> | null>(null);
  const [liveWatchlist, setLiveWatchlist] = useState<Record<string, unknown> | null>(null);
  const [signalsStatus, setSignalsStatus] = useState<Record<string, unknown> | null>(null);
  const [candidatesStatus, setCandidatesStatus] = useState<Record<string, unknown> | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [reg, watch, sig, cand] = await Promise.all([
          api.getLatestMarketRegime().catch(() => null),
          api.getLiveWatchlist().catch(() => null),
          api.getSignalsStatus().catch(() => null),
          api.getCandidatesStatus().catch(() => null),
        ]);
        if (cancelled) return;
        setMarketRegime(asRecord(reg));
        setLiveWatchlist(asRecord(watch));
        setSignalsStatus(asRecord(sig));
        setCandidatesStatus(asRecord(cand));
      } catch (e) {
        if (cancelled) return;
        setError((e as Error).message || "Failed to load Market Radar status.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const regimeLabel = useMemo(() => {
    const r = marketRegime;
    if (!r) return "unknown";
    return String(r.regime ?? r.status ?? "unknown");
  }, [marketRegime]);

  const watchSummary = useMemo(() => asRecord(liveWatchlist?.summary), [liveWatchlist]);

  return (
    <div className="mx-auto w-full max-w-[1600px] p-4 lg:p-8">
      <header className="mb-6">
        <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
          <Radar className="h-4 w-4" />
          market scanning & opportunity discovery
        </div>
        <h1 className="text-3xl font-black tracking-[-0.03em] text-white lg:text-4xl">Market Radar</h1>
        <p className="mt-2 max-w-5xl text-sm leading-relaxed text-slate-400">
          Market context used by the workflow: regime, candidate universe, live watchlist, signals, and exploration tools.
        </p>
      </header>

      <section className={`${shell} mb-4`}>
        <div className="flex flex-wrap items-center gap-2">
          <StatusPill label="regime" value={regimeLabel} />
          <StatusPill label="signals" value={String(signalsStatus?.status ?? "unknown")} />
          <StatusPill label="candidates" value={String(candidatesStatus?.status ?? "unknown")} />
          <StatusPill label="watchlist" value={String(watchSummary?.status ?? liveWatchlist?.status ?? "unknown")} />
          {loading ? <span className="ml-1 text-xs text-slate-500">Loading sources…</span> : null}
          {error ? <span className="ml-1 text-xs text-rose-200/90">{error}</span> : null}
        </div>
        <p className="mt-3 text-xs text-slate-500">
          These summaries are live API reads (no non_realed metrics). If a source is unavailable, it reports unknown/partial rather than inventing values.
        </p>
      </section>

      <section className={shell}>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          <HubCard
            title="Market Regime"
            href="/market-regime"
            description="Regime, confidence, inputs, and allowed/blocked strategy families."
            meta={[
              { label: "status", value: marketRegime ? String(marketRegime.status ?? "ok") : "unknown" },
              { label: "confidence", value: marketRegime ? String(marketRegime.confidence ?? "—") : "—" },
              { label: "checked_at", value: marketRegime ? String(marketRegime.checked_at ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Candidate Engine"
            href="/candidate-engine"
            description="Candidate discovery and prioritization feeding the watchlist."
            meta={[
              { label: "status", value: candidatesStatus ? String(candidatesStatus.status ?? "ok") : "unknown" },
              { label: "active", value: candidatesStatus ? String(candidatesStatus.active_count ?? "—") : "—" },
              { label: "updated", value: candidatesStatus ? String(candidatesStatus.updated_at ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Live Watchlist"
            href="/live-watchlist"
            description="Current candidate watchlist used by the workflow spine."
            meta={[
              { label: "rows", value: watchSummary ? String(watchSummary.row_count ?? "—") : "—" },
              { label: "symbols", value: watchSummary ? String(watchSummary.distinct_symbols ?? "—") : "—" },
              { label: "updated", value: watchSummary ? String(watchSummary.last_updated ?? "—") : "—" },
            ]}
          />
          <HubCard
            title="Signals"
            href="/signals"
            description="Signals & scoring visibility."
            meta={[
              { label: "status", value: signalsStatus ? String(signalsStatus.status ?? "ok") : "unknown" },
              { label: "active", value: signalsStatus ? String(signalsStatus.active_signals ?? "—") : "—" },
              { label: "updated", value: signalsStatus ? String(signalsStatus.updated_at ?? "—") : "—" },
            ]}
          />
          <HubCard title="Universe" href="/universe" description="Universe and candidates browsing." />
          <HubCard title="Candidates" href="/candidates" description="Candidate list and status detail." />
        </div>
      </section>
    </div>
  );
}

