"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  getLatestWorkflowRoute,
  getWorkflowRouterStatus,
  runWorkflowRoute,
  type WorkflowCheckerResult,
  type WorkflowDecision,
  type WorkflowRouteRequest,
  type WorkflowRouterStatusResponse,
} from "@/lib/api";

const SUPPORTED_WORKFLOWS = [
  "baseline_fast_path",
  "adjusted_research_path",
  "paper_only_path",
  "backtest_queue_path",
  "observe_only_path",
  "no_trade_path",
];

const CHECKERS = ["Session Checker", "Urgency Checker", "Proof Status Checker", "Risk State Checker"];

const defaultSample: WorkflowRouteRequest = {
  session: "market_open",
  market_condition: {
    regime: "risk_on",
    volatility_state: "normal",
    liquidity_state: "good",
    data_quality: "pass",
    urgency: "high",
  },
  strategy_or_response_status: {
    proof_status: "proven",
    paper_status: "passed",
    requires_backtest: false,
    already_backtested: true,
  },
  account_state: {
    risk_budget_available: true,
    paper_trading_enabled: true,
    live_trading_enabled: false,
    human_approval_required: true,
  },
  execution_state: {
    broker_ready: true,
    spread_pass: true,
    slippage_pass: true,
  },
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

function CheckerLine({ title, result }: { title: string; result?: WorkflowCheckerResult }) {
  const status = result?.status ?? "unknown";
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5">
      <div>
        <div className="text-sm font-medium text-slate-200">{title}</div>
        <div className="mt-0.5 text-xs text-slate-500">{result?.message ?? "No details yet (run a sample decision)."}</div>
      </div>
      <span className={`mt-0.5 inline-flex h-fit rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(status))}`}>
        {String(status)}
      </span>
    </div>
  );
}

function DecisionPanel({ decision }: { decision: WorkflowDecision }) {
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest simulated decision</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">{decision.selected_workflow}</div>
          <div className="mt-1 text-sm text-slate-400">{decision.reason}</div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(decision.workflow_mode)}`}>
            {decision.workflow_mode}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(decision.llm_used ? "warn" : "pass")}`}>
            LLM used: {decision.llm_used ? "Yes" : "No"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Allowed next stages</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {(decision.allowed_next_stages ?? []).length ? (
              decision.allowed_next_stages.map((n) => (
                <span key={`allow-${n}`} className="inline-flex rounded-lg border border-emerald-400/20 bg-emerald-500/5 px-2 py-0.5 text-xs text-emerald-100">
                  Stage {n}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">None</span>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Blocked stages</FieldLabel>
          <div className="mt-2 flex flex-wrap gap-2">
            {(decision.blocked_stages ?? []).length ? (
              decision.blocked_stages.map((n) => (
                <span key={`block-${n}`} className="inline-flex rounded-lg border border-red-500/25 bg-red-500/10 px-2 py-0.5 text-xs text-red-100">
                  Stage {n}
                </span>
              ))
            ) : (
              <span className="text-xs text-slate-500">None</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
        <FieldLabel>Checker results</FieldLabel>
        <div className="mt-2 space-y-2">
          {(decision.checker_results ?? []).length ? (
            decision.checker_results.map((r, idx) => (
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

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Next action</FieldLabel>
          <div className="mt-1 text-sm text-emerald-200/80">{decision.next_action ?? "—"}</div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <FieldLabel>Created at</FieldLabel>
          <div className="mt-1 text-sm text-slate-400">{decision.created_at ?? "—"}</div>
        </div>
      </div>
    </div>
  );
}

export default function WorkflowRouterPage() {
  const [status, setStatus] = useState<WorkflowRouterStatusResponse | null>(null);
  const [decision, setDecision] = useState<WorkflowDecision | null>(null);
  const [form, setForm] = useState<WorkflowRouteRequest>(defaultSample);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"run" | "latest" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, latest] = await Promise.all([getWorkflowRouterStatus(), getLatestWorkflowRoute()]);
        if (cancelled) return;
        setStatus(s);
        setDecision(latest.decision ?? s.latest_decision ?? null);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load workflow router status");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const supportedWorkflows = useMemo(() => status?.supported_workflows?.length ? status.supported_workflows : SUPPORTED_WORKFLOWS, [status]);

  const checkerResultsByName = useMemo(() => {
    const map = new Map<string, WorkflowCheckerResult>();
    for (const r of decision?.checker_results ?? []) map.set(r.checker, r);
    return map;
  }, [decision]);

  function setGate<K extends keyof WorkflowRouteRequest["account_state"]>(
    key: K,
    value: WorkflowRouteRequest["account_state"][K]
  ) {
    setForm((f) => ({ ...f, account_state: { ...f.account_state, [key]: value } }));
  }

  function setExecGate<K extends keyof WorkflowRouteRequest["execution_state"]>(
    key: K,
    value: WorkflowRouteRequest["execution_state"][K]
  ) {
    setForm((f) => ({ ...f, execution_state: { ...f.execution_state, [key]: value } }));
  }

  async function handleRunSample() {
    setActionLoading("run");
    setError(null);
    try {
      const res = await runWorkflowRoute(form);
      setDecision(res.decision);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Route decision failed");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleLoadLatest() {
    setActionLoading("latest");
    setError(null);
    try {
      const res = await getLatestWorkflowRoute();
      setDecision(res.decision);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load latest decision");
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
          <h2 className="mb-2 font-semibold text-red-200">Workflow Router</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  const routerStatus = status?.router_status ?? "unknown";

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Workflow Router</h1>
        <p className="mt-2 max-w-3xl text-sm text-slate-400">
          Stage 5 AI-Agent that selects baseline, adjusted, paper-only, backtest-queue, observe-only, or no-trade routes without calling an LLM.
        </p>
        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          This page simulates and explains route decisions. It does not execute trades or submit orders.
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-6">
        <SummaryCard label="Stage" value={5} />
        <SummaryCard label="Router Status" value={<span className="capitalize">{String(routerStatus)}</span>} />
        <SummaryCard label="LLM Required" value="No" hint="Non-LLM routing only" />
        <SummaryCard label="Baseline Workflow Available" value={status?.baseline_workflow_available ? "Yes" : "No"} />
        <SummaryCard label="Adjusted Workflow Available" value={status?.adjusted_workflow_available ? "Yes" : "No"} />
        <SummaryCard label="Latest Decision" value={decision?.selected_workflow ?? "—"} hint={decision?.workflow_mode ? `Mode: ${decision.workflow_mode}` : undefined} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Route decision simulation</div>
                <div className="mt-1 text-sm text-slate-400">Edit inputs and run a sample route decision (visibility only).</div>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={handleLoadLatest}
                  disabled={actionLoading !== null}
                  className="rounded-lg border border-white/10 bg-[#0a1018] px-3 py-2 text-sm font-medium text-slate-300 transition hover:border-emerald-400/25 hover:text-slate-100 disabled:opacity-50"
                >
                  {actionLoading === "latest" ? "Loading..." : "Load Latest Decision"}
                </button>
                <button
                  type="button"
                  onClick={handleRunSample}
                  disabled={actionLoading !== null}
                  className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/20 disabled:opacity-50"
                >
                  {actionLoading === "run" ? "Running..." : "Run Sample Route Decision"}
                </button>
              </div>
            </div>

            {error ? (
              <div className="mt-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">
                {error}
              </div>
            ) : null}

            <div className="mt-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Session</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.session}
                  onChange={(e) => setForm((f) => ({ ...f, session: e.target.value }))}
                >
                  <option value="market_open">market_open</option>
                  <option value="pre_market">pre_market</option>
                  <option value="after_hours">after_hours</option>
                  <option value="market_closed">market_closed</option>
                </select>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Urgency</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.market_condition.urgency}
                  onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, urgency: e.target.value } }))}
                >
                  <option value="low">low</option>
                  <option value="normal">normal</option>
                  <option value="high">high</option>
                </select>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Proof status</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.strategy_or_response_status.proof_status}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, strategy_or_response_status: { ...f.strategy_or_response_status, proof_status: e.target.value } }))
                  }
                >
                  <option value="proven">proven</option>
                  <option value="candidate">candidate</option>
                  <option value="unproven">unproven</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Data quality</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.market_condition.data_quality}
                  onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, data_quality: e.target.value } }))}
                >
                  <option value="pass">pass</option>
                  <option value="warn">warn</option>
                  <option value="fail">fail</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Liquidity state</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.market_condition.liquidity_state}
                  onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, liquidity_state: e.target.value } }))}
                >
                  <option value="good">good</option>
                  <option value="ok">ok</option>
                  <option value="thin">thin</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Volatility state</FieldLabel>
                <select
                  className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={form.market_condition.volatility_state}
                  onChange={(e) => setForm((f) => ({ ...f, market_condition: { ...f.market_condition, volatility_state: e.target.value } }))}
                >
                  <option value="low">low</option>
                  <option value="normal">normal</option>
                  <option value="high">high</option>
                  <option value="unknown">unknown</option>
                </select>
              </div>

              <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
                <FieldLabel>Account + execution gates</FieldLabel>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-white/20 bg-black/30"
                      checked={form.account_state.risk_budget_available}
                      onChange={(e) => setGate("risk_budget_available", e.target.checked)}
                    />
                    Risk budget available
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-white/20 bg-black/30"
                      checked={form.execution_state.broker_ready}
                      onChange={(e) => setExecGate("broker_ready", e.target.checked)}
                    />
                    Broker ready
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-white/20 bg-black/30"
                      checked={form.execution_state.spread_pass}
                      onChange={(e) => setExecGate("spread_pass", e.target.checked)}
                    />
                    Spread pass
                  </label>
                  <label className="flex items-center gap-2 text-sm text-slate-300">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-white/20 bg-black/30"
                      checked={form.execution_state.slippage_pass}
                      onChange={(e) => setExecGate("slippage_pass", e.target.checked)}
                    />
                    Slippage pass
                  </label>
                </div>
              </div>
            </div>
          </div>

          {decision ? <DecisionPanel decision={decision} /> : (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No decision loaded yet. Click “Run Sample Route Decision” to simulate a routing choice.
            </div>
          )}
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Supported workflows</h2>
            <ul className="mt-3 space-y-2 text-sm">
              {supportedWorkflows.map((w) => (
                <li key={w} className="rounded-lg border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2 text-slate-200">
                  {w}
                </li>
              ))}
            </ul>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Checker status</h2>
            <div className="mt-3 space-y-2">
              {CHECKERS.map((c) => (
                <CheckerLine key={c} title={c} result={checkerResultsByName.get(c)} />
              ))}
            </div>
            <div className="mt-3 text-xs text-slate-500">
              Checker results are shown after a simulated route decision run.
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}

