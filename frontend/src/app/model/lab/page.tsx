"use client";

import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import {
  api,
  type BlockedOrPlaceholderModel,
  type DataQualityReport,
  type FeatureStoreRow,
  type FeatureStoreRunResponse,
  type ModelLabRunRequest,
  type ModelLabRunResponse,
  type ModelOutput,
  type ModelRegistryResponse,
  type ModelRunPlanResponse,
  type ModelRunResponse,
  type NormalizedMarketSnapshot,
} from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

type PipelineAction = "quality" | "feature" | "plan" | "run" | "registry" | null;

const MODEL_LAB_SECTIONS = [
  { id: "model-lab-workflow", label: "Run Model Lab Workflow" },
  { id: "model-lab-data-quality", label: "Run Data Quality Check" },
  { id: "model-lab-feature-pipeline", label: "Run Feature Pipeline" },
  { id: "model-lab-model-run", label: "Run Model Run & Run Model Pipeline" },
] as const;

type ModelLabSectionId = (typeof MODEL_LAB_SECTIONS)[number]["id"];

function modelLabHashToSectionId(hash: string): ModelLabSectionId | null {
  const id = hash.replace(/^#/, "");
  return MODEL_LAB_SECTIONS.some((s) => s.id === id) ? (id as ModelLabSectionId) : null;
}

function statusClass(status?: string | null) {
  const value = (status || "unknown").toLowerCase();
  if (["pass", "completed", "available", "source_backed"].includes(value) || value.includes("configured")) {
    return "border-emerald-500 bg-emerald-500/10 text-emerald-300";
  }
  if (["warn", "demo", "placeholder", "placeholder_not_run", "not_trained", "not_available"].includes(value) || value.includes("missing")) {
    return "border-amber-500 bg-amber-500/10 text-amber-300";
  }
  if (["fail", "blocked", "error", "not_configured"].includes(value) || value.includes("unavailable")) {
    return "border-rose-500 bg-rose-500/10 text-rose-300";
  }
  return "border-slate-600 bg-slate-800 text-slate-300";
}

function Badge({ value }: { value?: string | null }) {
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusClass(value)}`}>{(value || "unknown").replace(/_/g, " ")}</span>;
}

function Panel({ title, children, className }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm ${className ?? ""}`}>
      <h2 className="mb-3 text-lg font-semibold text-emerald-500">{title}</h2>
      {children}
    </section>
  );
}

function SubBlock({ kicker, children }: { kicker: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-slate-800 pt-5 first:border-t-0 first:pt-0">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">{kicker}</h3>
      {children}
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-6 text-center text-sm text-slate-400">{message}</div>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{message}</div>;
}

function LoadingNote({ label }: { label: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-sm text-slate-300">{label}</div>;
}

function money(value?: number | null) {
  if (value === null || value === undefined) return "N/A";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function metricValue(value?: number | string | null) {
  if (value === null || value === undefined || value === "") return "N/A";
  return typeof value === "number" ? value.toLocaleString(undefined, { maximumFractionDigits: 4 }) : value;
}

function formatDate(value?: string | null) {
  if (!value) return "N/A";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function listText(items?: string[] | null) {
  return items && items.length ? items.join(", ") : "None";
}

function symbolList(symbols: string) {
  return symbols.split(",").map((symbol) => symbol.trim()).filter(Boolean);
}

function availableFeatureNames(row?: FeatureStoreRow | null) {
  if (!row) return [];
  return [
    ["technical_score", row.technical_score],
    ["momentum_score", row.momentum_score],
    ["volume_score", row.volume_score],
    ["rvol_score", row.rvol_score],
    ["options_score", row.options_score],
    ["sentiment_score", row.sentiment_score],
    ["volatility_score", row.volatility_score],
    ["macro_score", row.macro_score],
    ["regime_score", row.regime_score],
    ["liquidity_score", row.liquidity_score],
  ].filter(([, value]) => value !== null && value !== undefined).map(([name]) => name as string);
}

function outputName(output: ModelOutput | BlockedOrPlaceholderModel) {
  return output.model_name || output.model || "model";
}

function outputScore(output: ModelOutput | BlockedOrPlaceholderModel) {
  if ("prediction_score" in output && output.prediction_score !== undefined && output.prediction_score !== null) return `${Math.round(output.prediction_score * 100)}%`;
  if ("rank_score" in output && output.rank_score !== undefined && output.rank_score !== null) return `${Math.round(output.rank_score * 100)}%`;
  if ("score" in output && output.score !== undefined && output.score !== null) return metricValue(output.score);
  if ("probability_score" in output && output.probability_score !== undefined && output.probability_score !== null) return `${Math.round(output.probability_score * 100)}%`;
  if ("probability" in output && output.probability !== undefined && output.probability !== null) return `${Math.round(output.probability * 100)}%`;
  if ("prediction" in output && output.prediction !== undefined && output.prediction !== null) return String(output.prediction);
  if ("scores" in output && output.scores?.length) {
    const first = output.scores[0];
    return metricValue(typeof first.score === "number" || typeof first.score === "string" ? first.score : undefined);
  }
  return "N/A";
}

function nextAction(quality?: DataQualityReport | null, row?: FeatureStoreRow | null, plan?: ModelRunPlanResponse | null, run?: ModelRunResponse | null) {
  if (run?.next_action) return run.next_action;
  if (quality?.quality_status === "fail") return "Fix data source or provider before model run.";
  if (!row) return "Run feature-store pipeline first.";
  if (plan && !plan.models.some((model) => model.should_run)) return "Enable required model/data provider before treating outputs as actionable.";
  if ((run?.completed_models ?? run?.results ?? []).some((output) => ["weighted_ranker_v1", "weighted_ranker", "xgboost_ranker"].includes(outputName(output)))) return "Review risk filter before recommendation.";
  return "Run model plan or model pipeline after the feature row is available.";
}

function PipelineButton({ label, loading, disabled, onClick }: { label: string; loading: boolean; disabled?: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} disabled={loading || disabled} className="rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-3 text-sm font-bold text-emerald-300 disabled:cursor-not-allowed disabled:opacity-60">
      {loading ? "Working..." : label}
    </button>
  );
}

function DataQualityPanel({ report, loading }: { report: DataQualityReport | null; loading: boolean }) {
  if (loading) return <LoadingNote label="Running data quality check..." />;
  if (!report) return <EmptyState message="Run Data Quality Check to inspect provider, freshness, source, and tradability." />;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <Badge value={report.quality_status} />
        <Badge value={report.data_source} />
        <Badge value={report.freshness_status} />
      </div>
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Ticker" value={report.ticker} accent />
        <MetricCard label="Asset Class" value={report.asset_class} />
        <MetricCard label="Provider" value={report.provider ?? "none"} />
        <MetricCard label="Checked" value={formatDate(report.checked_at)} />
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <InfoList title="Missing Fields" items={report.missing_fields} />
        <InfoList title="Blockers" items={report.blockers} />
        <InfoList title="Warnings" items={report.warnings} />
      </div>
    </div>
  );
}

function InfoList({ title, items }: { title: string; items?: string[] }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      {items && items.length ? (
        <ul className="mt-2 space-y-2 text-sm leading-relaxed text-slate-300">
          {items.map((item) => <li key={item}>{item}</li>)}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-slate-400">None</p>
      )}
    </div>
  );
}

function NormalizedSnapshotPanel({ snapshot }: { snapshot?: NormalizedMarketSnapshot | null }) {
  if (!snapshot) return <EmptyState message="Run Feature Pipeline to generate normalized snapshot." />;
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <MetricCard label="Ticker" value={snapshot.ticker || snapshot.symbol || "N/A"} accent />
      <MetricCard label="Asset Class" value={snapshot.asset_class || "N/A"} />
      <MetricCard label="Price" value={money(snapshot.price ?? snapshot.current_price)} />
      <MetricCard label="Previous Close" value={money(snapshot.previous_close)} />
      <MetricCard label="Volume" value={metricValue(snapshot.volume)} />
      <MetricCard label="Spread" value={metricValue(snapshot.bid_ask_spread ?? snapshot.spread_percent)} />
      <MetricCard label="Timestamp" value={formatDate(snapshot.timestamp)} />
      <MetricCard label="Provider" value={snapshot.provider || snapshot.source || "N/A"} />
      <MetricCard label="Data Quality" value={snapshot.data_quality || "N/A"} />
    </div>
  );
}

function FeatureRowPanel({ row }: { row?: FeatureStoreRow | null }) {
  if (!row) return <EmptyState message="Run Feature Pipeline to create the latest feature row." />;
  const metrics = [
    ["Ticker", row.ticker],
    ["Horizon", row.horizon],
    ["Data Quality", row.data_quality],
    ["Technical", row.technical_score],
    ["Momentum", row.momentum_score],
    ["Volume", row.volume_score],
    ["RVOL", row.rvol_score],
    ["Options", row.options_score],
    ["Sentiment", row.sentiment_score],
    ["Volatility", row.volatility_score],
    ["Macro", row.macro_score],
    ["Regime", row.regime_score],
    ["Liquidity", row.liquidity_score],
    ["Confidence", row.confidence],
    ["Version", row.feature_version],
    ["Created", formatDate(row.created_at)],
  ];
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4 xl:grid-cols-8">
      {metrics.map(([label, value], index) => <MetricCard key={label} label={String(label)} value={metricValue(value)} accent={index === 0} />)}
    </div>
  );
}

function ModelPlanPanel({ plan, registry, row, quality, loading }: { plan: ModelRunPlanResponse | null; registry: ModelRegistryResponse | null; row?: FeatureStoreRow | null; quality?: DataQualityReport | null; loading: boolean }) {
  if (loading) return <LoadingNote label="Planning model run..." />;
  if (!plan) return <EmptyState message="Plan Model Run to see eligible and skipped models." />;
  const eligible = plan.models.filter((model) => model.should_run);
  const skipped = plan.models.filter((model) => !model.should_run);
  const required = registry?.models.flatMap((model) => model.should_run_when ?? []) ?? [];
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <MetricCard label="Selected Models" value={plan.models.length} accent />
        <MetricCard label="Eligible" value={eligible.length} />
        <MetricCard label="Skipped" value={skipped.length} />
        <MetricCard label="Feature Rows" value={plan.feature_rows_used ?? 0} />
        <MetricCard label="Data Quality" value={quality?.quality_status || row?.data_quality || "unknown"} />
      </div>
      <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
        <InfoList title="Required Features" items={[...new Set(required)].slice(0, 8)} />
        <InfoList title="Available Features" items={availableFeatureNames(row)} />
        <InfoList title="Plan Warnings" items={plan.warnings ?? []} />
      </div>
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
        <table className="w-full min-w-[900px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-emerald-600">
            <tr><th className="px-4 py-3">Model</th><th className="px-4 py-3">Eligibility</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Data Source</th><th className="px-4 py-3">Reason</th></tr>
          </thead>
          <tbody className="divide-y divide-slate-800">
            {plan.models.map((model) => (
              <tr key={model.key}>
                <td className="px-4 py-3 font-bold text-white">{model.key}</td>
                <td className="px-4 py-3"><Badge value={model.should_run ? "eligible" : "skipped"} /></td>
                <td className="px-4 py-3"><Badge value={model.status} /></td>
                <td className="px-4 py-3"><Badge value={model.data_source} /></td>
                <td className="max-w-xl px-4 py-3 text-slate-400">{model.reason}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ModelOutputsPanel({ run, loading }: { run: ModelRunResponse | null; loading: boolean }) {
  if (loading) return <LoadingNote label="Running model pipeline..." />;
  const outputs = (run?.completed_models?.length ? run.completed_models : run?.results ?? []).filter((output) => !["placeholder_not_run", "blocked", "missing_inputs", "not_configured", "not_trained", "not_available"].includes(output.status || ""));
  if (!outputs.length) return <EmptyState message="Run Model Pipeline to see model outputs." />;
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
      {outputs.map((output) => (
        <article key={`${outputName(output)}-${output.status}`} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-lg font-black text-white">{outputName(output)}</h3>
            <Badge value={output.status} />
          </div>
          <p className="mt-3 text-3xl font-black text-emerald-400">{outputScore(output)}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge value={output.data_source} />
            {"confidence" in output && output.confidence !== undefined && <Badge value={`confidence ${Math.round((output.confidence ?? 0) * 100)}%`} />}
          </div>
          {"scores" in output && output.scores?.length ? <p className="mt-3 text-sm text-slate-300">Scores returned: {output.scores.length}</p> : null}
          {"probability_score" in output && output.probability_score !== undefined && output.probability_score !== null ? <p className="mt-3 text-sm text-slate-300">Probability: {Math.round(output.probability_score * 100)}% · Confidence: {Math.round((output.confidence_score ?? 0) * 100)}%</p> : null}
          {"expected_return_score" in output && output.expected_return_score !== undefined && output.expected_return_score !== null ? <p className="mt-2 text-sm text-slate-400">Expected return estimate: {Math.round(output.expected_return_score * 10000) / 100}% ({output.expected_return_score_source || "estimate"})</p> : null}
          {"feature_contributions" in output && output.feature_contributions?.length ? <ContributionList contributions={output.feature_contributions} /> : null}
          {"result" in output && output.result ? <p className="mt-3 text-sm text-slate-400">Nested result returned from model service.</p> : null}
          {"warnings" in output && output.warnings?.length ? <InfoList title="Warnings" items={output.warnings} /> : null}
          {"notes" in output && output.notes?.length ? <InfoList title="Notes" items={output.notes} /> : null}
        </article>
      ))}
    </div>
  );
}

function ContributionList({ contributions }: { contributions: Array<Record<string, unknown>> }) {
  return (
    <div className="mt-3 rounded-lg border border-slate-800 bg-slate-950 p-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Feature Contributions</p>
      <div className="mt-2 space-y-2">
        {contributions.slice(0, 6).map((item, index) => (
          <div key={`${String(item.feature)}-${index}`} className="flex items-center justify-between gap-3 text-xs text-slate-300">
            <span>{String(item.feature || "feature").replace(/_/g, " ")}</span>
            <span className="font-mono text-emerald-300">{metricValue(typeof item.contribution === "number" ? item.contribution : String(item.contribution ?? "N/A"))}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function BlockedModelsPanel({ run, plan }: { run: ModelRunResponse | null; plan: ModelRunPlanResponse | null }) {
  const fromRun = [...(run?.not_trained_models ?? []), ...(run?.blocked_models ?? []), ...(run?.placeholder_models ?? [])];
  const fallbackFromRun = (run?.results ?? []).filter((output) => ["placeholder_not_run", "blocked", "missing_inputs", "not_configured", "not_trained", "not_available"].includes(output.status || ""));
  const fromPlan = (plan?.models ?? []).filter((model) => !model.should_run && model.status !== "available").map<BlockedOrPlaceholderModel>((model) => ({
    model: model.key,
    status: model.status === "placeholder" ? "placeholder_not_run" : model.status,
    reason: model.reason,
    needed_inputs: model.reason ? [model.reason] : [],
    next_step: "Wire the required data provider or production model before using this output.",
    data_source: model.data_source,
  }));
  const rows = fromRun.length ? fromRun : fallbackFromRun.length ? fallbackFromRun : fromPlan;
  if (!rows.length) return <EmptyState message="No blocked or placeholder models yet." />;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full min-w-[980px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr><th className="px-4 py-3">Model</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Reason</th><th className="px-4 py-3">Needed Inputs</th><th className="px-4 py-3">Next Step</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {rows.map((row) => (
            <tr key={`${outputName(row)}-${row.status}`}>
              <td className="px-4 py-3 font-bold text-white">{outputName(row)}</td>
              <td className="px-4 py-3"><Badge value={row.status} /></td>
              <td className="max-w-md px-4 py-3 text-slate-400">{row.reason || "Not enough inputs for this model."}</td>
              <td className="px-4 py-3 text-slate-300">{"needed_inputs" in row ? listText(row.needed_inputs) : "See reason"}</td>
              <td className="max-w-md px-4 py-3 text-slate-400">{"next_step" in row && row.next_step ? row.next_step : "Connect required data/model foundation first."}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function ModelLabPage() {
  const [dataSource, setDataSource] = useState<ModelLabRunRequest["data_source"]>("mock");
  const [model, setModel] = useState<ModelLabRunRequest["model"]>("xgboost_ranker");
  const [symbols, setSymbols] = useState("");
  const [trainSplit, setTrainSplit] = useState(70);
  const [assetClass, setAssetClass] = useState("stock");
  const [horizon, setHorizon] = useState("swing");
  const [result, setResult] = useState<ModelLabRunResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [pipelineError, setPipelineError] = useState<string | null>(null);
  const [pipelineAction, setPipelineAction] = useState<PipelineAction>(null);
  const [quality, setQuality] = useState<DataQualityReport | null>(null);
  const [featureRun, setFeatureRun] = useState<FeatureStoreRunResponse | null>(null);
  const [latestRows, setLatestRows] = useState<FeatureStoreRow[]>([]);
  const [registry, setRegistry] = useState<ModelRegistryResponse | null>(null);
  const [plan, setPlan] = useState<ModelRunPlanResponse | null>(null);
  const [modelRun, setModelRun] = useState<ModelRunResponse | null>(null);
  const [activeSectionId, setActiveSectionId] = useState<ModelLabSectionId>(MODEL_LAB_SECTIONS[0].id);
  const sectionNavRef = useRef<HTMLDivElement>(null);
  const sectionTabRefs = useRef<Partial<Record<ModelLabSectionId, HTMLAnchorElement>>>({});
  const [sectionIndicator, setSectionIndicator] = useState({ left: 0, width: 0 });

  const assignSectionTabRef = (id: ModelLabSectionId) => (node: HTMLAnchorElement | null) => {
    if (node) sectionTabRefs.current[id] = node;
    else delete sectionTabRefs.current[id];
  };

  const selectedSymbols = useMemo(() => symbolList(symbols), [symbols]);
  const pipelineSymbol = selectedSymbols[0] ?? null;
  const latestFeatureRow =
    featureRun?.row ??
    (pipelineSymbol ? latestRows.find((row) => row.ticker === pipelineSymbol.toUpperCase()) : undefined) ??
    latestRows[0] ??
    null;

  useEffect(() => {
    setPipelineAction("registry");
    Promise.all([api.getModelRunRegistry(), api.getLatestFeatureStoreRows()])
      .then(([registryResponse, rows]) => {
        setRegistry(registryResponse);
        setLatestRows(rows);
      })
      .catch((err) => setPipelineError(err instanceof Error ? err.message : "Pipeline metadata failed"))
      .finally(() => setPipelineAction(null));
  }, []);

  useEffect(() => {
    const syncFromHash = () => {
      const id = modelLabHashToSectionId(window.location.hash);
      if (id) setActiveSectionId(id);
    };
    syncFromHash();
    window.addEventListener("hashchange", syncFromHash);
    return () => window.removeEventListener("hashchange", syncFromHash);
  }, []);

  useLayoutEffect(() => {
    const updateIndicator = () => {
      const nav = sectionNavRef.current;
      const tab = sectionTabRefs.current[activeSectionId];
      if (!nav || !tab) return;
      const navRect = nav.getBoundingClientRect();
      const tabRect = tab.getBoundingClientRect();
      setSectionIndicator({
        left: tabRect.left - navRect.left + nav.scrollLeft,
        width: tabRect.width,
      });
    };
    updateIndicator();
    window.addEventListener("resize", updateIndicator);
    const ro = typeof ResizeObserver !== "undefined" ? new ResizeObserver(updateIndicator) : null;
    if (ro && sectionNavRef.current) ro.observe(sectionNavRef.current);
    return () => {
      window.removeEventListener("resize", updateIndicator);
      ro?.disconnect();
    };
  }, [activeSectionId]);

  async function runWorkflow() {
    setRunning(true);
    setError(null);
    try {
      const payload: ModelLabRunRequest = {
        data_source: dataSource,
        model,
        symbols: selectedSymbols,
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

  async function runDataQuality() {
    if (!pipelineSymbol) {
      setPipelineError("Enter at least one symbol in Symbols before running pipeline steps.");
      return;
    }
    setPipelineAction("quality");
    setPipelineError(null);
    try {
      setQuality(await api.getDataQuality(pipelineSymbol, assetClass, dataSource));
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : "Data quality check failed");
    } finally {
      setPipelineAction(null);
    }
  }

  async function runFeaturePipeline() {
    if (!pipelineSymbol) {
      setPipelineError("Enter at least one symbol in Symbols before running pipeline steps.");
      return;
    }
    setPipelineAction("feature");
    setPipelineError(null);
    try {
      const response = await api.runFeatureStore({ symbol: pipelineSymbol, asset_class: assetClass, horizon, source: dataSource });
      setFeatureRun(response);
      setQuality(response.quality_report);
      setLatestRows(await api.getFeatureStoreRowsBySymbol(pipelineSymbol));
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : "Feature pipeline failed");
    } finally {
      setPipelineAction(null);
    }
  }

  async function planModelRun() {
    if (!pipelineSymbol) {
      setPipelineError("Enter at least one symbol in Symbols before running pipeline steps.");
      return;
    }
    setPipelineAction("plan");
    setPipelineError(null);
    try {
      setPlan(await api.planModelRun({ symbols: [pipelineSymbol], asset_class: assetClass, horizon, source: dataSource, feature_rows: latestFeatureRow ? [latestFeatureRow] : null }));
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : "Model run plan failed");
    } finally {
      setPipelineAction(null);
    }
  }

  async function runModelPipeline() {
    if (!pipelineSymbol) {
      setPipelineError("Enter at least one symbol in Symbols before running pipeline steps.");
      return;
    }
    setPipelineAction("run");
    setPipelineError(null);
    try {
      const response = await api.runModelRun({ symbols: [pipelineSymbol], asset_class: assetClass, horizon, source: dataSource, feature_rows: latestFeatureRow ? [latestFeatureRow] : null });
      setModelRun(response);
      if (response.plan) setPlan(response.plan);
      if (response.feature_rows?.length) setLatestRows(response.feature_rows);
    } catch (err) {
      setPipelineError(err instanceof Error ? err.message : "Model pipeline failed");
    } finally {
      setPipelineAction(null);
    }
  }

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="model training workflow"
          title="Model Lab"
          description="Model Lab now combines experiment runs with pipeline visibility: data quality, normalization, feature-store rows, model planning, and paper/research model outputs."
        />

        <div ref={sectionNavRef} className="relative mb-4">
          <nav aria-label="Model Lab sections" className="flex flex-wrap gap-2 pb-3">
            {MODEL_LAB_SECTIONS.map((item) => {
              const selected = activeSectionId === item.id;
              return (
                <a
                  key={item.id}
                  ref={assignSectionTabRef(item.id)}
                  href={`#${item.id}`}
                  aria-current={selected ? "true" : undefined}
                  onClick={(event) => {
                    event.preventDefault();
                    setActiveSectionId(item.id);
                    window.history.replaceState(null, "", `#${item.id}`);
                  }}
                  className={`shrink-0 rounded-xl px-3 py-2 text-left text-sm font-semibold transition-colors duration-200 sm:px-4 ${
                    selected ? "text-emerald-300" : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
                  }`}
                >
                  {item.label}
                </a>
              );
            })}
          </nav>
          <div className="relative h-px w-full bg-slate-700/80">
            <div
              className="absolute -top-[2px] h-[3px] rounded-full bg-emerald-400 shadow-[0_0_16px_2px_rgba(52,211,153,0.65)] transition-[left,width] duration-300 ease-out"
              style={{ left: sectionIndicator.left, width: Math.max(sectionIndicator.width, 8) }}
            />
          </div>
        </div>

        <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm ring-1 ring-emerald-500/15 lg:p-6">
          <div className="space-y-6">
            {error ? (
              <div>
                <ErrorState message={error} />
              </div>
            ) : null}

            {pipelineError ? <div><ErrorState message={pipelineError} /></div> : null}
            {pipelineAction === "registry" ? <div><LoadingNote label="Loading model registry and latest feature rows..." /></div> : null}

            <div id={MODEL_LAB_SECTIONS[0].id} className="scroll-mt-6 space-y-6 border-b border-slate-700/80 pb-6">
              <h2 className="text-lg font-semibold text-emerald-500">{MODEL_LAB_SECTIONS[0].label}</h2>
              <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4">
                <h3 className="mb-4 text-sm font-semibold text-slate-200">Workflow controls</h3>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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

                  <label className="block">
                    <span className="text-sm font-semibold text-slate-300">Asset Class</span>
                    <select value={assetClass} onChange={(event) => setAssetClass(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white">
                      <option value="stock">Stock</option>
                      <option value="crypto">Crypto</option>
                      <option value="option">Option</option>
                    </select>
                  </label>

                  <label className="block">
                    <span className="text-sm font-semibold text-slate-300">Horizon</span>
                    <select value={horizon} onChange={(event) => setHorizon(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white">
                      <option value="intraday">Intraday</option>
                      <option value="day_trade">Day trade</option>
                      <option value="swing">Swing</option>
                      <option value="one_month">One month</option>
                    </select>
                  </label>

                  <label className="block sm:col-span-2 xl:col-span-3">
                    <span className="text-sm font-semibold text-slate-300">Symbols</span>
                    <input value={symbols} onChange={(event) => setSymbols(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" />
                  </label>

                  <label className="block">
                    <span className="text-sm font-semibold text-slate-300">Train Split</span>
                    <input type="number" min={50} max={90} value={trainSplit} onChange={(event) => setTrainSplit(Number(event.target.value))} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" />
                  </label>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 sm:gap-3">
                  <button type="button" onClick={runWorkflow} disabled={running} className="rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60">
                    {running ? "Running workflow..." : "Run Model Lab Workflow"}
                  </button>
                  <PipelineButton label="Run Data Quality Check" loading={pipelineAction === "quality"} disabled={!pipelineSymbol} onClick={runDataQuality} />
                  <PipelineButton label="Run Feature Pipeline" loading={pipelineAction === "feature"} disabled={!pipelineSymbol} onClick={runFeaturePipeline} />
                  <PipelineButton label="Plan Model Run" loading={pipelineAction === "plan"} disabled={!pipelineSymbol} onClick={planModelRun} />
                  <PipelineButton label="Run Model Pipeline" loading={pipelineAction === "run"} disabled={!pipelineSymbol} onClick={runModelPipeline} />
                </div>
                <p className="mt-3 text-sm text-slate-400">
                  Pipeline visibility runs one symbol at a time:{" "}
                  <span className="font-semibold text-emerald-300">{pipelineSymbol ?? "— (enter a symbol)"}</span>. Outputs are research/paper-only, not live trade instructions.
                </p>
              </div>

              <div className="grid grid-cols-1 gap-4 lg:grid-cols-2 lg:items-start">
                <Panel title="Next Action" className="h-fit min-w-0 p-4">
                  <p className="text-sm leading-relaxed text-slate-300">{nextAction(quality, latestFeatureRow, plan, modelRun)}</p>
                  <p className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-snug text-amber-200">
                    Research/paper-only: review data quality, model status, and risk filters before treating any output as actionable.
                  </p>
                </Panel>
                <div className="min-w-0">
                  {result ? (
                    <Panel title="Model Experiment Results" className="min-w-0">
                      <div className="space-y-0">
                        <SubBlock kicker="Run summary">
                          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
                            <MetricCard label="Status" value={result.workflow_status} accent />
                            <MetricCard label="Data Source" value={result.data_source} />
                            <MetricCard label="Model" value={result.model} />
                            <MetricCard label="Train Rows" value={result.split.train_rows} />
                            <MetricCard label="Test Rows" value={result.split.test_rows} />
                          </div>
                        </SubBlock>

                        <SubBlock kicker="Feature-agent output">
                          <div className="overflow-x-auto rounded-lg border border-slate-800">
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
                        </SubBlock>

                        <SubBlock kicker="Ranker output">
                          <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                            <span className="w-fit rounded-full border border-cyan-500 bg-cyan-500/10 px-3 py-1 text-xs font-bold uppercase text-cyan-300">
                              {result.ranker_result.model_available ? "XGBoost available" : "Fallback ranker used"}
                            </span>
                          </div>
                          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 2xl:grid-cols-3">
                            {result.ranker_result.scores.map((score) => (
                              <article key={score.symbol} className="rounded-lg border border-slate-800 bg-slate-900/80 p-3">
                                <p className="text-xs uppercase tracking-wide text-slate-500">Rank #{score.rank}</p>
                                <h4 className="mt-1 text-xl font-bold text-white">{score.symbol}</h4>
                                <p className="mt-2 text-lg font-bold text-emerald-400">{score.score}</p>
                                <p className="mt-1 text-xs uppercase tracking-wide text-cyan-300">{score.model_used}</p>
                                <p className="mt-2 text-sm leading-relaxed text-slate-400">{score.explanation}</p>
                              </article>
                            ))}
                          </div>
                          <div className="mt-4 space-y-2">
                            {result.ranker_result.notes.map((note) => (
                              <p key={note} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm leading-relaxed text-slate-300">{note}</p>
                            ))}
                          </div>
                        </SubBlock>

                        <SubBlock kicker="Next steps">
                          <ul className="space-y-2">
                            {result.next_steps.map((step) => (
                              <li key={step} className="rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2 text-sm leading-relaxed text-slate-300">{step}</li>
                            ))}
                          </ul>
                        </SubBlock>
                      </div>
                    </Panel>
                  ) : (
                    <Panel title="Model Experiment Results">
                      <EmptyState message="Run Model Lab Workflow to view existing XGBoost or weighted ranker experiment results." />
                    </Panel>
                  )}
                </div>
              </div>
            </div>

            <div id={MODEL_LAB_SECTIONS[1].id} className="scroll-mt-6 space-y-4 border-b border-slate-700/80 pb-6">
              <h2 className="text-lg font-semibold text-emerald-500">{MODEL_LAB_SECTIONS[1].label}</h2>
              <div className="space-y-4">
                <Panel title="Data Quality Result"><DataQualityPanel report={quality} loading={pipelineAction === "quality"} /></Panel>
                <Panel title="Normalized Snapshot"><NormalizedSnapshotPanel snapshot={featureRun?.normalized_snapshot} /></Panel>
              </div>
            </div>

            <div id={MODEL_LAB_SECTIONS[2].id} className="scroll-mt-6 space-y-4 border-b border-slate-700/80 pb-6">
              <h2 className="text-lg font-semibold text-emerald-500">{MODEL_LAB_SECTIONS[2].label}</h2>
              <Panel title="Pipeline Visibility">
                <p className="mb-4 text-sm leading-relaxed text-slate-400">
                  Full-width view of the most recent feature-store row for the pipeline symbol. Use the table below for a quick scan of every field.
                </p>
                <FeatureRowPanel row={latestFeatureRow} />
              </Panel>
            </div>

            <div id={MODEL_LAB_SECTIONS[3].id} className="scroll-mt-6 space-y-4">
              <h2 className="text-lg font-semibold text-emerald-500">{MODEL_LAB_SECTIONS[3].label}</h2>
              <Panel title="Model Run Plan"><ModelPlanPanel plan={plan} registry={registry} row={latestFeatureRow} quality={quality} loading={pipelineAction === "plan"} /></Panel>
              <Panel title="Model Outputs"><ModelOutputsPanel run={modelRun} loading={pipelineAction === "run"} /></Panel>
              <Panel title="Blocked / Placeholder Models"><BlockedModelsPanel run={modelRun} plan={plan} /></Panel>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
