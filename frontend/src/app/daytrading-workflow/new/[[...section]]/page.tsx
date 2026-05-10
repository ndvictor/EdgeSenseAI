"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";

type FetchState = {
  data: unknown;
  error: string | null;
  loading: boolean;
};

type SectionId =
  | "status-summary"
  | "scanner-candidate-feed"
  | "alpha-recommendation"
  | "evidence-promotion"
  | "risk-small-account"
  | "execution-boundary";

type WorkflowResponse = Record<string, unknown>;

type ScannerResponse = Record<string, unknown>;

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

const SECTIONS: Array<{
  id: SectionId;
  label: string;
  eyebrow: string;
  description: string;
  cards: string[];
}> = [
  {
    id: "status-summary",
    label: "Status Summary",
    eyebrow: "Overview",
    description: "Production workflow state, provider status, candidate source, and safety flags.",
    cards: ["Workflow status", "Recommendation status", "Provider", "Candidate source", "Safety flags"],
  },
  {
    id: "scanner-candidate-feed",
    label: "Scanner / Candidate Feed",
    eyebrow: "Input Feed",
    description: "Latest scanner and worker output. This must be the only production candidate source.",
    cards: ["Worker status", "Provider diagnostics", "Rejection counts", "Candidates"],
  },
  {
    id: "alpha-recommendation",
    label: "Alpha Recommendation",
    eyebrow: "Decision",
    description: "Alpha result from the orchestrator. Empty is safe when no scanner candidate qualifies.",
    cards: ["Selected symbol", "Strategy", "Final score", "Expected return", "Entry / stop / target", "Reason / blockers"],
  },
  {
    id: "evidence-promotion",
    label: "Evidence & Promotion",
    eyebrow: "Proof",
    description: "Read-only strategy/model readiness. No automatic activation and no broker action.",
    cards: ["Backtest proof", "Model evidence", "Promotion status", "Missing evidence"],
  },
  {
    id: "risk-small-account",
    label: "Risk / Small Account",
    eyebrow: "Sizing",
    description: "Small-account feasibility, risk limits, and blockers from the workflow run.",
    cards: ["Max risk dollars", "Position size", "Feasibility", "Daily limits"],
  },
  {
    id: "execution-boundary",
    label: "Execution Boundary",
    eyebrow: "Safety",
    description: "Paper/live/broker flags. This page should show broker_called=false and submitted_order=false by default.",
    cards: ["Paper trading status", "Approval required", "Broker called", "Submitted order", "Live trading status"],
  },
];

const ENDPOINT_CONTRACTS = [
  { method: "GET", path: "/health", purpose: "Backend health" },
  { method: "GET", path: "/api/platform-readiness/status", purpose: "Platform/provider readiness" },
  { method: "GET", path: "/api/final-readiness/status", purpose: "Final production readiness" },
  { method: "POST", path: "/api/workflow-orchestrator/run", purpose: "Run Alpha workflow" },
  { method: "GET", path: "/api/worker-status/latest", purpose: "Latest scanner/ingestion/feature worker state" },
  { method: "POST", path: "/api/scanner/run", purpose: "Manual real-provider scanner run" },
  { method: "GET", path: "/api/promotion/strategies/status", purpose: "Strategy promotion readiness" },
  { method: "GET", path: "/api/promotion/models/status", purpose: "Model promotion readiness" },
];

function apiUrl(path: string): string {
  if (!API_BASE_URL) throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  return `${API_BASE_URL}${path}`;
}

async function request(path: string, options?: RequestInit): Promise<unknown> {
  const response = await fetch(apiUrl(path), {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  });
  const text = await response.text();
  let body: unknown = null;
  if (text.trim()) {
    try {
      body = JSON.parse(text);
    } catch {
      body = { raw: text };
    }
  }
  if (!response.ok) {
    const detail = body && typeof body === "object" ? JSON.stringify(body) : text;
    throw new Error(`${path} failed with ${response.status}: ${detail}`);
  }
  return body;
}

async function safeLoad(fn: () => Promise<unknown>): Promise<FetchState> {
  try {
    return { data: await fn(), error: null, loading: false };
  } catch (error) {
    return { data: null, error: error instanceof Error ? error.message : String(error), loading: false };
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.length ? value.map((v) => text(v)).join(", ") : fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function firstDefined(...values: unknown[]): unknown {
  return values.find((value) => value !== undefined && value !== null && value !== "");
}

function nested(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) current = asRecord(current)[key];
  return current;
}

function runObject(workflow: unknown): Record<string, unknown> {
  const root = asRecord(workflow);
  return asRecord(root.run ?? root);
}

function recommendationObject(workflow: unknown): Record<string, unknown> {
  const root = asRecord(workflow);
  const run = runObject(workflow);
  return asRecord(root.recommendation ?? run.recommendation ?? run.alpha_recommendation);
}

function workerSummary(worker: unknown): Record<string, unknown> {
  return asRecord(worker);
}

function toneClass(value: unknown): string {
  const s = text(value, "").toLowerCase();
  if (s.includes("fail") || s.includes("block") || s.includes("disabled") || s.includes("error")) return "border-rose-400/35 bg-rose-500/10 text-rose-100";
  if (s.includes("warn") || s.includes("partial") || s.includes("not_configured") || s.includes("missing")) return "border-amber-400/35 bg-amber-500/10 text-amber-100";
  if (s.includes("pass") || s.includes("ready") || s.includes("ok") || s.includes("safe") || s.includes("false")) return "border-emerald-400/35 bg-emerald-500/10 text-emerald-100";
  return "border-slate-500/35 bg-slate-500/10 text-slate-200";
}

function Badge({ children, tone }: { children: React.ReactNode; tone?: unknown }) {
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.16em] ${toneClass(tone ?? children)}`}>{children}</span>;
}

function Card({ title, endpoint, children }: { title: string; endpoint: string; children: React.ReactNode }) {
  return (
    <section className="rounded-3xl border border-emerald-400/15 bg-[#071016]/75 p-4 shadow-[0_20px_80px_rgba(0,0,0,0.35)] backdrop-blur-xl">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-bold text-white">{title}</h3>
          <p className="mt-1 font-mono text-[11px] text-emerald-300/65">{endpoint}</p>
        </div>
      </div>
      {children}
    </section>
  );
}

function Metric({ label, value, tone }: { label: string; value: unknown; tone?: unknown }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-black/25 p-3">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className="mt-1 break-words text-sm font-semibold text-slate-100">{text(value)}</div>
      {tone !== undefined ? <div className="mt-2"><Badge tone={tone}>{text(tone)}</Badge></div> : null}
    </div>
  );
}

function ErrorBox({ error }: { error: string | null }) {
  if (!error) return null;
  return <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 p-3 text-sm text-amber-100">{error}</div>;
}

function JsonPreview({ value }: { value: unknown }) {
  return (
    <details className="mt-3 rounded-2xl border border-white/10 bg-black/30 p-3">
      <summary className="cursor-pointer text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">Raw response</summary>
      <pre className="mt-3 max-h-72 overflow-auto whitespace-pre-wrap text-xs leading-5 text-slate-300">{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

function StatusSummary({ workflow, platform, finalReady, health }: { workflow: FetchState; platform: FetchState; finalReady: FetchState; health: FetchState }) {
  const run = runObject(workflow.data);
  const rec = recommendationObject(workflow.data);
  const platformSystems = asRecord(nested(platform.data, ["systems"]));
  const dataPipeline = asRecord(platformSystems.data_pipeline);
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Workflow status" endpoint="POST /api/workflow-orchestrator/run">
        <ErrorBox error={workflow.error} />
        <div className="grid gap-3 md:grid-cols-2">
          <Metric label="Status" value={firstDefined(asRecord(workflow.data).status, run.status, "not_run")} tone={firstDefined(asRecord(workflow.data).status, run.status, "not_run")} />
          <Metric label="Workflow run id" value={firstDefined(run.workflow_run_id, run.orchestrator_run_id)} />
        </div>
      </Card>
      <Card title="Recommendation status" endpoint="POST /api/workflow-orchestrator/run">
        <div className="grid gap-3 md:grid-cols-2">
          <Metric label="Recommendation" value={firstDefined(rec.status, run.recommendation_status, "not_run")} tone={firstDefined(rec.status, run.recommendation_status, "not_run")} />
          <Metric label="Selected symbol" value={firstDefined(rec.symbol, run.selected_symbol, null)} />
        </div>
      </Card>
      <Card title="Provider" endpoint="GET /api/platform-readiness/status">
        <ErrorBox error={platform.error} />
        <div className="grid gap-3 md:grid-cols-2">
          <Metric label="Provider" value={firstDefined(dataPipeline.provider_name, platformSystems.provider_name)} />
          <Metric label="Provider status" value={firstDefined(dataPipeline.provider_status, asRecord(platform.data).status)} tone={firstDefined(dataPipeline.provider_status, asRecord(platform.data).status)} />
        </div>
      </Card>
      <Card title="Candidate source" endpoint="POST /api/workflow-orchestrator/run">
        <div className="grid gap-3 md:grid-cols-2">
          <Metric label="Candidate source" value={firstDefined(run.candidate_source, nested(run, ["watchlist", "candidate_source"]), "none")} />
          <Metric label="Usable symbols" value={firstDefined(run.usable_symbols, run.symbols, [])} />
        </div>
      </Card>
      <Card title="Safety flags" endpoint="POST /api/workflow-orchestrator/run + /health + readiness">
        <ErrorBox error={health.error || finalReady.error} />
        <div className="grid gap-3 md:grid-cols-4">
          <Metric label="Broker called" value={firstDefined(asRecord(workflow.data).broker_called, run.broker_called, false)} tone={firstDefined(asRecord(workflow.data).broker_called, run.broker_called, false)} />
          <Metric label="Submitted order" value={firstDefined(asRecord(workflow.data).submitted_order, run.submitted_order, false)} tone={firstDefined(asRecord(workflow.data).submitted_order, run.submitted_order, false)} />
          <Metric label="LLM used" value={firstDefined(asRecord(workflow.data).llm_used, run.llm_used, false)} tone={firstDefined(asRecord(workflow.data).llm_used, run.llm_used, false)} />
          <Metric label="Final readiness" value={firstDefined(asRecord(finalReady.data).status, "unknown")} tone={firstDefined(asRecord(finalReady.data).status, "unknown")} />
        </div>
      </Card>
    </div>
  );
}

function ScannerFeed({ worker, scanner }: { worker: FetchState; scanner: FetchState }) {
  const w = workerSummary(worker.data);
  const scannerWorker = asRecord(w.scanner_worker);
  const ingestion = asRecord(w.ingestion_worker);
  const feature = asRecord(w.feature_worker);
  const candidates = asList(scannerWorker.scanner_candidates);
  const matched = asList(asRecord(scanner.data).matched_signals);
  const skipped = asList(asRecord(scanner.data).skipped_signals);
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Worker status" endpoint="GET /api/worker-status/latest">
        <ErrorBox error={worker.error} />
        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Scanner" value={firstDefined(scannerWorker.status, "unknown")} tone={firstDefined(scannerWorker.status, "unknown")} />
          <Metric label="Ingestion" value={firstDefined(ingestion.status, "unknown")} tone={firstDefined(ingestion.status, "unknown")} />
          <Metric label="Features" value={firstDefined(feature.status, "unknown")} tone={firstDefined(feature.status, "unknown")} />
        </div>
      </Card>
      <Card title="Provider diagnostics" endpoint="GET /api/worker-status/latest">
        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Candidate count" value={firstDefined(w.candidate_count, 0)} />
          <Metric label="Snapshot count" value={firstDefined(w.snapshot_count, 0)} />
          <Metric label="Feature rows" value={firstDefined(w.feature_row_count, 0)} />
        </div>
      </Card>
      <Card title="Rejection counts" endpoint="POST /api/scanner/run">
        <ErrorBox error={scanner.error} />
        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Matched" value={matched.length} />
          <Metric label="Skipped" value={skipped.length} />
          <Metric label="Workflow trigger" value={firstDefined(asRecord(scanner.data).workflow_trigger_status, "not_run")} />
        </div>
      </Card>
      <Card title="Candidates" endpoint="GET /api/worker-status/latest + POST /api/scanner/run">
        <div className="space-y-2">
          {[...candidates, ...matched].slice(0, 12).map((row, index) => {
            const r = asRecord(row);
            return (
              <div key={`${text(r.symbol, "candidate")}-${index}`} className="rounded-2xl border border-white/10 bg-black/25 p-3">
                <div className="font-semibold text-white">{text(r.symbol)}</div>
                <div className="mt-1 text-xs text-slate-400">{text(firstDefined(r.reason, r.status, r.signal_key, r.provider_name))}</div>
              </div>
            );
          })}
          {!candidates.length && !matched.length ? <p className="text-sm text-slate-500">No scanner candidates yet.</p> : null}
        </div>
      </Card>
    </div>
  );
}

function AlphaRecommendation({ workflow }: { workflow: FetchState }) {
  const run = runObject(workflow.data);
  const rec = recommendationObject(workflow.data);
  const pricePlan = asRecord(firstDefined(rec.price_plan, run.price_plan));
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Selected symbol" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Symbol" value={firstDefined(rec.symbol, run.selected_symbol, null)} /></Card>
      <Card title="Strategy" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Strategy" value={firstDefined(rec.strategy_key, run.strategy_key, run.selected_strategy_key, "not_selected")} /></Card>
      <Card title="Final score" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Score" value={firstDefined(rec.final_score, run.final_score, "not_scored")} /></Card>
      <Card title="Expected return" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Expected return" value={firstDefined(rec.expected_return, rec.expected_return_percent, run.expected_return, "not_available")} /></Card>
      <Card title="Entry / stop / target" endpoint="POST /api/workflow-orchestrator/run">
        <div className="grid gap-3 md:grid-cols-3">
          <Metric label="Entry" value={firstDefined(pricePlan.entry, pricePlan.buy_zone_low, pricePlan.current_price)} />
          <Metric label="Stop" value={firstDefined(pricePlan.stop, pricePlan.stop_loss)} />
          <Metric label="Target" value={firstDefined(pricePlan.target, pricePlan.target_price)} />
        </div>
      </Card>
      <Card title="Reason / blockers" endpoint="POST /api/workflow-orchestrator/run">
        <Metric label="Reason" value={firstDefined(rec.reason, rec.final_reason, run.reason, "no source-backed recommendation yet")} />
        <div className="mt-3"><Metric label="Blockers" value={firstDefined(run.blockers, asRecord(workflow.data).blockers, [])} /></div>
      </Card>
    </div>
  );
}

function EvidencePromotion({ strategies, models, finalReady }: { strategies: FetchState; models: FetchState; finalReady: FetchState }) {
  const strategyRows = asList(asRecord(strategies.data).strategies);
  const modelRows = asList(asRecord(models.data).models);
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Backtest proof" endpoint="GET /api/promotion/strategies/status">
        <ErrorBox error={strategies.error} />
        <Metric label="Strategies tracked" value={strategyRows.length} />
      </Card>
      <Card title="Model evidence" endpoint="GET /api/promotion/models/status">
        <ErrorBox error={models.error} />
        <Metric label="Models tracked" value={modelRows.length} />
      </Card>
      <Card title="Promotion status" endpoint="GET /api/promotion/strategies/status + /models/status">
        <div className="space-y-2">
          {[...strategyRows, ...modelRows].slice(0, 10).map((row, index) => {
            const r = asRecord(row);
            return (
              <div key={`${text(firstDefined(r.strategy_key, r.model_key, index))}`} className="rounded-2xl border border-white/10 bg-black/25 p-3">
                <div className="font-mono text-xs text-emerald-200">{text(firstDefined(r.strategy_key, r.model_key))}</div>
                <div className="mt-1"><Badge tone={firstDefined(r.promotion_readiness, r.status)}>{text(firstDefined(r.promotion_readiness, r.status))}</Badge></div>
              </div>
            );
          })}
        </div>
      </Card>
      <Card title="Missing evidence" endpoint="GET /api/final-readiness/status + promotion endpoints">
        <ErrorBox error={finalReady.error} />
        <Metric label="Final readiness" value={firstDefined(asRecord(finalReady.data).status, "unknown")} tone={firstDefined(asRecord(finalReady.data).status, "unknown")} />
      </Card>
    </div>
  );
}

function RiskSmallAccount({ workflow }: { workflow: FetchState }) {
  const run = runObject(workflow.data);
  const rec = recommendationObject(workflow.data);
  const risk = asRecord(firstDefined(rec.risk_plan, run.risk_plan, run.small_account_decision));
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Max risk dollars" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Max risk" value={firstDefined(risk.max_dollar_risk, run.max_risk_dollars, "not_available")} /></Card>
      <Card title="Position size" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Position size" value={firstDefined(risk.position_size_dollars, run.position_size, "not_available")} /></Card>
      <Card title="Feasibility" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Feasibility" value={firstDefined(risk.account_fit, risk.feasibility, run.small_account_decision, "not_checked")} /></Card>
      <Card title="Daily limits" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Daily limit" value={firstDefined(run.max_daily_loss_dollars, risk.max_daily_loss_dollars, "not_available")} /></Card>
    </div>
  );
}

function ExecutionBoundary({ workflow, platform }: { workflow: FetchState; platform: FetchState }) {
  const run = runObject(workflow.data);
  const gates = asRecord(nested(platform.data, ["systems", "execution_gates"]));
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <Card title="Paper trading status" endpoint="GET /api/platform-readiness/status"><Metric label="Paper trading" value={firstDefined(gates.paper_trading_enabled, run.paper_trading_enabled, "unknown")} tone={firstDefined(gates.paper_trading_enabled, run.paper_trading_enabled, "unknown")} /></Card>
      <Card title="Approval required" endpoint="GET /api/platform-readiness/status"><Metric label="Require approval" value={firstDefined(gates.require_human_approval, run.approval_required, true)} tone={firstDefined(gates.require_human_approval, run.approval_required, true)} /></Card>
      <Card title="Broker called" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Broker called" value={firstDefined(asRecord(workflow.data).broker_called, run.broker_called, false)} tone={firstDefined(asRecord(workflow.data).broker_called, run.broker_called, false)} /></Card>
      <Card title="Submitted order" endpoint="POST /api/workflow-orchestrator/run"><Metric label="Submitted order" value={firstDefined(asRecord(workflow.data).submitted_order, run.submitted_order, false)} tone={firstDefined(asRecord(workflow.data).submitted_order, run.submitted_order, false)} /></Card>
      <Card title="Live trading status" endpoint="GET /api/platform-readiness/status"><Metric label="Live trading" value={firstDefined(gates.live_trading_enabled, run.live_trading_enabled, false)} tone={firstDefined(gates.live_trading_enabled, run.live_trading_enabled, false)} /></Card>
    </div>
  );
}

export default function NewDayTradingWorkflowPage() {
  const params = useParams<{ section?: string[] }>();
  const sectionParam = params?.section?.[0] as SectionId | undefined;
  const activeSection = SECTIONS.some((s) => s.id === sectionParam) ? sectionParam! : "status-summary";
  const section = SECTIONS.find((s) => s.id === activeSection) ?? SECTIONS[0];
  const [symbols, setSymbols] = useState("");
  const [health, setHealth] = useState<FetchState>({ data: null, error: null, loading: true });
  const [platform, setPlatform] = useState<FetchState>({ data: null, error: null, loading: true });
  const [finalReady, setFinalReady] = useState<FetchState>({ data: null, error: null, loading: true });
  const [worker, setWorker] = useState<FetchState>({ data: null, error: null, loading: true });
  const [strategies, setStrategies] = useState<FetchState>({ data: null, error: null, loading: true });
  const [models, setModels] = useState<FetchState>({ data: null, error: null, loading: true });
  const [workflow, setWorkflow] = useState<FetchState>({ data: null, error: null, loading: false });
  const [scanner, setScanner] = useState<FetchState>({ data: null, error: null, loading: false });
  const [busy, setBusy] = useState(false);

  const loadReadOnly = async () => {
    setHealth({ data: null, error: null, loading: true });
    setPlatform({ data: null, error: null, loading: true });
    setFinalReady({ data: null, error: null, loading: true });
    setWorker({ data: null, error: null, loading: true });
    setStrategies({ data: null, error: null, loading: true });
    setModels({ data: null, error: null, loading: true });
    const [h, p, f, w, s, m] = await Promise.all([
      safeLoad(() => request("/health")),
      safeLoad(() => request("/api/platform-readiness/status")),
      safeLoad(() => request("/api/final-readiness/status")),
      safeLoad(() => request("/api/worker-status/latest")),
      safeLoad(() => request("/api/promotion/strategies/status")),
      safeLoad(() => request("/api/promotion/models/status")),
    ]);
    setHealth(h);
    setPlatform(p);
    setFinalReady(f);
    setWorker(w);
    setStrategies(s);
    setModels(m);
  };

  useEffect(() => {
    void loadReadOnly();
  }, []);

  const symbolList = useMemo(() => symbols.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean), [symbols]);

  async function runWorkflow() {
    setBusy(true);
    setWorkflow({ data: null, error: null, loading: true });
    const result = await safeLoad(() =>
      request("/api/workflow-orchestrator/run", {
        method: "POST",
        body: JSON.stringify({ dry_run: true, allow_submit: false, symbols: symbolList, source: symbolList.length ? "manual" : "runtime" }),
      })
    );
    setWorkflow(result);
    setBusy(false);
    void loadReadOnly();
  }

  async function runScanner() {
    setBusy(true);
    setScanner({ data: null, error: null, loading: true });
    const result = await safeLoad(() =>
      request("/api/scanner/run", {
        method: "POST",
        body: JSON.stringify({ strategy_key: "stock_day_trading", symbols: symbolList, data_source: "auto", auto_run: false, trigger_type: "manual", trigger_workflow: false }),
      })
    );
    setScanner(result);
    setBusy(false);
    void loadReadOnly();
  }

  const content = {
    "status-summary": <StatusSummary workflow={workflow} platform={platform} finalReady={finalReady} health={health} />,
    "scanner-candidate-feed": <ScannerFeed worker={worker} scanner={scanner} />,
    "alpha-recommendation": <AlphaRecommendation workflow={workflow} />,
    "evidence-promotion": <EvidencePromotion strategies={strategies} models={models} finalReady={finalReady} />,
    "risk-small-account": <RiskSmallAccount workflow={workflow} />,
    "execution-boundary": <ExecutionBoundary workflow={workflow} platform={platform} />,
  }[activeSection];

  return (
    <main className="min-h-screen bg-[#02070b] text-slate-100">
      <div className="mx-auto flex max-w-[1600px] gap-6 px-5 py-6">
        <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-80 shrink-0 overflow-y-auto rounded-[2rem] border border-emerald-400/15 bg-[#061017]/90 p-4 shadow-[0_24px_90px_rgba(0,0,0,0.45)] backdrop-blur-xl lg:block">
          <div className="mb-5 rounded-3xl border border-emerald-300/15 bg-emerald-400/10 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-emerald-300/70">Production Contract</p>
            <h1 className="mt-2 text-xl font-black text-white">Day Trading Workflow</h1>
            <p className="mt-2 text-xs leading-5 text-slate-400">New dashboard using only allowlisted production endpoints.</p>
          </div>
          <nav className="space-y-2">
            {SECTIONS.map((item) => (
              <Link key={item.id} href={`/daytrading-workflow/new/${item.id}`} className={`block rounded-2xl border p-3 transition ${item.id === activeSection ? "border-emerald-300/45 bg-emerald-400/15 shadow-[0_0_30px_rgba(16,185,129,0.16)]" : "border-white/10 bg-white/[0.03] hover:border-emerald-300/25 hover:bg-emerald-400/10"}`}>
                <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-emerald-300/60">{item.eyebrow}</div>
                <div className="mt-1 font-semibold text-white">{item.label}</div>
                <div className="mt-2 flex flex-wrap gap-1">
                  {item.cards.map((card) => <span key={card} className="rounded-full border border-white/10 bg-black/25 px-2 py-0.5 text-[10px] text-slate-400">{card}</span>)}
                </div>
              </Link>
            ))}
          </nav>
        </aside>

        <section className="min-w-0 flex-1 space-y-5">
          <header className="rounded-[2rem] border border-emerald-400/15 bg-[#061017]/85 p-5 shadow-[0_28px_110px_rgba(0,0,0,0.42)] backdrop-blur-2xl">
            <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.28em] text-emerald-300/70">{section.eyebrow}</div>
            <h2 className="text-3xl font-black tracking-tight text-white">{section.label}</h2>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">{section.description}</p>
            <div className="mt-5 grid gap-3 lg:grid-cols-[1fr_auto_auto_auto]">
              <input value={symbols} onChange={(event) => setSymbols(event.target.value)} placeholder="Optional explicit symbols, comma-separated. Example: TSLA, PLTR" className="rounded-2xl border border-emerald-400/15 bg-black/35 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-600 focus:border-emerald-300/45" />
              <button disabled={busy} onClick={runScanner} className="rounded-2xl border border-emerald-300/35 bg-emerald-400/15 px-4 py-3 text-sm font-bold text-emerald-100 disabled:opacity-50">Run scanner</button>
              <button disabled={busy} onClick={runWorkflow} className="rounded-2xl border border-sky-300/35 bg-sky-400/15 px-4 py-3 text-sm font-bold text-sky-100 disabled:opacity-50">Run workflow</button>
              <button disabled={busy} onClick={loadReadOnly} className="rounded-2xl border border-white/10 bg-white/[0.05] px-4 py-3 text-sm font-bold text-slate-200 disabled:opacity-50">Refresh</button>
            </div>
          </header>

          <div className="grid gap-3 rounded-[2rem] border border-white/10 bg-black/25 p-4 md:grid-cols-2 xl:grid-cols-4">
            {ENDPOINT_CONTRACTS.map((endpoint) => (
              <div key={`${endpoint.method}-${endpoint.path}`} className="rounded-2xl border border-white/10 bg-[#071016] p-3">
                <Badge tone="ready">{endpoint.method}</Badge>
                <div className="mt-2 font-mono text-xs text-emerald-200">{endpoint.path}</div>
                <p className="mt-1 text-xs text-slate-500">{endpoint.purpose}</p>
              </div>
            ))}
          </div>

          {content}

          <section className="rounded-[2rem] border border-white/10 bg-black/25 p-4">
            <h3 className="text-sm font-bold uppercase tracking-[0.18em] text-slate-400">Debug preview</h3>
            <div className="grid gap-4 xl:grid-cols-2">
              <JsonPreview value={{ workflow: workflow.data, workflow_error: workflow.error }} />
              <JsonPreview value={{ worker: worker.data, worker_error: worker.error, scanner: scanner.data, scanner_error: scanner.error }} />
            </div>
          </section>
        </section>
      </div>
    </main>
  );
}
