"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { api, type FeatureStoreRow, type FeatureStoreRunResponse } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.25)] backdrop-blur";
const field =
  "w-full rounded-xl border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white placeholder:text-slate-500 focus:border-emerald-400/50 focus:outline-none";

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

  const refreshLatest = useCallback(async () => {
    setLoadError(null);
    try {
      setRows(await api.getLatestFeatureStoreRows());
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : "Failed to load feature rows");
    }
  }, []);

  useEffect(() => {
    void refreshLatest();
  }, [refreshLatest]);

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
          description="Runs the backend feature-store path for one symbol: market data, quality checks, and stored feature rows (in-memory for this process). Use Data validation for broader quality rollup; use Model Lab for experiments on top of these rows."
        />

        <p className="text-sm text-slate-400">
          Advanced runs:{" "}
          <Link href="/model/lab" className="text-emerald-300 underline-offset-2 hover:underline">
            Model Lab
          </Link>
        </p>

        <section className={cardShell}>
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
              disabled={loading}
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
            <h2 className="mb-3 text-lg font-semibold text-emerald-400">Last run</h2>
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
            <p className="text-sm text-slate-400">No rows yet. Run the pipeline above or start workflows that populate the feature store.</p>
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
