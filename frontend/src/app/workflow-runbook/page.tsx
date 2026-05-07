"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getWorkflowRunbookLatest,
  getWorkflowRunbookStages,
  getWorkflowRunbookStatus,
  type WorkflowRunbookLatestResponse,
  type WorkflowRunbookStage,
  type WorkflowRunbookStagesResponse,
  type WorkflowRunbookStatusResponse,
} from "@/lib/api";

function chip(status: string): string {
  const s = status.toLowerCase();
  if (s === "present" || s === "ok" || s === "ready") return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "partial_existing" || s === "partial" || s === "present_partial") return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "existing_gated") return "border-sky-500/45 bg-sky-500/15 text-sky-100";
  if (s === "backlog" || s === "missing" || s === "need_to_build") return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  if (s === "fail" || s === "blocked") return "border-red-500/45 bg-red-500/15 text-red-100";
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

function GatePill({ label, value }: { label: string; value: boolean | undefined }) {
  const v = value === true ? "enabled" : value === false ? "disabled" : "unknown";
  return (
    <div className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2">
      <div className="text-xs text-slate-300">{label}</div>
      <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${chip(v)}`}>{v}</span>
    </div>
  );
}

function StageCard({ stage }: { stage: WorkflowRunbookStage }) {
  const health = stage.health?.status ?? stage.implementation_status ?? "unknown";
  const route = stage.frontend_route?.trim() || "";

  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Stage {stage.stage_number}</div>
          <div className="mt-1 text-lg font-semibold text-slate-50">{stage.stage_name}</div>
          <div className="mt-1 text-sm text-slate-400">
            <span className="text-slate-200">{stage.stage_key}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(String(health))}`}>
            {String(health)}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(stage.uses_llm ? "warn" : "pass")}`}>
            uses_llm: {stage.uses_llm ? "true" : "false"}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(stage.submits_orders ? "fail" : "pass")}`}>
            submits_orders: {stage.submits_orders ? "true" : "false"}
          </span>
          <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${chip(stage.broker_called ? "fail" : "pass")}`}>
            broker_called: {stage.broker_called ? "true" : "false"}
          </span>
        </div>
      </div>

      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Connectivity</div>
          <div className="mt-2 grid gap-1 text-xs text-slate-400">
            <div>
              backend_endpoint_family: <span className="text-slate-200">{stage.backend_endpoint_family ?? "—"}</span>
            </div>
            <div>
              frontend_route:{" "}
              {route ? (
                <Link className="text-emerald-300 hover:text-emerald-200" href={route}>
                  {route}
                </Link>
              ) : (
                <span className="text-slate-500">—</span>
              )}
            </div>
            <div>
              action_type: <span className="text-slate-200">{stage.action_type ?? "—"}</span>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {route ? (
              <Link
                href={route}
                className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-emerald-400/25"
              >
                Open UI route
              </Link>
            ) : null}
            <span className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-300">
              Endpoint family: {stage.backend_endpoint_family ?? "—"}
            </span>
          </div>
        </div>

        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Operator guidance</div>
          <div className="mt-2 text-sm text-slate-300">{stage.recommended_operator_action ?? "—"}</div>
          {stage.safety_notes?.length ? (
            <div className="mt-3">
              <div className="text-xs text-slate-500">Safety notes</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {stage.safety_notes.map((n, i) => (
                  <span key={`${n}-${i}`} className="rounded bg-slate-800/60 px-2 py-0.5 text-xs text-slate-300">
                    {n}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      <div className="mt-3 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Inputs</div>
          <div className="mt-2 flex flex-wrap gap-1">
            {(stage.inputs ?? []).length ? (
              (stage.inputs ?? []).map((x, i) => (
                <span key={`${x}-${i}`} className="rounded bg-slate-800/60 px-2 py-0.5 text-xs text-slate-300">
                  {x}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-500">—</span>
            )}
          </div>
        </div>
        <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Outputs</div>
          <div className="mt-2 flex flex-wrap gap-1">
            {(stage.outputs ?? []).length ? (
              (stage.outputs ?? []).map((x, i) => (
                <span key={`${x}-${i}`} className="rounded bg-slate-800/60 px-2 py-0.5 text-xs text-slate-300">
                  {x}
                </span>
              ))
            ) : (
              <span className="text-sm text-slate-500">—</span>
            )}
          </div>
        </div>
      </div>

      <div className="mt-3 rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Next stage keys</div>
        <div className="mt-2 flex flex-wrap gap-1">
          {(stage.next_stage_keys ?? []).length ? (
            (stage.next_stage_keys ?? []).map((x, i) => (
              <span key={`${x}-${i}`} className="rounded bg-slate-800/60 px-2 py-0.5 text-xs text-slate-300">
                {x}
              </span>
            ))
          ) : (
            <span className="text-sm text-slate-500">—</span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function WorkflowRunbookPage() {
  const [status, setStatus] = useState<WorkflowRunbookStatusResponse | null>(null);
  const [stages, setStages] = useState<WorkflowRunbookStage[]>([]);
  const [latest, setLatest] = useState<WorkflowRunbookLatestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadAll(kind: "init" | "refresh") {
    if (kind === "refresh") setRefreshing(true);
    setError(null);
    try {
      const [s, st, l] = await Promise.all([getWorkflowRunbookStatus(), getWorkflowRunbookStages(), getWorkflowRunbookLatest()]);
      setStatus(s);
      setStages(st.stages ?? []);
      setLatest(l);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workflow runbook");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAll("init");
    // no polling
  }, []);

  const summary = status?.summary;
  const gates = status?.master_gates;

  const latestKeys = useMemo(() => {
    const snap = latest?.snapshot ?? null;
    return [
      ["session_router", snap?.session_router ?? null],
      ["workflow_router", snap?.workflow_router ?? null],
      ["strategy_eligibility", snap?.strategy_eligibility ?? null],
      ["trigger_monitoring", snap?.trigger_monitoring ?? null],
      ["execution_planner", snap?.execution_planner ?? null],
      ["position_monitoring", snap?.position_monitoring ?? null],
      ["close_position", snap?.close_position ?? null],
      ["post_trade_evaluation", snap?.post_trade_evaluation ?? null],
      ["learning_loop", snap?.learning_loop ?? null],
    ] as const;
  }, [latest]);

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
          <h2 className="mb-2 font-semibold text-red-200">Workflow Runbook</h2>
          <p className="text-sm text-red-100/90">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Workflow Runbook</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">
              End-to-end visibility dashboard for the US stock day-trading paper workflow. Shows stage connectivity, endpoint families, UI routes, latest snapshots, safety
              gates, and next actions.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {["US Stocks Only", "Day Trading Only", "Paper-First", "No LLM", "No Broker Submission"].map((t) => (
                <span
                  key={t}
                  className={
                    t === "No LLM" || t === "No Broker Submission"
                      ? "rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[10px] font-bold uppercase text-slate-300"
                      : "rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]"
                  }
                >
                  {t}
                </span>
              ))}
            </div>
          </div>
          <button
            type="button"
            onClick={() => loadAll("refresh")}
            disabled={refreshing}
            className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100 transition hover:bg-emerald-400/20 disabled:opacity-50"
          >
            {refreshing ? "Refreshing..." : "Refresh Runbook"}
          </button>
        </div>

        <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
          Read-only runbook dashboard. This page does not execute stages, does not call broker APIs, does not submit orders, and does not call any LLM.
        </div>

        {error ? (
          <div className="mt-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
        ) : null}
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
        <SummaryCard label="Workflow Status" value={summary?.workflow_status ?? "—"} />
        <SummaryCard label="Total Stages" value={summary?.total_stages ?? "—"} />
        <SummaryCard label="Implemented Stages" value={summary?.implemented_stages ?? "—"} />
        <SummaryCard label="Frontend Visible Stages" value={summary?.frontend_visible_stages ?? "—"} />
        <SummaryCard label="Live Trading Enabled" value={summary?.live_trading_enabled ? "Yes" : "No"} />
        <SummaryCard label="Broker Submission Enabled" value={summary?.broker_submission_enabled ? "Yes" : "No"} />
        <SummaryCard label="LLM Required" value={summary?.llm_required ? "Yes" : "No"} />
        <SummaryCard label="Next Action" value={<span className="text-base">{summary?.next_action ?? "—"}</span>} />
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div className="space-y-6">
          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Stages</h2>
                <p className="mt-1 text-xs text-slate-500">Runbook data from `/api/workflow-runbook/stages` (no other stage endpoints called here).</p>
              </div>
              <div className="text-xs text-slate-500">count: {stages.length}</div>
            </div>

            <div className="mt-4 space-y-4">
              {stages.map((st) => (
                <StageCard key={`${st.stage_number}-${st.stage_key}`} stage={st} />
              ))}
            </div>
          </div>
        </div>

        <aside className="space-y-4 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <div className="flex items-start justify-between gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Master Admin gates</h2>
              <Link className="text-xs text-emerald-300 hover:text-emerald-200" href="/settings?tab=master_admin">
                Master Admin Controls →
              </Link>
            </div>
            <div className="mt-3 grid gap-2">
              <GatePill label="workflow_enabled" value={gates?.workflow_enabled} />
              <GatePill label="execution_enabled" value={gates?.execution_enabled} />
              <GatePill label="paper_trading_enabled" value={gates?.paper_trading_enabled} />
              <GatePill label="live_trading_enabled" value={gates?.live_trading_enabled} />
              <GatePill label="broker_execution_enabled" value={gates?.broker_execution_enabled} />
              <GatePill label="human_approval_required" value={gates?.human_approval_required} />
              <GatePill label="emergency_stop" value={gates?.emergency_stop} />
              <GatePill label="force_close_requested" value={gates?.force_close_requested} />
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Latest snapshot</h2>
            <p className="mt-2 text-sm text-slate-300">
              {latest?.snapshot
                ? "Latest stage snapshot keys (read-only)."
                : "No latest snapshot yet. Run the individual stage page to populate latest state."}
            </p>
            <div className="mt-3 space-y-2">
              {latestKeys.map(([k, v]) => (
                <div key={k} className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/20 px-3 py-2">
                  <div className="text-xs text-slate-300">{k}</div>
                  <span className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${chip(v ? "present" : "backlog")}`}>
                    {v ? "present" : "null"}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Safety guarantees</h2>
            <ul className="mt-3 space-y-1 text-xs text-slate-400">
              <li>This page is read-only</li>
              <li>No workflow stages are executed from this page</li>
              <li>No broker calls</li>
              <li>No execution submit calls</li>
              <li>No LLM calls</li>
              <li>No live trading</li>
              <li>No automatic promotion</li>
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}

