"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  getWorkflowSchedulerStatus,
  listWorkflowSchedules,
  createWorkflowSchedule,
  enableWorkflowSchedule,
  disableWorkflowSchedule,
  runWorkflowSchedulerOnce,
  type OrchestratorRunRecord,
  type WorkflowScheduleRecord,
} from "@/lib/api";

const DEFAULT_WF_JSON = `{
  "asset_class": "stock",
  "horizon": "day_trading",
  "mode": "paper_first",
  "symbols": ["AMD"],
  "dry_run": true,
  "allow_submit": false,
  "require_human_approval": true,
  "stop_at_stage": 9
}`;

export default function WorkflowSchedulerPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [schedules, setSchedules] = useState<WorkflowScheduleRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState("Paper workflow dry-run");
  const [enabled, setEnabled] = useState(true);
  const [scheduleType, setScheduleType] = useState("interval");
  const [cron, setCron] = useState("");
  const [intervalSec, setIntervalSec] = useState(300);
  const [maxPerDay, setMaxPerDay] = useState(50);
  const [wfJson, setWfJson] = useState(DEFAULT_WF_JSON);
  const [onceJson, setOnceJson] = useState(DEFAULT_WF_JSON);
  const [onceBusy, setOnceBusy] = useState(false);
  const [onceResult, setOnceResult] = useState<OrchestratorRunRecord | null>(null);
  const [createBusy, setCreateBusy] = useState(false);

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const [st, list] = await Promise.all([getWorkflowSchedulerStatus(), listWorkflowSchedules(100)]);
      setStatus(st);
      setSchedules(list.schedules ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load scheduler");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setCreateBusy(true);
    setError(null);
    try {
      let workflow_request: Record<string, unknown> = {};
      try {
        workflow_request = JSON.parse(wfJson) as Record<string, unknown>;
      } catch {
        throw new Error("workflow_request JSON is invalid");
      }
      await createWorkflowSchedule({
        name,
        enabled,
        schedule_type: scheduleType,
        cron_expression: cron.trim() || null,
        interval_seconds: scheduleType === "cron" ? null : intervalSec,
        max_runs_per_day: maxPerDay,
        workflow_request,
      });
      setWfJson(DEFAULT_WF_JSON);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setCreateBusy(false);
    }
  }

  async function runOnce() {
    setOnceBusy(true);
    setOnceResult(null);
    setError(null);
    try {
      let workflow_request: Record<string, unknown> = {};
      try {
        workflow_request = JSON.parse(onceJson) as Record<string, unknown>;
      } catch {
        throw new Error("run-once workflow_request JSON is invalid");
      }
      const r = await runWorkflowSchedulerOnce({ workflow_request });
      setOnceResult(r.run);
    } catch (err) {
      setError(err instanceof Error ? err.message : "run-once failed");
    } finally {
      setOnceBusy(false);
    }
  }

  async function flip(sch: WorkflowScheduleRecord, on: boolean) {
    setError(null);
    try {
      if (on) await enableWorkflowSchedule(sch.schedule_id);
      else await disableWorkflowSchedule(sch.schedule_id);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Toggle failed");
    }
  }

  if (loading && !schedules.length) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Workflow Scheduler</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Schedules always invoke the orchestrator with dry-run safety. No order submission from scheduler endpoints.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100"
        >
          Refresh
        </button>
      </div>

      <div className="mb-6 rounded-xl border border-amber-400/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-100/90">
        <ul className="list-inside list-disc space-y-1">
          <li>Scheduler never submits orders.</li>
          <li>Scheduler calls orchestrator with dry_run=true and allow_submit=false (enforced server-side on run-once).</li>
          <li>Emergency stop and master gates still apply upstream.</li>
          <li>Human approval remains required at execution boundary.</li>
        </ul>
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
      ) : null}

      <div className="mb-6 rounded-xl border border-white/10 bg-[#070c12] px-4 py-3 text-xs text-slate-400">
        Scheduler status: {String(status?.status ?? "—")} · {JSON.stringify(status?.summary ?? {})}
      </div>

      <div className="mb-10 grid gap-6 lg:grid-cols-2">
        <form onSubmit={handleCreate} className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Create schedule</h2>
          <div className="mt-4 grid gap-3 text-sm">
            <label className="text-xs text-slate-400">
              Name
              <input className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-slate-100" value={name} onChange={(e) => setName(e.target.value)} required />
            </label>
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
              Enabled
            </label>
            <label className="text-xs text-slate-400">
              schedule_type
              <select
                className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-slate-100"
                value={scheduleType}
                onChange={(e) => setScheduleType(e.target.value)}
              >
                <option value="interval">interval</option>
                <option value="cron">cron</option>
              </select>
            </label>
            <label className="text-xs text-slate-400">
              cron_expression (optional)
              <input className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-xs text-slate-100" value={cron} onChange={(e) => setCron(e.target.value)} />
            </label>
            <label className="text-xs text-slate-400">
              interval_seconds
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-slate-100"
                value={intervalSec}
                onChange={(e) => setIntervalSec(Number(e.target.value))}
              />
            </label>
            <label className="text-xs text-slate-400">
              max_runs_per_day
              <input
                type="number"
                className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-slate-100"
                value={maxPerDay}
                onChange={(e) => setMaxPerDay(Number(e.target.value))}
              />
            </label>
            <label className="text-xs text-slate-400">
              workflow_request (JSON)
              <textarea
                className="mt-1 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-[11px] text-slate-100"
                rows={12}
                value={wfJson}
                onChange={(e) => setWfJson(e.target.value)}
              />
            </label>
          </div>
          <button
            type="submit"
            disabled={createBusy}
            className="mt-4 rounded-lg border border-emerald-400/50 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-100 disabled:opacity-50"
          >
            {createBusy ? "Creating…" : "Create schedule"}
          </button>
        </form>

        <div className="rounded-2xl border border-white/10 bg-[#0a1018] p-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Run once</h2>
          <p className="mt-1 text-xs text-slate-500">POST /api/workflow-scheduler/run-once — shows orchestrator run payload.</p>
          <textarea
            className="mt-3 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-[11px] text-slate-100"
            rows={12}
            value={onceJson}
            onChange={(e) => setOnceJson(e.target.value)}
          />
          <button
            type="button"
            disabled={onceBusy}
            onClick={runOnce}
            className="mt-3 rounded-lg border border-sky-400/45 bg-sky-500/10 px-4 py-2 text-sm font-semibold text-sky-100 disabled:opacity-50"
          >
            {onceBusy ? "Running…" : "Run once (orchestrator preview)"}
          </button>
          {onceResult ? (
            <pre className="mt-4 max-h-96 overflow-auto rounded border border-white/10 bg-black/40 p-3 text-[11px] text-slate-300">{JSON.stringify(onceResult, null, 2)}</pre>
          ) : null}
        </div>
      </div>

      <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Schedules</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[900px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 text-[10px] uppercase text-slate-500">
                <th className="pb-2 pr-2">id</th>
                <th className="pb-2 pr-2">name</th>
                <th className="pb-2 pr-2">type</th>
                <th className="pb-2 pr-2">enabled</th>
                <th className="pb-2 pr-2">interval / cron</th>
                <th className="pb-2 pr-2">max/day</th>
                <th className="pb-2">actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.schedule_id} className="border-b border-white/[0.04] text-slate-300">
                  <td className="py-2 pr-2 font-mono text-[10px] text-emerald-200/80">{s.schedule_id}</td>
                  <td className="py-2 pr-2">{s.name}</td>
                  <td className="py-2 pr-2">{s.schedule_type}</td>
                  <td className="py-2 pr-2">{s.enabled ? "yes" : "no"}</td>
                  <td className="py-2 pr-2 font-mono text-[10px]">
                    {s.cron_expression ?? "—"} / {s.interval_seconds ?? "—"}
                  </td>
                  <td className="py-2 pr-2">{s.max_runs_per_day}</td>
                  <td className="py-2">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        className="rounded border border-emerald-400/35 px-2 py-1 text-[10px] text-emerald-100"
                        onClick={() => flip(s, true)}
                      >
                        Enable
                      </button>
                      <button
                        type="button"
                        className="rounded border border-slate-500/40 px-2 py-1 text-[10px] text-slate-300"
                        onClick={() => flip(s, false)}
                      >
                        Disable
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {schedules.length === 0 ? <p className="mt-2 text-sm text-slate-500">No schedules yet.</p> : null}
      </div>

      <div className="mt-8">
        <Link href="/workflow-runbook" className="text-sm text-emerald-300 hover:text-emerald-200">
          ← Workflow Runbook
        </Link>
      </div>
    </div>
  );
}
