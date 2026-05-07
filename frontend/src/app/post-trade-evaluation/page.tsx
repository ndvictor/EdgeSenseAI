"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  evaluatePostTrade,
  getLatestPostTradeEvaluation,
  getPostTradeEvaluationStatus,
  type PostTradeChecker,
  type PostTradeEvaluationRequest,
  type PostTradeEvaluationResult,
  type PostTradeEvaluationStatusResponse,
} from "@/lib/api";

const OUTCOME_LABELS = [
  "win",
  "loss",
  "flat",
  "fakeout",
  "late_entry",
  "rule_violation",
  "slippage_issue",
  "stopped_out",
  "target_hit",
  "time_stop",
  "thesis_invalidated",
];

const CHECKERS = [
  "Outcome Labeler",
  "Realized PnL Calculator",
  "R-Multiple Calculator",
  "Performance Attribution",
  "Rule Compliance Checker",
];

const defaultSample: PostTradeEvaluationRequest = {
  trade: {
    trade_id: "trade_sample",
    symbol: "AMD",
    asset_class: "stock",
    horizon: "day_trading",
    side: "long",
    quantity: 13,
    planned_entry_price: 151.15,
    actual_entry_price: 151.2,
    planned_exit_price: 155.6,
    actual_exit_price: 155.5,
    stop_loss: 148.85,
    target_price: 155.6,
    opened_at: "2026-05-07T09:40:00-05:00",
    closed_at: "2026-05-07T10:25:00-05:00",
    exit_reason: "target_hit",
  },
  workflow_context: {
    selected_workflow: "baseline_fast_path",
    strategy_key: "regime_aware_momentum_catalyst",
    trigger_key: "rvol_vwap_breakout_confirm",
    session: "market_open",
  },
  thesis_outcome: {
    thesis_valid_at_exit: true,
    invalidation_hit: false,
    price_above_vwap_at_exit: true,
    volume_confirmed_at_exit: true,
    relative_strength_positive_at_exit: true,
  },
  execution_quality: {
    planned_entry_price: 151.15,
    actual_entry_price: 151.2,
    planned_exit_price: 155.6,
    actual_exit_price: 155.5,
    max_allowed_slippage_percent: 0.15,
  },
  rule_compliance: {
    entered_after_trigger: true,
    used_approved_strategy: true,
    respected_position_size: true,
    respected_stop_loss: true,
    respected_master_admin_gates: true,
    human_approval_obtained: true,
  },
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready" || s === "ok") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail" || s === "blocked" || s.includes("disabled")) return "border-red-500/45 bg-red-500/15 text-red-100";
  if (s === "unknown") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  if (OUTCOME_LABELS.includes(s)) {
    if (s === "win" || s === "target_hit") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
    if (s === "loss" || s === "stopped_out" || s === "rule_violation") return "border-red-500/45 bg-red-500/15 text-red-100";
    return "border-amber-500/45 bg-amber-500/15 text-amber-100";
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

function CheckerLine({ title, result }: { title: string; result?: PostTradeChecker }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (evaluate a sample trade)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-white/[0.06] py-2 last:border-0">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-xs text-slate-200">{value}</div>
    </div>
  );
}

function ResultPanel({ result }: { result: PostTradeEvaluationResult }) {
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated evaluation</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">
            {result.symbol} · {result.trade_id}
          </div>
          <div className="mt-1 text-sm text-slate-400">outcome_label: {result.outcome_label}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.outcome_label)}`}>
            {result.outcome_label}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.outcome_status)}`}>
            {result.outcome_status}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.llm_used ? "warn" : "pass")}`}>
            LLM used: {result.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>PnL</FieldLabel>
          <div className="mt-2">
            <Row label="realized_pnl" value={result.pnl.realized_pnl} />
            <Row label="realized_pnl_percent" value={result.pnl.realized_pnl_percent} />
            <Row label="gross_entry_notional" value={result.pnl.gross_entry_notional} />
            <Row label="gross_exit_notional" value={result.pnl.gross_exit_notional} />
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Risk & R</FieldLabel>
          <div className="mt-2">
            <Row label="risk_per_share" value={result.risk_result.risk_per_share} />
            <Row label="r_multiple" value={result.risk_result.r_multiple} />
            <Row label="planned_reward_risk" value={result.risk_result.planned_reward_risk} />
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Execution quality</FieldLabel>
          <div className="mt-2">
            <Row label="entry_slippage_percent" value={result.execution_quality_result.entry_slippage_percent} />
            <Row label="exit_slippage_percent" value={result.execution_quality_result.exit_slippage_percent} />
            <Row
              label="slippage_status"
              value={
                <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.execution_quality_result.slippage_status)}`}>
                  {result.execution_quality_result.slippage_status}
                </span>
              }
            />
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Rule compliance</FieldLabel>
          <div className="mt-2">
            <Row label="compliant" value={String(result.rule_compliance_result.compliant)} />
            <Row label="failed_rules" value={(result.rule_compliance_result.failed_rules ?? []).join(", ") || "—"} />
            <Row label="passed_rules" value={(result.rule_compliance_result.passed_rules ?? []).join(", ") || "—"} />
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Attribution</FieldLabel>
          <div className="mt-2">
            <Row label="primary_driver" value={result.attribution.primary_driver} />
            <Row label="secondary_driver" value={result.attribution.secondary_driver ?? "—"} />
            <Row label="session" value={result.attribution.session} />
            <Row label="strategy_key" value={result.attribution.strategy_key} />
            <Row label="trigger_key" value={result.attribution.trigger_key} />
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Meta</FieldLabel>
          <div className="mt-2">
            <Row label="evaluation_id" value={result.evaluation_id} />
            <Row label="created_at" value={result.created_at ?? "—"} />
            <Row label="next_action" value={result.next_action ?? "—"} />
          </div>
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
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
    </div>
  );
}

export default function PostTradeEvaluationPage() {
  const [status, setStatus] = useState<PostTradeEvaluationStatusResponse | null>(null);
  const [result, setResult] = useState<PostTradeEvaluationResult | null>(null);
  const [form, setForm] = useState<PostTradeEvaluationRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getPostTradeEvaluationStatus(), getLatestPostTradeEvaluation()]);
        if (cancelled) return;
        setStatus(s);
        setResult(latest.result ?? s.latest_evaluation ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load post-trade evaluation status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedOutcomes = useMemo(
    () => (status?.supported_outcome_labels?.length ? status.supported_outcome_labels : OUTCOME_LABELS),
    [status],
  );

  const checkerByName = useMemo(() => {
    const map = new Map<string, PostTradeChecker>();
    for (const r of status?.checker_statuses ?? []) map.set(r.checker, r);
    return map;
  }, [status]);

  async function handleRun() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await evaluatePostTrade(form);
      setResult(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Evaluation failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestPostTradeEvaluation();
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
          <h2 className="mb-2 font-semibold text-red-200">Post-Trade Evaluation</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const evaluatorStatus = status?.evaluator_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Post-Trade Evaluation</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 13 AI-Agent that evaluates closed or simulated-closed stock day-trading outcomes, PnL, R-multiple, slippage, rule compliance, and attribution without calling an LLM.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {["US Stocks Only", "Day Trading Only", "Paper-First", "No LLM", "No Broker Calls"].map((t) => (
            <span
              key={t}
              className={
                t === "No LLM" || t === "No Broker Calls"
                  ? "rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[10px] font-bold uppercase text-slate-300"
                  : "rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]"
              }
            >
              {t}
            </span>
          ))}
        </div>
        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          Visibility only. This page does not submit orders, does not call broker APIs, and does not call execution endpoints.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
        <SummaryCard label="Stage" value={13} />
        <SummaryCard label="Evaluator Status" value={<span className="capitalize">{String(evaluatorStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" />
        <SummaryCard label="Asset Scope" value="US Stocks" />
        <SummaryCard label="Horizon Scope" value="Day Trading" />
        <SummaryCard label="Mode Scope" value="Paper-first" />
        <SummaryCard label="Latest Evaluation" value={result?.symbol ?? "—"} hint={result?.outcome_label ? `Outcome: ${result.outcome_label}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{result?.next_action ?? status?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Outcome evaluation</div>
                <div className="mt-1 text-sm text-slate-400">Evaluate a sample closed (or simulated-closed) trade.</div>
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
                  {actionLoading === "run" ? "Evaluating..." : "Evaluate Sample Trade"}
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
                Target Hit Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    trade: { ...f.trade, actual_exit_price: 148.9, exit_reason: "stopped_out" },
                    thesis_outcome: { ...f.thesis_outcome, thesis_valid_at_exit: false, invalidation_hit: true },
                  }))
                }
              >
                Stopped Out Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    execution_quality: { ...f.execution_quality, max_allowed_slippage_percent: 0.05 },
                    trade: { ...f.trade, actual_entry_price: f.trade.planned_entry_price * 1.004, actual_exit_price: f.trade.planned_exit_price * 0.996, exit_reason: "slippage_issue" },
                  }))
                }
              >
                High Slippage Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    rule_compliance: { ...f.rule_compliance, respected_stop_loss: false, human_approval_obtained: false },
                    trade: { ...f.trade, exit_reason: "rule_violation" },
                  }))
                }
              >
                Rule Violation Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    thesis_outcome: { ...f.thesis_outcome, thesis_valid_at_exit: false, invalidation_hit: true },
                    trade: { ...f.trade, exit_reason: "thesis_invalidated" },
                  }))
                }
              >
                Thesis Invalidated Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, trade: { ...f.trade, asset_class: "crypto", symbol: "BTC-USD" } }))}
              >
                Crypto Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    trade: { ...f.trade, actual_exit_price: f.trade.actual_entry_price, exit_reason: "time_stop" },
                  }))
                }
              >
                Flat Time Stop Sample
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Trade</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade.trade_id}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, trade_id: e.target.value } }))}
                    />
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade.symbol}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, symbol: e.target.value } }))}
                    />
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade.asset_class}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, asset_class: e.target.value } }))}
                    >
                      <option value="stock">stock</option>
                      <option value="crypto">crypto</option>
                      <option value="etf">etf</option>
                      <option value="option">option</option>
                    </select>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade.horizon}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, horizon: e.target.value } }))}
                    >
                      <option value="day_trading">day_trading</option>
                      <option value="swing">swing</option>
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade.side}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, side: e.target.value } }))}
                    >
                      <option value="long">long</option>
                      <option value="short">short</option>
                    </select>
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade.quantity}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, quantity: Number(e.target.value) } }))}
                    />
                  </div>

                  {(
                    [
                      ["planned_entry_price", "planned_entry_price"],
                      ["actual_entry_price", "actual_entry_price"],
                      ["planned_exit_price", "planned_exit_price"],
                      ["actual_exit_price", "actual_exit_price"],
                      ["stop_loss", "stop_loss"],
                      ["target_price", "target_price"],
                    ] as const
                  ).map(([k, ph]) => (
                    <input
                      key={k}
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trade[k]}
                      onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, [k]: Number(e.target.value) } }))}
                      placeholder={ph}
                    />
                  ))}

                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.trade.opened_at}
                    onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, opened_at: e.target.value } }))}
                  />
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.trade.closed_at}
                    onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, closed_at: e.target.value } }))}
                  />
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.trade.exit_reason}
                    onChange={(e) => setForm((f) => ({ ...f, trade: { ...f.trade, exit_reason: e.target.value } }))}
                  >
                    {["target_hit", "stopped_out", "time_stop", "rule_violation", "slippage_issue", "thesis_invalidated", "flat", "fakeout", "late_entry", "win", "loss"].map((x) => (
                      <option key={x} value={x}>
                        {x}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Workflow context</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.workflow_context.selected_workflow}
                      onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, selected_workflow: e.target.value } }))}
                    >
                      {["baseline_fast_path", "conservative_path", "paper_only_path"].map((x) => (
                        <option key={x} value={x}>
                          {x}
                        </option>
                      ))}
                    </select>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.workflow_context.strategy_key}
                      onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, strategy_key: e.target.value } }))}
                    />
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.workflow_context.trigger_key}
                      onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, trigger_key: e.target.value } }))}
                    />
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.workflow_context.session}
                      onChange={(e) => setForm((f) => ({ ...f, workflow_context: { ...f.workflow_context, session: e.target.value } }))}
                    >
                      {["market_open", "midday", "power_hour", "after_hours"].map((x) => (
                        <option key={x} value={x}>
                          {x}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Thesis outcome</FieldLabel>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {(
                      [
                        ["thesis_valid_at_exit", "thesis_valid_at_exit"],
                        ["invalidation_hit", "invalidation_hit"],
                        ["price_above_vwap_at_exit", "price_above_vwap_at_exit"],
                        ["volume_confirmed_at_exit", "volume_confirmed_at_exit"],
                        ["relative_strength_positive_at_exit", "relative_strength_positive_at_exit"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.thesis_outcome[k]}
                          onChange={(e) => setForm((f) => ({ ...f, thesis_outcome: { ...f.thesis_outcome, [k]: e.target.checked } }))}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Execution quality</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.execution_quality.max_allowed_slippage_percent}
                      onChange={(e) => setForm((f) => ({ ...f, execution_quality: { ...f.execution_quality, max_allowed_slippage_percent: Number(e.target.value) } }))}
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Rule compliance</FieldLabel>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {(
                      [
                        ["entered_after_trigger", "entered_after_trigger"],
                        ["used_approved_strategy", "used_approved_strategy"],
                        ["respected_position_size", "respected_position_size"],
                        ["respected_stop_loss", "respected_stop_loss"],
                        ["respected_master_admin_gates", "respected_master_admin_gates"],
                        ["human_approval_obtained", "human_approval_obtained"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.rule_compliance[k]}
                          onChange={(e) => setForm((f) => ({ ...f, rule_compliance: { ...f.rule_compliance, [k]: e.target.checked } }))}
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
              No evaluation loaded yet. Click “Evaluate Sample Trade” to simulate output.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Safety guarantees</h2>
            <div className="mt-2 text-sm text-slate-300">
              No broker calls, no execution endpoints, no order submission, and no LLM summary in v1. Metrics are eligible for Stage 14 Learning Loop only when not blocked.
            </div>
            <div className="mt-3 grid gap-2">
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">no broker calls</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">no execution endpoints</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">no order submission</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">no LLM summary in v1</div>
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Useful links</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/close-position">
                Close Position
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/journal">
                Journal
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/learning-loop">
                Learning Loop
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/settings?tab=master_admin">
                Master Admin Controls
              </Link>
            </div>
            <div className="mt-2 text-xs text-slate-500">This page evaluates outcomes only.</div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported outcome labels</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {supportedOutcomes.map((o) => (
                <span key={o} className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(o)}`}>
                  {o}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Checker status</h2>
            <div className="mt-3 space-y-2">
              {CHECKERS.map((c) => (
                <CheckerLine key={c} title={c} result={checkerByName.get(c)} />
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">Checker status is reported by the post-trade-evaluation status endpoint.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

