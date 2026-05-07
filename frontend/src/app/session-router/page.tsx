"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  evaluateSessionRouter,
  getLatestSessionRouterEvaluation,
  getSessionRouterStatus,
  type SessionEvaluateRequest,
  type SessionRouterEvaluation,
  type SessionRouterStatusResponse,
} from "@/lib/api";

const SUPPORTED_SESSIONS = ["pre_market", "market_open", "post_market", "after_hours", "closed", "holiday", "unknown"];
const CHECKERS = ["Session Time Checker", "Market Calendar Checker"];

const defaultSample: SessionEvaluateRequest = {
  timestamp: "2026-05-07T09:35:00-05:00",
  timezone: "America/Chicago",
  market: "us_equities",
  use_current_time: false,
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail") return "border-red-500/45 bg-red-500/15 text-red-100";
  if (s === "unknown") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  return "border-slate-600/60 bg-slate-800/40 text-slate-300";
}

function SummaryCard({ label, value, hint }: { label: string; value: React.ReactNode; hint?: string }) {
  return (
    <div className="rounded-xl border border-emerald-400/15 bg-[#0a1018]/90 px-4 py-3 shadow-[0_0_0_1px_rgba(16,185,129,0.06)]">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-50">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}

function FieldLabel({ children }: { children: React.ReactNode }) {
  return <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{children}</div>;
}

function CheckerLine({ title, status, message }: { title: string; status?: string; message?: string }) {
  const s = status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{message ?? "No details yet (evaluate a timestamp)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(s))}`}>
        {String(s)}
      </span>
    </div>
  );
}

function EvaluationPanel({ evaln }: { evaln: SessionRouterEvaluation }) {
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest evaluation</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">{evaln.session}</div>
          <div className="mt-1 text-sm text-slate-400">
            Market <span className="text-slate-200">{evaln.market}</span> · TZ <span className="text-slate-200">{evaln.timezone}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(evaln.is_trading_day ? "pass" : "warn")}`}>
            Trading day: {evaln.is_trading_day ? "Yes" : "No"}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(evaln.is_holiday ? "warn" : "pass")}`}>
            Holiday: {evaln.is_holiday ? "Yes" : "No"}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(evaln.llm_used ? "warn" : "pass")}`}>
            LLM used: {evaln.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Evaluated at</FieldLabel>
          <div className="mt-1 text-sm text-slate-300">{evaln.evaluated_at}</div>
          <div className="mt-2 text-xs text-slate-500">Market date: {evaln.market_date ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Session notes</FieldLabel>
          <div className="mt-2 space-y-1 text-sm text-slate-400">
            {(evaln.session_notes ?? []).length ? (
              evaln.session_notes!.map((n, i) => (
                <div key={`${n}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2 text-xs text-slate-400">
                  {n}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">—</div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Allowed workflow bias</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {(evaln.allowed_workflow_bias ?? []).length ? (
              evaln.allowed_workflow_bias!.map((b) => (
                <span key={b} className="inline-flex rounded-lg border border-emerald-400/20 bg-emerald-500/5 px-2 py-0.5 text-xs text-emerald-100">
                  {b}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">—</span>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Blocked workflow bias</FieldLabel>
          <div className="mt-2 space-y-2">
            {(evaln.blocked_workflow_bias ?? []).length ? (
              evaln.blocked_workflow_bias!.map((b, i) => (
                <div key={`${b.bias}-${i}`} className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
                  <div className="text-xs font-semibold text-red-100">{b.bias}</div>
                  <div className="text-xs text-red-100/80">{b.reason}</div>
                </div>
              ))
            ) : (
              <span className="text-xs text-slate-500">—</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
        <FieldLabel>Next action</FieldLabel>
        <div className="mt-1 text-sm text-emerald-200/80">{evaln.next_action ?? "—"}</div>
      </div>
    </div>
  );
}

export default function SessionRouterPage() {
  const [status, setStatus] = useState<SessionRouterStatusResponse | null>(null);
  const [evaluation, setEvaluation] = useState<SessionRouterEvaluation | null>(null);
  const [form, setForm] = useState<SessionEvaluateRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"eval" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getSessionRouterStatus(), getLatestSessionRouterEvaluation()]);
        if (cancelled) return;
        setStatus(s);
        setEvaluation(latest.evaluation ?? s.latest_evaluation ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load session router status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedSessions = useMemo(
    () => (status?.supported_sessions?.length ? status.supported_sessions : SUPPORTED_SESSIONS),
    [status]
  );

  const checkerMap = useMemo(() => {
    const map = new Map<string, { status?: string; message?: string }>();
    for (const c of evaluation?.checker_statuses ?? []) {
      map.set(c.checker, { status: c.status, message: c.message });
    }
    return map;
  }, [evaluation]);

  async function handleEvaluate() {
    setActionLoading("eval");
    setError(null);
    try {
      const res = await evaluateSessionRouter(form);
      setEvaluation(res.evaluation);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluate failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestSessionRouterEvaluation();
      setEvaluation(res.evaluation);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load latest evaluation");
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
      </div>
    );
  }

  if (error && !status) {
    return (
      <div className="w-full p-4 lg:p-8">
        <div className="rounded-2xl border border-red-500/35 bg-red-500/10 p-4">
          <h2 className="mb-2 font-semibold text-red-200">Session Router</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const routerStatus = status?.router_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Session Router</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 3 AI-Agent that determines pre-market, market-open, post-market, after-hours, closed, or unknown session context without calling an LLM.
        </p>
        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          This page evaluates session context for visibility. It does not execute workflows or trading actions.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <SummaryCard label="Stage" value={3} />
        <SummaryCard label="Router Status" value={<span className="capitalize">{String(routerStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" hint="Non-LLM context only" />
        <SummaryCard label="Calendar Mode" value={status?.calendar_mode ?? "—"} />
        <SummaryCard label="Latest Session" value={evaluation?.session ?? "—"} hint={evaluation?.market_date ? `Market date: ${evaluation.market_date}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{evaluation?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Session evaluation</div>
                <div className="mt-1 text-sm text-slate-400">Evaluate a timestamp to determine session context and workflow bias guards.</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleLoadLatest}
                  disabled={actionLoading !== null}
                  className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-emerald-400/25 hover:text-slate-100 disabled:opacity-50"
                >
                  {actionLoading === "latest" ? "Loading..." : "Load Latest"}
                </button>
                <button
                  type="button"
                  onClick={handleEvaluate}
                  disabled={actionLoading !== null}
                  className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/20 disabled:opacity-50"
                >
                  {actionLoading === "eval" ? "Evaluating..." : "Evaluate Session"}
                </button>
              </div>
            </div>

            {error ? (
              <div className="mt-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">
                {error}
              </div>
            ) : null}

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, timestamp: "2026-05-07T09:35:00-05:00", use_current_time: false }))}
              >
                Market Open Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, timestamp: "2026-05-07T07:15:00-05:00", use_current_time: false }))}
              >
                Pre-Market Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, timestamp: "2026-05-09T10:00:00-05:00", use_current_time: false }))}
              >
                Weekend Closed Sample
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Timestamp</FieldLabel>
                <input
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.timestamp}
                  onChange={(e) => setForm((f) => ({ ...f, timestamp: e.target.value }))}
                  placeholder="2026-05-07T09:35:00-05:00"
                />
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Timezone</FieldLabel>
                <input
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.timezone}
                  onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
                  placeholder="America/Chicago"
                />
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Market</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.market}
                  onChange={(e) => setForm((f) => ({ ...f, market: e.target.value }))}
                >
                  <option value="us_equities">us_equities</option>
                  <option value="crypto">crypto</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Use current time</FieldLabel>
                <label className="mt-2 flex items-center gap-2 text-sm text-slate-300">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-white/20 bg-black/30"
                    checked={form.use_current_time}
                    onChange={(e) => setForm((f) => ({ ...f, use_current_time: e.target.checked }))}
                  />
                  Use current time (backend sets timestamp)
                </label>
              </div>
            </div>
          </div>

          {evaluation ? (
            <EvaluationPanel evaln={evaluation} />
          ) : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No evaluation loaded yet. Click “Evaluate Session” to evaluate a timestamp.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported sessions</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {supportedSessions.map((s) => (
                <li key={s} className="rounded-lg border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2 text-slate-200">
                  {s}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Checker status</h2>
            <div className="mt-3 space-y-2">
              {CHECKERS.map((c) => (
                <CheckerLine key={c} title={c} status={checkerMap.get(c)?.status} message={checkerMap.get(c)?.message} />
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">Checker status is shown after evaluation.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

