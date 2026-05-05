"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader } from "@/components/Cards";
import { StockSearchChart, type StockChartSelection } from "@/components/StockSearchChart";
import { api, type CandidateUniverseEntry } from "@/lib/api";
import { Plus, Check, Loader2 } from "lucide-react";

function money(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function percent(value?: number | null) {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toFixed(2)}%`;
}

function number(value?: number | null, suffix = "") {
  if (value === undefined || value === null || Number.isNaN(value)) return "—";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

function calcReport(selection: StockChartSelection | null) {
  const snapshot = selection?.snapshot;
  const history = selection?.history;
  const closes = history?.data.map((row) => row.close).filter((value): value is number => value !== null) ?? [];
  const volumes = history?.data.map((row) => row.volume).filter((value): value is number => value !== null) ?? [];
  const lastClose = closes.at(-1) ?? snapshot?.price ?? null;
  const firstClose = closes.at(0) ?? null;
  const prevClose = closes.length > 1 ? closes.at(-2) ?? null : snapshot?.previous_close ?? null;
  const momentum = firstClose && lastClose ? ((lastClose - firstClose) / firstClose) * 100 : null;
  const oneDayChange = prevClose && lastClose ? ((lastClose - prevClose) / prevClose) * 100 : snapshot?.change_percent ?? null;
  const avgVolume = volumes.length ? volumes.reduce((sum, value) => sum + value, 0) / volumes.length : snapshot?.average_volume ?? null;
  const latestVolume = volumes.at(-1) ?? snapshot?.volume ?? null;
  const rvol = avgVolume && latestVolume ? latestVolume / avgVolume : null;
  const spread = snapshot?.bid_ask_spread ?? null;
  const sourceQuality = snapshot?.data_quality ?? history?.data_quality ?? "not_loaded";
  const provider = snapshot?.provider ?? history?.provider ?? "—";
  const isMock = Boolean(snapshot?.is_mock || history?.is_mock);
  const hasUsableSourceData = Boolean(snapshot?.price && !isMock && sourceQuality === "real");

  let featureStatus = "waiting_for_source_data";
  if (isMock) featureStatus = "mock_selected_for_testing";
  else if (hasUsableSourceData) featureStatus = "source_data_ready";
  else if (selection) featureStatus = "source_unavailable";

  let modelStatus = "not_run";
  if (hasUsableSourceData) modelStatus = "ready_for_feature_agents_and_model_run";
  if (isMock) modelStatus = "disabled_for_mock_data";

  let riskStatus = "not_evaluated";
  if (hasUsableSourceData && spread !== null) riskStatus = spread <= 0.2 ? "spread_quality_pass" : "spread_review_needed";
  if (isMock) riskStatus = "disabled_for_mock_data";

  return {
    symbol: selection?.symbol ?? "Select a ticker",
    source: selection?.source ?? "auto",
    provider,
    sourceQuality,
    isMock,
    hasUsableSourceData,
    currentPrice: snapshot?.price ?? lastClose,
    dayChange: oneDayChange,
    rvol,
    spread,
    momentum,
    latestVolume,
    avgVolume,
    featureStatus,
    modelStatus,
    riskStatus,
    error: snapshot?.error || history?.error || null,
  };
}

export default function StocksPage() {
  const [selection, setSelection] = useState<StockChartSelection | null>(null);
  const [candidates, setCandidates] = useState<CandidateUniverseEntry[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);
  const report = useMemo(() => calcReport(selection), [selection]);

  // Load existing candidates on mount
  useEffect(() => {
    api.getCandidateUniverse()
      .then((response) => setCandidates(response.candidates))
      .catch(() => setCandidates([]));
  }, []);

  const isAlreadyCandidate = useMemo(() => {
    if (!selection?.symbol) return false;
    return candidates.some((c) => c.symbol === selection.symbol.toUpperCase() && c.status === "active");
  }, [candidates, selection]);

  const handleAddToCandidateUniverse = async () => {
    if (!selection?.symbol) return;

    setIsAdding(true);
    setAddSuccess(false);

    try {
      // Derive priority score from momentum if available, else default 50
      const momentum = report.momentum;
      const priorityScore = momentum !== null ? Math.min(100, Math.max(0, 50 + momentum)) : 50;

      await api.addCandidate({
        symbol: selection.symbol,
        asset_class: "stock",
        horizon: "swing",
        source_type: "stock_search",
        source_detail: "Added from Stocks page",
        priority_score: priorityScore,
        notes: "Manual candidate from Stocks workspace",
      });

      // Refresh candidates list
      const response = await api.getCandidateUniverse();
      setCandidates(response.candidates);
      setAddSuccess(true);
      setTimeout(() => setAddSuccess(false), 2000);
    } catch (err) {
      console.error("Failed to add candidate:", err);
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="stocks data workspace"
          title="Stocks"
          description="Search a ticker, select a data source, and inspect a source-backed report. Prototype model/risk endpoints are preserved, but this report is driven by the selected source response."
        />

        <div className="space-y-4">
          <StockSearchChart onSelectionChange={setSelection} />

          <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
            <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-500">Source-backed stock report</p>
                <h2 className="mt-1 text-xl font-black text-white">Current Workflow Candidate: {report.symbol}</h2>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase">
                <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-slate-300">Source: {report.source}</span>
                <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-slate-300">Provider: {report.provider}</span>
                <span className={`rounded-full border px-3 py-1 ${report.hasUsableSourceData ? "border-emerald-500 bg-emerald-500/10 text-emerald-300" : report.isMock ? "border-cyan-500 bg-cyan-500/10 text-cyan-300" : "border-amber-500 bg-amber-500/10 text-amber-300"}`}>Quality: {report.sourceQuality}</span>

                {/* Add to Candidate Universe Button */}
                {selection?.symbol && (
                  <button
                    onClick={handleAddToCandidateUniverse}
                    disabled={isAdding || isAlreadyCandidate}
                    className={`flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-bold uppercase transition-all ${
                      isAlreadyCandidate
                        ? "border-emerald-500 bg-emerald-500 text-slate-950"
                        : addSuccess
                          ? "border-emerald-500 bg-emerald-500 text-slate-950"
                          : "border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
                    }`}
                  >
                    {isAdding ? (
                      <>
                        <Loader2 className="h-3 w-3 animate-spin" />
                        Adding...
                      </>
                    ) : addSuccess ? (
                      <>
                        <Check className="h-3 w-3" />
                        Added!
                      </>
                    ) : isAlreadyCandidate ? (
                      <>
                        <Check className="h-3 w-3" />
                        In Universe
                      </>
                    ) : (
                      <>
                        <Plus className="h-3 w-3" />
                        Add to Candidate Universe
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>

            {report.error && (
              <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">
                {report.error}
              </div>
            )}

            <div className="mt-4 grid grid-cols-2 gap-4 lg:grid-cols-4">
              <ReportMetric label="Current Price" value={money(report.currentPrice)} />
              <ReportMetric label="Day Change" value={percent(report.dayChange)} />
              <ReportMetric label="RVOL" value={number(report.rvol, "x")} />
              <ReportMetric label="Spread" value={percent(report.spread)} />
            </div>
          </section>

          <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-emerald-500">Feature Pipeline</h2>
              <div className="grid grid-cols-2 gap-3">
                <ReportMetric label="Momentum" value={percent(report.momentum)} />
                <ReportMetric label="Latest Volume" value={number(report.latestVolume)} />
                <ReportMetric label="Avg Volume" value={number(report.avgVolume)} />
                <ReportMetric label="Feature Status" value={report.featureStatus.replace(/_/g, " ")} compact />
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-emerald-500">Model Pipeline</h2>
              <div className="space-y-3 text-sm text-slate-300">
                <p>Model status: <span className="font-bold text-white">{report.modelStatus.replace(/_/g, " ")}</span></p>
                <p>Input source: <span className="font-bold text-white">{report.provider}</span></p>
                <p>Mock guard: <span className={report.isMock ? "font-bold text-cyan-300" : "font-bold text-emerald-300"}>{report.isMock ? "explicit mock selected" : "no mock in report"}</span></p>
                <p className="text-slate-400">The trained model should consume feature-store rows produced from this selected source, not static defaults.</p>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-4 text-lg font-semibold text-emerald-500">Account + Risk Fit</h2>
              <div className="space-y-3 text-sm text-slate-300">
                <p>Risk status: <span className="font-bold text-white">{report.riskStatus.replace(/_/g, " ")}</span></p>
                <p>Spread: <span className="font-bold text-white">{percent(report.spread)}</span></p>
                <p>Actionability: <span className={report.hasUsableSourceData ? "font-bold text-amber-300" : "font-bold text-slate-400"}>{report.hasUsableSourceData ? "ready for model/risk validation" : "blocked until source data is usable"}</span></p>
                <p className="text-slate-400">No buy/target/stop output should be shown until source, features, model, and risk checks pass.</p>
              </div>
            </section>
          </div>

          <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-emerald-500">Stock Strategy Lanes</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {[
                ["Day Trade", "Needs intraday source data, RVOL, VWAP deviation, spread quality, short momentum, breakout/reversion alerts."],
                ["Swing", "Needs daily source data, momentum, breakout confirmation, sector relative strength, sentiment, options confirmation."],
                ["1 Month", "Needs MA20/50 trend, relative strength, earnings revisions, macro regime, volatility forecast."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <h3 className="text-lg font-bold text-white">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}

function ReportMetric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-500">{label}</p>
      <p className={`${compact ? "text-sm" : "text-2xl"} mt-2 font-black text-white capitalize`}>{value}</p>
    </div>
  );
}
