"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  api,
  createExecutionPlan,
  getExecutionPlannerStatus,
  getLatestExecutionPlan,
  type ExecutionPlanResult,
  type ExecutionPlannerChecker,
  type ExecutionPlannerPlanRequest,
  type ExecutionPlannerPrecheckHandoffResult,
  type ExecutionPlannerStatusResponse,
} from "@/lib/api";

const CHECKERS = [
  "Position Sizing Calculator",
  "Stop/Target Calculator",
  "Order Type Selector",
  "Slippage/Spread Calculator",
  "Master Admin Gate",
];

const defaultSample: ExecutionPlannerPlanRequest = {
  trigger_evaluation: {
    trigger_state: "fired",
    symbol: "",
    asset_class: "stock",
    horizon: "day_trading",
    trigger_key: "rvol_vwap_breakout_confirm",
  },
  market_snapshot: {
    current_price: 151.1,
    vwap: 149.8,
    atr: 2.25,
    bid: 151.05,
    ask: 151.15,
    spread_percent: 0.07,
    volume_confirms: true,
  },
  account_state: {
    account_equity: 10000,
    cash: 10000,
    risk_budget_available: true,
    max_risk_per_trade_percent: 1.0,
    max_position_size_percent: 20.0,
    paper_trading_enabled: true,
    live_trading_enabled: false,
    human_approval_required: true,
    execution_enabled: false,
  },
  planning_preferences: {
    order_style: "limit",
    stop_method: "atr",
    target_reward_risk: 2.0,
    atr_stop_multiplier: 1.0,
    max_spread_percent: 0.15,
  },
};

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "pass" || s === "present" || s === "ready" || s === "ok") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "warn" || s === "partial" || s.includes("paper")) return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "fail" || s === "blocked" || s.includes("disabled")) return "border-red-500/45 bg-red-500/15 text-red-100";
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

function CheckerLine({ title, result }: { title: string; result?: ExecutionPlannerChecker }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (create a sample plan)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function boolPill(label: string, value: boolean | undefined) {
  const v = value === true ? "enabled" : value === false ? "disabled" : "unknown";
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2">
      <div className="text-xs text-slate-300">{label}</div>
      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${chip(v)}`}>{v}</span>
    </div>
  );
}

function MasterAdminPanel({ plan }: { plan: ExecutionPlanResult | null }) {
  const r = plan?.execution_readiness;
  return (
    <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Master Admin gate</h2>
          <p className="mt-1 text-xs text-slate-500">
            Planning visibility only. These controls must remain safe before any Stage 10 handoff.
          </p>
        </div>
        <Link
          href="/settings?tab=master_admin"
          className="h-fit rounded-lg border border-white/10 bg-[#0a1018] px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-emerald-400/25 hover:text-slate-100"
        >
          Manage Master Admin Controls
        </Link>
      </div>
      <div className="mt-4 grid gap-2">
        {boolPill("Execution enabled", r?.execution_enabled)}
        {boolPill("Emergency stop", r?.emergency_stop)}
        {boolPill("Force close requested", r?.force_close_requested)}
        {boolPill("Human approval required", r?.human_approval_required)}
      </div>
    </div>
  );
}

function PlanPanel({ plan }: { plan: ExecutionPlanResult }) {
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated plan</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">
            {plan.symbol} · {plan.plan_id}
          </div>
          <div className="mt-1 text-sm text-slate-400">Status: {plan.plan_status}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(plan.plan_status)}`}>{plan.plan_status}</span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(plan.llm_used ? "warn" : "pass")}`}>
            LLM used: {plan.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Entry</FieldLabel>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>order_type: {plan.entry?.order_type ?? "—"}</div>
            <div>side: {plan.entry?.side ?? "—"}</div>
            <div>limit_price: {plan.entry?.limit_price ?? "—"}</div>
            <div>reference_price: {plan.entry?.reference_price ?? "—"}</div>
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Risk</FieldLabel>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>stop_loss: {plan.risk?.stop_loss ?? "—"}</div>
            <div>target_price: {plan.risk?.target_price ?? "—"}</div>
            <div>risk_per_share: {plan.risk?.risk_per_share ?? "—"}</div>
            <div>reward_per_share: {plan.risk?.reward_per_share ?? "—"}</div>
            <div>reward_risk_ratio: {plan.risk?.reward_risk_ratio ?? "—"}</div>
            <div>max_dollar_risk: {plan.risk?.max_dollar_risk ?? "—"}</div>
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Sizing</FieldLabel>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>planned_quantity: {plan.sizing?.planned_quantity ?? "—"}</div>
            <div>planned_notional: {plan.sizing?.planned_notional ?? "—"}</div>
            <div>position_size_percent: {plan.sizing?.position_size_percent ?? "—"}</div>
            <div>max_allowed_notional: {plan.sizing?.max_allowed_notional ?? "—"}</div>
            <div>sizing_status: {plan.sizing?.sizing_status ?? "—"}</div>
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Execution readiness</FieldLabel>
          <div className="mt-2 grid gap-2">
            {boolPill("Workflow enabled", plan.execution_readiness?.workflow_enabled)}
            {boolPill("Execution enabled", plan.execution_readiness?.execution_enabled)}
            {boolPill("Paper trading enabled", plan.execution_readiness?.paper_trading_enabled)}
            {boolPill("Live trading enabled", plan.execution_readiness?.live_trading_enabled)}
            {boolPill("Broker execution enabled", plan.execution_readiness?.broker_execution_enabled)}
          </div>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Blockers</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            {(plan.blockers ?? []).length ? plan.blockers!.map((b, i) => (
              <div key={`${b}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">{b}</div>
            )) : <div className="text-sm text-slate-500">—</div>}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Warnings</FieldLabel>
          <div className="mt-2 space-y-1 text-xs text-slate-400">
            {(plan.warnings ?? []).length ? plan.warnings!.map((w, i) => (
              <div key={`${w}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">{w}</div>
            )) : <div className="text-sm text-slate-500">—</div>}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
        <FieldLabel>Handoff note</FieldLabel>
        <div className="mt-1 text-sm text-slate-300">
          Stage 9 does not submit orders. If unblocked, the next stage is <span className="font-semibold">execution_precheck</span> inside the existing execution backend.
        </div>
        <div className="mt-2 text-xs text-slate-500">created_at: {plan.created_at ?? "—"} · next_action: {plan.next_action ?? "—"}</div>
      </div>
    </div>
  );
}

export default function ExecutionPlannerPage() {
  const [status, setStatus] = useState<ExecutionPlannerStatusResponse | null>(null);
  const [plan, setPlan] = useState<ExecutionPlanResult | null>(null);
  const [form, setForm] = useState<ExecutionPlannerPlanRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [handoff, setHandoff] = useState<ExecutionPlannerPrecheckHandoffResult | null>(null);
  const [handoffLoading, setHandoffLoading] = useState(false);
  const [handoffError, setHandoffError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getExecutionPlannerStatus(), getLatestExecutionPlan()]);
        if (cancelled) return;
        setStatus(s);
        setPlan(latest.result ?? s.latest_plan ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load execution planner status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const checkerByName = useMemo(() => {
    const map = new Map<string, ExecutionPlannerChecker>();
    for (const r of status?.checker_statuses ?? []) map.set(r.checker, r);
    return map;
  }, [status]);

  async function handleRun() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await createExecutionPlan(form);
      setPlan(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Plan creation failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestExecutionPlan();
      setPlan(res.result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load latest plan");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRunHandoff() {
    if (!plan || !plan.plan_status) return;
    setHandoffLoading(true);
    setHandoffError(null);
    try {
      const res = await api.createExecutionPlannerPrecheckHandoff({
        execution_plan: plan,
        handoff_preferences: {
          org_slug: "default",
          source: "execution_planner",
          allow_submit: false,
          require_human_approval: true,
        },
      });
      setHandoff(res.handoff);
    } catch (e) {
      setHandoffError(e instanceof Error ? e.message : "Safe precheck handoff failed");
    } finally {
      setHandoffLoading(false);
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
          <h2 className="mb-2 font-semibold text-red-200">Execution Planner</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const plannerStatus = status?.planner_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Execution Planner</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 9 AI-Agent that converts a fired stock day-trading trigger into an entry, stop, target, position size, and execution readiness plan without submitting orders or calling an LLM.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {[
            "US Stocks Only",
            "Day Trading Only",
            "Paper-First",
            "No LLM",
            "No Orders Submitted",
          ].map((t) => (
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
          Planning visibility only. This page does not submit orders, call broker APIs, or trigger execution endpoints.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
        <SummaryCard label="Stage" value={9} />
        <SummaryCard label="Planner Status" value={<span className="capitalize">{String(plannerStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" />
        <SummaryCard label="Asset Scope" value="US Stocks" />
        <SummaryCard label="Horizon Scope" value="Day Trading" />
        <SummaryCard label="Mode Scope" value="Paper-first" />
        <SummaryCard label="Latest Plan" value={plan?.symbol ?? "—"} hint={plan?.plan_id ? `Plan: ${plan.plan_id}` : undefined} />
        <SummaryCard label="Next Action" value={<span className="text-base">{plan?.next_action ?? status?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Plan simulation</div>
                <div className="mt-1 text-sm text-slate-400">Create a sample execution plan (visibility only).</div>
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
                  {actionLoading === "run" ? "Planning..." : "Create Sample Execution Plan"}
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
                onClick={() => setForm((f) => ({ ...f, account_state: { ...f.account_state, execution_enabled: false } }))}
              >
                Blocked by Master Admin Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm(defaultSample)}
              >
                Clean Paper Plan Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() =>
                  setForm((f) => ({
                    ...f,
                    trigger_evaluation: { ...f.trigger_evaluation, symbol: "", asset_class: "crypto" },
                  }))
                }
              >
                Crypto Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, trigger_evaluation: { ...f.trigger_evaluation, trigger_state: "armed" } }))}
              >
                Armed Trigger Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, market_snapshot: { ...f.market_snapshot, spread_percent: 0.5 } }))}
              >
                High Spread Blocked Sample
              </button>
              <button
                type="button"
                className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-1.5 text-sm text-slate-300 hover:border-emerald-400/25 hover:text-slate-100"
                onClick={() => setForm((f) => ({ ...f, account_state: { ...f.account_state, max_position_size_percent: 5.0 } }))}
              >
                Capped Quantity Sample
              </button>
            </div>

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Trigger evaluation</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <select
                    className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                    value={form.trigger_evaluation.trigger_state}
                    onChange={(e) => setForm((f) => ({ ...f, trigger_evaluation: { ...f.trigger_evaluation, trigger_state: e.target.value } }))}
                  >
                    {["fired", "armed", "not_ready", "blocked", "expired"].map((v) => <option key={v} value={v}>{v}</option>)}
                  </select>
                  <div className="grid gap-2 sm:grid-cols-2">
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_evaluation.symbol}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_evaluation: { ...f.trigger_evaluation, symbol: e.target.value } }))}
                    />
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_evaluation.asset_class}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_evaluation: { ...f.trigger_evaluation, asset_class: e.target.value } }))}
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
                      value={form.trigger_evaluation.horizon}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_evaluation: { ...f.trigger_evaluation, horizon: e.target.value } }))}
                    >
                      <option value="day_trading">day_trading</option>
                      <option value="swing">swing</option>
                      <option value="unknown">unknown</option>
                    </select>
                    <input
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.trigger_evaluation.trigger_key}
                      onChange={(e) => setForm((f) => ({ ...f, trigger_evaluation: { ...f.trigger_evaluation, trigger_key: e.target.value } }))}
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Market snapshot</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <div className="grid gap-2 sm:grid-cols-3">
                    {[
                      ["current_price", "Current"],
                      ["vwap", "VWAP"],
                      ["atr", "ATR"],
                    ].map(([k, label]) => (
                      <input
                        key={k}
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={(form.market_snapshot as any)[k]}
                        onChange={(e) => setForm((f) => ({ ...f, market_snapshot: { ...f.market_snapshot, [k]: Number(e.target.value) } }))}
                        placeholder={label}
                      />
                    ))}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {[
                      ["bid", "Bid"],
                      ["ask", "Ask"],
                      ["spread_percent", "Spread %"],
                    ].map(([k, label]) => (
                      <input
                        key={k}
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={(form.market_snapshot as any)[k]}
                        onChange={(e) => setForm((f) => ({ ...f, market_snapshot: { ...f.market_snapshot, [k]: Number(e.target.value) } }))}
                        placeholder={label}
                      />
                    ))}
                  </div>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-white/20 bg-black/30"
                      checked={form.market_snapshot.volume_confirms}
                      onChange={(e) => setForm((f) => ({ ...f, market_snapshot: { ...f.market_snapshot, volume_confirms: e.target.checked } }))}
                    />
                    Volume confirms
                  </label>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Account state</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <div className="grid gap-2 sm:grid-cols-2">
                    {[
                      ["account_equity", "Equity"],
                      ["cash", "Cash"],
                      ["max_risk_per_trade_percent", "Max risk %"],
                      ["max_position_size_percent", "Max pos %"],
                    ].map(([k, label]) => (
                      <input
                        key={k}
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={(form.account_state as any)[k]}
                        onChange={(e) => setForm((f) => ({ ...f, account_state: { ...f.account_state, [k]: Number(e.target.value) } }))}
                        placeholder={label}
                      />
                    ))}
                  </div>
                  <div className="grid gap-2 sm:grid-cols-2">
                    {(
                      [
                        ["risk_budget_available", "Risk budget available"],
                        ["paper_trading_enabled", "Paper trading enabled"],
                        ["live_trading_enabled", "Live trading enabled"],
                        ["human_approval_required", "Human approval required"],
                        ["execution_enabled", "Execution enabled"],
                      ] as const
                    ).map(([k, label]) => (
                      <label key={k} className="flex items-center gap-2 text-sm text-slate-300">
                        <input
                          type="checkbox"
                          className="h-4 w-4 rounded border-white/20 bg-black/30"
                          checked={form.account_state[k]}
                          onChange={(e) => setForm((f) => ({ ...f, account_state: { ...f.account_state, [k]: e.target.checked } }))}
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </div>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Planning preferences</FieldLabel>
                <div className="mt-2 grid gap-2">
                  <div className="grid gap-2 sm:grid-cols-2">
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.planning_preferences.order_style}
                      onChange={(e) => setForm((f) => ({ ...f, planning_preferences: { ...f.planning_preferences, order_style: e.target.value } }))}
                    >
                      <option value="limit">limit</option>
                      <option value="market">market</option>
                    </select>
                    <select
                      className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                      value={form.planning_preferences.stop_method}
                      onChange={(e) => setForm((f) => ({ ...f, planning_preferences: { ...f.planning_preferences, stop_method: e.target.value } }))}
                    >
                      <option value="atr">atr</option>
                      <option value="fixed">fixed</option>
                    </select>
                  </div>
                  <div className="grid gap-2 sm:grid-cols-3">
                    {[
                      ["target_reward_risk", "Target R/R"],
                      ["atr_stop_multiplier", "ATR mult"],
                      ["max_spread_percent", "Max spread %"],
                    ].map(([k, label]) => (
                      <input
                        key={k}
                        type="number"
                        className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                        value={(form.planning_preferences as any)[k]}
                        onChange={(e) => setForm((f) => ({ ...f, planning_preferences: { ...f.planning_preferences, [k]: Number(e.target.value) } }))}
                        placeholder={label}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>

          {plan ? (
            <>
              <PlanPanel plan={plan} />

              <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Stage 9 → Stage 10 Precheck Handoff</div>
                    <p className="mt-1 text-sm text-slate-400">
                      Converts the current execution plan into a safe execution request preview and runs offline precheck logic. This never submits orders and never calls the broker.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRunHandoff}
                    disabled={!plan || !plan.plan_status || loading || actionLoading !== null || handoffLoading}
                    className="h-fit rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/20 disabled:opacity-50"
                  >
                    {handoffLoading ? "Running..." : "Run Safe Precheck Handoff"}
                  </button>
                </div>

                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                    <FieldLabel>Safety guarantees</FieldLabel>
                    <div className="mt-2 grid gap-2">
                      {boolPill("submitted_order (guarantee)", false)}
                      {boolPill("broker_called (guarantee)", false)}
                      {boolPill("allow_submit forced false", false)}
                      {boolPill("live trading enabled from this page", false)}
                    </div>
                    <div className="mt-3 text-xs text-slate-500">
                      This page does not call execution submit endpoints. It only calls the precheck handoff endpoint for preview.
                    </div>
                  </div>

                  <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                    <FieldLabel>Links (no submit here)</FieldLabel>
                    <div className="mt-2 flex flex-wrap gap-2 text-sm">
                      <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/auto-execution-monitor">
                        Auto-Execution Monitor
                      </Link>
                      <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/settings?tab=master_admin">
                        Master Admin Controls
                      </Link>
                      <Link className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-200 hover:border-emerald-400/25" href="/tradenow">
                        TradeNow
                      </Link>
                    </div>
                  </div>
                </div>

                {handoffError ? (
                  <div className="mt-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">
                    {handoffError}
                  </div>
                ) : null}

                {handoff ? (
                  <div className="mt-4 space-y-3">
                    <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                      <FieldLabel>Handoff result</FieldLabel>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(handoff.precheck_status)}`}>{handoff.precheck_status}</span>
                        <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(handoff.submitted_order ? "fail" : "pass")}`}>
                          submitted_order: {handoff.submitted_order ? "true" : "false"}
                        </span>
                        <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(handoff.broker_called ? "fail" : "pass")}`}>
                          broker_called: {handoff.broker_called ? "true" : "false"}
                        </span>
                      </div>
                      <div className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
                        <div>handoff_id: {handoff.handoff_id}</div>
                        <div>handoff_to_stage: {handoff.handoff_to_stage}</div>
                        <div>handoff_type: {handoff.handoff_type}</div>
                        <div>plan_id: {handoff.plan_id}</div>
                        <div>symbol: {handoff.symbol}</div>
                        <div>llm_used: {String(handoff.llm_used)}</div>
                        <div>created_at: {handoff.created_at}</div>
                      </div>
                      <div className="mt-3 text-sm text-emerald-200/80">next_action: {handoff.next_action}</div>
                    </div>

                    <div className="grid gap-3 lg:grid-cols-2">
                      <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                        <FieldLabel>Blockers</FieldLabel>
                        <div className="mt-2 space-y-1 text-xs text-slate-400">
                          {(handoff.blockers ?? []).length ? handoff.blockers.map((b, i) => (
                            <div key={`${b}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">{b}</div>
                          )) : <div className="text-sm text-slate-500">—</div>}
                        </div>
                      </div>
                      <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                        <FieldLabel>Warnings</FieldLabel>
                        <div className="mt-2 space-y-1 text-xs text-slate-400">
                          {(handoff.warnings ?? []).length ? handoff.warnings.map((w, i) => (
                            <div key={`${w}-${i}`} className="rounded-lg border border-white/5 bg-black/20 px-3 py-2">{w}</div>
                          )) : <div className="text-sm text-slate-500">—</div>}
                        </div>
                      </div>
                    </div>

                    <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                      <FieldLabel>Execution request preview</FieldLabel>
                      <pre className="mt-2 max-h-[320px] overflow-auto rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-slate-200">
{JSON.stringify(handoff.execution_request_preview ?? {}, null, 2)}
                      </pre>
                    </div>

                    <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                      <FieldLabel>Precheck preview</FieldLabel>
                      <div className="mt-2 text-sm text-slate-300">
                        status: <span className="font-semibold">{handoff.precheck?.status ?? "—"}</span>
                      </div>
                      {(handoff.precheck?.steps ?? []).length ? (
                        <pre className="mt-2 max-h-[260px] overflow-auto rounded-lg border border-white/10 bg-black/30 p-3 text-xs text-slate-200">
{JSON.stringify(handoff.precheck.steps, null, 2)}
                        </pre>
                      ) : (
                        <div className="mt-2 text-sm text-slate-500">Offline precheck preview returned no step details in v1.</div>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/60 p-4 text-sm text-slate-400">
                    Run the safe handoff to preview the Stage 10 precheck request and results. No orders will be submitted.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No plan loaded yet. Click “Create Sample Execution Plan” to simulate planning output.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <MasterAdminPanel plan={plan} />
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Checker status</h2>
            <div className="mt-3 space-y-2">
              {CHECKERS.map((c) => (
                <CheckerLine key={c} title={c} result={checkerByName.get(c)} />
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">Checker status is reported by the planner status endpoint.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

