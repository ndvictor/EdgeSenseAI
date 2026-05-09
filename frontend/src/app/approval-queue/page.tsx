"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  getApprovalQueueStatus,
  listApprovalQueueItems,
  approveApprovalQueueItem,
  rejectApprovalQueueItem,
  cancelApprovalQueueItem,
  type ApprovalQueueItemRecord,
} from "@/lib/api";

export default function ApprovalQueuePage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [items, setItems] = useState<ApprovalQueueItemRecord[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reason, setReason] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const [st, li] = await Promise.all([getApprovalQueueStatus(), listApprovalQueueItems(100)]);
      setStatus(st);
      setItems(li.items ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load approval queue");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const summary = status?.summary as Record<string, unknown> | undefined;
  const counts = useMemo(() => {
    const by: Record<string, number> = {};
    for (const it of items) {
      by[it.status] = (by[it.status] ?? 0) + 1;
    }
    return by;
  }, [items]);

  async function act(id: string, kind: "approve" | "reject" | "cancel") {
    setBusyId(id);
    setError(null);
    try {
      const body = { actor: "ui_operator", reason: reason.trim() || null };
      if (kind === "approve") await approveApprovalQueueItem(id, body);
      if (kind === "reject") await rejectApprovalQueueItem(id, body);
      if (kind === "cancel") await cancelApprovalQueueItem(id, body);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Action failed");
    } finally {
      setBusyId(null);
    }
  }

  if (loading && !items.length) {
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
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Approval Queue</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Human gate at workflow boundaries. Approvals do not submit broker orders — they only unlock the next gated workflow step.
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

      <div className="mb-4 rounded-xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100/90">
        Approval does not submit a broker order. It only unlocks the next gated workflow step. No execution submit is called from this page.
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
      ) : null}

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="rounded-xl border border-emerald-400/15 bg-[#0a1018]/90 px-4 py-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Pending</div>
          <div className="mt-1 text-2xl font-semibold text-slate-50">{String(summary?.pending_count ?? counts.pending ?? "—")}</div>
        </div>
        <div className="rounded-xl border border-emerald-400/15 bg-[#0a1018]/90 px-4 py-3">
          <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Total items (local)</div>
          <div className="mt-1 text-2xl font-semibold text-slate-50">{items.length}</div>
        </div>
        {["approved", "rejected", "cancelled"].map((s) => (
          <div key={s} className="rounded-xl border border-white/10 bg-[#0a1018]/90 px-4 py-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{s}</div>
            <div className="mt-1 text-2xl font-semibold text-slate-50">{counts[s] ?? 0}</div>
          </div>
        ))}
      </div>

      <div className="mb-4 rounded-xl border border-white/10 bg-[#070c12] p-4">
        <label className="text-xs text-slate-400">
          Optional reason / note for approve, reject, or cancel
          <input
            className="mt-1 w-full max-w-xl rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </label>
      </div>

      <div className="space-y-4">
        {items.map((it) => (
          <div key={it.approval_id} className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <div className="font-mono text-sm text-emerald-200/90">{it.approval_id}</div>
                <div className="mt-1 text-xs text-slate-500">
                  workflow <span className="font-mono text-slate-300">{it.workflow_run_id}</span>
                </div>
                {it.orchestrator_run_id ? (
                  <div className="text-xs text-slate-500">
                    orchestrator <span className="font-mono text-slate-300">{it.orchestrator_run_id}</span>
                  </div>
                ) : null}
              </div>
              <span className="rounded-full border border-white/10 bg-black/30 px-3 py-1 text-[11px] font-bold uppercase text-slate-200">
                {it.status}
              </span>
            </div>
            <div className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
              <div>
                type: <span className="text-slate-200">{it.approval_type}</span>
              </div>
              <div>
                required approver: <span className="text-slate-200">{it.required_approver ?? "—"}</span>
              </div>
              <div>
                expires: <span className="text-slate-200">{it.expires_at ?? "—"}</span>
              </div>
              <div>
                created: <span className="text-slate-200">{it.created_at}</span>
              </div>
            </div>
            <div className="mt-3 rounded-lg border border-white/[0.06] bg-black/25 p-2 text-xs">
              <div className="text-slate-500">requested_action</div>
              <pre className="mt-1 overflow-auto text-[11px] text-slate-300">{JSON.stringify(it.requested_action, null, 2)}</pre>
            </div>
            <div className="mt-2 rounded-lg border border-white/[0.06] bg-black/25 p-2 text-xs">
              <div className="text-slate-500">risk_summary</div>
              <pre className="mt-1 overflow-auto text-[11px] text-slate-300">{JSON.stringify(it.risk_summary, null, 2)}</pre>
            </div>
            {it.status === "pending" ? (
              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busyId === it.approval_id}
                  onClick={() => act(it.approval_id, "approve")}
                  className="rounded-lg border border-emerald-400/50 bg-emerald-500/15 px-3 py-2 text-xs font-bold text-emerald-100"
                >
                  Approve gated workflow handoff
                </button>
                <button
                  type="button"
                  disabled={busyId === it.approval_id}
                  onClick={() => act(it.approval_id, "reject")}
                  className="rounded-lg border border-red-400/45 bg-red-500/10 px-3 py-2 text-xs font-bold text-red-100"
                >
                  Reject handoff
                </button>
                <button
                  type="button"
                  disabled={busyId === it.approval_id}
                  onClick={() => act(it.approval_id, "cancel")}
                  className="rounded-lg border border-slate-500/40 bg-slate-800/50 px-3 py-2 text-xs font-bold text-slate-200"
                >
                  Cancel request
                </button>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-500">No actions — item is {it.status}.</p>
            )}
          </div>
        ))}
        {items.length === 0 ? <p className="text-sm text-slate-500">No approval items.</p> : null}
      </div>

      <div className="mt-8">
        <Link href="/workflow-runbook" className="text-sm text-emerald-300 hover:text-emerald-200">
          ← Workflow Runbook
        </Link>
      </div>
    </div>
  );
}
