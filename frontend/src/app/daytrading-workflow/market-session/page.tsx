"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

type WorkerStatus = Record<string, unknown>;

function apiUrl(path: string): string {
  if (!API_BASE) throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  return `${API_BASE}${path}`;
}

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(apiUrl(path));
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${path} failed with ${response.status}${body ? `: ${body.slice(0, 240)}` : ""}`);
  }
  return (await response.json()) as T;
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function pick(source: unknown, key: string): unknown {
  if (!source || typeof source !== "object") return undefined;
  return (source as Record<string, unknown>)[key];
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 border-b border-white/[0.06] py-2 last:border-0">
      <span className="w-44 shrink-0 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</span>
      <span className="min-w-0 flex-1 break-words font-mono text-sm text-slate-100">{valueText(value)}</span>
    </div>
  );
}

function Card({ title, endpoint, children }: { title: string; endpoint: string; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-cyan-400/15 bg-black/35 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <div className="mb-4">
        <h2 className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-100">{title}</h2>
        <p className="mt-1 font-mono text-[11px] text-cyan-300/70">{endpoint}</p>
      </div>
      {children}
    </section>
  );
}

export default function MarketSessionPage() {
  const [worker, setWorker] = useState<WorkerStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getJson<WorkerStatus>("/api/worker-status/latest");
      setWorker(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const scanner = pick(worker, "scanner_worker");
  const diagnostics = pick(worker, "latest_scanner_diagnostics");

  const marketSession = pick(worker, "market_session") ?? pick(scanner, "market_session") ?? pick(diagnostics, "market_session");
  const scannerMode = pick(worker, "scanner_mode") ?? pick(scanner, "scanner_mode") ?? pick(diagnostics, "scanner_mode");
  const currentTimeEt = pick(worker, "current_time_et") ?? pick(scanner, "current_time_et") ?? pick(diagnostics, "current_time_et");
  const clockSource = pick(worker, "clock_source") ?? pick(scanner, "clock_source") ?? pick(diagnostics, "clock_source");

  return (
    <main className="min-h-screen bg-[#03070b] px-6 py-6 text-slate-100">
      <div className="mx-auto max-w-6xl space-y-5">
        <header className="rounded-3xl border border-cyan-400/15 bg-[#061017]/85 p-5 shadow-[0_24px_90px_rgba(0,0,0,0.45)] backdrop-blur-xl">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">Day Trading Workflow</p>
              <h1 className="mt-2 text-2xl font-black tracking-tight text-white">Market Session Visibility</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                This page shows the shared session state that now gates the Azure scheduled scanner worker and the Session Router Agent.
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Link href="/daytrading-workflow/new/scanner-candidate-feed" className="rounded-xl border border-white/10 bg-white/[0.05] px-4 py-2 text-sm font-semibold text-slate-200 hover:border-cyan-300/35">
                Back to Scanner Feed
              </Link>
              <button disabled={loading} onClick={() => void refresh()} className="rounded-xl border border-cyan-300/35 bg-cyan-400/15 px-4 py-2 text-sm font-bold text-cyan-100 disabled:opacity-50">
                {loading ? "Refreshing…" : "Refresh"}
              </button>
            </div>
          </div>
          {error ? <p className="mt-4 rounded-xl border border-amber-400/25 bg-amber-500/10 p-3 text-sm text-amber-100">{error}</p> : null}
        </header>

        <section className="grid gap-4 md:grid-cols-4">
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-300/70">Market session</div>
            <div className="mt-2 text-lg font-black text-white">{valueText(marketSession)}</div>
          </div>
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-300/70">Scanner mode</div>
            <div className="mt-2 text-lg font-black text-white">{valueText(scannerMode)}</div>
          </div>
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-300/70">Clock source</div>
            <div className="mt-2 text-lg font-black text-white">{valueText(clockSource)}</div>
          </div>
          <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-cyan-300/70">Current ET</div>
            <div className="mt-2 text-sm font-bold text-white">{valueText(currentTimeEt)}</div>
          </div>
        </section>

        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Shared session fields" endpoint="GET /api/worker-status/latest">
            <Row label="market_session" value={marketSession} />
            <Row label="market_date" value={pick(worker, "market_date") ?? pick(scanner, "market_date") ?? pick(diagnostics, "market_date")} />
            <Row label="current_time_et" value={currentTimeEt} />
            <Row label="clock_source" value={clockSource} />
            <Row label="is_trading_day" value={pick(worker, "is_trading_day") ?? pick(scanner, "is_trading_day") ?? pick(diagnostics, "is_trading_day")} />
            <Row label="is_market_open" value={pick(worker, "is_market_open") ?? pick(scanner, "is_market_open") ?? pick(diagnostics, "is_market_open")} />
            <Row label="is_pre_market" value={pick(worker, "is_pre_market") ?? pick(scanner, "is_pre_market") ?? pick(diagnostics, "is_pre_market")} />
            <Row label="is_regular_market" value={pick(worker, "is_regular_market") ?? pick(scanner, "is_regular_market") ?? pick(diagnostics, "is_regular_market")} />
            <Row label="is_post_market" value={pick(worker, "is_post_market") ?? pick(scanner, "is_post_market") ?? pick(diagnostics, "is_post_market")} />
            <Row label="next_open" value={pick(worker, "next_open") ?? pick(scanner, "next_open") ?? pick(diagnostics, "next_open")} />
            <Row label="next_close" value={pick(worker, "next_close") ?? pick(scanner, "next_close") ?? pick(diagnostics, "next_close")} />
          </Card>

          <Card title="Worker scanner state" endpoint="GET /api/worker-status/latest">
            <Row label="scanner_worker.status" value={pick(scanner, "status")} />
            <Row label="scanner_mode" value={scannerMode} />
            <Row label="recommendation_status" value={pick(scanner, "recommendation_status")} />
            <Row label="selected_symbols" value={pick(scanner, "selected_symbols")} />
            <Row label="blockers" value={pick(scanner, "blockers")} />
            <Row label="warnings" value={pick(scanner, "warnings")} />
            <Row label="candidate_count" value={pick(worker, "candidate_count")} />
          </Card>
        </div>

        <Card title="Raw worker-status response" endpoint="GET /api/worker-status/latest">
          <pre className="max-h-[500px] overflow-auto whitespace-pre-wrap rounded-xl bg-black/40 p-4 text-xs leading-5 text-slate-300">
            {JSON.stringify(worker, null, 2)}
          </pre>
        </Card>
      </div>
    </main>
  );
}
