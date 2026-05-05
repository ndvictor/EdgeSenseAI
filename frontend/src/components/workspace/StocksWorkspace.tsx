"use client";

import { useEffect, useMemo, useState } from "react";
import { StockSearchChart, type StockChartSelection } from "@/components/StockSearchChart";
import { api, type CandidateUniverseEntry } from "@/lib/api";
import { Plus, Check, Loader2 } from "lucide-react";
import { wsInner, wsMetric, wsSection } from "@/components/workspace/styling";

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

export type StocksWorkspaceVariant = "stocks" | "etf";

export function StocksWorkspace({ variant = "stocks", hideChart = false }: { variant?: StocksWorkspaceVariant; hideChart?: boolean }) {
  const [selection, setSelection] = useState<StockChartSelection | null>(null);
  const [candidates, setCandidates] = useState<CandidateUniverseEntry[]>([]);
  const [isAdding, setIsAdding] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);
  const report = useMemo(() => calcReport(selection), [selection]);

  const assetClass = variant === "etf" ? "etf" : "stock";
  const headerEyebrow = variant === "etf" ? "etf data workspace" : "stocks data workspace";
  const headerTitle = variant === "etf" ? "ETFs" : "Stocks";
  const headerDescription =
    variant === "etf"
      ? "Search an ETF ticker, inspect source-backed data, and add liquid funds to the candidate universe. ETFs route like equities on Alpaca (share qty, regular session defaults)."
      : "Search a ticker, select a data source, and inspect a source-backed report. Prototype model/risk endpoints are preserved, but this report is driven by the selected source response.";

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
      const momentum = report.momentum;
      const priorityScore = momentum !== null ? Math.min(100, Math.max(0, 50 + momentum)) : 50;

      await api.addCandidate({
        symbol: selection.symbol,
        asset_class: assetClass,
        horizon: "swing",
        source_type: variant === "etf" ? "etf_search" : "stock_search",
        source_detail: variant === "etf" ? "Added from ETF workspace" : "Added from Stocks workspace",
        priority_score: priorityScore,
        notes: variant === "etf" ? "Manual ETF candidate" : "Manual candidate from Stocks workspace",
      });

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
    <div className="space-y-4">
      {hideChart ? null : (
        <StockSearchChart
          pageEyebrow={headerEyebrow}
          pageTitle={headerTitle}
          pageDescription={headerDescription}
          onSelectionChange={setSelection}
        />
      )}

      {report.error && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{report.error}</div>
      )}

      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-slate-500">
          {selection?.symbol ? (
            <>
              Selected ticker{" "}
              <span className="font-mono font-semibold text-slate-300">{selection.symbol}</span>
            </>
          ) : (
            hideChart
              ? "Load a ticker in the TradeNow chart to enable candidate actions."
              : "Select a ticker above to enable candidate actions."
          )}
        </p>
        {selection?.symbol ? (
          <button
            type="button"
            onClick={handleAddToCandidateUniverse}
            disabled={isAdding || isAlreadyCandidate}
            className={`flex shrink-0 items-center justify-center gap-1 rounded-full border px-3 py-1.5 text-xs font-bold uppercase transition-all ${
              isAlreadyCandidate
                ? "border-emerald-500 bg-emerald-500 text-slate-950"
                : addSuccess
                  ? "border-emerald-500 bg-emerald-500 text-slate-950"
                  : "border-emerald-500 bg-black/40 text-emerald-300 hover:bg-emerald-500 hover:text-slate-950"
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
                In universe
              </>
            ) : (
              <>
                <Plus className="h-3 w-3" />
                Add to candidate universe
              </>
            )}
          </button>
        ) : null}
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section className={wsSection}>
          <h2 className="mb-4 text-lg font-semibold text-emerald-300">Model pipeline</h2>
          <div className="space-y-3 text-sm text-slate-300">
            <p>
              Model status: <span className="font-bold text-white">{report.modelStatus.replace(/_/g, " ")}</span>
            </p>
            <p>
              Input source: <span className="font-bold text-white">{report.provider}</span>
            </p>
            <p>
              Mock guard:{" "}
              <span className={report.isMock ? "font-bold text-cyan-300" : "font-bold text-emerald-300"}>
                {report.isMock ? "explicit mock selected" : "no mock in report"}
              </span>
            </p>
            <p className="text-slate-400">The trained model should consume feature-store rows produced from this selected source, not static defaults.</p>
          </div>
        </section>

        <section className={wsSection}>
          <h2 className="mb-4 text-lg font-semibold text-emerald-300">Account + risk fit</h2>
          <div className="space-y-3 text-sm text-slate-300">
            <p>
              Risk status: <span className="font-bold text-white">{report.riskStatus.replace(/_/g, " ")}</span>
            </p>
            <p>
              Spread: <span className="font-bold text-white">{percent(report.spread)}</span>
            </p>
            <p>
              Actionability:{" "}
              <span className={report.hasUsableSourceData ? "font-bold text-amber-300" : "font-bold text-slate-400"}>
                {report.hasUsableSourceData ? "ready for model/risk validation" : "blocked until source data is usable"}
              </span>
            </p>
            <p className="text-slate-400">No buy/target/stop output should be shown until source, features, model, and risk checks pass.</p>
          </div>
        </section>
      </div>

      <section className={wsSection}>
        <h2 className="mb-3 text-lg font-semibold text-emerald-300">{variant === "etf" ? "ETF strategy lanes" : "Stock strategy lanes"}</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          {(
            variant === "etf"
              ? [
                  ["Core beta", "Broad market and sector ETFs: trend, relative strength vs benchmark, flows, and macro regime."],
                  ["Income / factor", "Dividend, quality, low-vol funds: yield sustainability, duration risk, and factor crowding."],
                  ["Thematic", "Thematic baskets: concentration, liquidity, roll yield (commodity), and NAV vs price dislocations."],
                ]
              : [
                  ["Day trade", "Needs intraday source data, RVOL, VWAP deviation, spread quality, short momentum, breakout/reversion alerts."],
                  ["Swing", "Needs daily source data, momentum, breakout confirmation, sector relative strength, sentiment, options confirmation."],
                  ["1 month", "Needs MA20/50 trend, relative strength, earnings revisions, macro regime, volatility forecast."],
                ]
          ).map(([title, body]) => (
            <div key={title} className={wsInner}>
              <h3 className="text-lg font-bold text-white">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function ReportMetric({ label, value, compact = false }: { label: string; value: string; compact?: boolean }) {
  return (
    <div className={wsMetric}>
      <p className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">{label}</p>
      <p className={`${compact ? "text-sm" : "text-2xl"} mt-2 font-black capitalize text-white`}>{value}</p>
    </div>
  );
}
