"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  evaluateTriggerMonitoring,
  getLatestTriggerMonitoringEvaluation,
  getTriggerMonitoringStatus,
  type TriggerCheckerResult,
  type TriggerEvaluationResult,
  type TriggerMonitoringEvaluateRequest,
  type TriggerMonitoringStatusResponse,
} from "@/lib/api";

const TRIGGER_STATES = ["not_ready", "armed", "fired", "expired", "missed", "invalidated", "blocked"];

const CHECKERS = [
  "Trigger Rule Registry",
  "Timing Window Checker",
  "Signal Expiration Checker",
  "Eligibility Dependency Checker",
];

const defaultSample: TriggerMonitoringEvaluateRequest = {
  workflow_context: {
    selected_workflow: "baseline_fast_path",
    workflow_mode: "baseline",
    session: "market_open",
  },
  eligibility_context: {
    eligible: true,
    eligibility_status: "eligible",
    strategy_key: "regime_aware_momentum_catalyst",
    strategy_group: "regime_aware_momentum",
  },
  trigger_candidate: {
    symbol: "AMD",
    asset_class: "stock",
    horizon: "day_trading",
    trigger_key: "rvol_vwap_breakout_confirm",
    created_at: "2026-05-07T09:30:00-05:00",
    expires_at: "2026-05-07T09:45:00-05:00",
    trigger_price: 150.25,
    current_price: 151.1,
    vwap: 149.8,
  },
  current_state: {
    evaluated_at: "2026-05-07T09:35:00-05:00",
    data_quality: "pass",
    spread_pass: true,
    volume_confirms: true,
    price_above_trigger: true,
    price_above_vwap: true,
    invalidation_hit: false,
  },
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail") return "border-red-500/45 bg-red-500/15 text-red-100";
  if (s === "unknown") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  if (TRIGGER_STATES.includes(s)) {
    if (s === "fired") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
    if (s === "armed") return "border-cyan-500/40 bg-cyan-500/10 text-cyan-200";
    if (s === "expired" || s === "missed" || s === "invalidated") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
    if (s === "blocked") return "border-red-500/45 bg-red-500/15 text-red-100";
    if (s === "not_ready") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  }
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

function CheckerLine({ title, result }: { title: string; result?: TriggerCheckerResult }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (run a sample evaluation)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function ResultPanel({ result }: { result: TriggerEvaluationResult }) {
  const timing = result.timing;
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated evaluation</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">
            {result.symbol} · {result.trigger_key}
          </div>
          <div className="mt-1 text-sm text-slate-400">{result.reason}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.trigger_state)}`}>
            {result.trigger_state}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.llm_used ? "warn" : "pass")}`}>
            LLM used: {result.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Trigger identity</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-300">
            <span className="rounded-lg border border-white/10 bg-black/20 px-2 py-0.5">asset: {result.asset_class}</span>
            <span className="rounded-lg border border-white/10 bg-black/20 px-2 py-0.5">horizon: {result.horizon}</span>
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Timing</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            <div>created_at: {timing?.created_at ?? "—"}</div>
            <div>expires_at: {timing?.expires_at ?? "—"}</div>
            <div>evaluated_at: {timing?.evaluated_at ?? "—"}</div>
            <div>seconds_to_expiration: {timing?.seconds_to_expiration ?? "—"}</div>
            <div>is_expired: {String(timing?.is_expired ?? "—")}</div>
            <div>is_within_window: {String(timing?.is_within_window ?? "—")}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Requirements passed</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {(result.requirements_passed ?? []).length ? (
              result.requirements_passed!.map((r) => (
                <span key={r} className="inline-flex rounded-lg border border-emerald-400/20 bg-emerald-500/5 px-2 py-0.5 text-xs text-emerald-100">
                  {r}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">—</span>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Requirements failed</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {(result.requirements_failed ?? []).length ? (
              result.requirements_failed!.map((r) => (
                <span key={r} className="inline-flex rounded-lg border border-red-500/25 bg-red-500/10 px-2 py-0.5 text-xs text-red-100">
                  {r}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">—</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Blockers</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            {(result.blockers ?? []).length ? (
              result.blockers!.map((b, i) => (
                <div key={`${b}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">
                  {b}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">—</div>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Warnings</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            {(result.warnings ?? []).length ? (
              result.warnings!.map((w, i) => (
                <div key={`${w}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">
                  {w}
                </div>
              ))
            ) : (
              <div className="text-sm text-slate-500">—</div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
        <FieldLabel>Next action</FieldLabel>
        <div className="mt-1 text-sm text-emerald-200/80">{result.next_action ?? "—"}</div>
        <div className="mt-2 text-xs text-slate-500">Created at: {result.created_at ?? "—"}</div>
      </div>

      <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
        <FieldLabel>Checker results</FieldLabel>
        <div className="mt-2 space-y-2">
          {(result.checker_results ?? []).length ? (
            result.checker_results!.map((r, idx) => (
              <div key={`${r.checker}-${idx}`} className="flex items-start justify-between gap-3 rounded-lg border border-white/5 bg-black/20 px-3 py-2">
                <div>
                  <div className="text-sm font-medium text-slate-200">{r.checker}</div>
                  <div className="mt-0.5 text-xs text-slate-500">{r.message ?? "—"}</div>
                </div>
                <span className={`inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(r.status))}`}>
                  {String(r.status)}
                </span>
              </div>
            ))
          ) : (
            <div className="text-sm text-slate-500">No checker results returned.</div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function TriggerMonitoringPage() {
  const [status, setStatus] = useState<TriggerMonitoringStatusResponse | null>(null);
  const [result, setResult] = useState<TriggerEvaluationResult | null>(null);
  const [form, setForm] = useState<TriggerMonitoringEvaluateRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getTriggerMonitoringStatus(), getLatestTriggerMonitoringEvaluation()]);
        if (cancelled) return;
        setStatus(s);
        setResult(latest.result ?? s.latest_evaluation ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load trigger monitoring status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedStates = useMemo(
    () => (status?.supported_trigger_states?.length ? status.supported_trigger_states : TRIGGER_STATES),
    [status]
  );

  const checkerByName = useMemo(() => {
    const map = new Map<string, TriggerCheckerResult>();
    for (const r of result?.checker_results ?? []) map.set(r.checker, r);
    return map;
  }, [result]);

  async function handleRun() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await evaluateTriggerMonitoring(form);
      setResult(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Trigger evaluation failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestTriggerMonitoringEvaluation();
      setResult(res.result);
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
          <h2 className="mb-2 font-semibold text-red-200">Trigger Monitoring</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const monitorStatus = status?.monitor_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Trigger Monitoring</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 8 AI-Agent that evaluates whether a stock day-trading trigger is armed, fired, expired, missed, invalidated, or blocked without calling an LLM.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          <span className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]">
            US Stocks Only
          </span>
          <span className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]">
            Day Trading Only
          </span>
          <span className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]">
            Paper-First
          </span>
          <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[10px] font-bold uppercase text-slate-300">
            No LLM
          </span>
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          This page simulates trigger-state evaluation for visibility. It does not execute trading actions.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
        <SummaryCard label="Stage" value={8} />
        <SummaryCard label="Monitor Status" value={<span className="capitalize">{String(monitorStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" />
        <SummaryCard label="Asset Scope" value="US Stocks" />
        <SummaryCard label="Horizon Scope" value="Day Trading" />
        <SummaryCard label="Mode Scope" value="Paper-first" />
        <SummaryCard label="Latest Evaluation" value={result?.symbol ?? "—"} hint={result?.trigger_state ? `State: ${result.trigger_state}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{result?.next_action ?? status?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Trigger evaluation simulation</div>
                <div className="mt-1 text-sm text-slate-400">Edit inputs and run a sample trigger evaluation (visibility only).</div>
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
                  onClick={handleRun}
                  disabled={actionLoading !== null}
                  className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/20 disabled:opacity-50"
                >
                  {actionLoading === "run" ? "Running..." : "Run Sample Trigger Evaluation"}
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
                onClick={() => setForm(defaultSample)}
              >
                Fired Trigger Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    trigger_candidate: { ...f.trigger_candidate, expires_at: "2026-05-07T09:34:00-05:00" },
                    current_state: { ...f.current_state, evaluated_at: "2026-05-07T09:35:00-05:00" },
                  }))
                }
              >
                Expired Trigger Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    trigger_candidate: { ...f.trigger_candidate, asset_class: "crypto", symbol: "BTC-USD" },
                  }))
                }
              >
                Blocked Crypto Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    eligibility_context: { ...f.eligibility_context, eligible: false, eligibility_status: "blocked" },
                  }))
                }
              >
                Eligibility Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    current_state: { ...f.current_state, price_above_trigger: false, price_above_vwap: false },
                  }))
                }
              >
                Missed Trigger Sample
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Workflow context</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.workflow_context.selected_workflow}
                    onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, selected_workflow: e.target.value } }))}
                  >
                    {["baseline_fast_path", "adjusted_research_path", "paper_only_path", "backtest_queue_path", "observe_only_path", "no_trade_path"].map((w) => (
                      <option key={w} value={w}>{w}</option>
                    ))}
                  </select>
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.workflow_context.workflow_mode}
                    onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, workflow_mode: e.target.value } }))}
                  >
                    {["baseline", "adjusted", "paper_only", "backtest_queue", "observe_only", "no_trade"].map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.workflow_context.session}
                    onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, session: e.target.value } }))}
                  >
                    {["pre_market", "market_open", "post_market", "after_hours", "closed", "holiday", "unknown"].map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Eligibility context</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-white/20 bg-black/30"
                      checked={form.eligibility_context.eligible}
                      onChange={(e) => setForm((f) => ({ ...f, eligibility_context: { ...f.eligibility_context, eligible: e.target.checked } }))}
                    />
                    Eligible
                  </label>
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.eligibility_context.eligibility_status}
                    onChange={(e) => setForm((f) => ({ ...f, eligibility_context: { ...f.eligibility_context, eligibility_status: e.target.value } }))}
                  >
                    {["eligible", "paper_only", "research_only", "blocked"].map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.eligibility_context.strategy_key}
                    onChange={(e) => setForm((f) => ({ ...f, eligibility_context: { ...f.eligibility_context, strategy_key: e.target.value } }))}
                  />
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.eligibility_context.strategy_group}
                    onChange={(e) => setForm((f) => ({ ...f, eligibility_context: { ...f.eligibility_context, strategy_group: e.target.value } }))}
                  >
                    {["regime_aware_momentum", "catalyst_event_driven", "rvol_vwap_breakout", "cross_sectional_ranking"].map((v) => (
                      <option key={v} value={v}>{v}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Trigger candidate</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.symbol}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, symbol: e.target.value } }))}
                      placeholder="AMD"
                    />
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.asset_class}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, asset_class: e.target.value } }))}
                    >
                      <option value="stock">stock</option>
                      <option value="crypto">crypto</option>
                      <option value="etf">etf</option>
                      <option value="option">option</option>
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.horizon}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, horizon: e.target.value } }))}
                    >
                      <option value="day_trading">day_trading</option>
                      <option value="swing">swing</option>
                      <option value="unknown">unknown</option>
                    </select>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.trigger_key}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, trigger_key: e.target.value } }))}
                    />
                  </div>
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.trigger_candidate.created_at}
                    onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, created_at: e.target.value } }))}
                  />
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.trigger_candidate.expires_at}
                    onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, expires_at: e.target.value } }))}
                  />
                  <div className="grid gap-2 sm:grid-cols-3">
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.trigger_price}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, trigger_price: Number(e.target.value) } }))}
                    />
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.current_price}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, current_price: Number(e.target.value) } }))}
                    />
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_candidate.vwap}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_candidate: { ...f.trigger_candidate, vwap: Number(e.target.value) } }))}
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Current state</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.current_state.evaluated_at}
                    onChange={(e) => setForm((f) => ({ ...f, current_state: { ...f.current_state, evaluated_at: e.target.value } }))}
                  />
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.current_state.data_quality}
                    onChange={(e) => setForm((f) => ({ ...f, current_state: { ...f.current_state, data_quality: e.target.value } }))}
                  >
                    {["pass", "warn", "fail", "unknown"].map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {(
                      [
                        ["spread_pass", "Spread pass"],
                        ["volume_confirms", "Volume confirms"],
                        ["price_above_trigger", "Price above trigger"],
                        ["price_above_vwap", "Price above VWAP"],
                        ["invalidation_hit", "Invalidation hit"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.current_state[k]}
                          onChange={(e) => setForm((f) => ({ ...f, current_state: { ...f.current_state, [k]: e.target.checked } }))}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {result ? (
            <ResultPanel result={result} />
          ) : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No evaluation loaded yet. Click “Run Sample Trigger Evaluation” to simulate a trigger state.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported trigger states</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {supportedStates.map((s) => (
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
                <CheckerLine key={c} title={c} result={checkerByName.get(c)} />
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">Checker results are shown after evaluation.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

