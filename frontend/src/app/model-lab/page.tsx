"use client";

import { useState } from "react";
import { api, type ModelLabRunResponse, type ModelLabRunRequest } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function ModelLabPage() {
  const [dataSource, setDataSource] = useState<ModelLabRunRequest["data_source"]>("mock");
  const [model, setModel] = useState<ModelLabRunRequest["model"]>("xgboost_ranker");
  const [symbols, setSymbols] = useState("AMD,NVDA,BTC-USD");
  const [trainSplit, setTrainSplit] = useState(70);
  const [result, setResult] = useState<ModelLabRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  async function runWorkflow() {
    setRunning(true);
    setError(null);
    try {
      const payload: ModelLabRunRequest = {
        data_source: dataSource,
        model,
        symbols: symbols.split(",").map((symbol) => symbol.trim()).filter(Boolean),
        train_split_percent: trainSplit,
        test_split_percent: 100 - trainSplit,
        feature_set: "prototype_v1",
      };
      const response = await api.runModelLab(payload);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Model Lab workflow failed");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="model training workflow"
          title="Model Lab"
          description="Select data source, model, feature set, train/test split, and run a ranking workflow. This connects the feature-agent output into an XGBoost-compatible ranker path with a fallback ranker when XGBoost is unavailable."
        />

        {error && <div className="mb-4 rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        <div className="space-y-4">
          <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-emerald-500">Workflow Controls</h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
              <label className="block">
                <span className="text-sm font-semibold text-slate-300">Data Source</span>
                <select value={dataSource} onChange={(event) => setDataSource(event.target.value as ModelLabRunRequest["data_source"])} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white">
                  <option value="mock">Mock prototype</option>
                  <option value="yfinance">YFinance research</option>
                </select>
              </label>

              <label className="block">
                <span className="text-sm font-semibold text-slate-300">Model</span>
                <select value={model} onChange={(event) => setModel(event.target.value as ModelLabRunRequest["model"])} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white">
                  <option value="xgboost_ranker">XGBoost ranker</option>
                  <option value="weighted_ranker">Weighted fallback ranker</option>
                </select>
              </label>

              <label className="block lg:col-span-2">
                <span className="text-sm font-semibold text-slate-300">Symbols</span>
                <input value={symbols} onChange={(event) => setSymbols(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" />
              </label>

              <label className="block">
                <span className="text-sm font-semibold text-slate-300">Train Split</span>
                <input type="number" min={50} max={90} value={trainSplit} onChange={(event) => setTrainSplit(Number(event.target.value))} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" />
              </label>
            </div>

            <button onClick={runWorkflow} disabled={running} className="mt-4 rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60">
              {running ? "Running workflow..." : "Run Model Lab Workflow"}
            </button>
          </section>

          {result && (
            <>
              <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-emerald-500">Run Summary</h2>
                <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
                  <MetricCard label="Status" value={result.workflow_status} accent />
                  <MetricCard label="Data Source" value={result.data_source} />
                  <MetricCard label="Model" value={result.model} />
                  <MetricCard label="Train Rows" value={result.split.train_rows} />
                  <MetricCard label="Test Rows" value={result.split.test_rows} />
                </div>
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-emerald-500">Feature-Agent Output</h2>
                <div className="overflow-x-auto rounded-xl border border-slate-800">
                  <table className="w-full min-w-[1100px] text-left text-sm">
                    <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                      <tr>
                        <th className="px-4 py-3">Symbol</th>
                        <th className="px-4 py-3">Price</th>
                        <th className="px-4 py-3">Feature</th>
                        <th className="px-4 py-3">Momentum</th>
                        <th className="px-4 py-3">RVOL</th>
                        <th className="px-4 py-3">Spread Quality</th>
                        <th className="px-4 py-3">Trend/VWAP</th>
                        <th className="px-4 py-3">Volatility</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800 bg-slate-950">
                      {result.features.map((row) => (
                        <tr key={row.symbol} className="hover:bg-slate-900">
                          <td className="px-4 py-3 font-bold text-cyan-300">{row.symbol}</td>
                          <td className="px-4 py-3 text-slate-300">${row.current_price.toLocaleString()}</td>
                          <td className="px-4 py-3 font-bold text-emerald-300">{row.feature_score}</td>
                          <td className="px-4 py-3 text-slate-300">{row.momentum_score}</td>
                          <td className="px-4 py-3 text-slate-300">{row.rvol_score}</td>
                          <td className="px-4 py-3 text-slate-300">{row.spread_quality_score}</td>
                          <td className="px-4 py-3 text-slate-300">{row.trend_vs_vwap_score}</td>
                          <td className="px-4 py-3 text-slate-300">{row.volatility_score}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <div className="mb-3 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                  <h2 className="text-lg font-semibold text-emerald-500">XGBoost Ranker Output</h2>
                  <span className="w-fit rounded-full border border-cyan-500 bg-cyan-500/10 px-3 py-1 text-xs font-bold uppercase text-cyan-300">
                    {result.ranker_result.model_available ? "XGBoost available" : "Fallback ranker used"}
                  </span>
                </div>
                <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
                  {result.ranker_result.scores.map((score) => (
                    <article key={score.symbol} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                      <p className="text-xs uppercase tracking-wide text-slate-500">Rank #{score.rank}</p>
                      <h3 className="mt-1 text-3xl font-black text-white">{score.symbol}</h3>
                      <p className="mt-2 text-2xl font-black text-emerald-400">{score.score}</p>
                      <p className="mt-2 text-xs uppercase tracking-wide text-cyan-300">{score.model_used}</p>
                      <p className="mt-2 text-sm leading-relaxed text-slate-400">{score.explanation}</p>
                    </article>
                  ))}
                </div>
                <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                  {result.ranker_result.notes.map((note) => (
                    <p key={note} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">{note}</p>
                  ))}
                </div>
              </section>

              <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                <h2 className="mb-3 text-lg font-semibold text-emerald-500">Next Steps</h2>
                <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  {result.next_steps.map((step) => (
                    <p key={step} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">{step}</p>
                  ))}
                </div>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
