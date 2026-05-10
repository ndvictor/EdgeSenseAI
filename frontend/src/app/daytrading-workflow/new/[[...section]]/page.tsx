"use client";

import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

type OrchestratorHttpResponse = {
  status: string;
  recommendation: Record<string, unknown>;
  submitted_order: boolean;
  broker_called: boolean;
  llm_used: boolean;
  blockers: string[];
  warnings: string[];
  run: Record<string, unknown>;
};

type V1StatusBundle = {
  status: string;
  health: Record<string, unknown>;
  platform_readiness: Record<string, unknown>;
  final_readiness: Record<string, unknown>;
};

type SectionId =
  | "status-summary"
  | "scanner-candidate-feed"
  | "alpha-recommendation"
  | "evidence-promotion"
  | "risk-small-account"
  | "execution-boundary";

const NAV: Array<{ id: SectionId; label: string; href: string }> = [
  { id: "status-summary", label: "Status Summary", href: "/daytrading-workflow/new/status-summary" },
  { id: "scanner-candidate-feed", label: "Scanner / Candidate Feed", href: "/daytrading-workflow/new/scanner-candidate-feed" },
  { id: "alpha-recommendation", label: "Alpha Recommendation", href: "/daytrading-workflow/new/alpha-recommendation" },
  { id: "evidence-promotion", label: "Evidence & Promotion", href: "/daytrading-workflow/new/evidence-promotion" },
  { id: "risk-small-account", label: "Risk / Small Account", href: "/daytrading-workflow/new/risk-small-account" },
  { id: "execution-boundary", label: "Execution Boundary", href: "/daytrading-workflow/new/execution-boundary" },
];

function apiUrl(path: string): string {
  if (!API_BASE) throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  return `${API_BASE}${path}`;
}

async function dashGetJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path));
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`${path} ${res.status}${t ? `: ${t.slice(0, 200)}` : ""}`);
  }
  const text = await res.text();
  if (!text.trim()) throw new Error(`${path} returned empty body`);
  return JSON.parse(text) as T;
}

async function dashPostJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(apiUrl(path), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`${path} ${res.status}${t ? `: ${t.slice(0, 200)}` : ""}`);
  }
  const text = await res.text();
  if (!text.trim()) throw new Error(`${path} returned empty body`);
  return JSON.parse(text) as T;
}

function pick<T = unknown>(obj: unknown, path: string[]): T | undefined {
  let cur: unknown = obj;
  for (const key of path) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[key];
  }
  return cur as T;
}

function str(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "object") return JSON.stringify(v);
  return String(v);
}

function envelopeFromWorkflowLatest(workflowLatest: { run: Record<string, unknown> | null } | null): OrchestratorHttpResponse | null {
  const run = workflowLatest?.run;
  if (!run || typeof run !== "object") return null;
  const recRaw = run.recommendation;
  const rec = recRaw && typeof recRaw === "object" ? (recRaw as Record<string, unknown>) : {};
  return {
    status: String(run.status ?? ""),
    recommendation: rec,
    submitted_order: Boolean(run.submitted_order),
    broker_called: Boolean(run.broker_called),
    llm_used: Boolean(run.llm_used),
    blockers: Array.isArray(run.blockers) ? (run.blockers as string[]) : [],
    warnings: Array.isArray(run.warnings) ? (run.warnings as string[]) : [],
    run,
  };
}

function DataCard({
  title,
  endpoint,
  expected,
  children,
}: {
  title: string;
  endpoint: string;
  expected?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-white/10 bg-black/35 p-4 shadow-[0_16px_50px_rgba(0,0,0,0.28)] backdrop-blur-xl">
      <h3 className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</h3>
      <p className="mt-1 font-mono text-[10px] leading-4 text-cyan-300/80">{endpoint}</p>
      {expected ? <p className="mt-1 text-[10px] text-slate-500">Expected: {expected}</p> : null}
      <div className="mt-3 space-y-2 text-sm text-slate-200">{children}</div>
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-wrap gap-x-2 gap-y-1 border-b border-white/[0.06] py-1.5 last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className="min-w-0 flex-1 break-words font-medium text-slate-100">{value}</span>
    </div>
  );
}

function parseSymbols(input: string): string[] {
  return input
    .split(/[\s,]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export default function NewDayTradingWorkflowDashboard() {
  const params = useParams();
  const pathname = usePathname();
  const rawSeg = params?.section;
  const segments = Array.isArray(rawSeg) ? rawSeg : rawSeg ? [rawSeg] : [];
  const section: SectionId = (segments[0] as SectionId) || "status-summary";

  const [symbolsInput, setSymbolsInput] = useState("");
  const [statusBundle, setStatusBundle] = useState<V1StatusBundle | null>(null);
  const [workerLatest, setWorkerLatest] = useState<Record<string, unknown> | null>(null);
  const [scannerLatest, setScannerLatest] = useState<Record<string, unknown> | null>(null);
  const [promoStrategies, setPromoStrategies] = useState<Record<string, unknown> | null>(null);
  const [promoModels, setPromoModels] = useState<Record<string, unknown> | null>(null);
  const [workflowLatest, setWorkflowLatest] = useState<{ run: Record<string, unknown> | null } | null>(null);
  const [recommendationLatest, setRecommendationLatest] = useState<Record<string, unknown> | null>(null);
  const [riskStatus, setRiskStatus] = useState<Record<string, unknown> | null>(null);
  const [executionBoundary, setExecutionBoundary] = useState<Record<string, unknown> | null>(null);
  const [scannerResult, setScannerResult] = useState<Record<string, unknown> | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [scannerBusy, setScannerBusy] = useState(false);
  const [workflowBusy, setWorkflowBusy] = useState(false);
  const [actionMsg, setActionMsg] = useState<string | null>(null);

  const activeHref = useMemo(() => NAV.find((n) => n.id === section)?.href ?? NAV[0].href, [section]);

  const refreshGets = useCallback(async () => {
    setLoadError(null);
    setRefreshing(true);
    try {
      const [bundle, workers, scanner, ps, pm, wf, rec, risk, exec] = await Promise.all([
        dashGetJson<V1StatusBundle>("/api/v1/daytrading/status"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/workers/latest"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/scanner/latest"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/evidence/strategies"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/evidence/models"),
        dashGetJson<{ run: Record<string, unknown> | null }>("/api/v1/daytrading/workflow/latest"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/recommendation/latest"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/risk/status"),
        dashGetJson<Record<string, unknown>>("/api/v1/daytrading/execution-boundary"),
      ]);
      setStatusBundle(bundle);
      setWorkerLatest(workers);
      setScannerLatest(scanner);
      setPromoStrategies(ps);
      setPromoModels(pm);
      setWorkflowLatest(wf);
      setRecommendationLatest(rec);
      setRiskStatus(risk);
      setExecutionBoundary(exec);
    } catch (e) {
      setLoadError(e instanceof Error ? e.message : String(e));
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void refreshGets();
  }, [refreshGets]);

  const orch = useMemo(() => envelopeFromWorkflowLatest(workflowLatest), [workflowLatest]);
  const run = orch?.run;
  const rec = orch?.recommendation ?? {};
  const health = statusBundle?.health;
  const platform = statusBundle?.platform_readiness;
  const finalReadiness = statusBundle?.final_readiness;
  const systems = platform?.systems as Record<string, unknown> | undefined;
  const dataPipe = systems?.data_pipeline as Record<string, unknown> | undefined;
  const execGates =
    (executionBoundary?.execution_gates as Record<string, unknown> | undefined) ??
    (systems?.execution_gates as Record<string, unknown> | undefined);
  const smallAcctSys = systems?.small_account_feasibility as Record<string, unknown> | undefined;
  const fromLatestWf = executionBoundary?.from_latest_workflow as Record<string, unknown> | undefined;

  const scannerWorker = workerLatest?.scanner_worker as Record<string, unknown> | undefined;
  const ingestionWorker = workerLatest?.ingestion_worker as Record<string, unknown> | undefined;
  const featureWorker = workerLatest?.feature_worker as Record<string, unknown> | undefined;
  const scannerDx =
    (scannerResult?.scanner_diagnostics as Record<string, unknown> | undefined) ??
    (scannerLatest?.latest_scanner_diagnostics as Record<string, unknown> | undefined);

  const strategiesList = promoStrategies?.strategies as Array<Record<string, unknown>> | undefined;
  const modelsList = promoModels?.models as Array<Record<string, unknown>> | undefined;

  const riskRun = riskStatus?.run as Record<string, unknown> | undefined;
  const recRisk = riskStatus?.recommendation as Record<string, unknown> | undefined;

  const onRunScanner = async () => {
    setActionMsg(null);
    setScannerBusy(true);
    try {
      const symbols = parseSymbols(symbolsInput);
      const body = {
        strategy_key: "stock_day_trading",
        symbols,
        data_source: "auto",
        auto_run: false,
        trigger_type: "manual",
        trigger_workflow: false,
        max_candidates: 10,
      };
      const out = await dashPostJson<Record<string, unknown>>("/api/v1/daytrading/scanner/run", body);
      setScannerResult(out);
      setActionMsg("Scanner run completed.");
      await refreshGets();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setScannerBusy(false);
    }
  };

  const onRunWorkflow = async () => {
    setActionMsg(null);
    setWorkflowBusy(true);
    try {
      const symbols = parseSymbols(symbolsInput);
      const body = {
        dry_run: true,
        allow_submit: false,
        symbols,
        source: symbols.length ? "manual" : "runtime",
      };
      await dashPostJson<Record<string, unknown>>("/api/v1/daytrading/workflow/run", body);
      setActionMsg("Workflow run completed.");
      await refreshGets();
    } catch (e) {
      setActionMsg(e instanceof Error ? e.message : String(e));
    } finally {
      setWorkflowBusy(false);
    }
  };

  const usingNonReal = Boolean(run?.using_non_real_data);

  return (
    <div className="flex min-h-screen bg-[#03070b] text-slate-100">
      <aside className="flex w-72 shrink-0 flex-col border-r border-cyan-400/10 bg-[#05080d]/95 px-3 py-4">
        <div className="mb-4 px-1">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-400/70">Day Trading Workflow</div>
          <div className="mt-1 text-lg font-semibold text-cyan-100">Production UI</div>
          <p className="mt-1 text-[11px] leading-4 text-slate-500">Day Trading v1 API only (`/api/v1/daytrading/*`).</p>
        </div>
        <nav className="flex-1 space-y-1 overflow-y-auto">
          {NAV.map((item) => {
            const on = pathname === item.href || (item.id === "status-summary" && pathname === "/daytrading-workflow/new");
            return (
              <Link
                key={item.id}
                href={item.href}
                className={`block rounded-xl px-3 py-2 text-sm font-medium transition-colors ${
                  on ? "border border-cyan-400/35 bg-cyan-400/10 text-white" : "text-slate-300 hover:bg-white/[0.04] hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <main className="min-h-screen flex-1 overflow-auto">
        <div className="border-b border-cyan-400/10 bg-[#05080d]/80 px-6 py-4 backdrop-blur-xl">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <h1 className="text-xl font-bold text-white">Day-trading workflow (new)</h1>
              <p className="mt-1 text-xs text-slate-400">Section: {section}</p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <label className="flex min-w-[200px] flex-1 flex-col text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                Symbols (optional)
                <input
                  value={symbolsInput}
                  onChange={(e) => setSymbolsInput(e.target.value)}
                  className="mt-1 rounded-lg border border-cyan-400/20 bg-black/40 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400/50"
                  placeholder="TSLA, PLTR"
                />
              </label>
              <button
                type="button"
                disabled={scannerBusy}
                onClick={() => void onRunScanner()}
                className="rounded-lg border border-cyan-400/40 bg-cyan-500/15 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-500/25 disabled:opacity-50"
              >
                {scannerBusy ? "Running…" : "Run Scanner"}
              </button>
              <button
                type="button"
                disabled={workflowBusy}
                onClick={() => void onRunWorkflow()}
                className="rounded-lg border border-cyan-400/40 bg-cyan-500/15 px-4 py-2 text-sm font-semibold text-cyan-100 hover:bg-cyan-500/25 disabled:opacity-50"
              >
                {workflowBusy ? "Running…" : "Run Workflow"}
              </button>
              <button
                type="button"
                disabled={refreshing}
                onClick={() => void refreshGets()}
                className="rounded-lg border border-white/15 bg-white/[0.06] px-4 py-2 text-sm font-semibold text-slate-200 hover:border-cyan-400/30 disabled:opacity-50"
              >
                {refreshing ? "Refreshing…" : "Refresh"}
              </button>
            </div>
          </div>
          {loadError ? <p className="mt-3 text-sm text-amber-200">Refresh error: {loadError}</p> : null}
          {actionMsg ? <p className="mt-2 text-sm text-cyan-100">{actionMsg}</p> : null}
        </div>

        <div className="space-y-4 p-6">
          <section className="rounded-xl border border-cyan-400/20 bg-cyan-950/30 px-4 py-3 text-xs text-cyan-50">
            <span className="font-semibold">Safety display</span>
            <span className="mt-1 block text-cyan-100/90">
              broker_called=
              {str(orch?.broker_called ?? run?.broker_called ?? fromLatestWf?.broker_called ?? false)}, submitted_order=
              {str(orch?.submitted_order ?? run?.submitted_order ?? fromLatestWf?.submitted_order ?? false)}, llm_used=
              {str(orch?.llm_used ?? run?.llm_used ?? fromLatestWf?.llm_used ?? false)}, live_trading_enabled=
              {str(pick(execGates, ["live_trading_enabled"]) ?? false)}, mock_data_used=
              {str(usingNonReal)}, synthetic_data_used=
              {str(usingNonReal)}
            </span>
            <span className="mt-1 block text-[10px] text-slate-400">
              Bundle: GET /api/v1/daytrading/status (health) {health ? "ok" : "not loaded"}.
            </span>
          </section>

          {section === "status-summary" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <DataCard
                title="Workflow status"
                endpoint="GET /api/v1/daytrading/workflow/latest + POST /api/v1/daytrading/workflow/run"
                expected="status, run.status, run.workflow_run_id, run.orchestrator_run_id"
              >
                {!orch ? (
                  <p className="text-slate-500">Run workflow to populate. Safe empty: no run yet.</p>
                ) : (
                  <>
                    <Row label="status (top)" value={str(orch.status)} />
                    <Row label="run.status" value={str(run?.status)} />
                    <Row label="run.workflow_run_id" value={str(run?.workflow_run_id)} />
                    <Row label="run.orchestrator_run_id" value={str(run?.orchestrator_run_id)} />
                  </>
                )}
              </DataCard>
              <DataCard
                title="Recommendation status"
                endpoint="GET /api/v1/daytrading/recommendation/latest"
                expected="recommendation.status, recommendation.symbol, run.alpha_recommendation"
              >
                {!orch ? (
                  <p className="text-slate-500">No recommendation until workflow run.</p>
                ) : (
                  <>
                    <Row label="recommendation.status" value={str(rec.status)} />
                    <Row label="recommendation.symbol" value={str(rec.symbol)} />
                    <Row label="run.recommendation" value={str(run?.recommendation)} />
                    <Row label="run.alpha_recommendation" value={str(run?.alpha_recommendation)} />
                    <Row label="GET recommendation.latest.symbol" value={str(recommendationLatest?.selected_symbol)} />
                  </>
                )}
              </DataCard>
              <DataCard
                title="Provider"
                endpoint="GET /api/v1/daytrading/status → platform_readiness"
                expected="systems.data_pipeline.provider_name, provider_status, freshness_status"
              >
                <Row label="provider_name" value={str(dataPipe?.provider_name)} />
                <Row label="provider_status" value={str(dataPipe?.provider_status)} />
                <Row label="freshness_status" value={str(dataPipe?.freshness_status)} />
              </DataCard>
              <DataCard
                title="Candidate source"
                endpoint="GET /api/v1/daytrading/workflow/latest"
                expected="run.candidate_source, usable_symbols, symbols, selected_symbol"
              >
                {!orch ? (
                  <p className="text-slate-500">Run workflow for candidate fields.</p>
                ) : (
                  <>
                    <Row label="run.candidate_source" value={str(run?.candidate_source)} />
                    <Row label="run.usable_symbols" value={str(run?.usable_symbols)} />
                    <Row label="run.symbols" value={str(run?.symbols)} />
                    <Row label="run.selected_symbol" value={str(run?.selected_symbol)} />
                  </>
                )}
              </DataCard>
              <DataCard
                title="Safety flags"
                endpoint="GET /api/v1/daytrading/execution-boundary + workflow latest"
                expected="broker_called, submitted_order, llm_used, allow_submit, live_trading_enabled, broker_execution_enabled"
              >
                <Row label="broker_called" value={str(orch?.broker_called ?? run?.broker_called ?? fromLatestWf?.broker_called ?? false)} />
                <Row label="submitted_order" value={str(orch?.submitted_order ?? run?.submitted_order ?? fromLatestWf?.submitted_order ?? false)} />
                <Row label="llm_used" value={str(orch?.llm_used ?? run?.llm_used ?? fromLatestWf?.llm_used ?? false)} />
                <Row label="allow_submit" value={str(run?.allow_submit ?? fromLatestWf?.allow_submit ?? false)} />
                <Row label="live_trading_enabled" value={str(pick(execGates, ["live_trading_enabled"]) ?? "—")} />
                <Row label="broker_execution_enabled" value={str(pick(execGates, ["broker_execution_enabled"]) ?? "—")} />
              </DataCard>
            </div>
          ) : null}

          {section === "scanner-candidate-feed" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <DataCard title="Worker status" endpoint="GET /api/v1/daytrading/workers/latest" expected="scanner, ingestion, feature worker.status">
                <Row label="scanner_worker.status" value={str(scannerWorker?.status)} />
                <Row label="ingestion_worker.status" value={str(ingestionWorker?.status)} />
                <Row label="feature_worker.status" value={str(featureWorker?.status)} />
              </DataCard>
              <DataCard
                title="Provider diagnostics"
                endpoint="GET /api/v1/daytrading/workers/latest + GET /api/v1/daytrading/status"
                expected="counts, persistence_mode, provider"
              >
                <Row label="candidate_count" value={str(workerLatest?.candidate_count)} />
                <Row label="snapshot_count" value={str(workerLatest?.snapshot_count)} />
                <Row label="feature_row_count" value={str(workerLatest?.feature_row_count)} />
                <Row label="persistence_mode" value={str(workerLatest?.persistence_mode)} />
                <Row label="data_pipeline.provider_name" value={str(dataPipe?.provider_name)} />
                <Row label="data_pipeline.provider_status" value={str(dataPipe?.provider_status)} />
              </DataCard>
              <DataCard
                title="Rejection counts"
                endpoint="POST /api/v1/daytrading/scanner/run"
                expected="matched_signals, skipped_signals, workflow_trigger_status"
              >
                {!scannerResult && !scannerDx ? (
                  <p className="text-slate-500">Run scanner to populate. Safe empty: no scanner response yet.</p>
                ) : (
                  <>
                    <Row label="matched_signals.length" value={str(Array.isArray(scannerDx?.matched_signals) ? (scannerDx?.matched_signals as unknown[]).length : "—")} />
                    <Row label="skipped_signals.length" value={str(Array.isArray(scannerDx?.skipped_signals) ? (scannerDx?.skipped_signals as unknown[]).length : "—")} />
                    <Row label="workflow_trigger_status" value={str(scannerDx?.workflow_trigger_status ?? scannerResult?.workflow_trigger_status)} />
                    <Row label="next_action" value={str(scannerDx?.next_action)} />
                  </>
                )}
              </DataCard>
              <DataCard
                title="Candidates"
                endpoint="GET /api/v1/daytrading/workers/latest + POST /api/v1/daytrading/scanner/run"
                expected="scanner_candidates, matched_signals"
              >
                <Row label="scanner_worker.scanner_candidates" value={str(scannerWorker?.scanner_candidates)} />
                <Row label="matched_signals (last scanner)" value={str(scannerDx?.matched_signals)} />
                <Row label="symbols_scanned" value={str(scannerDx?.symbols_scanned)} />
              </DataCard>
            </div>
          ) : null}

          {section === "alpha-recommendation" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <DataCard title="Selected symbol" endpoint="GET /api/v1/daytrading/workflow/latest" expected="recommendation.symbol, run.selected_symbol">
                {!orch ? (
                  <p className="text-slate-500">no qualified setup / selected_symbol null until workflow.</p>
                ) : (
                  <>
                    <Row label="recommendation.symbol" value={str(rec.symbol)} />
                    <Row label="run.selected_symbol" value={str(run?.selected_symbol)} />
                    <Row label="run.alpha_selected_symbol" value={str(run?.alpha_selected_symbol)} />
                  </>
                )}
              </DataCard>
              <DataCard title="Strategy" endpoint="GET /api/v1/daytrading/workflow/latest" expected="strategy keys">
                {!orch ? (
                  <p className="text-slate-500">—</p>
                ) : (
                  <>
                    <Row label="recommendation.strategy_key" value={str(rec.strategy_key)} />
                    <Row label="run.strategy_key" value={str(run?.strategy_key)} />
                    <Row label="run.selected_strategy_key" value={str(run?.selected_strategy_key)} />
                    <Row label="run.alpha_strategy_key" value={str(run?.alpha_strategy_key)} />
                  </>
                )}
              </DataCard>
              <DataCard title="Final score" endpoint="GET /api/v1/daytrading/workflow/latest" expected="final_score / alpha_score">
                {!orch ? (
                  <p className="text-slate-500">—</p>
                ) : (
                  <>
                    <Row label="recommendation.final_score" value={str(rec.final_score)} />
                    <Row label="run.final_score" value={str(run?.final_score)} />
                    <Row label="run.alpha_score" value={str(run?.alpha_score)} />
                  </>
                )}
              </DataCard>
              <DataCard title="Expected return" endpoint="GET /api/v1/daytrading/workflow/latest" expected="expected_return fields">
                {!orch ? (
                  <p className="text-slate-500">—</p>
                ) : (
                  <>
                    <Row label="recommendation.expected_return" value={str(rec.expected_return)} />
                    <Row label="recommendation.expected_return_percent" value={str(rec.expected_return_percent)} />
                    <Row label="run.expected_return" value={str(run?.expected_return)} />
                  </>
                )}
              </DataCard>
              <DataCard title="Entry / stop / target" endpoint="GET /api/v1/daytrading/workflow/latest" expected="price_plan">
                {!orch ? (
                  <p className="text-slate-500">—</p>
                ) : (
                  <>
                    <Row label="recommendation.price_plan" value={str(rec.price_plan)} />
                    <Row label="price_plan.entry" value={str(pick(rec.price_plan as object, ["entry"]))} />
                    <Row label="price_plan.stop / stop_loss" value={str(pick(rec.price_plan as object, ["stop"]) ?? pick(rec.price_plan as object, ["stop_loss"]))} />
                    <Row label="price_plan.target / target_price" value={str(pick(rec.price_plan as object, ["target"]) ?? pick(rec.price_plan as object, ["target_price"]))} />
                  </>
                )}
              </DataCard>
              <DataCard title="Reason / blockers" endpoint="GET /api/v1/daytrading/workflow/latest" expected="reason, blockers, warnings">
                {!orch ? (
                  <p className="text-slate-500">blockers may include no_scanner_candidates_passed_filters when empty.</p>
                ) : (
                  <>
                    <Row label="recommendation.reason" value={str(rec.reason)} />
                    <Row label="recommendation.final_reason" value={str(rec.final_reason)} />
                    <Row label="run.blockers" value={str(run?.blockers)} />
                    <Row label="envelope blockers" value={str(orch.blockers)} />
                    <Row label="warnings" value={str(orch.warnings)} />
                  </>
                )}
              </DataCard>
            </div>
          ) : null}

          {section === "evidence-promotion" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <DataCard title="Backtest proof" endpoint="GET /api/v1/daytrading/evidence/strategies" expected="strategies[] metrics">
                {strategiesList?.length ? (
                  <pre className="max-h-64 overflow-auto rounded-lg bg-black/40 p-2 text-xs text-slate-300">
                    {JSON.stringify(
                      strategiesList.map((s) => ({
                        strategy_key: s.strategy_key,
                        sample_size: s.sample_size,
                        avg_r: s.avg_r,
                        profit_factor: s.profit_factor,
                        max_drawdown_r: s.max_drawdown_r,
                      })),
                      null,
                      2
                    )}
                  </pre>
                ) : (
                  <p className="text-slate-500">promotion_readiness=not_ready / empty strategies safe.</p>
                )}
              </DataCard>
              <DataCard title="Model evidence" endpoint="GET /api/v1/daytrading/evidence/models" expected="models[] metrics">
                {modelsList?.length ? (
                  <pre className="max-h-64 overflow-auto rounded-lg bg-black/40 p-2 text-xs text-slate-300">
                    {JSON.stringify(
                      modelsList.map((m) => ({
                        model_key: m.model_key,
                        sample_size: m.sample_size,
                        validation_score: m.validation_score,
                        calibration_status: m.calibration_status,
                        prediction_error_r: m.prediction_error_r,
                      })),
                      null,
                      2
                    )}
                  </pre>
                ) : (
                  <p className="text-slate-500">Safe empty: no models.</p>
                )}
              </DataCard>
              <DataCard title="Promotion status" endpoint="GET /api/v1/daytrading/evidence/*" expected="promotion_readiness">
                <Row label="strategies status" value={str(promoStrategies?.status)} />
                <Row label="models status" value={str(promoModels?.status)} />
                <Row
                  label="readiness sample"
                  value={str(strategiesList?.map((s) => `${String(s.strategy_key)}:${String(s.promotion_readiness)}`).join("; "))}
                />
              </DataCard>
              <DataCard
                title="Missing evidence"
                endpoint="GET /api/v1/daytrading/evidence/* + GET /api/v1/daytrading/status → final_readiness"
                expected="blockers, next_action, missing_backend_components"
              >
                <Row label="strategy blockers (first)" value={str(strategiesList?.[0]?.blockers)} />
                <Row label="model blockers (first)" value={str(modelsList?.[0]?.blockers)} />
                <Row label="final_readiness.next_action" value={str(finalReadiness?.next_action)} />
                <Row label="missing_backend_components" value={str(finalReadiness?.missing_backend_components)} />
              </DataCard>
            </div>
          ) : null}

          {section === "risk-small-account" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <DataCard title="Max risk dollars" endpoint="GET /api/v1/daytrading/risk/status" expected="run.max_risk_dollars, recommendation.risk_plan">
                {!riskStatus?.run && !orch ? (
                  <p className="text-slate-500">max_risk_dollars null until workflow.</p>
                ) : (
                  <>
                    <Row label="run.max_risk_dollars" value={str(riskRun?.max_risk_dollars ?? riskStatus?.max_risk_dollars ?? run?.max_risk_dollars)} />
                    <Row label="recommendation.risk_plan.max_dollar_risk" value={str(pick(recRisk?.risk_plan ?? rec.risk_plan, ["max_dollar_risk"]))} />
                  </>
                )}
              </DataCard>
              <DataCard title="Position size" endpoint="GET /api/v1/daytrading/risk/status" expected="position_size">
                {!riskStatus?.run && !orch ? (
                  <p className="text-slate-500">—</p>
                ) : (
                  <>
                    <Row label="run.position_size" value={str(riskRun?.position_size ?? riskStatus?.position_size ?? run?.position_size)} />
                    <Row label="recommendation.risk_plan.position_size_dollars" value={str(pick(recRisk?.risk_plan ?? rec.risk_plan, ["position_size_dollars"]))} />
                  </>
                )}
              </DataCard>
              <DataCard title="Feasibility" endpoint="GET /api/v1/daytrading/risk/status" expected="small_account_decision, feasible_symbols">
                {!riskStatus?.run && !orch ? (
                  <p className="text-slate-500">feasibility=no_candidate safe when no run.</p>
                ) : (
                  <>
                    <Row label="run.small_account_decision" value={str(riskRun?.small_account_decision ?? riskStatus?.small_account_decision ?? run?.small_account_decision)} />
                    <Row label="recommendation.risk_plan.account_fit" value={str(pick(recRisk?.risk_plan ?? rec.risk_plan, ["account_fit"]))} />
                    <Row label="run.feasible_symbols" value={str(riskRun?.feasible_symbols ?? run?.feasible_symbols)} />
                    <Row label="run.rejected_symbols" value={str(riskRun?.rejected_symbols ?? run?.rejected_symbols)} />
                  </>
                )}
              </DataCard>
              <DataCard title="Daily limits" endpoint="GET /api/v1/daytrading/risk/status + GET /api/v1/daytrading/status" expected="max_daily_loss, systems">
                {!orch ? (
                  <p className="text-slate-500">—</p>
                ) : (
                  <Row label="run.max_daily_loss_dollars" value={str(riskRun?.max_daily_loss_dollars ?? run?.max_daily_loss_dollars)} />
                )}
                <Row label="systems.small_account_feasibility" value={str(JSON.stringify(smallAcctSys))} />
                <Row label="systems.execution_gates (summary)" value={str(execGates ? JSON.stringify(execGates) : "—")} />
              </DataCard>
            </div>
          ) : null}

          {section === "execution-boundary" ? (
            <div className="grid gap-4 lg:grid-cols-2">
              <DataCard title="Paper trading status" endpoint="GET /api/v1/daytrading/execution-boundary" expected="execution_gates">
                <Row label="paper_trading_enabled" value={str(pick(execGates, ["paper_trading_enabled"]))} />
                <Row label="execution_enabled" value={str(pick(execGates, ["execution_enabled"]))} />
              </DataCard>
              <DataCard title="Approval required" endpoint="GET /api/v1/daytrading/execution-boundary" expected="require_human_approval, run.approval_required">
                <Row label="require_human_approval" value={str(pick(execGates, ["require_human_approval"]))} />
                <Row label="run.approval_required" value={str(run?.approval_required ?? fromLatestWf?.approval_required ?? "—")} />
              </DataCard>
              <DataCard title="Broker called" endpoint="GET /api/v1/daytrading/execution-boundary" expected="broker_called — expected false">
                <Row label="broker_called" value={str(orch?.broker_called ?? run?.broker_called ?? fromLatestWf?.broker_called ?? false)} />
                <Row label="Expected safe" value="false" />
              </DataCard>
              <DataCard title="Submitted order" endpoint="GET /api/v1/daytrading/execution-boundary" expected="submitted_order — expected false">
                <Row label="submitted_order" value={str(orch?.submitted_order ?? run?.submitted_order ?? fromLatestWf?.submitted_order ?? false)} />
                <Row label="Expected safe" value="false" />
              </DataCard>
              <DataCard title="Live trading status" endpoint="GET /api/v1/daytrading/execution-boundary" expected="live_trading, broker_execution">
                <Row label="live_trading_enabled" value={str(pick(execGates, ["live_trading_enabled"]))} />
                <Row label="broker_execution_enabled" value={str(pick(execGates, ["broker_execution_enabled"]))} />
                <Row label="Expected safe" value="live_trading_enabled false in paper-first contract" />
              </DataCard>
            </div>
          ) : null}

          <p className="text-center text-[10px] text-slate-600">
            Active route: {activeHref} · <span className="font-mono">/api/v1/daytrading/*</span> only · No legacy dashboard import
          </p>
        </div>
      </main>
    </div>
  );
}
