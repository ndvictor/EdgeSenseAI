"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getAgentRuntimeAgents,
  getAgentRuntimeLatest,
  getAgentRuntimeStatus,
  createAgentRun,
  type AgentRuntimeAgentDescriptor,
  type AgentRunResultRecord,
} from "@/lib/api";

export default function AgentRuntimePage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [latest, setLatest] = useState<Record<string, unknown> | null>(null);
  const [agents, setAgents] = useState<AgentRuntimeAgentDescriptor[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [agentKey, setAgentKey] = useState("session_router_agent");
  const [manualBusy, setManualBusy] = useState(false);
  const [manualResult, setManualResult] = useState<AgentRunResultRecord | null>(null);

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const [st, lat, ag] = await Promise.all([getAgentRuntimeStatus(), getAgentRuntimeLatest(), getAgentRuntimeAgents()]);
      setStatus(st);
      setLatest(lat);
      setAgents(ag.agents ?? []);
      if (ag.agents?.length && !ag.agents.some((a) => a.agent_key === agentKey)) {
        setAgentKey(ag.agents[0].agent_key);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agent runtime");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const summary = status?.summary as Record<string, unknown> | undefined;
  const safety = status?.safety as Record<string, unknown> | undefined;

  const defaultSample = useMemo(
    () => ({
      agent_key: "session_router_agent",
      inputs: { timestamp: "2026-05-07T09:35:00-05:00" },
      context: { source: "ui_agent_runtime" },
      dry_run: true,
      requested_stage: 3,
      idempotency_key: `ui_ar_${Date.now()}`,
    }),
    [],
  );

  async function runManual() {
    setManualBusy(true);
    setManualResult(null);
    try {
      const body = {
        ...defaultSample,
        agent_key: agentKey,
        idempotency_key: `ui_ar_${agentKey}_${Date.now()}`,
      };
      const r = await createAgentRun(body);
      setManualResult(r.agent_run);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Agent run failed");
    } finally {
      setManualBusy(false);
    }
  }

  if (loading && !status) {
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
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Agent Runtime</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Deterministic agent registry and dry-run execution. No LLM routing here — agents call internal tools only.
          </p>
          <div className="mt-3 flex flex-wrap gap-2 text-[10px] font-bold uppercase text-emerald-200/90">
            {["US Stocks", "Day trading", "Paper-first", "No broker submit"].map((x) => (
              <span key={x} className="rounded-full border border-emerald-400/35 bg-emerald-500/10 px-3 py-1">
                {x}
              </span>
            ))}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={load}
            className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100"
          >
            Refresh
          </button>
          <Link href="/workflow-runbook" className="rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-sm text-slate-200">
            Runbook →
          </Link>
        </div>
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
      ) : null}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["persistence_mode", String(latest?.persistence_mode ?? summary?.persistence_mode ?? "—")],
          ["redis_mode", String(latest?.redis_mode ?? summary?.redis_mode ?? "—")],
          ["registered_agents_count", String(latest?.registered_agents_count ?? agents.length)],
          ["workflow_runs (latest keys)", latest?.latest_workflow_run ? "has_run" : "none"],
          ["status", String(status?.status ?? "—")],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl border border-emerald-400/15 bg-[#0a1018]/90 px-4 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{k}</div>
            <div className="mt-1 text-lg font-semibold text-slate-50">{v}</div>
          </div>
        ))}
      </div>

      {safety ? (
        <div className="mb-6 rounded-xl border border-white/10 bg-[#070c12] p-4">
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Safety flags</h2>
          <pre className="mt-2 max-h-40 overflow-auto text-xs text-slate-400">{JSON.stringify(safety, null, 2)}</pre>
        </div>
      ) : null}

      <div className="mb-6 rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Agents</h2>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[1100px] border-collapse text-left text-xs">
            <thead>
              <tr className="border-b border-white/10 text-[10px] uppercase text-slate-500">
                <th className="pb-2 pr-2">agent_key</th>
                <th className="pb-2 pr-2">display-name</th>
                <th className="pb-2 pr-2">stage</th>
                <th className="pb-2 pr-2">role</th>
                <th className="pb-2 pr-2">type</th>
                <th className="pb-2 pr-2">status</th>
                <th className="pb-2 pr-2">uses_llm</th>
                <th className="pb-2 pr-2">allowed_tools</th>
                <th className="pb-2 pr-2">forbidden</th>
                <th className="pb-2">safety_notes</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr key={a.agent_key} className="border-b border-white/[0.04] align-top text-slate-300">
                  <td className="py-2 pr-2 font-mono text-emerald-200/90">{a.agent_key}</td>
                  <td className="py-2 pr-2">{a.display_name}</td>
                  <td className="py-2 pr-2">{a.stage_number ?? "—"}</td>
                  <td className="py-2 pr-2">{a.role}</td>
                  <td className="py-2 pr-2">{a.agent_type}</td>
                  <td className="py-2 pr-2">{a.status}</td>
                  <td className="py-2 pr-2">{a.uses_llm ? "yes" : "no"}</td>
                  <td className="py-2 pr-2 font-mono text-[10px] text-slate-400">{(a.allowed_tools ?? []).join(", ") || "—"}</td>
                  <td className="py-2 pr-2 font-mono text-[10px] text-slate-400">{(a.forbidden_actions ?? []).join(", ") || "—"}</td>
                  <td className="py-2 text-[11px] text-slate-500">{(a.safety_notes ?? []).slice(0, 2).join("; ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-2xl border border-white/10 bg-[#0a1018] p-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Manual dry-run agent run</h2>
        <p className="mt-1 text-xs text-slate-500">
          Posts to <code className="text-emerald-200/80">/api/agent-runtime/agent-runs</code> with safe defaults. Idempotency key is unique per click.
        </p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-400">
            Agent
            <select
              className="mt-1 block rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
              value={agentKey}
              onChange={(e) => setAgentKey(e.target.value)}
            >
              {agents.map((a) => (
                <option key={a.agent_key} value={a.agent_key}>
                  {a.agent_key}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={manualBusy}
            onClick={runManual}
            className="rounded-lg border border-emerald-400/50 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-100 disabled:opacity-50"
          >
            {manualBusy ? "Running…" : "Run sample agent-runs"}
          </button>
        </div>
        {manualResult ? (
          <div className="mt-4 space-y-2 rounded-xl border border-white/[0.06] bg-black/25 p-3 text-sm text-slate-300">
            <div>
              <span className="text-slate-500">run_id</span>{" "}
              <span className="font-mono text-xs text-emerald-200/90">{manualResult.run_id}</span>
            </div>
            <div>
              <span className="text-slate-500">workflow_run_id</span>{" "}
              <span className="font-mono text-xs">{manualResult.workflow_run_id}</span>
            </div>
            <div>
              <span className="text-slate-500">status</span> {manualResult.status}
            </div>
            <div>
              <span className="text-slate-500">next_action</span> {manualResult.next_action}
            </div>
            <div>
              <span className="text-slate-500">next_agent</span> {manualResult.next_agent ?? "—"}
            </div>
            {(manualResult.blockers?.length ?? 0) > 0 ? <div className="text-red-200/90">blockers: {manualResult.blockers.join("; ")}</div> : null}
            {(manualResult.warnings?.length ?? 0) > 0 ? <div className="text-amber-100/90">warnings: {manualResult.warnings.join("; ")}</div> : null}
            <div>
              <span className="text-slate-500">decision</span>
              <pre className="mt-1 max-h-40 overflow-auto rounded border border-white/10 bg-black/40 p-2 text-[11px]">
                {JSON.stringify(manualResult.decision, null, 2)}
              </pre>
            </div>
            <div>
              <span className="text-slate-500">trace</span>
              <pre className="mt-1 max-h-64 overflow-auto rounded border border-white/10 bg-black/40 p-2 text-[11px]">
                {JSON.stringify(manualResult.trace, null, 2)}
              </pre>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
