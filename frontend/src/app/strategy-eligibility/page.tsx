"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  checkStrategyEligibility,
  getLatestStrategyEligibilityCheck,
  getStrategyEligibilityStatus,
  type StrategyEligibilityCheckRequest,
  type StrategyEligibilityCheckerResult,
  type StrategyEligibilityResult,
  type StrategyEligibilityStatusResponse,
} from "@/lib/api";

const STRATEGY_GROUPS = [
  "regime_aware_momentum",
  "catalyst_event_driven",
  "rvol_vwap_breakout",
  "cross_sectional_ranking",
  "options_quality_volatility",
  "execution_quality",
  "lob_microstructure_research",
];

const CHECKERS = [
  "Proof Status Checker",
  "Data Quality Gate",
  "Risk Budget Gate",
  "Liquidity Gate",
  "Strategy Requirements Checker",
];

const defaultSample: StrategyEligibilityCheckRequest = {
  workflow_context: {
    selected_workflow: "baseline_fast_path",
    workflow_mode: "baseline",
    session: "market_open",
  },
  strategy_candidate: {
    strategy_key: "regime_aware_momentum_catalyst",
    strategy_group: "regime_aware_momentum",
    proof_status: "proven",
    paper_status: "passed",
    requires_backtest: false,
    already_backtested: true,
  },
  market_condition: {
    regime: "risk_on",
    volatility_state: "normal",
    liquidity_state: "good",
    data_quality: "pass",
    urgency: "high",
  },
  features: {
    rvol_elevated: true,
    price_above_vwap: true,
    vwap_reclaiming: false,
    relative_strength_positive: true,
    catalyst_confirmed: true,
    volume_confirms: true,
    spread_pass: true,
    risk_reward_pass: true,
  },
  account_state: {
    risk_budget_available: true,
    paper_trading_enabled: true,
    live_trading_enabled: false,
    human_approval_required: true,
  },
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready" || s === "eligible") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial" || s === "paper_only" || s === "research_only") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail" || s === "blocked") return "border-red-500/45 bg-red-500/15 text-red-100";
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

function CheckerLine({ title, result }: { title: string; result?: StrategyEligibilityCheckerResult }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (run a sample check)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function ResultPanel({ result }: { result: StrategyEligibilityResult }) {
  const eligibility = result.eligibility_status ?? (result.eligible ? "eligible" : "blocked");
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated check</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">{result.strategy_key}</div>
          <div className="mt-1 text-sm text-slate-400">{result.reason}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(eligibility)}`}>{eligibility}</span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(result.llm_used ? "warn" : "pass")}`}>
            LLM used: {result.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Strategy group</FieldLabel>
          <div className="mt-1 text-sm text-slate-200">{result.strategy_group}</div>
          <div className="mt-2 text-xs text-slate-500">Proof: {result.proof_status ?? "—"} · Paper: {result.paper_status ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Allowed / blocked next stages</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {(result.allowed_next_stages ?? []).length ? (
              result.allowed_next_stages!.map((n) => (
                <span key={`allow-${n}`} className="inline-flex rounded-lg border border-emerald-400/20 bg-emerald-500/5 px-2 py-0.5 text-xs text-emerald-100">
                  Stage {n}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">Allowed: —</span>
            )}
          </div>
          <div className="mt-2 space-y-2">
            {(result.blocked_next_stages ?? []).length ? (
              result.blocked_next_stages!.map((b, i) => (
                <div key={`${b.stage}-${i}`} className="flex flex-wrap items-baseline justify-between gap-2 rounded-lg border border-red-500/20 bg-red-500/10 px-3 py-2">
                  <div className="text-xs font-semibold text-red-100">Stage {b.stage}</div>
                  <div className="text-xs text-red-100/80">{b.reason}</div>
                </div>
              ))
            ) : null}
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
                <span className={`inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(r.status))}`}>{String(r.status)}</span>
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

export default function StrategyEligibilityPage() {
  const [status, setStatus] = useState<StrategyEligibilityStatusResponse | null>(null);
  const [result, setResult] = useState<StrategyEligibilityResult | null>(null);
  const [form, setForm] = useState<StrategyEligibilityCheckRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getStrategyEligibilityStatus(), getLatestStrategyEligibilityCheck()]);
        if (cancelled) return;
        setStatus(s);
        setResult(latest.result ?? s.latest_check ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load strategy eligibility status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedGroups = useMemo(
    () => (status?.supported_strategy_groups?.length ? status.supported_strategy_groups : STRATEGY_GROUPS),
    [status]
  );

  const checkerByName = useMemo(() => {
    const map = new Map<string, StrategyEligibilityCheckerResult>();
    for (const r of result?.checker_results ?? []) map.set(r.checker, r);
    return map;
  }, [result]);

  function setFeature(key: keyof StrategyEligibilityCheckRequest["features"], value: boolean) {
    setForm((f) => ({ ...f, features: { ...f.features, [key]: value } }));
  }

  function setAccount(key: keyof StrategyEligibilityCheckRequest["account_state"], value: boolean) {
    setForm((f) => ({ ...f, account_state: { ...f.account_state, [key]: value } }));
  }

  async function handleRun() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await checkStrategyEligibility(form);
      setResult(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Eligibility check failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestStrategyEligibilityCheck();
      setResult(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load latest check");
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
          <h2 className="mb-2 font-semibold text-red-200">Strategy Eligibility</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const checkerStatus = status?.checker_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Strategy Eligibility</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 7 AI-Agent that checks whether a strategy or response logic is allowed under the selected workflow, market conditions, proof status, data quality, and risk gates without calling an LLM.
        </p>
        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          This page simulates eligibility and requirements. It does not execute strategies or trading actions.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <SummaryCard label="Stage" value={7} />
        <SummaryCard label="Checker Status" value={<span className="capitalize">{String(checkerStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" hint="Non-LLM gating only" />
        <SummaryCard label="Latest Check" value={result?.strategy_key ?? "—"} hint={result?.eligibility_status ? `Status: ${result.eligibility_status}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{result?.next_action ?? status?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Eligibility simulation</div>
                <div className="mt-1 text-sm text-slate-400">Edit inputs and run a sample eligibility check (visibility only).</div>
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
                  {actionLoading === "run" ? "Running..." : "Run Sample Eligibility Check"}
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
                Eligible Momentum Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({ ...f, market_condition: { ...f.market_condition, data_quality: "fail" } }))
                }
              >
                Data Quality Fail Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, proof_status: "unproven" }, workflow_context: { ...f.workflow_context, session: "market_open" } }))
                }
              >
                Market-Open Unproven Sample
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
                <FieldLabel>Strategy candidate</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <input
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.strategy_candidate.strategy_key}
                    onChange={(e) => setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, strategy_key: e.target.value } }))}
                  />
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.strategy_candidate.strategy_group}
                    onChange={(e) => setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, strategy_group: e.target.value } }))}
                  >
                    {supportedGroups.map((g) => <option key={g} value={g}>{g}</option>)}
                  </select>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.strategy_candidate.proof_status}
                      onChange={(e) => setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, proof_status: e.target.value } }))}
                    >
                      {["proven", "candidate", "unproven", "unknown"].map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.strategy_candidate.paper_status}
                      onChange={(e) => setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, paper_status: e.target.value } }))}
                    >
                      {["passed", "not_run", "failed", "unknown"].map((p) => <option key={p} value={p}>{p}</option>)}
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={form.strategy_candidate.requires_backtest}
                        onChange={(e) => setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, requires_backtest: e.target.checked } }))}
                      />
                      Requires backtest
                    </label>
                    <label className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={form.strategy_candidate.already_backtested}
                        onChange={(e) => setForm((f) => ({ ...f, strategy_candidate: { ...f.strategy_candidate, already_backtested: e.target.checked } }))}
                      />
                      Already backtested
                    </label>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Market condition</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.market_condition.regime}
                    onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, regime: e.target.value } }))}
                  >
                    {["risk_on", "risk_off", "mixed", "unknown"].map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.market_condition.volatility_state}
                      onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, volatility_state: e.target.value } }))}
                    >
                      {["low", "normal", "high", "unknown"].map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.market_condition.liquidity_state}
                      onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, liquidity_state: e.target.value } }))}
                    >
                      {["good", "ok", "thin", "unknown"].map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.market_condition.data_quality}
                      onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, data_quality: e.target.value } }))}
                    >
                      {["pass", "warn", "fail", "unknown"].map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                    <select className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.market_condition.urgency}
                      onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, urgency: e.target.value } }))}
                    >
                      {["low", "normal", "high"].map((v) => <option key={v} value={v}>{v}</option>)}
                    </select>
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Feature gates</FieldLabel>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {(
                    [
                      ["rvol_elevated", "RVOL elevated"],
                      ["price_above_vwap", "Price above VWAP"],
                      ["vwap_reclaiming", "VWAP reclaiming"],
                      ["relative_strength_positive", "Relative strength positive"],
                      ["catalyst_confirmed", "Catalyst confirmed"],
                      ["volume_confirms", "Volume confirms"],
                      ["spread_pass", "Spread pass"],
                      ["risk_reward_pass", "Risk/reward pass"],
                    ] as const
                  ).map(([k, label]) => (
                    <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={form.features[k]}
                        onChange={(e) => setFeature(k, e.target.checked)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Account state</FieldLabel>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {(
                    [
                      ["risk_budget_available", "Risk budget available"],
                      ["paper_trading_enabled", "Paper trading enabled"],
                      ["live_trading_enabled", "Live trading enabled"],
                      ["human_approval_required", "Human approval required"],
                    ] as const
                  ).map(([k, label]) => (
                    <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                      <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-black/30"
                        checked={form.account_state[k]}
                        onChange={(e) => setAccount(k, e.target.checked)}
                      />
                      {label}
                    </label>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {result ? (
            <ResultPanel result={result} />
          ) : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No check loaded yet. Click “Run Sample Eligibility Check” to simulate a decision.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported strategy groups</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {supportedGroups.map((g) => (
                <li key={g} className="rounded-lg border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2 text-slate-200">
                  {g}
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
            <div className="mt-3 text-xs text-slate-500">Checker results are shown after a simulated check.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

