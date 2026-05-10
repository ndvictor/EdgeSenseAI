"use client";

import Link from "next/link";
import React, { useEffect, useMemo, useState } from "react";
import {
  api,
  type DataQualityStatusResponse,
  type MarketDataSnapshot,
  type ModelRegistryResponse,
  type ModelSelectionResponse,
  type OrchestratorRunRecord,
  type RankedStrategy,
  type SelectedModel,
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

/** Best-effort “workflow selected” strategy for visibility (not a legal promotion). */
function deriveWorkflowSelectedStrategy(
  planRec: Record<string, unknown> | null,
  modelSel: ModelSelectionResponse | null,
  orch: OrchestratorRunRecord | null,
): { key: string; source: string } | null {
  if (modelSel?.strategy_key?.trim()) {
    return { key: modelSel.strategy_key.trim(), source: "model-selection/latest → strategy_key" };
  }
  if (planRec) {
    const sk = planRec.strategy_key;
    if (typeof sk === "string" && sk.trim()) return { key: sk.trim(), source: "runbook execution_planner blob" };
    const te = asRecord(planRec.trigger_evaluation);
    const tsk = te?.strategy_key;
    if (typeof tsk === "string" && tsk.trim()) return { key: tsk.trim(), source: "execution_planner.trigger_evaluation" };
  }
  const r = orch as Record<string, unknown> | null;
  if (r) {
    const sk = r.strategy_key;
    if (typeof sk === "string" && sk.trim()) return { key: sk.trim(), source: "orchestrator run" };
    const meta = asRecord(r.metadata);
    const msk = meta?.strategy_key;
    if (typeof msk === "string" && msk.trim()) return { key: msk.trim(), source: "orchestrator.metadata.strategy_key" };
  }
  return null;
}

function collectChosenModels(ms: ModelSelectionResponse): SelectedModel[] {
  const buckets = [ms.selected_scanner_models, ms.selected_scoring_models, ms.selected_validation_models];
  const out: SelectedModel[] = [];
  for (const b of buckets) {
    for (const m of b ?? []) {
      if (m.selected) out.push(m);
    }
  }
  return out;
}

function pickNumber(v: unknown): number | null {
  if (typeof v === "number" && Number.isFinite(v)) return v;
  if (typeof v === "string" && v.trim()) {
    const n = Number(v);
    if (Number.isFinite(n)) return n;
  }
  return null;
}

function pickFromPlan(plan: Record<string, unknown> | null, keys: string[]): unknown {
  if (!plan) return null;
  for (const k of keys) {
    if (plan[k] != null) return plan[k];
  }
  for (const nest of ["plan", "entry", "signal", "trade_plan", "execution_plan"]) {
    const inner = asRecord(plan[nest]);
    if (!inner) continue;
    for (const k of keys) {
      if (inner[k] != null) return inner[k];
    }
  }
  return null;
}

function normalizeMoney(n: number | null): string {
  if (n == null) return "—";
  const abs = Math.abs(n);
  const digits = abs >= 100 ? 2 : abs >= 10 ? 3 : 4;
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function isStrategyRankingPayload(
  x: StrategyRankingResponse | { message: string; status: string },
): x is StrategyRankingResponse {
  return "ranked_strategies" in x && Array.isArray((x as StrategyRankingResponse).ranked_strategies);
}

function isModelSelectionPayload(
  x: ModelSelectionResponse | { message: string; status: string },
): x is ModelSelectionResponse {
  return "strategy_key" in x && "selected_scanner_models" in x;
}

function JsonPeek({ label, data, max = 2800 }: { label: string; data: unknown; max?: number }) {
  const raw = useMemo(() => {
    try {
      return JSON.stringify(data, null, 2) ?? "";
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
  const [modelSelection, setModelSelection] = useState<ModelSelectionResponse | null>(null);
  const [modelSelectionMsg, setModelSelectionMsg] = useState<string | null>(null);
  const [modelRegistry, setModelRegistry] = useState<ModelRegistryResponse | null>(null);
  const [modelEvidence, setModelEvidence] = useState<Record<string, unknown> | null>(null);
  const [proofStatus, setProofStatus] = useState<Record<string, unknown> | null>(null);
  const [proofRecords, setProofRecords] = useState<Record<string, unknown>[]>([]);
  const [qlibStatus, setQlibStatus] = useState<Record<string, unknown> | null>(null);
  const [qlibAutomation, setQlibAutomation] = useState<Record<string, unknown> | null>(null);
  const [qlibSignals, setQlibSignals] = useState<Record<string, unknown> | null>(null);
  const [dqStatus, setDqStatus] = useState<DataQualityStatusResponse | null>(null);

  const [priceSnap, setPriceSnap] = useState<MarketDataSnapshot | null>(null);
  const [priceErr, setPriceErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [
          sr,
          msel,
          mr,
          me,
          ps,
          pr,
          qs,
          qa,
          qsig,
          dq,
        ] = await Promise.all([
          api.getLatestStrategyRanking().catch(() => null),
          api.getLatestModelSelection().catch(() => null),
          api.getModelRunRegistry().catch(() => null),
          api.getLatestModelEvidenceRecord().catch(() => null),
          api.getProofRegistryStatus().catch(() => null),
          api.listProofRegistryRecords(12).catch(() => null),
          api.getQlibStatus().catch(() => null),
          api.getQlibAutomationStatus().catch(() => null),
          api.getLatestQlibSignals().catch(() => null),
          api.getDataQualityStatus().catch(() => null),
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
        if (msel && isModelSelectionPayload(msel)) {
          setModelSelection(msel);
          setModelSelectionMsg(null);
        } else if (msel && "message" in msel) {
          setModelSelection(null);
          setModelSelectionMsg(String((msel as { message?: string }).message ?? "No model selection"));
        } else {
          setModelSelection(null);
          setModelSelectionMsg(null);
        }
        setModelRegistry(mr);
        setModelEvidence(me?.record ?? null);
        setProofStatus(ps);
        setProofRecords(pr?.records ?? []);
        setQlibStatus(qs);
        setQlibAutomation(qa);
        setQlibSignals(qsig?.artifact ?? null);
        setDqStatus(dq);
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

  const workflowStrategy = useMemo(
    () => deriveWorkflowSelectedStrategy(planRec, modelSelection, orchestratorRun),
    [planRec, modelSelection, orchestratorRun],
  );

  const rankingAligns =
    workflowStrategy && topRanked
      ? workflowStrategy.key.toLowerCase() === topRanked.strategy_key.toLowerCase()
      : null;

  const chosenModels = modelSelection ? collectChosenModels(modelSelection) : [];

  const orchRec = asRecord(orchestratorRun);
  const orchTimeline = (orchRec?.stage_timeline as Array<Record<string, unknown>> | undefined) ?? [];
  const orchWorkflowRunId = typeof orchRec?.workflow_run_id === "string" ? (orchRec.workflow_run_id as string) : null;
  const orchOrchestratorRunId = typeof orchRec?.orchestrator_run_id === "string" ? (orchRec.orchestrator_run_id as string) : null;

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
  const watchlistBlob = latestBlob?.watchlist_builder ?? null;
  const watchRec = asRecord(watchlistBlob);
  const watchSummary = asRecord(watchRec?.summary);
  const marketBlob = latestBlob?.market_condition_scanner ?? null;
  const marketRec = asRecord(marketBlob);
  const gateRec = asRecord(marketRec?.gate_readiness);
  const gateTrust = gateRec ? Boolean(gateRec.heuristic_operator_trust) : null;

  const dqRollup = dqStatus?.summary?.rollup_status ?? dqStatus?.summary?.status ?? null;
  const dqBlockers = dqStatus?.summary?.pipeline_blockers ?? [];

  const planEntry = useMemo(() => pickNumber(pickFromPlan(planRec, ["entry", "entry_price", "limit_price", "buy_price"])), [planRec]);
  const planStop = useMemo(() => pickNumber(pickFromPlan(planRec, ["stop", "stop_price", "stop_loss"])), [planRec]);
  const planTarget = useMemo(() => pickNumber(pickFromPlan(planRec, ["target", "target_price", "take_profit"])), [planRec]);
  const planQty = useMemo(() => pickNumber(pickFromPlan(planRec, ["qty", "quantity", "shares"])), [planRec]);

  const operatorBlockers = useMemo(() => {
    const b: string[] = [];
    if (dqRollup === "fail") b.push("Data quality rollup = fail");
    if (dqRollup === "warn") b.push("Data quality rollup = warn (review freshness/warnings)");
    for (const x of dqBlockers) {
      if (typeof x === "string" && x.trim()) b.push(`Data quality: ${x.trim()}`);
    }
    if (marketRec?.status && String(marketRec.status).toLowerCase() === "fail") b.push("Market condition scanner status = fail");
    if (gateTrust === false) b.push("Market regime trust heuristic = no (treat as context, not a gate)");
    if (!resolvedSymbol) b.push("No symbol resolved from execution planner / orchestrator context");
    if (planRec && planEntry == null) b.push("Execution plan missing entry price");
    if (planRec && planStop == null) b.push("Execution plan missing stop price");
    if (planRec && planQty == null) b.push("Execution plan missing quantity");
    return b.slice(0, 12);
  }, [dqRollup, dqBlockers, marketRec, gateTrust, resolvedSymbol, planRec, planEntry, planStop, planQty]);

  const paperDecision = useMemo(() => {
    if (!planRec) return "hold";
    if (operatorBlockers.some((x) => x.toLowerCase().includes("fail") || x.toLowerCase().includes("missing"))) return "hold";
    return "proceed_to_paper";
  }, [planRec, operatorBlockers]);

  return (
    <div className="space-y-6">
      <div className={panelClass}>
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Run correlation (Phase 3)</h3>
        <p className="mt-1 text-xs text-slate-500">
          Use <span className="text-slate-300">workflow_run_id</span> as the spine. Orchestrator + agent run IDs are the canonical trace for “this run”.
        </p>
        <dl className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
          <div>
            workflow_run_id: <span className="font-mono text-emerald-200/90">{orchWorkflowRunId ?? "—"}</span>
          </div>
          <div>
            orchestrator_run_id: <span className="font-mono text-slate-200/90">{orchOrchestratorRunId ?? "—"}</span>
          </div>
          <div>
            execution_plan_id:{" "}
            <span className="font-mono text-slate-200/90">{typeof planRec?.plan_id === "string" ? String(planRec.plan_id) : "—"}</span>
          </div>
          <div>
            strategy_ranking_run_id (latest):{" "}
            <span className="font-mono text-slate-200/90">{strategyRanking?.run_id ?? "—"}</span>
          </div>
          <div>
            model_selection_run_id (latest): <span className="font-mono text-slate-200/90">{modelSelection?.run_id ?? "—"}</span>
          </div>
          <div>
            trace:{" "}
            {orchWorkflowRunId ? (
              <Link className="text-sky-300 hover:text-sky-200" href={`/workflow-runbook?workflow_run_id=${encodeURIComponent(orchWorkflowRunId)}`}>
                open trace tools →
              </Link>
            ) : (
              <span className="text-slate-500">—</span>
            )}
          </div>
        </dl>

        {orchTimeline.length ? (
          <details className="mt-3 rounded-lg border border-white/[0.06] bg-black/25">
            <summary className="cursor-pointer px-2 py-1.5 text-[11px] text-slate-400">Stage → agent_run_id map</summary>
            <div className="border-t border-white/[0.06] p-2">
              <ul className="max-h-48 space-y-1 overflow-auto text-[11px] text-slate-400">
                {orchTimeline.slice(0, 18).map((row, i) => (
                  <li key={i} className="flex items-center justify-between gap-3">
                    <span className="truncate">
                      stage {String(row.stage ?? "—")} · {String(row.agent_key ?? "—")}
                    </span>
                    <span className="font-mono text-emerald-200/80">{String(row.run_id ?? "—")}</span>
                  </li>
                ))}
              </ul>
            </div>
          </details>
        ) : (
          <p className="mt-2 text-xs text-slate-500">No orchestrator stage timeline loaded yet. Run a workflow preview to populate.</p>
        )}
      </div>

      <div className={panelClass}>
        <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Watchlist builder (stage 6 blob)</h3>
        <p className="mt-1 text-xs text-slate-500">
          From <code className="text-emerald-200/80">GET /api/workflow-runbook/latest</code> →{" "}
          <code className="text-emerald-200/80">watchlist_builder</code>.
        </p>
        {watchSummary ? (
          <div className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
            <div>
              Rows: <span className="text-slate-200">{String(watchSummary.row_count ?? "—")}</span>
            </div>
            <div>
              Distinct symbols: <span className="text-slate-200">{String(watchSummary.distinct_symbols ?? "—")}</span>
            </div>
              {typeof watchSummary.last_updated === "string" ? (
                <div className="sm:col-span-2 text-[11px] text-slate-500">Updated: {watchSummary.last_updated}</div>
              ) : null}
            {typeof watchSummary.note === "string" ? (
              <div className="sm:col-span-2 text-[11px] text-slate-500">{watchSummary.note}</div>
            ) : null}
          </div>
        ) : (
          <p className="mt-2 text-xs text-slate-500">No watchlist_builder blob yet.</p>
        )}
        {Array.isArray(watchRec?.symbols) && (watchRec.symbols as string[]).length ? (
          <div className="mt-3 flex max-h-24 flex-wrap gap-1 overflow-y-auto">
            {(watchRec.symbols as string[]).slice(0, 40).map((s) => (
              <span key={s} className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-300">
                {s}
              </span>
            ))}
            {(watchRec.symbols as string[]).length > 40 ? (
              <span className="text-[10px] text-slate-500">+{(watchRec.symbols as string[]).length - 40} more</span>
            ) : null}
          </div>
        ) : null}
        <JsonPeek label="Raw watchlist_builder JSON" data={watchlistBlob} max={2200} />
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className={panelClass}>
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Data quality rollup (stage 2)</h3>
          <p className="mt-1 text-xs text-slate-500">
            <code className="text-emerald-200/80">GET /api/data-quality/status</code> — sampled candidates with pass/warn/fail and freshness.
          </p>
          {dqStatus?.summary ? (
            <div className="mt-3 space-y-1 text-xs text-slate-400">
              <div>
                Rollup: <span className="text-slate-200">{String(dqStatus.summary.rollup_status ?? dqStatus.summary.status ?? "—")}</span>
              </div>
              <div>
                Universe {String(dqStatus.summary.active_candidates_in_universe ?? "—")} · sampled{" "}
                {String(dqStatus.summary.symbols_sampled ?? dqStatus.summary.symbols_checked_today ?? "—")}
              </div>
              <div>
                Pass/warn/fail: {String(dqStatus.summary.pass ?? 0)} / {String(dqStatus.summary.warnings ?? 0)} / {String(dqStatus.summary.fails ?? 0)}
              </div>
              <div>
                Fresh/stale/unknown: {String(dqStatus.summary.fresh ?? 0)} / {String(dqStatus.summary.stale ?? 0)} /{" "}
                {String(dqStatus.summary.unknown_freshness ?? 0)}
              </div>
              {(dqStatus.summary.pipeline_blockers?.length ?? 0) > 0 ? (
                <div className="mt-2 text-[11px] text-red-200/90">Blockers: {dqStatus.summary.pipeline_blockers!.join("; ")}</div>
              ) : null}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">No data-quality status yet.</p>
          )}
          {dqStatus?.symbol_samples?.length ? (
            <details className="mt-2">
              <summary className="cursor-pointer text-[11px] text-slate-400">Symbol samples ({dqStatus.symbol_samples.length})</summary>
              <pre className="mt-2 max-h-40 overflow-auto rounded border border-white/10 bg-black/25 p-2 text-[10px] text-slate-400">
                {JSON.stringify(dqStatus.symbol_samples.slice(0, 12), null, 2)}
              </pre>
            </details>
          ) : null}
        </div>

        <div className={panelClass}>
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Market condition scanner (stage 4)</h3>
          <p className="mt-1 text-xs text-slate-500">
            Runbook blob <code className="text-emerald-200/80">market_condition_scanner</code> from latest market regime model run.
          </p>
          {marketRec ? (
            <div className="mt-3 space-y-1 text-xs text-slate-400">
              <div>
                Regime: <span className="text-slate-200">{String(marketRec.regime ?? "—")}</span> · status{" "}
                <span className="text-slate-200">{String(marketRec.status ?? "—")}</span>
              </div>
              <div>
                Trend/vol: {String(marketRec.trend_state ?? "—")} / {String(marketRec.volatility_state ?? "—")} · conf{" "}
                {String(marketRec.confidence ?? "—")}
              </div>
              {(marketRec.blockers as string[] | undefined)?.length ? (
                <div className="text-[11px] text-red-200/90">Blockers: {(marketRec.blockers as string[]).join("; ")}</div>
              ) : null}
              {(marketRec.warnings as string[] | undefined)?.length ? (
                <div className="text-[11px] text-amber-200/90">Warnings: {(marketRec.warnings as string[]).join("; ")}</div>
              ) : null}
              {gateRec ? (
                <div className="mt-2 rounded-lg border border-amber-500/25 bg-amber-500/10 p-2 text-[11px] text-amber-100/90">
                  Gate readiness: {gateRec.heuristic_operator_trust ? "operator-trust yes (still review inputs)" : "operator-trust no"} ·{" "}
                  {String(gateRec.rationale ?? "")}
                </div>
              ) : null}
            </div>
          ) : (
            <p className="mt-2 text-xs text-slate-500">No market condition snapshot yet. Run Market Regime, then refresh runbook.</p>
          )}
          <JsonPeek label="inputs_used" data={marketRec?.inputs_used} max={1600} />
        </div>
      </div>

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
              <div className="rounded-lg border border-sky-500/25 bg-sky-500/10 p-3 text-xs">
                <div className="font-semibold uppercase tracking-wide text-sky-200/90">Workflow-selected strategy (derived)</div>
                {workflowStrategy ? (
                  <div className="mt-2 text-slate-200">
                    <span className="font-mono text-emerald-200/90">{workflowStrategy.key}</span>
                    <div className="mt-1 text-[11px] text-slate-500">Source: {workflowStrategy.source}</div>
                    {rankingAligns === true ? (
                      <div className="mt-1 text-[11px] text-emerald-200/80">Matches top ranked strategy.</div>
                    ) : rankingAligns === false ? (
                      <div className="mt-1 text-[11px] text-amber-200/90">
                        Differs from top rank ({topRanked?.strategy_key ?? "—"}); ranking is latest snapshot, not necessarily same run.
                      </div>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-2 text-slate-500">
                    No strategy_key yet from model-selection/latest, planner blob, or orchestrator run — see ranking below.
                  </p>
                )}
              </div>
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
          <h3 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Model selection, registry & evidence</h3>
          <p className="mt-1 text-xs text-slate-500">
            Selection: <code className="text-emerald-200/80">GET /api/model-selection/latest</code> · Registry:{" "}
            <code className="text-emerald-200/80">GET /api/model-runs/registry</code> · Evidence:{" "}
            <code className="text-emerald-200/80">GET /api/model-evidence/latest</code>
          </p>
          {modelSelectionMsg && !modelSelection ? (
            <p className="mt-2 text-xs text-slate-500">{modelSelectionMsg}</p>
          ) : null}
          {modelSelection ? (
            <div className="mt-3 space-y-2 rounded-lg border border-violet-500/20 bg-violet-500/10 p-3 text-xs">
              <div className="text-[10px] font-semibold uppercase tracking-wide text-violet-200/90">Latest model selection</div>
              <div>
                <span className="text-slate-500">strategy_key</span>{" "}
                <span className="font-mono text-slate-200">{modelSelection.strategy_key}</span> ·{" "}
                <span className="text-slate-500">status</span> <span className="text-slate-200">{modelSelection.status}</span>
              </div>
              <div className="text-slate-400">{modelSelection.reason}</div>
              {(modelSelection.blockers?.length ?? 0) > 0 ? (
                <div className="text-[11px] text-red-200/90">Blockers: {modelSelection.blockers.join("; ")}</div>
              ) : null}
              <div className="text-[11px] text-slate-500">
                Selected models (selected=true):{" "}
                {chosenModels.length ? (
                  <ul className="mt-1 list-inside list-disc text-slate-300">
                    {chosenModels.map((m) => (
                      <li key={`${m.model_key}-${m.model_type}`}>
                        <span className="font-mono text-emerald-200/80">{m.model_key}</span> ({m.model_type}) — {m.reason}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <span className="text-slate-500">none flagged selected in payload.</span>
                )}
              </div>
              {(modelSelection.skipped_models?.length ?? 0) > 0 ? (
                <details className="text-[11px] text-slate-500">
                  <summary className="cursor-pointer text-slate-400">Skipped models ({modelSelection.skipped_models.length})</summary>
                  <ul className="mt-1 max-h-32 overflow-auto font-mono text-[10px] text-slate-400">
                    {modelSelection.skipped_models.map((m) => (
                      <li key={`skip-${m.model_key}`}>
                        {m.model_key}: {m.skip_reason ?? m.reason}
                      </li>
                    ))}
                  </ul>
                </details>
              ) : null}
              <JsonPeek label="Full model-selection JSON" data={modelSelection} max={2400} />
            </div>
          ) : null}
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
          Composed from execution planner latest blob, derived workflow strategy (model-selection / planner / orchestrator), strategy ranking,
          model stack, evidence, and a market snapshot.{" "}
          <span className="font-medium text-slate-300">Paper-first; no order submit</span> from this page.
        </p>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 p-3">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Operator summary (paper-first)</div>
            <dl className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
              <div className="sm:col-span-2">
                Paper decision:{" "}
                <span className={`font-semibold ${paperDecision === "proceed_to_paper" ? "text-emerald-200" : "text-amber-200"}`}>
                  {paperDecision.replaceAll("_", " ")}
                </span>
              </div>
              <div className="sm:col-span-2">
                Strategy:{" "}
                <span className="text-slate-200">
                  {workflowStrategy?.key ?? topRanked?.strategy_key ?? "—"}
                </span>{" "}
                <span className="text-[11px] text-slate-500">{workflowStrategy ? `(${workflowStrategy.source})` : ""}</span>
              </div>
              <div className="sm:col-span-2">
                Models:{" "}
                <span className="text-slate-200">
                  {chosenModels.length ? chosenModels.map((m) => m.model_key).slice(0, 3).join(", ") : "—"}
                </span>
                {chosenModels.length > 3 ? <span className="text-[11px] text-slate-500"> (+{chosenModels.length - 3} more)</span> : null}
              </div>
              <div>
                Symbol: <span className="font-mono text-emerald-200/90">{resolvedSymbol ?? "—"}</span>
              </div>
              <div>
                Data quality: <span className="text-slate-200">{dqRollup ? String(dqRollup) : "—"}</span>
              </div>
              <div>
                Entry: <span className="text-slate-200">{normalizeMoney(planEntry)}</span>
              </div>
              <div>
                Stop: <span className="text-slate-200">{normalizeMoney(planStop)}</span>
              </div>
              <div>
                Target: <span className="text-slate-200">{normalizeMoney(planTarget)}</span>
              </div>
              <div>
                Qty: <span className="text-slate-200">{planQty != null ? String(planQty) : "—"}</span>
              </div>
              <div className="sm:col-span-2 text-[11px] text-slate-500">
                Market regime trust: {gateTrust == null ? "unknown" : gateTrust ? "yes (still review inputs)" : "no"} ·{" "}
                {typeof gateRec?.rationale === "string" ? gateRec.rationale : "treat as context, not sole gate"}
              </div>
            </dl>

            {operatorBlockers.length ? (
              <div className="mt-3 rounded-lg border border-rose-500/25 bg-rose-500/10 p-2">
                <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-rose-200/90">Blockers / review items</div>
                <ul className="mt-2 space-y-1 text-[11px] text-rose-100/90">
                  {operatorBlockers.map((b, i) => (
                    <li key={`${b}-${i}`}>- {b}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="mt-3 rounded-lg border border-emerald-400/20 bg-emerald-400/10 p-2 text-[11px] text-emerald-100/90">
                No blockers detected in visible sources. Proceed with paper-only workflow checks.
              </div>
            )}

            {planRec ? <JsonPeek label="execution_planner blob (raw)" data={plan} max={2600} /> : <p className="mt-2 text-xs text-slate-500">No execution_planner in runbook latest.</p>}
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
                <div>NonReal: {priceSnap.is_non_real ? "yes" : "no"}</div>
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
