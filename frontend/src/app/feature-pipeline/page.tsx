"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  api,
  type FeatureStoreRow,
  type FeatureStoreRunResponse,
  type PipelineAutomationRunResponse,
  type PipelineFeatureStoreRunArtifact,
} from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";
const field =
  "w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400/50 focus:outline-none";

const PIPELINE_CLIENT_TIMEOUT_MS = 420_000;

function parseSeedSymbols(text: string): string[] {
  const out: string[] = [];
  for (const part of text.split(/[\s,]+/)) {
    const s = part.trim().toUpperCase();
    if (s && !out.includes(s)) out.push(s);
  }
  return out;
}

function featureRunsFromArtifacts(artifacts: Record<string, unknown> | undefined): PipelineFeatureStoreRunArtifact[] {
  const raw = artifacts?.feature_store_runs;
  if (!Array.isArray(raw)) return [];
  return raw.filter((x): x is PipelineFeatureStoreRunArtifact => {
    if (!x || typeof x !== "object") return false;
    const o = x as Record<string, unknown>;
    return typeof o.symbol === "string" && typeof o.row_id === "string";
  });
}

export default function FeaturePipelinePage() {
  const [symbol, setSymbol] = useState("AMD");
  const [assetClass, setAssetClass] = useState("stock");
  const [horizon, setHorizon] = useState<"intraday" | "day_trade" | "swing" | "one_month">("swing");
  const [source, setSource] = useState<string>("auto");
  const [rows, setRows] = useState<FeatureStoreRow[]>([]);
  const [lastRun, setLastRun] = useState<FeatureStoreRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [runError, setRunError] = useState<string | null>(null);

  const [autoSeeds, setAutoSeeds] = useState("SPY, QQQ, AAPL, MSFT, AMD, NVDA");
  const [autoHorizon, setAutoHorizon] = useState("day_trading");
  const [autoMaxCandidates, setAutoMaxCandidates] = useState(10);
  const [autoDryRun, setAutoDryRun] = useState(true);
  const [featuresOnly, setFeaturesOnly] = useState(false);
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoError, setAutoError] = useState<string | null>(null);
  const [autoNotice, setAutoNotice] = useState<string | null>(null);
  const [lastAutoRun, setLastAutoRun] = useState<PipelineAutomationRunResponse | null>(null);

  const refreshLatest = useCallback(async () => {
    setLoadError(null);
    try {
      setRows(await api.getLatestFeatureStoreRows());
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load feature rows");
    }
  }, []);

  const refreshLatestPipeline = useCallback(async () => {
    try {
      const env = await api.getLatestPipelineAutomationRun();
      if (env.run) setLastAutoRun(env.run);
    } catch {
      /* optional */
    }
  }, []);

  useEffect(() => {
    void refreshLatest();
    void refreshLatestPipeline();
  }, [refreshLatest, refreshLatestPipeline]);

  const autoFeatureRuns = useMemo(
    () => featureRunsFromArtifacts(lastAutoRun?.artifacts as Record<string, unknown> | undefined),
    [lastAutoRun],
  );

  async function runAutomatedPipeline() {
    setAutoError(null);
    setAutoNotice(null);
    setAutoLoading(true);
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), PIPELINE_CLIENT_TIMEOUT_MS);
    try {
      const seeds = parseSeedSymbols(autoSeeds);
      const payload = {
        asset_class: assetClass,
        horizon: autoHorizon,
        mode: "paper_first" as const,
        source: autoDryRun ? "mock" : source,
        seed_symbols: seeds.length ? seeds : ["AMD"],
        max_candidates: Math.max(1, Math.min(100, autoMaxCandidates)),
        dry_run: autoDryRun,
        require_human_approval: true,
        stop_at_stage: featuresOnly ? 0 : 100,
      };
      const env = await api.runPipelineAutomation(payload, controller.signal);
      setLastAutoRun(env.run);
      const featCount = featureRunsFromArtifacts(env.run.artifacts as Record<string, unknown>).length;
      setAutoNotice(
        `Pipeline ${env.run.pipeline_run_id}: ${env.run.status}. Feature rows written for ${featCount} symbol(s). ${featuresOnly ? "Orchestrator skipped." : ""}`,
      );
      await refreshLatest();
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Automated pipeline failed";
      setAutoError(e instanceof DOMException && e.name === "AbortError" ? `Timed out after ${PIPELINE_CLIENT_TIMEOUT_MS / 60000} minutes.` : msg);
    } finally {
      clearTimeout(timer);
      setAutoLoading(false);
    }
  }

  async function runPipeline() {
    setRunError(null);
    setLoading(true);
    try {
      const sym = symbol.trim().toUpperCase();
      if (!sym) {
        setRunError("Enter a symbol");
        return;
      }
      const response = await api.runFeatureStore({
        symbol: sym,
        asset_class: assetClass,
        horizon,
        source,
      });
      setLastRun(response);
      await refreshLatest();
    } catch (e) {
      setRunError(e instanceof Error ? e.message : "Pipeline run failed");
    } finally {
      setLoading(false);
    }
  }

  const q = lastRun?.quality_report;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-6">
        <PageHeader
          eyebrow="market snapshot → normalization → features"
          title="Feature pipeline"
          description="Run the full backend automation (feed, quality, feature store, universe, optional orchestrator) via POST /api/pipeline/run, or exercise a single symbol through /api/feature-store/run. Rows below reflect this backend process."
        />

        <section className={cardShell}>
          <h2 className="mb-1 text-lg font-semibold text-emerald-400">Automated data pipeline → feature store</h2>
          <p className="mb-4 text-sm text-slate-400">
            Calls <code className="text-emerald-200/90">POST /api/pipeline/run</code>. Builds feature rows for each seed symbol, then universe selection. Uncheck “Features only” to also run the workflow orchestrator (several minutes).
          </p>
          <div className="grid gap-4 lg:grid-cols-2">
            <label className="block space-y-1">
              <span className="text-xs uppercase tracking-wide text-slate-500">Seed symbols (comma-separated)</span>
              <input
                className={field}
                value={autoSeeds}
                onChange={(e) => setAutoSeeds(e.target.value)}
                placeholder="SPY, QQQ, AMD…"
              />
            </label>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block space-y-1">
                <span className="text-xs uppercase tracking-wide text-slate-500">Pipeline horizon</span>
                <select className={field} value={autoHorizon} onChange={(e) => setAutoHorizon(e.target.value)}>
                  <option value="day_trading">day_trading</option>
                  <option value="intraday">intraday</option>
                  <option value="swing">swing</option>
                  <option value="one_month">one_month</option>
                </select>
              </label>
              <label className="block space-y-1">
                <span className="text-xs uppercase tracking-wide text-slate-500">Max candidates</span>
                <input
                  className={field}
                  type="number"
                  min={1}
                  max={100}
                  value={autoMaxCandidates}
                  onChange={(e) => setAutoMaxCandidates(Number(e.target.value))}
                />
              </label>
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center gap-4">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={autoDryRun} onChange={(e) => setAutoDryRun(e.target.checked)} className="rounded border-emerald-400/40" />
              Dry run (mock market data — recommended)
            </label>
            <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-300">
              <input type="checkbox" checked={featuresOnly} onChange={(e) => setFeaturesOnly(e.target.checked)} className="rounded border-emerald-400/40" />
              Features only (skip orchestrator; faster)
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void runAutomatedPipeline()}
              disabled={autoLoading || loading}
              className="rounded-xl border border-cyan-400/40 bg-cyan-500/15 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-500/25 disabled:opacity-50"
            >
              {autoLoading ? "Running full pipeline…" : "Run automated pipeline"}
            </button>
            <button
              type="button"
              onClick={() => void refreshLatestPipeline()}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-white/10"
            >
              Load last API run
            </button>
          </div>
          {autoNotice && <p className="mt-3 text-sm text-emerald-200/90">{autoNotice}</p>}
          {autoError && <p className="mt-3 text-sm text-rose-300">{autoError}</p>}

          {lastAutoRun && (
            <div className="mt-6 space-y-4">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-slate-500">Last pipeline response</h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard label="Run id" value={lastAutoRun.pipeline_run_id} accent />
                <MetricCard label="Status" value={lastAutoRun.status} />
                <MetricCard
                  label="Selected symbols"
                  value={lastAutoRun.selected_symbols.length ? lastAutoRun.selected_symbols.join(", ") : "—"}
                />
                <MetricCard label="Orchestrator" value={lastAutoRun.orchestrator_run_id ?? "—"} />
              </div>
              {(lastAutoRun.blockers?.length ?? 0) > 0 && (
                <p className="text-sm text-rose-200">Blockers: {lastAutoRun.blockers.join("; ")}</p>
              )}
              {(lastAutoRun.warnings?.length ?? 0) > 0 && (
                <p className="text-sm text-amber-200">Warnings: {lastAutoRun.warnings.join("; ")}</p>
              )}
              <p className="text-sm text-slate-400">{lastAutoRun.next_action}</p>
            </div>
          )}

          {autoFeatureRuns.length > 0 && (
            <div className="mt-6">
              <h3 className="mb-2 text-sm font-semibold text-emerald-400">Feature store (from this pipeline run)</h3>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[640px] border-collapse text-left text-sm">
                  <thead>
                    <tr className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-slate-500">
                      <th className="py-2 pr-3">Symbol</th>
                      <th className="py-2 pr-3">Quality</th>
                      <th className="py-2 pr-3">Source</th>
                      <th className="py-2 pr-3">Provider</th>
                      <th className="py-2 pr-3">Row id</th>
                      <th className="py-2">Warnings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {autoFeatureRuns.map((r) => (
                      <tr key={`${r.symbol}-${r.row_id}`} className="border-b border-white/5 text-slate-200">
                        <td className="py-2 pr-3 font-mono text-emerald-200">{r.symbol}</td>
                        <td className="py-2 pr-3">{r.quality_status}</td>
                        <td className="py-2 pr-3">{r.data_source}</td>
                        <td className="py-2 pr-3">{r.provider ?? "—"}</td>
                        <td className="py-2 pr-3 font-mono text-xs text-slate-400">{r.row_id}</td>
                        <td className="py-2 text-xs text-amber-100/80">{(r.warnings ?? []).join("; ") || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        <p className="text-sm text-slate-400">
          Advanced runs:{" "}
          <Link href="/model/lab" className="text-emerald-300 underline-offset-2 hover:underline">
            Model Lab
          </Link>
        </p>

        <section className={cardShell}>
          <h2 className="mb-3 text-lg font-semibold text-emerald-400">Single symbol — feature store only</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <label className="block space-y-1">
              <span className="text-xs uppercase tracking-wide text-slate-500">Symbol</span>
              <input className={field} value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="e.g. AMD" />
            </label>
            <label className="block space-y-1">
              <span className="text-xs uppercase tracking-wide text-slate-500">Asset class</span>
              <select className={field} value={assetClass} onChange={(e) => setAssetClass(e.target.value)}>
                <option value="stock">stock</option>
                <option value="option">option</option>
                <option value="crypto">crypto</option>
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs uppercase tracking-wide text-slate-500">Horizon</span>
              <select className={field} value={horizon} onChange={(e) => setHorizon(e.target.value as typeof horizon)}>
                <option value="intraday">intraday</option>
                <option value="day_trade">day_trade</option>
                <option value="swing">swing</option>
                <option value="one_month">one_month</option>
              </select>
            </label>
            <label className="block space-y-1">
              <span className="text-xs uppercase tracking-wide text-slate-500">Data source</span>
              <select className={field} value={source} onChange={(e) => setSource(e.target.value)}>
                <option value="auto">auto</option>
                <option value="alpaca">alpaca</option>
                <option value="yfinance">yfinance</option>
                <option value="polygon">polygon</option>
                <option value="mock">mock (explicit)</option>
              </select>
            </label>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void runPipeline()}
              disabled={loading || autoLoading}
              className="rounded-xl border border-emerald-400/40 bg-emerald-500/15 px-4 py-2 text-sm font-semibold text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-50"
            >
              {loading ? "Running…" : "Run feature pipeline"}
            </button>
            <button
              type="button"
              onClick={() => void refreshLatest()}
              className="rounded-xl border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-white/10"
            >
              Refresh latest rows
            </button>
          </div>
          {runError && <p className="mt-3 text-sm text-rose-300">{runError}</p>}
          {loadError && <p className="mt-3 text-sm text-amber-200">{loadError}</p>}
        </section>

        {lastRun && q && (
          <section className={cardShell}>
            <h2 className="mb-3 text-lg font-semibold text-emerald-400">Last single-symbol run</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <MetricCard label="Ticker" value={lastRun.row.ticker} accent />
              <MetricCard label="Quality" value={q.quality_status} />
              <MetricCard label="Data source (row)" value={lastRun.row.data_source} />
              <MetricCard label="Confidence" value={lastRun.row.confidence != null ? String(lastRun.row.confidence) : "—"} />
            </div>
            {q.blockers && q.blockers.length > 0 && (
              <p className="mt-3 text-sm text-rose-200">Blockers: {q.blockers.join("; ")}</p>
            )}
            {lastRun.warnings && lastRun.warnings.length > 0 && (
              <p className="mt-3 text-sm text-amber-200">Warnings: {lastRun.warnings.join("; ")}</p>
            )}
          </section>
        )}

        <section className={cardShell}>
          <h2 className="mb-3 text-lg font-semibold text-emerald-400">Latest feature rows (this backend process)</h2>
          {rows.length === 0 ? (
            <p className="text-sm text-slate-400">No rows yet. Run the automated pipeline or single-symbol run above.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] border-collapse text-left text-sm">
                <thead>
                  <tr className="border-b border-emerald-400/15 text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2 pr-3">Ticker</th>
                    <th className="py-2 pr-3">Horizon</th>
                    <th className="py-2 pr-3">Quality</th>
                    <th className="py-2 pr-3">Source</th>
                    <th className="py-2 pr-3">Technical</th>
                    <th className="py-2 pr-3">Confidence</th>
                    <th className="py-2">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(0, 25).map((r) => (
                    <tr key={r.id} className="border-b border-white/5 text-slate-200">
                      <td className="py-2 pr-3 font-mono text-emerald-200">{r.ticker}</td>
                      <td className="py-2 pr-3">{r.horizon}</td>
                      <td className="py-2 pr-3">{r.data_quality}</td>
                      <td className="py-2 pr-3">{r.data_source}</td>
                      <td className="py-2 pr-3">{r.technical_score ?? "—"}</td>
                      <td className="py-2 pr-3">{r.confidence ?? "—"}</td>
                      <td className="py-2 text-xs text-slate-500">{new Date(r.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
