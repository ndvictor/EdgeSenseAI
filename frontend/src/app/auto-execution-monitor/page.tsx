"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { api, type ExecutionOrderDetailResponse, type ExecutionOrderListItem, type ExecutionSummaryResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

type TradeNowConfig = {
  autonomous_status?: string;
  autonomous_execution_enabled_env?: boolean;
  automatic_execution_user_enabled?: boolean;
  autonomous_blockers?: string[];
  blockers?: string[];
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

function apiUrl(path: string): string {
  if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured. Set it in frontend/.env.local.");
  }
  return `${API_BASE_URL}${path}`;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

function StatusPill({ value }: { value: string }) {
  const v = value.toLowerCase();
  const ok = ["paper", "connected", "ready", "submitted", "filled", "partially_filled"].some((t) => v.includes(t));
  const warn = ["pending", "blocked", "rejected", "canceled", "error", "not_configured", "missing_backend_endpoint"].some((t) => v.includes(t));
  return (
    <span
      className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase ${
        ok
          ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-200"
          : warn
            ? "border-amber-500/40 bg-amber-500/10 text-amber-200"
            : "border-slate-700 bg-slate-900 text-slate-300"
      }`}
    >
      {value.replaceAll("_", " ")}
    </span>
  );
}

function errLabel(err: unknown, path: string): string {
  const msg = err instanceof Error ? err.message : String(err);
  if (msg.includes("404")) return `missing_backend_endpoint ${path}`;
  if (msg.toLowerCase().includes("failed to fetch")) return `not_configured ${path}`;
  return msg;
}

export default function AutoExecutionMonitorPage() {
  const [summary, setSummary] = useState<ExecutionSummaryResponse | null>(null);
  const [orders, setOrders] = useState<ExecutionOrderListItem[]>([]);
  const [selectedAuditId, setSelectedAuditId] = useState<string>("");
  const [selectedDetail, setSelectedDetail] = useState<ExecutionOrderDetailResponse | null>(null);
  const [tradenow, setTradenow] = useState<TradeNowConfig | null>(null);

  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [onlyPending, setOnlyPending] = useState(true);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const refresh = useCallback(async () => {
    setError(null);
    try {
      const [s, o] = await Promise.all([api.getExecutionSummary(), api.getExecutionOrders(80)]);
      setSummary(s);
      setOrders(o.orders);
    } catch (e) {
      setSummary(null);
      setOrders([]);
      setError(errLabel(e, "/api/execution/summary or /api/execution/orders"));
    }

    try {
      setTradenow(await apiFetch<TradeNowConfig>("/api/tradenow/config"));
    } catch (e) {
      setTradenow((prev) => prev ?? { autonomous_status: errLabel(e, "/api/tradenow/config") });
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) return;
    const t = setInterval(() => refresh(), 10_000);
    return () => clearInterval(t);
  }, [autoRefresh, refresh]);

  const pending = useMemo(() => orders.filter((o) => o.final_status === "pending_approval"), [orders]);
  const visibleOrders = useMemo(() => (onlyPending ? pending : orders), [onlyPending, pending, orders]);

  useEffect(() => {
    if (!selectedAuditId) {
      setSelectedDetail(null);
      setDetailError(null);
      return;
    }
    setDetailError(null);
    api
      .getExecutionOrder(selectedAuditId)
      .then(setSelectedDetail)
      .catch((e) => {
        setSelectedDetail(null);
        setDetailError(errLabel(e, `/api/execution/orders/${selectedAuditId}`));
      });
  }, [selectedAuditId]);

  const approve = async (auditId: string) => {
    setBusy(auditId);
    setError(null);
    try {
      await api.postExecutionApprove({ audit_id: auditId, org_slug: "default" });
      await refresh();
      setSelectedAuditId(auditId);
    } catch (e) {
      setError(errLabel(e, "/api/execution/approve"));
    } finally {
      setBusy(null);
    }
  };

  const reject = async (auditId: string) => {
    setBusy(auditId);
    setError(null);
    try {
      await api.postExecutionReject({ audit_id: auditId, org_slug: "default", reason: "rejected_in_monitor" });
      await refresh();
      if (selectedAuditId === auditId) setSelectedAuditId("");
    } catch (e) {
      setError(errLabel(e, "/api/execution/reject"));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-4">
        <PageHeader
          eyebrow="paper-first monitoring"
          title="Auto-Execution Monitor"
          description="Operational visibility for automated execution gates. Paper is default. Live trading is blocked unless explicitly enabled in backend env and approved by prechecks."
        />

        {error ? <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div> : null}

        <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-emerald-500">Execution mode & gates</h2>
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => refresh()}
                className="rounded-lg border border-slate-600 bg-slate-900 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:bg-slate-800"
              >
                Refresh
              </button>
              <label className="flex items-center gap-2 text-xs text-slate-300">
                <input type="checkbox" checked={autoRefresh} onChange={(e) => setAutoRefresh(e.target.checked)} />
                Auto-refresh (10s)
              </label>
            </div>
          </div>

          <div className="mb-3 flex flex-wrap gap-2">
            <StatusPill value={summary?.edgesense.execution_mode ?? "not_configured"} />
            <StatusPill value={summary?.edgesense.live_trading_enabled ? "live_enabled_env_true" : "live_enabled_env_false"} />
            <StatusPill value={summary?.edgesense.require_human_approval ? "human_approval_required" : "human_approval_not_required"} />
            <StatusPill value={tradenow?.autonomous_status ?? "autonomous_status_unknown"} />
          </div>

          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 lg:grid-cols-6">
            <MetricCard label="Daily loss used" value={summary ? `${summary.risk_state.daily_loss_pct_used.toFixed(2)}%` : "—"} accent />
            <MetricCard label="Daily loss cap" value={summary ? `${summary.edgesense.max_daily_loss_pct}%` : "—"} />
            <MetricCard label="Max trade risk" value={summary ? `${summary.edgesense.max_trade_risk_pct}%` : "—"} />
            <MetricCard label="Open positions cap" value={summary ? String(summary.edgesense.max_open_positions) : "—"} />
            <MetricCard label="Max symbol exposure" value={summary ? `${summary.edgesense.max_symbol_exposure_pct}%` : "—"} />
            <MetricCard label="Risk lockout" value={summary ? (summary.risk_state.risk_lockout_active ? "active" : "clear") : "—"} />
          </div>

          <p className="mt-3 text-xs text-slate-500">
            Audits and risk usage are currently <span className="font-semibold text-slate-400">process-memory</span>. For durable monitoring, wire audits to storage later.
            For manual execution tests, use{" "}
            <Link className="text-emerald-400 underline hover:text-emerald-300" href="/tradenow">
              TradeNow
            </Link>
            .
          </p>
        </section>

        <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
            <h2 className="text-lg font-semibold text-emerald-500">Approval queue & recent executions</h2>
            <label className="flex items-center gap-2 text-xs text-slate-300">
              <input type="checkbox" checked={onlyPending} onChange={(e) => setOnlyPending(e.target.checked)} />
              Show pending approvals only
            </label>
          </div>

          <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <div className="overflow-x-auto rounded-lg border border-slate-800">
                <table className="w-full min-w-[860px] text-left text-sm">
                  <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      <th className="px-3 py-2">Audit</th>
                      <th className="px-3 py-2">Symbol</th>
                      <th className="px-3 py-2">Status</th>
                      <th className="px-3 py-2">When</th>
                      <th className="px-3 py-2">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {visibleOrders.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-3 py-6 text-center text-sm text-slate-500">
                          No matching audits yet.
                        </td>
                      </tr>
                    ) : (
                      visibleOrders.map((o) => (
                        <tr key={o.audit_id} className={selectedAuditId === o.audit_id ? "bg-white/[0.03]" : ""}>
                          <td className="px-3 py-2 font-mono text-xs text-emerald-300">
                            <button type="button" onClick={() => setSelectedAuditId(o.audit_id)} className="underline hover:text-emerald-200">
                              {o.audit_id}
                            </button>
                          </td>
                          <td className="px-3 py-2 font-semibold text-white">{String(o.request_summary?.symbol ?? "—")}</td>
                          <td className="px-3 py-2">
                            <StatusPill value={o.final_status} />
                            {o.blockers?.length ? <p className="mt-1 text-xs text-amber-200">{o.blockers.slice(0, 2).join("; ")}</p> : null}
                          </td>
                          <td className="px-3 py-2 text-xs text-slate-400">{new Date(o.created_at).toLocaleString()}</td>
                          <td className="px-3 py-2">
                            {o.final_status === "pending_approval" ? (
                              <div className="flex flex-wrap gap-2">
                                <button
                                  type="button"
                                  disabled={busy === o.audit_id}
                                  onClick={() => approve(o.audit_id)}
                                  className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2 py-1 text-xs font-semibold text-emerald-200 hover:bg-emerald-500/20 disabled:opacity-50"
                                >
                                  Approve (paper)
                                </button>
                                <button
                                  type="button"
                                  disabled={busy === o.audit_id}
                                  onClick={() => reject(o.audit_id)}
                                  className="rounded border border-rose-500/40 bg-rose-500/10 px-2 py-1 text-xs font-semibold text-rose-200 hover:bg-rose-500/20 disabled:opacity-50"
                                >
                                  Reject
                                </button>
                              </div>
                            ) : (
                              <span className="text-xs text-slate-600">—</span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Audit detail</h3>
              {detailError ? <p className="text-xs text-amber-200">{detailError}</p> : null}
              {!selectedAuditId ? (
                <p className="text-sm text-slate-400">Select an audit id to inspect precheck steps and blockers.</p>
              ) : selectedDetail ? (
                <div className="space-y-2 text-xs text-slate-300">
                  <p className="font-mono text-emerald-300">{selectedAuditId}</p>
                  {"final_status" in selectedDetail ? (
                    <p>
                      Status: <span className="font-semibold text-slate-100">{String(selectedDetail.final_status)}</span>
                    </p>
                  ) : null}
                  {"blockers" in selectedDetail && Array.isArray(selectedDetail.blockers) && selectedDetail.blockers.length ? (
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-slate-500">Blockers</p>
                      <ul className="mt-1 space-y-1 text-amber-200/90">
                        {selectedDetail.blockers.slice(0, 8).map((b) => (
                          <li key={b}>{b}</li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                  {"precheck" in selectedDetail && selectedDetail.precheck?.steps?.length ? (
                    <div>
                      <p className="text-[10px] font-semibold uppercase text-slate-500">Precheck steps</p>
                      <ul className="mt-1 space-y-1 text-slate-400">
                        {selectedDetail.precheck.steps.map((s) => (
                          <li key={s.name}>
                            {s.passed ? "✓" : "✗"} {s.name}
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null}
                </div>
              ) : (
                <p className="text-sm text-slate-500">Loading…</p>
              )}
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}

