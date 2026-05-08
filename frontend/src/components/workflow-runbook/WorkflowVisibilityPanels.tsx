"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";
import {
  api,
  type MarketDataSnapshot,
  type ModelRegistryResponse,
  type OrchestratorRunRecord,
  type RankedStrategy,
  type StrategyRankingResponse,
  type WorkflowRunbookLatestSnapshot,
} from "@/lib/api";

function asRecord(v: unknown): Record<string, unknown> | null {
  return v && typeof v === "object" && !Array.isArray(v) ? (v as Record<string, unknown>) : null;
}

function pickSymbolFromPlan(plan: Record<string, unknown> | null): string | null {
  if (!plan) return null;
  for (const k of ["symbol", "ticker", "underlying", "asset_symbol"]) {
    const v = plan[k];
    if (typeof v === "string" && v.trim()) return v.trim().toUpperCase();
  }
  for (const nest of ["plan", "entry", "signal", "trade_plan", "execution_plan"]) {
    const inner = asRecord(plan[nest]);
    if (inner) {
      for (const k of ["symbol", "ticker"]) {
        const v = inner[k];
        if (typeof v === "string" && v.trim()) return v.trim().toUpperCase();
      }
    }
  }
  return null;
}

function pickSymbolFromOrchestrator(run: OrchestratorRunRecord | null): string | null {
  if (!run) return null;
  const r = run as Record<string, unknown>;
  const syms = r.symbols;
  if (Array.isArray(syms) && syms.length && typeof syms[0] === "string") return String(syms[0]).toUpperCase();
  const meta = asRecord(r.metadata);
  const ctx = asRecord(meta?.context ?? meta?.input);
  if (ctx) {
    const s = pickSymbolFromPlan(ctx);
    if (s) return s;
  }
  return null;
}

function isStrategyRankingPayload(
  x: StrategyRankingResponse | { message: string; status: string },
): x is StrategyRankingResponse {
  return "ranked_strategies" in x && Array.isArray((x as StrategyRankingResponse).ranked_strategies);
}

function JsonPeek({ label, data, max = 2800 }: { label: string; data: unknown; max?: number }) {
  const raw = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2);
    } catch {
      return String(data);
    }
  }, [data]);
  const truncated = raw.length > max ? `${raw.slice(0, max)}\n…` : raw;
  return (
    <details className="mt-2 rounded-lg border border-white/[0.06] bg-black/25">
      <summary className="cursor-pointer px-2 py-1.5 text-[11px] text-slate-400">{label}</summary>
      <pre className="max-h-56 overflow-auto border-t border-white/[0.06] p-2 text-[10px] text-slate-400">{truncated}</pre>
    </details>
  );
}

export function WorkflowVisibilityPanels({
  latestBlob,
  orchestratorRun,
  refreshKey,
}: {
  latestBlob: WorkflowRunbookLatestSnapshot | null;
  orchestratorRun: OrchestratorRunRecord | null;
  refreshKey: number;
}) {
  const [loading, setLoading] = useState(false);
  const [strategyRanking, setStrategyRanking] = useState<StrategyRankingResponse | null>(null);
  const [strategyMsg, setStrategyMsg] = useState<string | null>(null);
  const [modelRegistry, setModelRegistry] = useState<ModelRegistryResponse | null>(null);
  const [modelEvidence, setModelEvidence] = useState<Record<string, unknown> | null>(null);
  const [proofStatus, setProofStatus] = useState<Record<string, unknown> | null>(null);
  const [proofRecords, setProofRecords] = useState<Record<string, unknown>[]>([]);
  const [qlibStatus, setQlibStatus] = useState<Record<string, unknown> | null>(null);
  const [qlibAutomation, setQlibAutomation] = useState<Record<string, unknown> | null>(null);
  const [qlibSignals, setQlibSignals] = useState<Record<string, unknown> | null>(null);

  const [priceSnap, setPriceSnap] = useState<MarketDataSnapshot | null>(null);
  const [priceErr, setPriceErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [
          sr,
          mr,
          me,
          ps,
          pr,
          qs,
          qa,
          qsig,
        ] = await Promise.all([
          api.getLatestStrategyRanking().catch(() => null),
          api.getModelRunRegistry().catch(() => null),
          api.getLatestModelEvidenceRecord().catch(() => null),
          api.getProofRegistryStatus().catch(() => null),
          api.listProofRegistryRecords(12).catch(() => null),
          api.getQlibStatus().catch(() => null),
          api.getQlibAutomationStatus().catch(() => null),
          api.getLatestQlibSignals().catch(() => null),
        ]);
        if (cancelled) return;
        if (sr && isStrategyRankingPayload(sr)) {
          setStrategyRanking(sr);
          setStrategyMsg(null);
        } else if (sr && "message" in sr) {
          setStrategyRanking(null);
          setStrategyMsg(String((sr as { message?: string }).message ?? "No strategy ranking"));
        } else {
          setStrategyRanking(null);
          setStrategyMsg(null);
        }
        setModelRegistry(mr);
        setModelEvidence(me?.record ?? null);
        setProofStatus(ps);
        setProofRecords(pr?.records ?? []);
        setQlibStatus(qs);
        setQlibAutomation(qa);
        setQlibSignals(qsig?.artifact ?? null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  const plan = latestBlob?.execution_planner ?? null;
  const planRec = asRecord(plan);

  const topRanked: RankedStrategy | undefined = strategyRanking?.ranked_strategies?.[0];

  const resolvedSymbol = useMemo(() => {
    const fromPlan = pickSymbolFromPlan(planRec);
    if (fromPlan) return fromPlan;
    const fromOrch = pickSymbolFromOrchestrator(orchestratorRun);
    if (fromOrch) return fromOrch;
    return null;
  }, [planRec, orchestratorRun]);

  useEffect(() => {
    let cancelled = false;
    setPriceSnap(null);
    setPriceErr(null);
    if (!resolvedSymbol) return;
    (async () => {
      try {
        const snap = await api.getMarketDataSnapshot(resolvedSymbol, "auto");
        if (!cancelled) setPriceSnap(snap);
      } catch (e) {
        if (!cancelled) setPriceErr(e instanceof Error ? e.message : "Price fetch failed");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [resolvedSymbol, refreshKey]);

  const panelClass = "rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4";

  return (
    <div className="space-y-6">
      {loading ? (
        <p className="text-xs text-slate-500">Loading strategy, model, proof, and Qlib panels…</p>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <div className={panelClass}>
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Strategy ranking</h3>
          <p className="mt-1 text-xs text-slate-500">
            <code className="text-emerald-200/80">GET /api/strategy-ranking/latest</code> — paper-first context only.
          </p>
          {strategyMsg && !strategyRanking ? <p className="mt-2 text-sm text-slate-400">{strategyMsg}</p> : null}
          {strategyRanking ? (
            <div className="mt-3 space-y-2 text-sm text-slate-300">
              <div className="text-xs text-slate-500">
                run_id <span className="font-mono text-slate-400">{strategyRanking.run_id}</span> · status{" "}
                <span className="text-slate-200">{strategyRanking.status}</span>
              </div>
              {topRanked ? (
                <div className="rounded-lg border border-white/10 bg-black/20 p-3">
                  <div className="text-xs font-semibold text-emerald-200/90">
                    #{topRanked.rank} {topRanked.strategy_key}
                  </div>
                  <div className="mt-1 text-xs text-slate-400">{topRanked.strategy_family}</div>
                  <div className="mt-2 text-xs text-slate-300">{topRanked.reason}</div>
                  {(topRanked.blockers?.length ?? 0) > 0 ? (
                    <div className="mt-2 text-xs text-red-200/90">Blockers: {topRanked.blockers.join("; ")}</div>
                  ) : null}
                </div>
              ) : (
                <p className="text-xs text-slate-500">No ranked strategies in payload.</p>
              )}
              <JsonPeek label="Full ranking JSON" data={strategyRanking} />
            </div>
          ) : null}
        </div>

        <div className={panelClass}>
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Model registry & evidence</h3>
          <p className="mt-1 text-xs text-slate-500">
            Registry: <code className="text-emerald-200/80">GET /api/model-runs/registry</code> · Latest evidence:{" "}
            <code className="text-emerald-200/80">GET /api/model-evidence/latest</code>
          </p>
          {modelRegistry ? (
            <div className="mt-3 text-xs text-slate-400">
              <span className="text-slate-300">{modelRegistry.available_model_count ?? modelRegistry.models?.length ?? 0}</span>{" "}
              models · source {String(modelRegistry.data_source ?? "—")}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">Registry unavailable.</p>
          )}
          {modelEvidence ? (
            <JsonPeek label="Latest model evidence" data={modelEvidence} max={2200} />
          ) : (
            <p className="mt-2 text-xs text-slate-500">No model evidence record.</p>
          )}
        </div>

        <div className={panelClass}>
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Proof registry</h3>
          <p className="mt-1 text-xs text-slate-500">
            <code className="text-emerald-200/80">GET /api/proof-registry/status</code> and records — governance visibility only.
          </p>
          {proofStatus ? (
            <pre className="mt-2 max-h-32 overflow-auto rounded border border-white/10 bg-black/30 p-2 text-[10px] text-slate-400">
              {JSON.stringify(proofStatus, null, 2)}
            </pre>
          ) : null}
          <div className="mt-2 text-[11px] text-slate-500">{proofRecords.length} recent records</div>
          {proofRecords.length ? (
            <ul className="mt-2 max-h-40 space-y-1 overflow-auto text-[11px] text-slate-400">
              {proofRecords.slice(0, 8).map((rec, i) => (
                <li key={i} className="truncate font-mono">
                  {String(rec.proof_id ?? rec.id ?? rec["proof_key"] ?? i)}
                </li>
              ))}
            </ul>
          ) : null}
        </div>

        <div className={panelClass}>
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Qlib</h3>
          <p className="mt-1 text-xs text-amber-100/80">
            Qlib automation and artifacts here are <span className="font-semibold text-amber-100">metadata-only</span> in this UI — no remote
            training or scoring jobs are started from the runbook.
          </p>
          {qlibStatus ? (
            <pre className="mt-2 max-h-28 overflow-auto rounded border border-white/10 bg-black/30 p-2 text-[10px] text-slate-400">
              {JSON.stringify(qlibStatus, null, 2)}
            </pre>
          ) : null}
          {qlibAutomation ? (
            <JsonPeek label="Automation status (metadata)" data={qlibAutomation} max={1600} />
          ) : null}
          {qlibSignals ? (
            <JsonPeek label="Latest signals artifact" data={qlibSignals} max={1600} />
          ) : (
            <p className="mt-2 text-xs text-slate-500">No latest Qlib signals artifact.</p>
          )}
        </div>
      </div>

      <div className={panelClass}>
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Final trade decision (read-only composer)</h3>
        <p className="mt-1 text-xs text-slate-500">
          Composed from execution planner latest blob, top strategy ranking, model evidence summary, and a market snapshot.{" "}
          <span className="font-medium text-slate-300">Paper-first; no order submit</span> from this page.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Execution planner (latest)</div>
            {planRec ? (
              <JsonPeek label="execution_planner blob" data={plan} max={3200} />
            ) : (
              <p className="mt-2 text-xs text-slate-500">No execution_planner in runbook latest.</p>
            )}
          </div>
          <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Symbol &amp; price snapshot</div>
            <div className="mt-2 text-sm text-slate-300">
              Symbol:{" "}
              <span className="font-mono text-emerald-200/90">{resolvedSymbol ?? "— (derive from planner or orchestrator)"}</span>
            </div>
            {priceErr ? <p className="mt-2 text-xs text-red-300/90">{priceErr}</p> : null}
            {priceSnap ? (
              <dl className="mt-3 grid gap-1 text-xs text-slate-400">
                <div>
                  Last: <span className="text-slate-200">{priceSnap.price != null ? String(priceSnap.price) : "—"}</span>
                </div>
                <div>Change: {priceSnap.change_percent != null ? `${priceSnap.change_percent.toFixed(2)}%` : "—"}</div>
                <div>Provider: {priceSnap.provider ?? "—"}</div>
                <div>Mock: {priceSnap.is_mock ? "yes" : "no"}</div>
              </dl>
            ) : resolvedSymbol ? (
              <p className="mt-2 text-xs text-slate-500">Loading snapshot…</p>
            ) : null}
          </div>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
          <Link className="text-sky-300 hover:text-sky-200" href="/paper-trading">
            Paper trading →
          </Link>
          <Link className="text-sky-300 hover:text-sky-200" href="/approval-queue">
            Approval queue →
          </Link>
        </div>
      </div>
    </div>
  );
}
