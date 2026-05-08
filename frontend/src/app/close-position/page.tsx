"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getClosePositionStatus,
  getLatestClosePositionReview,
  reviewClosePosition,
  type CloseOrderPreview,
  type ClosePositionChecker,
  type ClosePositionReviewRequest,
  type ClosePositionReviewResult,
  type ClosePositionStatusResponse,
} from "@/lib/api";

const REVIEW_ACTIONS = ["hold", "reduce_review", "close_review", "blocked"];
const CHECKERS = ["Exit Rule Evaluator", "Close Position Agent", "Close Order Preview Builder", "Master Admin Gate"];

const defaultSample: ClosePositionReviewRequest = {
  position_evaluation: {
    evaluation_id: "pm_sample",
    position_id: "pos_sample",
    symbol: "AMD",
    asset_class: "stock",
    horizon: "day_trading",
    position_status: "exit_review",
    recommended_action: "exit_review",
    pnl: {
      unrealized_pnl: -29.9,
      unrealized_pnl_percent: -1.52,
      r_multiple: -1.0,
    },
    risk: {
      risk_per_share: 2.3,
      current_distance_to_stop: 0.0,
      distance_to_target: 6.75,
      position_notional: 1935.7,
      position_size_percent: 19.36,
      daily_loss_percent: 0.7,
    },
    thesis_validity: {
      valid: false,
      score: 0.25,
      failed_reasons: ["invalidation_hit"],
      passed_reasons: [],
    },
    blockers: [],
    warnings: ["thesis_invalidated"],
  },
  position: {
    quantity: 13,
    side: "long",
    current_price: 148.9,
    entry_price: 151.15,
  },
  master_admin: {
    workflow_enabled: true,
    execution_enabled: false,
    paper_trading_enabled: true,
    live_trading_enabled: false,
    broker_execution_enabled: false,
    human_approval_required: true,
    emergency_stop: false,
    force_close_requested: false,
  },
  review_preferences: {
    reduce_percent: 50,
    close_reason: "stage_11_exit_review",
    order_style: "market",
    allow_submit: false,
  },
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready" || s === "ok") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail" || s === "blocked" || s.includes("disabled")) return "border-red-500/45 bg-red-500/15 text-red-100";
  if (s === "unknown") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  if (REVIEW_ACTIONS.includes(s)) {
    if (s === "hold") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
    if (s === "reduce_review" || s === "close_review") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
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

function CheckerLine({ title, result }: { title: string; result?: ClosePositionChecker }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (run a sample review)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function PreviewRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 border-b border-white/[0.06] py-2 last:border-0">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-xs text-slate-200">{value}</div>
    </div>
  );
}

function CloseOrderPreviewPanel({ preview }: { preview: CloseOrderPreview }) {
  return (
    <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
      <FieldLabel>Close order preview (not submitted)</FieldLabel>
      <div className="mt-2">
        <PreviewRow label="symbol" value={preview.symbol} />
        <PreviewRow label="side" value={preview.side} />
        <PreviewRow label="quantity" value={preview.quantity} />
        <PreviewRow label="order_type" value={preview.order_type} />
        <PreviewRow label="limit_price" value={preview.limit_price ?? "—"} />
        <PreviewRow label="time_in_force" value={preview.time_in_force ?? "—"} />
        <PreviewRow label="source" value={preview.source ?? "—"} />
        <PreviewRow label="reason" value={preview.reason ?? "—"} />
        <PreviewRow label="human_approval_confirmed" value={String(preview.human_approval_confirmed ?? false)} />
      </div>
    </div>
  );
}

function ResultPanel({ result }: { result: ClosePositionReviewResult }) {
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated review</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">
            {result.symbol} · {result.position_id}
          </div>
          <div className="mt-1 text-sm text-slate-400">{result.reason}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.review_action)}`}>
            {result.review_action}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.review_status)}`}>
            {result.review_status}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Safety fields</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.submitted_order ? "fail" : "pass")}`}>
              submitted_order: {result.submitted_order ? "true" : "false"}
            </span>
            <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.broker_called ? "fail" : "pass")}`}>
              broker_called: {result.broker_called ? "true" : "false"}
            </span>
            <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.llm_used ? "warn" : "pass")}`}>
              LLM used: {result.llm_used ? "Yes" : "No"}
            </span>
          </div>
          <div className="mt-3 text-xs text-slate-500">
            Review-only visibility: no execution endpoints are called and no broker APIs are called from this page.
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Identifiers</FieldLabel>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>review_id: {result.review_id}</div>
            <div>position_id: {result.position_id}</div>
            <div>created_at: {result.created_at ?? "—"}</div>
            <div>next_action: {result.next_action ?? "—"}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Blockers</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            {(result.blockers ?? []).length ? result.blockers!.map((b, i) => (
              <div key={`${b}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">{b}</div>
            )) : <div className="text-sm text-slate-500">—</div>}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Warnings</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            {(result.warnings ?? []).length ? result.warnings!.map((w, i) => (
              <div key={`${w}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">{w}</div>
            )) : <div className="text-sm text-slate-500">—</div>}
          </div>
        </div>
      </div>

      {result.close_order_preview ? (
        <div className="mt-4">
          <CloseOrderPreviewPanel preview={result.close_order_preview} />
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/60 p-4 text-sm text-slate-400">
          No close order preview returned in this v1 response.
        </div>
      )}
    </div>
  );
}

export default function ClosePositionPage() {
  const [status, setStatus] = useState<ClosePositionStatusResponse | null>(null);
  const [result, setResult] = useState<ClosePositionReviewResult | null>(null);
  const [form, setForm] = useState<ClosePositionReviewRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getClosePositionStatus(), getLatestClosePositionReview()]);
        if (cancelled) return;
        setStatus(s);
        setResult(latest.result ?? latest.close_review ?? s.latest_review ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load close position status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedActions = useMemo(
    () => (status?.supported_review_actions?.length ? status.supported_review_actions : REVIEW_ACTIONS),
    [status]
  );

  const checkerByName = useMemo(() => {
    const map = new Map<string, ClosePositionChecker>();
    for (const r of status?.checker_statuses ?? []) map.set(r.checker, r);
    return map;
  }, [status]);

  async function handleRun() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await reviewClosePosition({
        ...form,
        review_preferences: { ...form.review_preferences, allow_submit: false },
      });
      setResult(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Close review failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestClosePositionReview();
      setResult(res.result ?? res.close_review ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load latest review");
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
          <h2 className="mb-2 font-semibold text-red-200">Close Position</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const reviewStatus = status?.review_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Close Position</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 12 AI-Agent that reviews whether to hold, reduce, or prepare a close-position request preview without submitting orders, calling brokers, or using an LLM.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {["US Stocks Only", "Day Trading Only", "Paper-First", "No LLM", "No Close Orders Submitted"].map((t) => (
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
          Review visibility only. This page never submits close orders, never calls broker APIs, and never calls execution endpoints.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
        <SummaryCard label="Stage" value={12} />
        <SummaryCard label="Review Status" value={<span className="capitalize">{String(reviewStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" />
        <SummaryCard label="Asset Scope" value="US Stocks" />
        <SummaryCard label="Horizon Scope" value="Day Trading" />
        <SummaryCard label="Mode Scope" value="Paper-first" />
        <SummaryCard label="Latest Review" value={result?.symbol ?? "—"} hint={result?.review_action ? `Action: ${result.review_action}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{result?.next_action ?? status?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Close/reduce review</div>
                <div className="mt-1 text-sm text-slate-400">Review a sample close decision (visibility only).</div>
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
                  {actionLoading === "run" ? "Reviewing..." : "Review Sample Close Decision"}
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
                Exit Review Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, review_preferences: { ...f.review_preferences, reduce_percent: 50 }, position_evaluation: { ...f.position_evaluation, recommended_action: "exit_review" } }))}
              >
                Reduce Review Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, position_status: "hold", recommended_action: "hold" } }))}
              >
                Hold Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, asset_class: "crypto", symbol: "BTC-USD" } }))}
              >
                Crypto Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, master_admin: { ...f.master_admin, force_close_requested: true } }))}
              >
                Force Close Requested Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, master_admin: { ...f.master_admin, execution_enabled: false } }))}
              >
                Execution Disabled Sample
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Position evaluation</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.evaluation_id}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, evaluation_id: e.target.value } }))}
                    />
                    <input className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.position_id}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, position_id: e.target.value } }))}
                    />
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.symbol}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, symbol: e.target.value } }))}
                    />
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.asset_class}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, asset_class: e.target.value } }))}
                    >
                      <option value="stock">stock</option>
                      <option value="crypto">crypto</option>
                      <option value="etf">etf</option>
                      <option value="option">option</option>
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.horizon}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, horizon: e.target.value } }))}
                    >
                      <option value="day_trading">day_trading</option>
                      <option value="swing">swing</option>
                    </select>
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.position_status}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, position_status: e.target.value } }))}
                    >
                      <option value="exit_review">exit_review</option>
                      <option value="hold">hold</option>
                      <option value="blocked">blocked</option>
                    </select>
                  </div>
                  <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.position_evaluation.recommended_action}
                    onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, recommended_action: e.target.value } }))}
                  >
                    <option value="exit_review">exit_review</option>
                    <option value="reduce">reduce</option>
                    <option value="hold">hold</option>
                    <option value="blocked">blocked</option>
                  </select>

                  <div className="grid gap-2 sm:grid-cols-3">
                    {[
                      ["unrealized_pnl", "uPnL"],
                      ["unrealized_pnl_percent", "uPnL %"],
                      ["r_multiple", "R mult"],
                    ].map(([k, label]) => (
                      <input
                        key={k}
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={(form.position_evaluation.pnl as any)[k]}
                        onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, pnl: { ...f.position_evaluation.pnl, [k]: Number(e.target.value) } } }))}
                        placeholder={label}
                      />
                    ))}
                  </div>

                  <div className="grid gap-2 sm:grid-cols-3">
                    {[
                      ["risk_per_share", "Risk/sh"],
                      ["current_distance_to_stop", "Dist stop"],
                      ["distance_to_target", "Dist tgt"],
                      ["position_notional", "Notional"],
                      ["position_size_percent", "Pos %"],
                      ["daily_loss_percent", "Daily loss %"],
                    ].map(([k, label]) => (
                      <input
                        key={k}
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={(form.position_evaluation.risk as any)[k]}
                        onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, risk: { ...f.position_evaluation.risk, [k]: Number(e.target.value) } } }))}
                        placeholder={label}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Thesis validity</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={form.position_evaluation.thesis_validity.valid}
                        onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, thesis_validity: { ...f.position_evaluation.thesis_validity, valid: e.target.checked } } }))}
                      />
                      thesis_valid
                    </label>
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.position_evaluation.thesis_validity.score}
                      onChange={(e) => setForm((f) => ({ ...f, position_evaluation: { ...f.position_evaluation, thesis_validity: { ...f.position_evaluation.thesis_validity, score: Number(e.target.value) } } }))}
                    />
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={(form.position_evaluation.thesis_validity.failed_reasons ?? []).join(",")}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          position_evaluation: {
                            ...f.position_evaluation,
                            thesis_validity: {
                              ...f.position_evaluation.thesis_validity,
                              failed_reasons: e.target.value.split(",").map((x) => x.trim()).filter(Boolean),
                            },
                          },
                        }))
                      }
                      placeholder="failed_reasons (comma separated)"
                    />
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={(form.position_evaluation.thesis_validity.passed_reasons ?? []).join(",")}
                      onChange={(e) =>
                        setForm((f) => ({
                          ...f,
                          position_evaluation: {
                            ...f.position_evaluation,
                            thesis_validity: {
                              ...f.position_evaluation.thesis_validity,
                              passed_reasons: e.target.value.split(",").map((x) => x.trim()).filter(Boolean),
                            },
                          },
                        }))
                      }
                      placeholder="passed_reasons (comma separated)"
                    />
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Position</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <div className="grid gap-2 sm:grid-cols-2">
                      <input
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={form.position.quantity}
                        onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, quantity: Number(e.target.value) } }))}
                      />
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
                        value={form.position.current_price}
                        onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, current_price: Number(e.target.value) } }))}
                      />
                      <input
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={form.position.entry_price}
                        onChange={(e) => setForm((f) => ({ ...f, position: { ...f.position, entry_price: Number(e.target.value) } }))}
                      />
                    </div>
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Master Admin</FieldLabel>
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    {(
                      [
                        ["workflow_enabled", "Workflow enabled"],
                        ["execution_enabled", "Execution enabled"],
                        ["paper_trading_enabled", "Paper trading enabled"],
                        ["live_trading_enabled", "Live trading enabled"],
                        ["broker_execution_enabled", "Broker execution enabled"],
                        ["human_approval_required", "Human approval required"],
                        ["emergency_stop", "Emergency stop"],
                        ["force_close_requested", "Force close requested"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.master_admin[k]}
                          onChange={(e) => setForm((f) => ({ ...f, master_admin: { ...f.master_admin, [k]: e.target.checked } }))}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                  <FieldLabel>Review preferences</FieldLabel>
                  <div className="mt-2 grid gap-2">
                    <input
                      type="number"
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.review_preferences.reduce_percent}
                      onChange={(e) => setForm((f) => ({ ...f, review_preferences: { ...f.review_preferences, reduce_percent: Number(e.target.value) } }))}
                    />
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.review_preferences.close_reason}
                      onChange={(e) => setForm((f) => ({ ...f, review_preferences: { ...f.review_preferences, close_reason: e.target.value } }))}
                    />
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.review_preferences.order_style}
                      onChange={(e) => setForm((f) => ({ ...f, review_preferences: { ...f.review_preferences, order_style: e.target.value } }))}
                    >
                      <option value="market">market</option>
                      <option value="limit">limit</option>
                    </select>
                    <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-300">
                      <span>allow_submit</span>
                      <span className="text-xs text-slate-500">forced false in v1</span>
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={false}
                        disabled
                        readOnly
                      />
                    </label>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {result ? (
            <ResultPanel result={result} />
          ) : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No review loaded yet. Click “Review Sample Close Decision” to simulate review output.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Safety guarantees</h2>
            <div className="mt-2 text-sm text-slate-300">
              Review only: submitted_order=false, broker_called=false, allow_submit forced false, no execution endpoints called, no live trading, and human approval required before any future workflow.
            </div>
            <div className="mt-3 grid gap-2">
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">submitted_order = false</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">broker_called = false</div>
              <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs text-slate-300">allow_submit forced false</div>
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Useful links</h2>
            <div className="mt-3 flex flex-wrap gap-2 text-sm">
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/position-monitoring">
                Position Monitoring
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/settings?tab=master_admin">
                Master Admin Controls
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/auto-execution-monitor">
                Auto-Execution Monitor
              </Link>
              <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/tradenow">
                TradeNow
              </Link>
            </div>
            <div className="mt-2 text-xs text-slate-500">This page does not submit orders.</div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported review actions</h2>
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
            <div className="mt-3 text-xs text-slate-500">Checker status is reported by the close-position status endpoint.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

