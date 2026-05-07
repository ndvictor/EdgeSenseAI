"use client";

import React, { useEffect, useState } from "react";
import {
  api,
  getPlatformReadinessStatus,
  type PlatformReadinessResponse,
  type PlatformReadinessStatusResponse,
  type TracingStatusResponse,
  type ExecutionSummaryResponse,
} from "@/lib/api";

const statusColors = {
  pass: "bg-green-500",
  warn: "bg-yellow-500",
  fail: "bg-red-500",
  ready: "bg-green-500",
  partial: "bg-yellow-500",
  "not_ready": "bg-red-500",
  true: "bg-green-500",
  false: "bg-gray-400",
};

export default function PlatformReadinessPage() {
  const [readiness, setReadiness] = useState<PlatformReadinessResponse | null>(null);
  const [spine, setSpine] = useState<PlatformReadinessStatusResponse | null>(null);
  const [tracing, setTracing] = useState<TracingStatusResponse | null>(null);
  const [execution, setExecution] = useState<ExecutionSummaryResponse | null>(null);
  const [executionErr, setExecutionErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [readinessData, spineData, tracingData] = await Promise.all([
          api.getPlatformReadiness(),
          getPlatformReadinessStatus().catch(() => null),
          api.getTracingStatus(),
        ]);
        setReadiness(readinessData);
        setSpine(spineData);
        setTracing(tracingData);
        setExecutionErr(null);
        try {
          setExecution(await api.getExecutionSummary());
        } catch (e) {
          setExecution(null);
          setExecutionErr(e instanceof Error ? e.message : "not_configured");
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to fetch readiness data");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [refreshKey]);

  const handleRefresh = () => setRefreshKey(k => k + 1);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full p-4 lg:p-8">
        <div className="rounded-2xl border border-red-500/35 bg-red-500/10 p-4 backdrop-blur">
          <h2 className="mb-2 font-semibold text-red-300">Error Loading Platform Readiness</h2>
          <p className="text-sm text-red-200/90">{error}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 rounded-lg border border-red-500/40 bg-red-500/20 px-4 py-2 text-sm text-red-100 transition hover:bg-red-500/30"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!readiness) {
    return (
      <div className="w-full p-4 lg:p-8">
        <div className="rounded-2xl border border-amber-500/35 bg-amber-500/10 p-4 backdrop-blur">
          <p className="text-amber-200">No readiness data available</p>
        </div>
      </div>
    );
  }

  const persistenceChecks = readiness.checks.filter(c => 
    c.key.includes("database") || c.key.includes("postgres") || c.key.includes("pgvector") || c.key.includes("redis")
  );
  const monitoringChecks = readiness.checks.filter(c => 
    c.key.includes("market_data") || c.key.includes("langsmith")
  );
  const safetyChecks = readiness.checks.filter(c => 
    c.key.includes("live_trading") || c.key.includes("approval") || c.key.includes("llm") || c.key.includes("candidate")
  );
  const configChecks = readiness.checks.filter(c => 
    c.key.includes("env") || c.key.includes("version") || c.key.includes("secret")
  );

  return (
    <div className="mx-auto w-full max-w-7xl p-4 lg:p-8">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Platform Readiness</h1>
          <p className="text-slate-400 mt-1">
            Operational spine (Phase 4), environment checklist, persistence status, and safety configuration
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="flex items-center gap-2 rounded-xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-300 transition hover:bg-emerald-500/20"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {spine ? (
        <div className="mb-10 rounded-xl border border-emerald-500/30 bg-emerald-950/20 p-6 shadow">
          <h2 className="mb-1 text-lg font-semibold text-emerald-200">Operational checklist (Phase 4)</h2>
          <p className="mb-4 text-sm text-slate-400">
            Source: <span className="font-mono text-slate-300">GET /api/platform-readiness/status</span> · updated {String(spine.updated_at ?? "—")}
          </p>
          <div className="mb-4 grid gap-3 text-sm md:grid-cols-2">
            <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-3">
              <div className="text-xs uppercase text-slate-500">next_action</div>
              <p className="mt-1 text-slate-200">{String(spine.next_action ?? "—")}</p>
            </div>
            <div className="rounded-lg border border-slate-700 bg-slate-900/80 p-3">
              <div className="text-xs uppercase text-slate-500">safety_summary (backend)</div>
              <pre className="mt-1 max-h-24 overflow-auto text-xs text-slate-400">
                {JSON.stringify(spine.systems?.safety_summary ?? {}, null, 2)}
              </pre>
            </div>
          </div>
          <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {[
              "database",
              "redis",
              "agent_runtime",
              "workflow_orchestrator",
              "approval_queue",
              "audit_log",
              "workflow_scheduler",
              "governance",
              "qlib_integration",
              "proof_registry",
              "model_evidence",
              "strategy_evidence",
              "execution_gates",
              "master_admin",
            ].map((k) => (
              <div key={k} className="rounded-lg border border-slate-700 bg-slate-900/60 p-3">
                <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-500">{k}</div>
                <pre className="mt-2 max-h-40 overflow-auto text-[10px] text-slate-400">
                  {JSON.stringify((spine.systems as Record<string, unknown> | undefined)?.[k] ?? {}, null, 2)}
                </pre>
              </div>
            ))}
          </div>
          {(spine.missing_backend_components?.length ?? 0) > 0 ? (
            <div className="mb-3 rounded border border-amber-600/40 bg-amber-900/20 p-3 text-sm text-amber-100">
              <div className="font-semibold">missing_backend_components</div>
              <ul className="mt-1 list-inside list-disc">
                {(spine.missing_backend_components ?? []).map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {(spine.missing_frontend_components?.length ?? 0) > 0 ? (
            <div className="rounded border border-sky-600/40 bg-sky-900/20 p-3 text-sm text-sky-100">
              <div className="font-semibold">missing_frontend_components (backend inventory hint)</div>
              <ul className="mt-1 list-inside list-disc">
                {(spine.missing_frontend_components ?? []).map((x) => (
                  <li key={x}>{x}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : (
        <div className="mb-8 rounded-lg border border-slate-700 bg-slate-900/40 p-4 text-sm text-slate-400">
          Phase 4 operational spine unavailable (API error or offline). Environment checklist below still applies when loaded.
        </div>
      )}

      {/* EdgeSense execution (backend env) */}
      <div className="mb-8 rounded-lg border border-slate-700 bg-slate-900 p-6 shadow">
        <h3 className="mb-3 text-lg font-semibold text-white">Execution &amp; Alpaca (EdgeSense)</h3>
        {executionErr ? (
          <p className="text-sm text-amber-300">
            {executionErr.includes("404") ? "missing_backend_endpoint /api/execution/summary" : `not_configured — ${executionErr}`}
          </p>
        ) : execution ? (
          <div className="grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
            <div className="rounded border border-slate-800 bg-slate-800/50 p-3">
              <p className="text-slate-400">Alpaca / data stack</p>
              <p className="mt-1 text-slate-200">
                Use Platform checks below for connection. Paper keys are backend-only; this card reflects{" "}
                <span className="font-mono text-emerald-300">EDGESENSE_*</span> execution gates.
              </p>
            </div>
            <div className="rounded border border-slate-800 bg-slate-800/50 p-3">
              <p className="text-slate-400">Order router status</p>
              <ul className="mt-2 list-inside list-disc space-y-1 text-slate-300">
                <li>Execution mode: {execution.edgesense.execution_mode}</li>
                <li>Live trading enabled (env): {execution.edgesense.live_trading_enabled ? "true" : "false"}</li>
                <li>Human approval required: {execution.edgesense.require_human_approval ? "true" : "false"}</li>
                <li>Default order type: {execution.edgesense.default_order_type}</li>
                <li>Risk state: daily loss used {execution.risk_state.daily_loss_pct_used.toFixed(2)}% · lockout {execution.risk_state.risk_lockout_active ? "yes" : "no"}</li>
              </ul>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">Loading execution summary…</p>
        )}
      </div>

      {/* Overall Status */}
      <div className="mb-8">
        <div className={`p-6 rounded-lg border-2 ${
          readiness.status === "ready" ? "border-emerald-500 bg-emerald-900/20" :
          readiness.status === "partial" ? "border-yellow-500 bg-yellow-900/20" :
          "border-red-500 bg-red-900/20"
        }`}>
          <div className="flex items-center gap-4">
            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${
              readiness.status === "ready" ? "bg-green-500" :
              readiness.status === "partial" ? "bg-yellow-500" :
              "bg-red-500"
            }`}>
              <span className="text-white text-2xl font-bold">
                {readiness.status === "ready" ? "✓" :
                 readiness.status === "partial" ? "⚠" :
                 "✗"}
              </span>
            </div>
            <div>
              <h2 className="text-xl font-semibold capitalize">
                {readiness.status.replace("_", " ")}
              </h2>
              <p className="text-sm text-slate-400">
                Generated at: {new Date(readiness.generated_at).toLocaleString()}
              </p>
            </div>
          </div>

          {readiness.blockers.length > 0 && (
            <div className="mt-4 p-4 bg-red-900/30 rounded border border-red-700">
              <h3 className="font-semibold text-red-300 mb-2">Blockers (Must Fix)</h3>
              <ul className="list-disc list-inside text-red-400 text-sm">
                {readiness.blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}

          {readiness.warnings.length > 0 && (
            <div className="mt-4 p-4 bg-yellow-900/30 rounded border border-yellow-700">
              <h3 className="font-semibold text-yellow-300 mb-2">Warnings (Review Recommended)</h3>
              <ul className="list-disc list-inside text-yellow-400 text-sm">
                {readiness.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Check Sections Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Persistence Section */}
        <div className="bg-slate-900 rounded-lg shadow border border-slate-700 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
            <span className="w-3 h-3 rounded-full bg-blue-500"></span>
            Persistence
          </h3>
          <div className="space-y-3">
            {persistenceChecks.map((check) => (
              <div key={check.key} className="flex items-start gap-3 p-3 bg-slate-800 rounded">
                <div className={`w-3 h-3 rounded-full mt-1.5 ${statusColors[check.status]}`} />
                <div className="flex-1">
                  <div className="font-medium text-sm">{check.label}</div>
                  <div className="text-sm text-gray-600">{check.message}</div>
                  <div className="text-xs text-gray-400 mt-1">Required for: {check.required_for}</div>
                </div>
              </div>
            ))}
            {persistenceChecks.length === 0 && (
              <p className="text-gray-500 text-sm">No persistence checks configured</p>
            )}
          </div>
        </div>

        {/* Monitoring Section */}
        <div className="bg-slate-900 rounded-lg shadow border border-slate-700 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
            <span className="w-3 h-3 rounded-full bg-purple-500"></span>
            Monitoring & Observability
          </h3>
          <div className="space-y-3">
            {monitoringChecks.map((check) => (
              <div key={check.key} className="flex items-start gap-3 p-3 bg-slate-800 rounded">
                <div className={`w-3 h-3 rounded-full mt-1.5 ${statusColors[check.status]}`} />
                <div className="flex-1">
                  <div className="font-medium text-sm">{check.label}</div>
                  <div className="text-sm text-gray-600">{check.message}</div>
                </div>
              </div>
            ))}
            {monitoringChecks.length === 0 && (
              <p className="text-gray-500 text-sm">No monitoring checks configured</p>
            )}
          </div>

          {/* Tracing Sub-section */}
          {tracing && (
            <div className="mt-4 p-4 bg-slate-800 rounded border border-slate-600">
              <h4 className="font-semibold text-sm mb-3 text-white">LangSmith Tracing</h4>
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${tracing.enabled ? "bg-green-500" : "bg-gray-400"}`} />
                  <span>Enabled: {tracing.enabled ? "Yes" : "No"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${tracing.configured ? "bg-green-500" : "bg-gray-400"}`} />
                  <span>Configured: {tracing.configured ? "Yes" : "No"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${tracing.api_key_configured ? "bg-green-500" : "bg-gray-400"}`} />
                  <span>API Key: {tracing.api_key_configured ? "Present" : "Missing"}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${tracing.project_configured ? "bg-green-500" : "bg-gray-400"}`} />
                  <span>Project: {tracing.project_configured ? "Set" : "Not set"}</span>
                </div>
              </div>
              <div className="mt-3 text-xs text-gray-500">
                Mode: <span className="font-mono">{tracing.mode}</span>
              </div>
            </div>
          )}
        </div>

        {/* Safety Section */}
        <div className="bg-slate-900 rounded-lg shadow border border-slate-700 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            Safety Guards
          </h3>
          <div className="space-y-3">
            {safetyChecks.map((check) => (
              <div key={check.key} className={`flex items-start gap-3 p-3 rounded ${
                check.status === "pass" ? "bg-emerald-900/30" :
                check.status === "warn" ? "bg-yellow-900/30" :
                "bg-red-900/30"
              }`}>
                <div className={`w-3 h-3 rounded-full mt-1.5 ${statusColors[check.status]}`} />
                <div className="flex-1">
                  <div className="font-medium text-sm">{check.label}</div>
                  <div className="text-sm text-gray-600">{check.message}</div>
                </div>
              </div>
            ))}
            {safetyChecks.length === 0 && (
              <p className="text-gray-500 text-sm">No safety checks configured</p>
            )}
          </div>
        </div>

        {/* Configuration Section */}
        <div className="bg-slate-900 rounded-lg shadow border border-slate-700 p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2 text-white">
            <span className="w-3 h-3 rounded-full bg-gray-500"></span>
            Configuration
          </h3>
          <div className="space-y-3">
            {configChecks.map((check) => (
              <div key={check.key} className="flex items-start gap-3 p-3 bg-slate-800 rounded">
                <div className={`w-3 h-3 rounded-full mt-1.5 ${statusColors[check.status]}`} />
                <div className="flex-1">
                  <div className="font-medium text-sm">{check.label}</div>
                  <div className="text-sm text-gray-600">{check.message}</div>
                </div>
              </div>
            ))}
            {configChecks.length === 0 && (
              <p className="text-gray-500 text-sm">No configuration checks configured</p>
            )}
          </div>
        </div>
      </div>

      {/* All Checks Table */}
      <div className="mt-8 bg-slate-900 rounded-lg shadow border border-slate-700 p-6">
        <h3 className="text-lg font-semibold mb-4 text-white">All Checks ({readiness.checks.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-800">
              <tr>
                <th className="px-4 py-2 text-left font-medium text-slate-300">Check</th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">Status</th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">Message</th>
                <th className="px-4 py-2 text-left font-medium text-slate-300">Required For</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {readiness.checks.map((check) => (
                <tr key={check.key} className="hover:bg-slate-800">
                  <td className="px-4 py-3 font-medium text-slate-200">{check.label}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      check.status === "pass" ? "bg-emerald-900/50 text-emerald-300" :
                      check.status === "warn" ? "bg-yellow-900/50 text-yellow-300" :
                      "bg-red-900/50 text-red-300"
                    }`}>
                      {check.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{check.message}</td>
                  <td className="px-4 py-3 text-slate-500">{check.required_for}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
