"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { checkWorkflowGovernance, getWorkflowGovernanceStatus, type WorkflowGovernanceCheckResult } from "@/lib/api";

export default function WorkflowGovernancePage() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [checkResult, setCheckResult] = useState<WorkflowGovernanceCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [symbols, setSymbols] = useState("AMD");

  async function load() {
    setError(null);
    setLoading(true);
    try {
      setStatus(await getWorkflowGovernanceStatus());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed governance status");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function runCheck() {
    setBusy(true);
    setError(null);
    try {
      const syms = symbols
        .split(/[\s,]+/)
        .map((x) => x.trim().toUpperCase())
        .filter(Boolean);
      const r = await checkWorkflowGovernance({
        asset_class: "stock",
        horizon: "day_trading",
        mode: "paper_first",
        symbols: syms.length ? syms : ["AMD"],
        allow_submit: false,
        dry_run: true,
        require_human_approval: true,
        source: "manual",
      });
      setCheckResult(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Governance check failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading && !status) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
      </div>
    );
  }

  const summary = status?.summary as Record<string, unknown> | undefined;

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Workflow Governance</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            System-wide gates and limits for workflow orchestration. Read-only display plus explicit governance check (no broker calls).
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="rounded-lg border border-emerald-400/50 bg-emerald-400/15 px-3 py-2 text-sm font-semibold text-emerald-100"
        >
          Refresh status
        </button>
      </div>

      {error ? (
        <div className="mb-4 rounded-xl border border-red-500/35 bg-red-500/10 px-4 py-3 text-sm text-red-100/90">{error}</div>
      ) : null}

      <div className="mb-6 rounded-xl border border-white/10 bg-[#070c12] p-4 text-xs text-slate-400">
        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Current governance status</div>
        <pre className="mt-2 max-h-48 overflow-auto text-[11px] text-slate-300">{JSON.stringify(summary ?? status, null, 2)}</pre>
      </div>

      <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
        <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Run governance check</h2>
        <p className="mt-1 text-xs text-slate-500">POST /api/workflow-governance/check — asset_class stock, horizon day_trading, mode paper_first, allow_submit false, dry_run true.</p>
        <div className="mt-4 flex flex-wrap items-end gap-3">
          <label className="text-xs text-slate-400">
            Symbols
            <input
              className="mt-1 block rounded-lg border border-white/10 bg-black/30 px-3 py-2 text-sm text-slate-100"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={busy}
            onClick={runCheck}
            className="rounded-lg border border-emerald-400/50 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-100 disabled:opacity-50"
          >
            {busy ? "Checking…" : "Run governance check"}
          </button>
        </div>

        {checkResult ? (
          <div className="mt-6 space-y-3 text-sm text-slate-300">
            <div className="rounded-lg border border-white/10 bg-black/25 px-3 py-2">
              decision: <span className="font-bold text-emerald-200">{checkResult.decision}</span>
            </div>
            {(checkResult.blockers?.length ?? 0) > 0 ? (
              <div className="rounded-lg border border-red-500/35 bg-red-500/10 px-3 py-2 text-red-100/90">
                blockers: {checkResult.blockers.join("; ")}
              </div>
            ) : null}
            {(checkResult.warnings?.length ?? 0) > 0 ? (
              <div className="rounded-lg border border-amber-400/35 bg-amber-500/10 px-3 py-2 text-amber-100/90">
                warnings: {checkResult.warnings.join("; ")}
              </div>
            ) : null}
            <div>
              <div className="text-xs text-slate-500">gates</div>
              <pre className="mt-1 max-h-40 overflow-auto rounded border border-white/10 bg-black/40 p-2 text-[11px]">
                {JSON.stringify(checkResult.gates, null, 2)}
              </pre>
            </div>
            <div>
              <div className="text-xs text-slate-500">limits</div>
              <pre className="mt-1 max-h-40 overflow-auto rounded border border-white/10 bg-black/40 p-2 text-[11px]">
                {JSON.stringify(checkResult.limits, null, 2)}
              </pre>
            </div>
            {checkResult.next_action ? (
              <div className="text-xs text-slate-400">
                next_action: <span className="text-slate-200">{checkResult.next_action}</span>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      <div className="mt-8">
        <Link href="/workflow-runbook" className="text-sm text-emerald-300 hover:text-emerald-200">
          ← Workflow Runbook
        </Link>
      </div>
    </div>
  );
}
