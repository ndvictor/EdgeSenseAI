"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getWorkflowRunbookLatest,
  getWorkflowRunbookStages,
  getWorkflowRunbookStatus,
  getLatestWorkflowOrchestratorRun,
  listWorkflowOrchestratorRuns,
  runWorkflowOrchestrator,
  getWorkflowOrchestratorTrace,
  pauseWorkflowOrchestratorRun,
  resumeWorkflowOrchestratorRun,
  stopWorkflowOrchestratorRun,
  getPlatformReadinessStatus,
  getAgentRuntimeStatus,
  getApprovalQueueStatus,
  getWorkflowSchedulerStatus,
  getQlibStatus,
  getAgentRun,
  type AgentRunResultRecord,
  type OrchestratorRunRecord,
  type WorkflowRunbookLatestResponse,
  type WorkflowRunbookStage,
  type WorkflowRunbookStagesResponse,
  type WorkflowRunbookStatusResponse,
  type WorkflowOrchestratorTraceResponse,
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

type MainTab = "operator" | "catalog";

export default function WorkflowRunbookPage() {
  const [status, setStatus] = useState<WorkflowRunbookStatusResponse | null>(null);
  const [stages, setStages] = useState<WorkflowRunbookStage[]>([]);
  const [latest, setLatest] = useState<WorkflowRunbookLatestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mainTab, setMainTab] = useState<MainTab>("operator");

  const [prRollup, setPrRollup] = useState<Record<string, unknown> | null>(null);
  const [arStatus, setArStatus] = useState<Record<string, unknown> | null>(null);
  const [latestOrc, setLatestOrc] = useState<OrchestratorRunRecord | null>(null);
  const [approvalSum, setApprovalSum] = useState<Record<string, unknown> | null>(null);
  const [schedStatus, setSchedStatus] = useState<Record<string, unknown> | null>(null);
  const [qlibSt, setQlibSt] = useState<Record<string, unknown> | null>(null);

  const [symbolsText, setSymbolsText] = useState("AMD");
  const [source, setSource] = useState("manual");
  const [maxCand, setMaxCand] = useState(5);
  const [stopStage, setStopStage] = useState(9);
  const [simPos, setSimPos] = useState(false);
  const [simClose, setSimClose] = useState(false);
  const [orcBusy, setOrcBusy] = useState(false);
  const [lastRun, setLastRun] = useState<OrchestratorRunRecord | null>(null);
  const [activeWfId, setActiveWfId] = useState<string>("");
  const [trace, setTrace] = useState<WorkflowOrchestratorTraceResponse | null>(null);
  const [recentRuns, setRecentRuns] = useState<OrchestratorRunRecord[]>([]);
  const [traceErr, setTraceErr] = useState<string | null>(null);
  const [agentTraceByRunId, setAgentTraceByRunId] = useState<Record<string, AgentRunResultRecord | null>>({});
  const [agentTraceLoading, setAgentTraceLoading] = useState<string | null>(null);

  const summary = status?.summary;
  const gates = status?.master_gates;

  const loadOperatorSnapshot = useCallback(async () => {
    try {
      const [pr, ar, lo, ap, sch, ql] = await Promise.all([
        getPlatformReadinessStatus().catch(() => null),
        getAgentRuntimeStatus().catch(() => null),
        getLatestWorkflowOrchestratorRun().catch(() => null),
        getApprovalQueueStatus().catch(() => null),
        getWorkflowSchedulerStatus().catch(() => null),
        getQlibStatus().catch(() => null),
      ]);
      if (pr) setPrRollup(pr as Record<string, unknown>);
      if (ar) setArStatus(ar as Record<string, unknown>);
      if (lo?.run) setLatestOrc(lo.run);
      else setLatestOrc(null);
      if (ap) setApprovalSum(ap as Record<string, unknown>);
      if (sch) setSchedStatus(sch as Record<string, unknown>);
      if (ql) setQlibSt(ql as Record<string, unknown>);
    } catch {
      /* best-effort */
    }
  }, []);

  const loadRecentRuns = useCallback(async () => {
    try {
      const r = await listWorkflowOrchestratorRuns(25);
      setRecentRuns(r.runs ?? []);
    } catch {
      setRecentRuns([]);
    }
  }, []);

  async function loadAll(kind: "init" | "refresh") {
    if (kind === "refresh") setRefreshing(true);
    setError(null);
    try {
      const [s, st, l] = await Promise.all([getWorkflowRunbookStatus(), getWorkflowRunbookStages(), getWorkflowRunbookLatest()]);
      setStatus(s);
      setStages(st.stages ?? []);
      setLatest(l);
      await Promise.all([loadOperatorSnapshot(), loadRecentRuns()]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load workflow runbook");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadAll("init");
  }, []);

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

  async function handleRunWorkflow() {
    setOrcBusy(true);
    setError(null);
    try {
      const syms = symbolsText
        .split(/[\s,]+/)
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean);
      const res = await runWorkflowOrchestrator({
        symbols: syms.length ? syms : ["AMD"],
        asset_class: "stock",
        horizon: "day_trading",
        mode: "paper_first",
        source,
        max_candidates: maxCand,
        stop_at_stage: stopStage,
        dry_run: true,
        require_human_approval: true,
        allow_submit: false,
        simulated_position: simPos,
        simulated_closed_trade: simClose,
      });
      setLastRun(res.run);
      setActiveWfId(res.run.workflow_run_id);
      await loadRecentRuns();
      await loadOperatorSnapshot();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run workflow failed");
    } finally {
      setOrcBusy(false);
    }
  }

  async function handleLoadTrace() {
    const id = activeWfId || lastRun?.workflow_run_id || latestOrc?.workflow_run_id;
    if (!id) {
      setTraceErr("Set a workflow_run_id by running a workflow or picking a recent run.");
      return;
    }
    setTraceErr(null);
    try {
      const t = await getWorkflowOrchestratorTrace(id);
      setTrace(t);
    } catch (e) {
      setTraceErr(e instanceof Error ? e.message : "Trace load failed");
    }
  }

  async function doPauseResumeStop(action: "pause" | "resume" | "stop") {
    const id = activeWfId || lastRun?.workflow_run_id || latestOrc?.workflow_run_id;
    if (!id) {
      setError("No workflow_run_id for control action.");
      return;
    }
    setError(null);
    try {
      if (action === "pause") await pauseWorkflowOrchestratorRun(id);
      if (action === "resume") await resumeWorkflowOrchestratorRun(id);
      if (action === "stop") await stopWorkflowOrchestratorRun(id);
      await handleLoadTrace();
      await loadRecentRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Control action failed");
    }
  }

  async function loadAgentTrace(runId: string) {
    setAgentTraceLoading(runId);
    try {
      const r = await getAgentRun(runId);
      setAgentTraceByRunId((prev) => ({ ...prev, [runId]: r.agent_run }));
    } catch {
      setAgentTraceByRunId((prev) => ({ ...prev, [runId]: null }));
    } finally {
      setAgentTraceLoading(null);
    }
  }

  const prSystems = (prRollup?.systems as Record<string, unknown> | undefined) ?? undefined;
  const execGates = prSystems?.execution_gates as Record<string, unknown> | undefined;
  const brokerSubmitGate = execGates?.broker_execution_enabled;

  const pendingApprovals =
    (approvalSum?.summary as Record<string, unknown> | undefined)?.pending_count ??
    (approvalSum?.summary as Record<string, unknown> | undefined)?.["pending_count"];

  const displayRun = lastRun ?? latestOrc;
  const timeline = (displayRun?.stage_timeline as Array<Record<string, unknown>>) ?? [];

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
              Agent-driven paper-first workflow control dashboard with trace, approval boundary, safety gates, and operator next actions.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              {["US Stocks", "Day Trading", "Paper-First", "Human Approval", "No Broker Submit"].map((t) => (
                <span
                  key={t}
                  className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-[10px] font-bold uppercase text-emerald-200 shadow-[0_0_16px_rgba(16,185,129,0.10)]"
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
            {refreshing ? "Refreshing..." : "Refresh all"}
          </button>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {(
            [
              ["operator", "Operator control"],
              ["catalog", "Stage catalog (read-only)"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setMainTab(id)}
              className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
                mainTab === id
                  ? "border-emerald-400/50 bg-emerald-400/15 text-emerald-100"
                  : "border-white/10 bg-[#0a1018] text-slate-400 hover:border-emerald-400/25"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {error ? (
          <div className="mt-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
        ) : null}
      </div>

      {mainTab === "operator" ? (
        <div className="mb-10 space-y-6">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
            <SummaryCard
              label="Platform readiness"
              value={<span className="text-base font-medium">{(prRollup?.status as string) ?? "—"}</span>}
              hint={((prRollup?.systems as Record<string, unknown>)?.database as Record<string, unknown>)?.connected === true ? "DB ok" : "Check /platform-readiness"}
            />
            <SummaryCard
              label="Agent runtime"
              value={
                <span className="text-base">
                  {String((arStatus?.summary as Record<string, unknown>)?.persistence_mode ?? "—")}
                </span>
              }
              hint={`Redis: ${String((arStatus?.summary as Record<string, unknown>)?.redis_mode ?? "—")}`}
            />
            <SummaryCard
              label="Latest workflow"
              value={<span className="text-base">{latestOrc?.status ?? "—"}</span>}
              hint={latestOrc?.workflow_run_id ? latestOrc.workflow_run_id.slice(0, 18) + "…" : undefined}
            />
            <SummaryCard label="Approvals pending" value={pendingApprovals != null ? String(pendingApprovals) : "—"} />
            <SummaryCard
              label="Scheduler"
              value={
                <span className="text-base">
                  {String((schedStatus?.summary as Record<string, unknown>)?.persistence_mode ?? (schedStatus?.status as string) ?? "—")}
                </span>
              }
            />
            <SummaryCard label="Qlib" value={<span className="text-base">{(qlibSt?.status as string) ?? "—"}</span>} />
            <SummaryCard
              label="Broker submission (gate)"
              value={brokerSubmitGate === true ? "true" : brokerSubmitGate === false ? "false" : String(summary?.broker_submission_enabled ?? "—")}
            />
            <SummaryCard label="Next action" value={<span className="text-base">{displayRun?.next_action ?? summary?.next_action ?? "—"}</span>} />
          </div>

          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12]/95 p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Run workflow (orchestrator preview)</h2>
            <p className="mt-1 text-xs text-slate-500">
              Calls <code className="text-emerald-200/90">POST /api/workflow-orchestrator/run</code> only. Deterministic agents; no LLM; no broker submission.
              <Link className="ml-2 text-emerald-300 hover:text-emerald-200" href="/approval-queue">
                Approval queue →
              </Link>
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
              <label className="block text-xs text-slate-400">
                Symbols
                <input
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={symbolsText}
                  onChange={(e) => setSymbolsText(e.target.value)}
                />
              </label>
              <label className="block text-xs text-slate-400">
                Source
                <select
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                >
                  {["manual", "scanner", "candidate", "command_center"].map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-xs text-slate-400">
                Max candidates
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={maxCand}
                  onChange={(e) => setMaxCand(Number(e.target.value))}
                />
              </label>
              <label className="block text-xs text-slate-400">
                Stop at stage
                <input
                  type="number"
                  className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
                  value={stopStage}
                  onChange={(e) => setStopStage(Number(e.target.value))}
                />
              </label>
              <div className="flex flex-col gap-2 text-xs text-slate-400">
                <span className="font-semibold text-slate-500">Locked safety</span>
                <div className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-slate-300">
                  asset_class: stock · horizon: day_trading · mode: paper_first
                  <br />
                  dry_run: true · require_human_approval: true · allow_submit: false
                </div>
              </div>
              <div className="flex flex-col gap-3 text-xs">
                <label className="flex items-center gap-2 text-slate-300">
                  <input type="checkbox" checked={simPos} onChange={(e) => setSimPos(e.target.checked)} />
                  Simulated position path
                </label>
                <label className="flex items-center gap-2 text-slate-300">
                  <input type="checkbox" checked={simClose} onChange={(e) => setSimClose(e.target.checked)} />
                  Simulated closed trade path
                </label>
              </div>
            </div>
            <button
              type="button"
              disabled={orcBusy}
              onClick={handleRunWorkflow}
              className="mt-4 rounded-lg border border-emerald-400/60 bg-emerald-500/20 px-4 py-2 text-sm font-bold text-emerald-50 hover:bg-emerald-500/25 disabled:opacity-50"
            >
              {orcBusy ? "Running…" : "Run workflow"}
            </button>
          </div>

          {displayRun ? (
            <div className="rounded-2xl border border-white/10 bg-[#0a1018] p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Last / latest orchestrator result</h3>
              <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2 lg:grid-cols-3">
                {[
                  ["orchestrator_run_id", displayRun.orchestrator_run_id],
                  ["workflow_run_id", displayRun.workflow_run_id],
                  ["status", displayRun.status],
                  ["current_stage", String(displayRun.current_stage ?? "—")],
                  ["current_agent_key", String(displayRun.current_agent_key ?? "—")],
                  ["approval_required", String(displayRun.approval_required)],
                  ["approval_id", String(displayRun.approval_id ?? "—")],
                  ["execution_boundary_reached", String(displayRun.execution_boundary_reached)],
                  ["submitted_order", String(displayRun.submitted_order)],
                  ["broker_called", String(displayRun.broker_called)],
                  ["llm_used", String(displayRun.llm_used)],
                ].map(([k, v]) => (
                  <div key={k} className="rounded-lg border border-white/[0.06] bg-black/20 px-3 py-2">
                    <div className="text-[10px] uppercase text-slate-500">{k}</div>
                    <div className="break-all font-mono text-xs text-emerald-100/90">{v}</div>
                  </div>
                ))}
              </dl>
              {(displayRun.blockers?.length ?? 0) > 0 ? (
                <div className="mt-3 text-xs text-red-200">Blockers: {displayRun.blockers.join("; ")}</div>
              ) : null}
              {(displayRun.warnings?.length ?? 0) > 0 ? (
                <div className="mt-3 text-xs text-amber-100/90">Warnings: {displayRun.warnings.join("; ")}</div>
              ) : null}
            </div>
          ) : null}

          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Stage timeline</h3>
              <input
                className="rounded-lg border border-white/10 bg-black/30 px-2 py-1 text-xs text-slate-200"
                placeholder="workflow_run_id override"
                value={activeWfId}
                onChange={(e) => setActiveWfId(e.target.value)}
              />
            </div>
            <div className="mt-3 space-y-2">
              {timeline.length === 0 ? (
                <p className="text-sm text-slate-500">No timeline until you run a workflow.</p>
              ) : (
                timeline.map((row, i) => {
                  const runId = String(row.run_id ?? "");
                  return (
                    <div key={`${runId}-${i}`} className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3 text-sm">
                      <div className="flex flex-wrap gap-2 text-xs text-slate-400">
                        <span className="rounded bg-slate-800/80 px-2 py-0.5">stage {String(row.stage ?? row.stage_number ?? i + 1)}</span>
                        <span className="text-slate-200">{String(row.agent_key ?? "—")}</span>
                        <span className={chip(String(row.status ?? "")) + " rounded px-2 py-0.5"}>{String(row.status ?? "—")}</span>
                        <span className="text-slate-500">{String(row.at ?? row.created_at ?? "")}</span>
                      </div>
                      <div className="mt-2 font-mono text-[11px] text-slate-500">run_id {runId}</div>
                      <button
                        type="button"
                        className="mt-2 rounded border border-white/10 bg-black/30 px-2 py-1 text-[11px] text-emerald-200 hover:border-emerald-400/30"
                        disabled={!runId || agentTraceLoading === runId}
                        onClick={() => loadAgentTrace(runId)}
                      >
                        {agentTraceLoading === runId ? "Loading agent trace…" : "Load agent trace (runtime)"}
                      </button>
                      {agentTraceByRunId[runId] ? (
                        <pre className="mt-2 max-h-48 overflow-auto rounded border border-white/10 bg-black/40 p-2 text-[10px] text-slate-300">
                          {JSON.stringify(agentTraceByRunId[runId]?.trace ?? [], null, 2)}
                        </pre>
                      ) : agentTraceByRunId[runId] === null ? (
                        <p className="mt-2 text-xs text-red-300/90">Could not load agent run.</p>
                      ) : null}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => loadOperatorSnapshot()}
              className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-emerald-400/25"
            >
              Refresh latest
            </button>
            <button
              type="button"
              onClick={handleLoadTrace}
              className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-xs font-semibold text-slate-200 hover:border-emerald-400/25"
            >
              Load audit trace
            </button>
            <button
              type="button"
              onClick={() => doPauseResumeStop("pause")}
              className="rounded-lg border border-amber-400/30 bg-amber-500/10 px-3 py-2 text-xs font-semibold text-amber-100"
            >
              Pause run
            </button>
            <button
              type="button"
              onClick={() => doPauseResumeStop("resume")}
              className="rounded-lg border border-sky-400/30 bg-sky-500/10 px-3 py-2 text-xs font-semibold text-sky-100"
            >
              Resume run
            </button>
            <button
              type="button"
              onClick={() => doPauseResumeStop("stop")}
              className="rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-xs font-semibold text-red-100"
            >
              Stop run
            </button>
          </div>
          {traceErr ? <p className="text-xs text-red-300/90">{traceErr}</p> : null}
          {trace?.audit_events?.length ? (
            <div className="rounded-2xl border border-white/10 bg-[#070c12] p-4">
              <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Workflow audit trace</h3>
              <p className="mt-1 text-xs text-slate-500">
                From <code className="text-slate-400">GET /api/workflow-orchestrator/trace/{`{workflow_run_id}`}</code>. Agent-level tool steps appear under “Load agent trace”.
              </p>
              <ul className="mt-3 space-y-2 text-xs">
                {trace.audit_events.map((ev, i) => (
                  <li key={`${String(ev.audit_id ?? i)}`} className="rounded-lg border border-white/[0.06] bg-black/25 px-3 py-2 text-slate-300">
                    <span className="text-slate-500">{String(ev.created_at)}</span> ·{" "}
                    <span className="font-medium text-slate-200">{String(ev.event_type)}</span> · {String(ev.message)}
                    <div className="mt-1 text-[10px] text-slate-500">actor {String(ev.actor)} · severity {String(ev.severity)}</div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
            <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Recent orchestrator runs</h3>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-white/10 text-[10px] uppercase text-slate-500">
                    <th className="pb-2 pr-2">Orchestrator id</th>
                    <th className="pb-2 pr-2">Workflow id</th>
                    <th className="pb-2 pr-2">Status</th>
                    <th className="pb-2 pr-2">Stage</th>
                    <th className="pb-2">Updated</th>
                  </tr>
                </thead>
                <tbody>
                  {recentRuns.map((r) => (
                    <tr key={r.orchestrator_run_id} className="border-b border-white/[0.04] text-slate-300">
                      <td className="py-2 pr-2 font-mono text-[11px] text-emerald-200/80">{r.orchestrator_run_id}</td>
                      <td className="py-2 pr-2 font-mono text-[11px]">
                        <button
                          type="button"
                          className="text-left text-sky-200/90 hover:underline"
                          onClick={() => {
                            setActiveWfId(r.workflow_run_id);
                            setLastRun(r);
                          }}
                        >
                          {r.workflow_run_id}
                        </button>
                      </td>
                      <td className="py-2 pr-2">{r.status}</td>
                      <td className="py-2 pr-2">{r.current_stage ?? "—"}</td>
                      <td className="py-2">{r.updated_at}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {recentRuns.length === 0 ? <p className="mt-2 text-sm text-slate-500">No runs yet.</p> : null}
            </div>
          </div>
        </div>
      ) : null}

      {mainTab === "catalog" ? (
        <>
          <div className="mt-3 rounded-xl border border-white/10 bg-[#0a1018] px-4 py-3 text-sm text-slate-300">
            Stage catalog is read-only. Operator execution uses the Orchestrator tab. No broker APIs and no execution submit from this page.
          </div>

          <div className="mb-6 mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-8">
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
                  <li>Orchestrator runs are preview/dry-run by policy on this UI</li>
                  <li>No execution submit endpoints from Runbook</li>
                  <li>No broker calls from Runbook</li>
                  <li>No LLM controls</li>
                  <li>Human approval boundary preserved at execution planner</li>
                </ul>
              </div>
            </aside>
          </div>
        </>
      ) : null}
    </div>
  );
}
