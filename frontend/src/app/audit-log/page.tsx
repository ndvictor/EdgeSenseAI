"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { getAuditLogStatus, listAuditLogEvents, type AuditLogEventRecord } from "@/lib/api";

export default function AuditLogPage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [events, setEvents] = useState<AuditLogEventRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [fltType, setFltType] = useState("");
  const [fltSev, setFltSev] = useState("");
  const [fltWf, setFltWf] = useState("");

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const [st, ev] = await Promise.all([getAuditLogStatus(), listAuditLogEvents(200)]);
      setStatus(st);
      setEvents(ev.events ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load audit log");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      if (fltType && !e.event_type.toLowerCase().includes(fltType.toLowerCase())) return false;
      if (fltSev && e.severity.toLowerCase() !== fltSev.toLowerCase()) return false;
      if (fltWf && !(e.workflow_run_id ?? "").toLowerCase().includes(fltWf.toLowerCase())) return false;
      return true;
    });
  }, [events, fltType, fltSev, fltWf]);

  if (loading && !events.length) {
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
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Audit Log</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">Immutable workflow audit trail for orchestrator, scheduler, and governance events (read-only UI).</p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100"
        >
          Refresh
        </button>
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
      ) : null}

      <div className="mb-6 rounded-xl border border-emerald-400/15 bg-[#0a1018]/90 px-4 py-3 text-xs text-slate-400">
        Service status: <span className="text-slate-200">{String(status?.status ?? "—")}</span> ·{" "}
        {JSON.stringify(status?.summary ?? {})}
      </div>

      <div className="mb-4 flex flex-wrap gap-3">
        <input
          className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
          placeholder="Filter event_type"
          value={fltType}
          onChange={(e) => setFltType(e.target.value)}
        />
        <input
          className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
          placeholder="Filter severity (exact)"
          value={fltSev}
          onChange={(e) => setFltSev(e.target.value)}
        />
        <input
          className="rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
          placeholder="Filter workflow_run_id contains"
          value={fltWf}
          onChange={(e) => setFltWf(e.target.value)}
        />
        <span className="self-center text-xs text-slate-500">
          Showing {filtered.length} / {events.length}
        </span>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-emerald-400/10 bg-[#070c12]/95">
        <table className="w-full min-w-[960px] border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-white/10 text-[10px] uppercase text-slate-500">
              <th className="px-3 py-2">audit_id</th>
              <th className="px-3 py-2">workflow_run_id</th>
              <th className="px-3 py-2">orchestrator</th>
              <th className="px-3 py-2">agent_run</th>
              <th className="px-3 py-2">event_type</th>
              <th className="px-3 py-2">actor</th>
              <th className="px-3 py-2">severity</th>
              <th className="px-3 py-2">message</th>
              <th className="px-3 py-2">created_at</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
              <tr key={e.audit_id} className="border-b border-white/[0.04] align-top text-slate-300">
                <td className="px-3 py-2 font-mono text-[10px] text-emerald-200/80">{e.audit_id}</td>
                <td className="px-3 py-2 font-mono text-[10px]">{e.workflow_run_id ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-[10px]">{e.orchestrator_run_id ?? "—"}</td>
                <td className="px-3 py-2 font-mono text-[10px]">{e.agent_run_id ?? "—"}</td>
                <td className="px-3 py-2">{e.event_type}</td>
                <td className="px-3 py-2">{e.actor}</td>
                <td className="px-3 py-2">{e.severity}</td>
                <td className="px-3 py-2 max-w-[280px]">{e.message}</td>
                <td className="px-3 py-2 whitespace-nowrap text-slate-500">{e.created_at}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-8">
        <Link href="/workflow-runbook" className="text-sm text-emerald-300 hover:text-emerald-200">
          ← Workflow Runbook
        </Link>
      </div>
    </div>
  );
}
