"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  evaluatePositionMonitoring,
  getLatestPositionMonitoringEvaluation,
  getPositionMonitoringStatus,
  type PositionEvaluationResult,
  type PositionMonitoringChecker,
  type PositionMonitoringEvaluateRequest,
  type PositionMonitoringStatusResponse,
} from "@/lib/api";

const ACTIONS = ["hold", "watch", "reduce", "exit_review", "blocked"];
const CHECKERS = ["PnL Calculator", "Thesis Validity Checker", "Position Risk Monitor", "Master Admin Gate"];

const defaultSample: PositionMonitoringEvaluateRequest = {
  position: {
    position_id: "pos_sample",
    symbol: "",
    asset_class: "stock",
    horizon: "day_trading",
    side: "long",
    quantity: 13,
    entry_price: 151.15,
    current_price: 152.2,
    stop_loss: 148.85,
    target_price: 155.6,
    opened_at: "2026-05-07T09:40:00-05:00",
  },
  thesis: {
    strategy_key: "regime_aware_momentum_catalyst",
    trigger_key: "rvol_vwap_breakout_confirm",
    vwap: 149.8,
    price_above_vwap: true,
    volume_confirms: true,
    relative_strength_positive: true,
    invalidation_hit: false,
  },
  risk_state: {
    account_equity: 10000,
    max_daily_loss_percent: 3.0,
    current_daily_loss_percent: 0.4,
    max_position_size_percent: 20.0,
    force_close_requested: false,
    emergency_stop: false,
  },
  monitoring_preferences: {
    time_stop_minutes: 45,
    reduce_at_r_multiple: 1.5,
    exit_at_thesis_invalid: true,
  },
  evaluated_at: "2026-05-07T10:00:00-05:00",
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready" || s === "ok") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial" || s === "watch") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail" || s === "blocked" || s.includes("disabled")) return "border-red-500/45 bg-red-500/15 text-red-100";
  if (s === "unknown") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  if (ACTIONS.includes(s)) {
    if (s === "hold") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
    if (s === "reduce" || s === "exit_review") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
    if (s === "blocked") return "border-red-500/45 bg-red-500/15 text-red-100";
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

function CheckerLine({ title, result }: { title: string; result?: PositionMonitoringChecker }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (evaluate a sample position)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function ResultPanel({ result }: { result: PositionEvaluationResult }) {
  const tv = result.thesis_validity;
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated evaluation</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">
            {result.symbol} · {result.position_id}
          </div>
          <div className="mt-1 text-sm text-slate-400">position_status: {result.position_status}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.recommended_action)}`}>
            {result.recommended_action}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.llm_used ? "warn" : "pass")}`}>
            LLM used: {result.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>PnL</FieldLabel>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>unrealized_pnl: {result.pnl?.unrealized_pnl ?? "—"}</div>
            <div>unrealized_pnl_percent: {result.pnl?.unrealized_pnl_percent ?? "—"}</div>
            <div>r_multiple: {result.pnl?.r_multiple ?? "—"}</div>
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Risk</FieldLabel>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>risk_per_share: {result.risk?.risk_per_share ?? "—"}</div>
            <div>current_distance_to_stop: {result.risk?.current_distance_to_stop ?? "—"}</div>
            <div>distance_to_target: {result.risk?.distance_to_target ?? "—"}</div>
            <div>position_notional: {result.risk?.position_notional ?? "—"}</div>
            <div>position_size_percent: {result.risk?.position_size_percent ?? "—"}</div>
            <div>daily_loss_percent: {result.risk?.daily_loss_percent ?? "—"}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Thesis validity</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(tv?.valid ? "pass" : "fail")}`}>
              valid: {String(tv?.valid ?? "—")}
            </span>
            <span className="inline-flex rounded-lg border border-white/10 bg-black/20 px-2 py-0.5 text-[11px] font-medium text-slate-300">
              score: {tv?.score ?? "—"}
            </span>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Passed</div>
              <div className="mt-2 space-y-1 text-xs text-slate-400">
                {(tv?.passed_reasons ?? []).length ? tv!.passed_reasons!.map((r, i) => (
                  <div key={`${r}-${i}`} className="rounded-md border border-white/5 bg-black/20 px-2 py-1">{r}</div>
                )) : <div className="text-slate-500">—</div>}
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Failed</div>
              <div className="mt-2 space-y-1 text-xs text-slate-400">
                {(tv?.failed_reasons ?? []).length ? tv!.failed_reasons!.map((r, i) => (
                  <div key={`${r}-${i}`} className="rounded-md border border-white/5 bg-black/20 px-2 py-1">{r}</div>
                )) : <div className="text-slate-500">—</div>}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Actions + notes</FieldLabel>
          <div className="mt-2 grid gap-2 text-xs text-slate-400">
            <div>evaluation_id: {result.evaluation_id}</div>
            <div>position_id: {result.position_id}</div>
            <div>created_at: {result.created_at ?? "—"}</div>
            <div>next_action: {result.next_action ?? "—"}</div>
          </div>
          <div className="mt-3 grid gap-2">
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Blockers</div>
              <div className="mt-2 space-y-1 text-xs text-slate-400">
                {(result.blockers ?? []).length ? result.blockers!.map((b, i) => (
                  <div key={`${b}-${i}`} className="rounded-md border border-white/5 bg-black/20 px-2 py-1">{b}</div>
                )) : <div className="text-slate-500">—</div>}
              </div>
            </div>
            <div className="rounded-lg border border-white/10 bg-black/20 p-3">
              <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Warnings</div>
              <div className="mt-2 space-y-1 text-xs text-slate-400">
                {(result.warnings ?? []).length ? result.warnings!.map((w, i) => (
                  <div key={`${w}-${i}`} className="rounded-md border border-white/5 bg-black/20 px-2 py-1">{w}</div>
                )) : <div className="text-slate-500">—</div>}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function PositionMonitoringPage() {
  const [status, setStatus] = useState<PositionMonitoringStatusResponse | null>(null);
  const [result, setResult] = useState<PositionEvaluationResult | null>(null);
  const [form, setForm] = useState<PositionMonitoringEvaluateRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getPositionMonitoringStatus(), getLatestPositionMonitoringEvaluation()]);
        if (cancelled) return;
        setStatus(s);
        setResult(latest.result ?? s.latest_evaluation ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load position monitoring status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedActions = useMemo(
    () => (status?.supported_position_actions?.length ? status.supported_position_actions : ACTIONS),
    [status]
  );

  const checkerByName = useMemo(() => {
    const map = new Map<string, PositionMonitoringChecker>();
    for (const r of status?.checker_statuses ?? []) map.set(r.checker, r);
    return map;
  }, [status]);

  async function handleRun() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await evaluatePositionMonitoring(form);
      setResult(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Position evaluation failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestPositionMonitoringEvaluation();
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
          <h2 className="mb-2 font-semibold text-red-200">Position Monitoring</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const monitorStatus = status?.monitor_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Position Monitoring</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 11 AI-Agent that evaluates active stock day-trading position health, PnL, thesis validity, and risk state without closing positions or calling an LLM.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {["US Stocks Only", "Day Trading Only", "Paper-First", "No LLM", "No Close Orders"].map((t) => (
            <span
              key={t}
              className={
                t === "No LLM"
                  ? "rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[10px] font-bold uppercase text-slate-300"
                  : "rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]"
              }
            >
              {t}
            </span>
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          Monitoring visibility only. This page does not close positions, submit orders, call broker APIs, or call execution endpoints. Stage 12 handles close review later.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
        <SummaryCard label="Stage" value={11} />
        <SummaryCard label="Monitor Status" value={<span className="capitalize">{String(monitorStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" />
        <SummaryCard label="Asset Scope" value="US Stocks" />
        <SummaryCard label="Horizon Scope" value="Day Trading" />
        <SummaryCard label="Mode Scope" value="Paper-first" />
        <SummaryCard label="Latest Evaluation" value={result?.symbol ?? "—"} hint={result?.recommended_action ? `Action: ${result.recommended_action}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{result?.next_action ?? status?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Position evaluation</div>
                <div className="mt-1 text-sm text-slate-400">Evaluate a sample position (visibility only).</div>
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
                  {actionLoading === "run" ? "Evaluating..." : "Evaluate Sample Position"}
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
                Healthy Hold Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, thesis: { ...f.thesis, invalidation_hit: true }, monitoring_preferences: { ...f.monitoring_preferences, exit_at_thesis_invalid: true } }))}
              >
                Thesis Invalid Exit Review Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, risk_state: { ...f.risk_state, force_close_requested: true } }))}
              >
                Force Close Requested Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, position: { ...f.position, asset_class: "crypto", symbol: "" } }))}
              >
                Crypto Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, position: { ...f.position, current_price: 156.0 } }))}
              >
                High R Multiple Reduce Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, monitoring_preferences: { ...f.monitoring_preferences, time_stop_minutes: 1 }, evaluated_at: "2026-05-07T10:30:00-05:00" }))}
              >
                Time Stop Exit Review Sample
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Position</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.position.position_id}
                    onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, position_id: e.target.value } }))}
                  />
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.symbol}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, symbol: e.target.value } }))}
                    />
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.asset_class}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, asset_class: e.target.value } }))}
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
                      value={form.position.horizon}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, horizon: e.target.value } }))}
                    >
                      <option value="day_trading">day_trading</option>
                      <option value="swing">swing</option>
                    </select>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.side}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, side: e.target.value } }))}
                    >
                      <option value="long">long</option>
                      <option value="short">short</option>
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.quantity}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, quantity: Number(e.target.value) } }))}
                    />
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.entry_price}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, entry_price: Number(e.target.value) } }))}
                    />
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.current_price}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, current_price: Number(e.target.value) } }))}
                    />
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position.stop_loss}
                      onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, stop_loss: Number(e.target.value) } }))}
                    />
                  </div>
                  <input
                    type="number"
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.position.target_price}
                    onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, target_price: Number(e.target.value) } }))}
                  />
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.position.opened_at}
                    onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, opened_at: e.target.value } }))}
                  />
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Thesis</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.thesis.strategy_key}
                      onChange={(e) => setForm((f) => ({ ...f, thesis: { ...f.thesis, strategy_key: e.target.value } }))}
                    />
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.thesis.trigger_key}
                      onChange={(e) => setForm((f) => ({ ...f, thesis: { ...f.thesis, trigger_key: e.target.value } }))}
                    />
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.thesis.vwap}
                      onChange={(e) => setForm((f) => ({ ...f, thesis: { ...f.thesis, vwap: Number(e.target.value) } }))}
                    />
                    {(
                      [
                        ["price_above_vwap", "Price above VWAP"],
                        ["volume_confirms", "Volume confirms"],
                        ["relative_strength_positive", "Relative strength positive"],
                        ["invalidation_hit", "Invalidation hit"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.thesis[k]}
                          onChange={(e) => setForm((f) => ({ ...f, thesis: { ...f.thesis, [k]: e.target.checked } }))}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Risk state</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <div className="grid gap-2 sm:grid-cols-2">
                      {[
                        ["account_equity", "Equity"],
                        ["max_daily_loss_percent", "Max daily loss %"],
                        ["current_daily_loss_percent", "Current daily loss %"],
                        ["max_position_size_percent", "Max position %"],
                      ].map(([k, label]) => (
                        <input
                          key={k}
                          type="number"
                          className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                          value={(form.risk_state as any)[k]}
                          onChange={(e) => setForm((f) => ({ ...f, risk_state: { ...f.risk_state, [k]: Number(e.target.value) } }))}
                          placeholder={label}
                        />
                      ))}
                    </div>
                    {(
                      [
                        ["force_close_requested", "Force close requested"],
                        ["emergency_stop", "Emergency stop"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.risk_state[k]}
                          onChange={(e) => setForm((f) => ({ ...f, risk_state: { ...f.risk_state, [k]: e.target.checked } }))}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Monitoring preferences</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <div className="grid gap-2 sm:grid-cols-2">
                      <input
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={form.monitoring_preferences.time_stop_minutes}
                        onChange={(e) => setForm((f) => ({ ...f, monitoring_preferences: { ...f.monitoring_preferences, time_stop_minutes: Number(e.target.value) } }))}
                      />
                      <input
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={form.monitoring_preferences.reduce_at_r_multiple}
                        onChange={(e) => setForm((f) => ({ ...f, monitoring_preferences: { ...f.monitoring_preferences, reduce_at_r_multiple: Number(e.target.value) } }))}
                      />
                    </div>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={form.monitoring_preferences.exit_at_thesis_invalid}
                        onChange={(e) => setForm((f) => ({ ...f, monitoring_preferences: { ...f.monitoring_preferences, exit_at_thesis_invalid: e.target.checked } }))}
                      />
                      Exit review at thesis invalid
                    </label>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.evaluated_at}
                      onChange={(e) => setForm((f) => ({ ...f, evaluated_at: e.target.value }))}
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {result ? (
            <ResultPanel result={result} />
          ) : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No evaluation loaded yet. Click “Evaluate Sample Position” to simulate monitoring output.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Safety guarantees</h2>
            <div className="mt-2 text-sm text-slate-300">
              Monitoring only: no close orders, no broker calls, no execution endpoints. Stage 12 handles close review later.
            </div>
            <div className="mt-3 grid gap-2">
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">No close orders submitted</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">No broker APIs called</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">No execution endpoints called</div>
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Useful links</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/settings?tab=master_admin">
                Master Admin Controls
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/auto-execution-monitor">
                Auto-Execution Monitor
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/live-watchlist">
                Live Watchlist
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/execution-planner">
                Execution Planner
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported position actions</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {supportedActions.map((a) => (
                <li key={a} className="rounded-lg border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2 text-slate-200">
                  {a}
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
            <div className="mt-3 text-xs text-slate-500">Checker status is reported by the monitoring status endpoint.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

