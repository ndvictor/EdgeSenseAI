"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;

const sections = [
  { label: "Status Summary", route: "/api/v1/daytrading/status", link: "/daytrading-control-center#status" },
  { label: "Scanner / Candidate Feed", route: "/api/v1/daytrading/scanner/latest", link: "/daytrading-control-center#scanner" },
  { label: "Alpha Recommendation", route: "/api/v1/daytrading/recommendation/latest", link: "/daytrading-control-center#alpha" },
  { label: "Evidence & Promotion", route: "/api/v1/daytrading/evidence/strategies + /models", link: "/daytrading-control-center#evidence" },
  { label: "Risk / Small Account", route: "/api/v1/daytrading/risk/status", link: "/daytrading-control-center#risk" },
  { label: "Execution Boundary", route: "/api/v1/daytrading/execution-boundary", link: "/daytrading-control-center#execution" },
  { label: "Market Session", route: "/api/v1/daytrading/workers/latest", link: "/daytrading-control-center#session" },
  { label: "Settings", route: "Azure env + CORS + frontend API URL", link: "/daytrading-control-center#settings" },
];

const MIGRATION_POLICY_MESSAGE =
  "Legacy runtime routes are intentionally restricted in production. Do not re-enable legacy fetches from the frontend. Use the migration table to move useful legacy route fields into the clean `/api/v1/daytrading/*` contract routes. The dashboard should only call v1 routes. Legacy routes may remain in the backend for internal migration and non-production review, but they are not production UI endpoints.";

/** Legacy route → v1 + what to migrate. Legacy UI fetch always No in production; v1 Yes when a dashboard endpoint exists. */
const mappingRows: Array<{
  area: string;
  legacyRoute: string;
  v1Route: string;
  migrationAction: string;
  legacyUiFetch: "No";
  v1UiFetch: "Yes" | "Planned";
}> = [
  {
    area: "Command Center",
    legacyRoute: "/api/command-center",
    v1Route: "/api/v1/daytrading/status, /api/v1/daytrading/workflow/latest",
    migrationAction: "Move aggregated status, readiness, and control-surface fields into v1 status/workflow bundles; keep orchestration behind v1 workflow routes.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Live Watchlist",
    legacyRoute: "/api/live-watchlist/latest",
    v1Route: "/api/v1/daytrading/scanner/latest, /api/v1/daytrading/workers/latest",
    migrationAction: "Surface candidate/scanner-linked worker output in v1 scanner/workers payloads instead of watchlist JSON.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Edge Signals",
    legacyRoute: "/api/edge-signals/latest",
    v1Route: "/api/v1/daytrading/scanner/latest",
    migrationAction: "Fold signal summaries into scanner diagnostics / worker status fields exposed on v1 scanner latest.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Models Status",
    legacyRoute: "/api/models/status",
    v1Route: "/api/v1/daytrading/evidence/models",
    migrationAction: "Use promotion model evidence contract only; align model health fields with `evidence/models`.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Market Snapshots",
    legacyRoute: "/api/market/snapshots",
    v1Route: "/api/v1/daytrading/workers/latest",
    migrationAction: "Keep snapshot ingestion internal; expose only counts/status the operator needs via workers latest.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Features",
    legacyRoute: "/api/features/*",
    v1Route: "/api/v1/daytrading/workers/latest",
    migrationAction: "Feature row summaries belong in worker output; add v1 fields if operators need more detail.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Model Pipeline",
    legacyRoute: "/api/model-pipeline/*",
    v1Route: "/api/v1/daytrading/recommendation/latest",
    migrationAction: "Pipeline scoring and alpha output must surface through orchestrator → recommendation/latest projection.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Candidate Universe",
    legacyRoute: "/api/candidate-universe/*",
    v1Route: "(add v1 projection when needed)",
    migrationAction: "Do not use legacy universe routes from production UI; design a read-only v1 slice if operators need universe visibility.",
    legacyUiFetch: "No",
    v1UiFetch: "Planned",
  },
  {
    area: "Universe Selection",
    legacyRoute: "/api/universe-selection/*",
    v1Route: "(add v1 projection when needed)",
    migrationAction: "Selection runs stay server-side; any operator visibility goes through a future v1 read model.",
    legacyUiFetch: "No",
    v1UiFetch: "Planned",
  },
  {
    area: "Approval Queue",
    legacyRoute: "/api/approval-queue/*",
    v1Route: "/api/v1/daytrading/execution-boundary",
    migrationAction: "Map safe approval/boundary signals into execution-boundary; never expose queue mutations from this dashboard.",
    legacyUiFetch: "No",
    v1UiFetch: "Yes",
  },
  {
    area: "Audit Log",
    legacyRoute: "/api/audit-log/*",
    v1Route: "(separate admin surface; not day-trading v1)",
    migrationAction: "Keep audit out of trading control center; dedicated admin UI if required.",
    legacyUiFetch: "No",
    v1UiFetch: "Planned",
  },
  {
    area: "Workflow Scheduler",
    legacyRoute: "/api/workflow-scheduler/*",
    v1Route: "(timing via workers/session — extend v1 if needed)",
    migrationAction: "Scheduler triggers stay backend/Azure; expose schedule/session hints via workers or future v1 field.",
    legacyUiFetch: "No",
    v1UiFetch: "Planned",
  },
];

/** Do not call from this dashboard (browser) — production quarantine / not production UI endpoints. */
const LEGACY_ROUTES_NEVER_IN_UI = [
  "/api/command-center",
  "/api/live-watchlist/latest",
  "/api/edge-signals/latest",
  "/api/models/status",
  "/api/market/snapshots",
  "/api/features/*",
  "/api/model-pipeline/*",
  "/api/candidate-universe/*",
  "/api/universe-selection/*",
  "/api/approval-queue/*",
  "/api/audit-log/*",
  "/api/workflow-scheduler/*",
] as const;

/** This control center and production day-trading dashboards should only use these API paths (GETs for display; POST scanner/workflow run live on the operator dashboard). */
const V1_ROUTES_PRODUCTION_UI = [
  "/api/v1/daytrading/status",
  "/api/v1/daytrading/scanner/latest",
  "/api/v1/daytrading/workers/latest",
  "/api/v1/daytrading/recommendation/latest",
  "/api/v1/daytrading/evidence/strategies",
  "/api/v1/daytrading/evidence/models",
  "/api/v1/daytrading/risk/status",
  "/api/v1/daytrading/execution-boundary",
  "/api/v1/daytrading/contracts/routes",
] as const;

const settingsRows = [
  ["NEXT_PUBLIC_API_URL", "Frontend Azure Container App", API_BASE || "not configured", "Backend API base used by browser fetches."],
  ["CORS_ORIGINS", "Backend Azure Container App", "https://<frontend-fqdn>,https://<custom-domain>,http://localhost:3900", "CORS allows origins, not routes."],
  ["APP_ENV / ENVIRONMENT", "Backend Azure Container App", "production", "Turns on production route quarantine."],
  ["MARKET_DATA_MODE", "Backend + workers", "provider", "Requires real provider mode."],
  ["MARKET_DATA_PROVIDER", "Backend + workers", "alpaca | polygon | yfinance", "Primary real data source."],
  ["SCANNER_SYMBOLS", "Scanner worker ACA/job", "explicit comma-separated real symbols", "Scheduled scanner universe. No code fallback symbols."],
  ["ALLOW_SYNTHETIC_MARKET_DATA", "Backend + workers", "false", "Blocks synthetic/fake output."],
  ["LIVE_TRADING_ENABLED", "Backend Azure Container App", "false", "Live trading remains disabled unless explicitly enabled."],
];

async function fetchJson(path: string) {
  if (!API_BASE) throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) throw new Error(`${path} returned ${response.status}`);
  return response.json();
}

function valueText(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function field(source: unknown, key: string) {
  if (!source || typeof source !== "object") return undefined;
  return (source as Record<string, unknown>)[key];
}

function Card({ id, title, endpoint, children }: { id: string; title: string; endpoint: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-6 rounded-3xl border border-cyan-400/15 bg-black/35 p-5 shadow-[0_24px_90px_rgba(0,0,0,0.42)] backdrop-blur-xl">
      <div className="mb-4">
        <h2 className="text-sm font-bold uppercase tracking-[0.18em] text-cyan-100">{title}</h2>
        <p className="mt-1 font-mono text-[11px] text-cyan-300/70">{endpoint}</p>
      </div>
      {children}
    </section>
  );
}

function Row({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="flex flex-wrap gap-x-3 gap-y-1 border-b border-white/[0.06] py-2 last:border-0">
      <span className="w-52 shrink-0 text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">{label}</span>
      <span className="min-w-0 flex-1 break-words font-mono text-sm text-slate-100">{valueText(value)}</span>
    </div>
  );
}

export default function DayTradingControlCenter() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [workers, setWorkers] = useState<Record<string, unknown> | null>(null);
  const [routes, setRoutes] = useState<Record<string, unknown> | null>(null);
  const [strategies, setStrategies] = useState<Record<string, unknown> | null>(null);
  const [models, setModels] = useState<Record<string, unknown> | null>(null);
  const [risk, setRisk] = useState<Record<string, unknown> | null>(null);
  const [execution, setExecution] = useState<Record<string, unknown> | null>(null);
  const [recommendation, setRecommendation] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([
      fetchJson("/api/v1/daytrading/status"),
      fetchJson("/api/v1/daytrading/workers/latest"),
      fetchJson("/api/v1/daytrading/contracts/routes"),
      fetchJson("/api/v1/daytrading/evidence/strategies"),
      fetchJson("/api/v1/daytrading/evidence/models"),
      fetchJson("/api/v1/daytrading/risk/status"),
      fetchJson("/api/v1/daytrading/execution-boundary"),
      fetchJson("/api/v1/daytrading/recommendation/latest"),
    ]).then((results) => {
      const setters = [setStatus, setWorkers, setRoutes, setStrategies, setModels, setRisk, setExecution, setRecommendation];
      results.forEach((result, index) => {
        if (result.status === "fulfilled") setters[index](result.value as Record<string, unknown>);
      });
      const failed = results.find((result) => result.status === "rejected");
      if (failed && failed.status === "rejected") setError(failed.reason instanceof Error ? failed.reason.message : String(failed.reason));
    });
  }, []);

  const scanner = field(workers, "scanner_worker");
  const diagnostics = field(workers, "latest_scanner_diagnostics");

  return (
    <main className="min-h-screen bg-[#03070b] text-slate-100">
      <div className="flex min-h-screen">
        <aside className="sticky top-0 hidden h-screen w-80 shrink-0 overflow-y-auto border-r border-cyan-400/10 bg-[#05080d]/95 px-4 py-5 lg:block">
          <div className="mb-5 rounded-3xl border border-cyan-400/20 bg-cyan-400/10 p-4">
            <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">EdgeSenseAI</p>
            <h1 className="mt-2 text-xl font-black text-white">Day Trading Control Center</h1>
            <p className="mt-2 text-xs leading-5 text-slate-400">Mapped v1 API dashboard. Legacy paths are migration references only — production UI fetches `/api/v1/daytrading/*` only.</p>
          </div>
          <nav className="space-y-2">
            {sections.map((item) => (
              <a key={item.label} href={item.link} className="block rounded-2xl border border-white/10 bg-white/[0.03] p-3 hover:border-cyan-300/30 hover:bg-cyan-400/10">
                <div className="font-semibold text-white">{item.label}</div>
                <div className="mt-1 font-mono text-[10px] text-cyan-300/60">{item.route}</div>
              </a>
            ))}
          </nav>
          <div className="mt-5 space-y-2 text-sm">
            <Link href="/" className="block rounded-xl border border-white/10 px-3 py-2 text-slate-300 hover:text-cyan-200">← Home</Link>
            <Link href="/daytrading-workflow/new" className="block rounded-xl border border-cyan-400/20 px-3 py-2 text-cyan-200">Production v1 Dashboard →</Link>
          </div>
        </aside>

        <section className="min-w-0 flex-1 space-y-5 px-5 py-6 lg:px-8">
          <header className="rounded-[2rem] border border-cyan-400/15 bg-[#061017]/85 p-5 shadow-[0_28px_110px_rgba(0,0,0,0.42)] backdrop-blur-2xl">
            <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">New route</p>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-white">Day Trading Control Center</h1>
            <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
              This control center reads only the Day Trading v1 contract. Legacy routes are not production UI endpoints; they remain for backend migration and non-production review.
            </p>
            {error ? <p className="mt-4 rounded-xl border border-amber-400/25 bg-amber-500/10 p-3 text-sm text-amber-100">Partial load warning: {error}</p> : null}
          </header>

          <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4"><div className="text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">API base</div><div className="mt-2 break-words font-mono text-xs text-white">{API_BASE || "not configured"}</div></div>
            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4"><div className="text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Status</div><div className="mt-2 text-lg font-black text-white">{valueText(field(status, "status"))}</div></div>
            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4"><div className="text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Scanner</div><div className="mt-2 text-lg font-black text-white">{valueText(field(scanner, "status"))}</div></div>
            <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/10 p-4"><div className="text-[10px] uppercase tracking-[0.16em] text-cyan-300/70">Market session</div><div className="mt-2 text-lg font-black text-white">{valueText(field(workers, "market_session") ?? field(scanner, "market_session") ?? field(diagnostics, "market_session"))}</div></div>
          </section>

          <Card id="status" title="Status Summary" endpoint="GET /api/v1/daytrading/status">
            <Row label="status" value={field(status, "status")} />
            <Row label="health" value={field(status, "health")} />
            <Row label="platform_readiness" value={field(status, "platform_readiness")} />
            <Row label="final_readiness" value={field(status, "final_readiness")} />
          </Card>

          <Card id="scanner" title="Scanner / Candidate Feed" endpoint="GET /api/v1/daytrading/scanner/latest + /workers/latest">
            <Row label="scanner_worker.status" value={field(scanner, "status")} />
            <Row label="candidate_count" value={field(workers, "candidate_count")} />
            <Row label="snapshot_count" value={field(workers, "snapshot_count")} />
            <Row label="feature_row_count" value={field(workers, "feature_row_count")} />
            <Row label="selected_symbols" value={field(scanner, "selected_symbols")} />
            <Row label="rejection_counts" value={field(workers, "rejection_counts")} />
          </Card>

          <Card id="session" title="Market Session" endpoint="GET /api/v1/daytrading/workers/latest">
            <Row label="market_session" value={field(workers, "market_session") ?? field(scanner, "market_session") ?? field(diagnostics, "market_session")} />
            <Row label="scanner_mode" value={field(workers, "scanner_mode") ?? field(scanner, "scanner_mode") ?? field(diagnostics, "scanner_mode")} />
            <Row label="clock_source" value={field(workers, "clock_source") ?? field(scanner, "clock_source") ?? field(diagnostics, "clock_source")} />
            <Row label="current_time_et" value={field(workers, "current_time_et") ?? field(scanner, "current_time_et") ?? field(diagnostics, "current_time_et")} />
            <Row label="next_open" value={field(workers, "next_open") ?? field(scanner, "next_open") ?? field(diagnostics, "next_open")} />
            <Row label="next_close" value={field(workers, "next_close") ?? field(scanner, "next_close") ?? field(diagnostics, "next_close")} />
          </Card>

          <Card id="alpha" title="Alpha Recommendation" endpoint="GET /api/v1/daytrading/recommendation/latest">
            <Row label="status" value={field(recommendation, "status")} />
            <Row label="selected_symbol" value={field(recommendation, "selected_symbol") ?? field(recommendation, "symbol")} />
            <Row label="strategy" value={field(recommendation, "strategy_key")} />
            <Row label="score" value={field(recommendation, "final_score")} />
            <Row label="blockers" value={field(recommendation, "blockers")} />
          </Card>

          <Card id="evidence" title="Evidence & Promotion" endpoint="GET /api/v1/daytrading/evidence/strategies + /models">
            <Row label="strategy status" value={field(strategies, "status")} />
            <Row label="strategies" value={field(strategies, "strategies")} />
            <Row label="model status" value={field(models, "status")} />
            <Row label="models" value={field(models, "models")} />
          </Card>

          <Card id="risk" title="Risk / Small Account" endpoint="GET /api/v1/daytrading/risk/status">
            <Row label="status" value={field(risk, "status")} />
            <Row label="max_risk_dollars" value={field(risk, "max_risk_dollars")} />
            <Row label="position_size" value={field(risk, "position_size")} />
            <Row label="feasibility" value={field(risk, "feasibility") ?? field(risk, "small_account_decision")} />
            <Row label="daily_limits" value={field(risk, "daily_limits")} />
          </Card>

          <Card id="execution" title="Execution Boundary" endpoint="GET /api/v1/daytrading/execution-boundary">
            <Row label="paper_trading_status" value={field(execution, "paper_trading_status") ?? field(execution, "paper_trading_enabled")} />
            <Row label="approval_required" value={field(execution, "approval_required")} />
            <Row label="broker_called" value={field(execution, "broker_called")} />
            <Row label="submitted_order" value={field(execution, "submitted_order")} />
            <Row label="live_trading_status" value={field(execution, "live_trading_status") ?? field(execution, "live_trading_enabled")} />
          </Card>

          <Card id="mapping" title="Legacy → v1 migration map" endpoint="Static mapping + GET /api/v1/daytrading/contracts/routes">
            <div className="mb-4 rounded-2xl border border-cyan-400/20 bg-cyan-950/40 p-4 text-sm leading-6 text-slate-200">
              <p className="font-semibold text-cyan-100">Production UI policy</p>
              <p className="mt-2 text-slate-300">{MIGRATION_POLICY_MESSAGE}</p>
              <p className="mt-3 text-xs uppercase tracking-[0.14em] text-slate-500">Table columns</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-xs text-slate-400">
                <li>
                  <span className="text-slate-200">Legacy route</span> — old source of capability (not called from production UI).
                </li>
                <li>
                  <span className="text-slate-200">New v1 route</span> — production dashboard endpoint under `/api/v1/daytrading/*`.
                </li>
                <li>
                  <span className="text-slate-200">Migration action</span> — which fields or services must move into v1.
                </li>
                <li>
                  <span className="text-slate-200">Frontend fetch allowed</span> — <span className="text-rose-200">No</span> for legacy paths; <span className="text-cyan-200">Yes</span> for v1 where the route exists (otherwise <span className="text-amber-200">Planned</span>).
                </li>
              </ul>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1100px] text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.16em] text-slate-500">
                  <tr>
                    <th className="p-2">Area</th>
                    <th className="p-2">Legacy route (old source)</th>
                    <th className="p-2">New v1 route (dashboard endpoint)</th>
                    <th className="p-2">Migration action</th>
                    <th className="p-2">Legacy UI fetch</th>
                    <th className="p-2">V1 UI fetch</th>
                  </tr>
                </thead>
                <tbody>
                  {mappingRows.map((row) => (
                    <tr key={row.area} className="border-t border-white/[0.06]">
                      <td className="p-2 font-semibold text-white">{row.area}</td>
                      <td className="p-2 font-mono text-rose-200/95">{row.legacyRoute}</td>
                      <td className="p-2 font-mono text-cyan-200/95">{row.v1Route}</td>
                      <td className="p-2 text-slate-300">{row.migrationAction}</td>
                      <td className="p-2 font-semibold text-rose-300">{row.legacyUiFetch}</td>
                      <td className="p-2 font-semibold text-cyan-300">{row.v1UiFetch}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details className="mt-4 rounded-2xl border border-white/10 bg-black/25 p-3">
              <summary className="cursor-pointer text-sm font-semibold text-slate-300">Route contract payload (GET /api/v1/daytrading/contracts/routes)</summary>
              <pre className="mt-3 max-h-96 overflow-auto whitespace-pre-wrap text-xs text-slate-400">{JSON.stringify(routes, null, 2)}</pre>
            </details>
          </Card>

          <Card id="settings" title="Settings UI" endpoint="Azure Container Apps env / dashboard read-only settings">
            <div className="mb-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-sm leading-6 text-slate-200">
              <p className="font-semibold text-white">Migration and production UI</p>
              <p className="mt-2 text-slate-300">{MIGRATION_POLICY_MESSAGE}</p>
            </div>
            <div className="mb-4 grid gap-4 lg:grid-cols-2">
              <div className="rounded-2xl border border-rose-400/25 bg-rose-950/30 p-4">
                <h3 className="text-xs font-bold uppercase tracking-[0.16em] text-rose-200">Do not call from the dashboard (browser)</h3>
                <p className="mt-2 text-xs text-slate-400">These paths are quarantined or non–production UI; migrating features must land in v1 instead.</p>
                <ul className="mt-3 space-y-1.5 font-mono text-[11px] text-rose-100/90">
                  {LEGACY_ROUTES_NEVER_IN_UI.map((path) => (
                    <li key={path}>{path}</li>
                  ))}
                </ul>
              </div>
              <div className="rounded-2xl border border-cyan-400/25 bg-cyan-950/30 p-4">
                <h3 className="text-xs font-bold uppercase tracking-[0.16em] text-cyan-200">Production dashboard GET contract (this page)</h3>
                <p className="mt-2 text-xs text-slate-400">
                  Only these v1 paths are used for display here. Operator run actions on other UIs may use{" "}
                  <span className="font-mono text-cyan-200">POST /api/v1/daytrading/scanner/run</span> and{" "}
                  <span className="font-mono text-cyan-200">POST /api/v1/daytrading/workflow/run</span> — never legacy POSTs.
                </p>
                <ul className="mt-3 space-y-1.5 font-mono text-[11px] text-cyan-100/90">
                  {V1_ROUTES_PRODUCTION_UI.map((path) => (
                    <li key={path}>{path}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[900px] text-left text-sm">
                <thead className="text-xs uppercase tracking-[0.16em] text-slate-500"><tr><th className="p-2">Setting</th><th className="p-2">Owner</th><th className="p-2">Expected value</th><th className="p-2">Purpose</th></tr></thead>
                <tbody>
                  {settingsRows.map(([key, owner, value, purpose]) => (
                    <tr key={key} className="border-t border-white/[0.06]"><td className="p-2 font-mono text-cyan-200">{key}</td><td className="p-2 text-slate-300">{owner}</td><td className="p-2 font-mono text-slate-100">{value}</td><td className="p-2 text-slate-400">{purpose}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm text-amber-100">
              This settings panel is read-only. Change Azure values with `az containerapp update --set-env-vars ...`, then redeploy/restart as needed. Ensure{" "}
              <span className="font-mono">CORS_ORIGINS</span> lists every frontend origin (local and deployed); CORS is origin-based, not per-route.
            </div>
          </Card>
        </section>
      </div>
    </main>
  );
}
