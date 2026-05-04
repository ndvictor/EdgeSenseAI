"use client";

import React, { useEffect, useState } from "react";
import { api, PlatformReadinessResponse, TracingStatusResponse } from "@/lib/api";

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
  const [tracing, setTracing] = useState<TracingStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [readinessData, tracingData] = await Promise.all([
          api.getPlatformReadiness(),
          api.getTracingStatus(),
        ]);
        setReadiness(readinessData);
        setTracing(tracingData);
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
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-red-700 font-semibold mb-2">Error Loading Platform Readiness</h2>
          <p className="text-red-600">{error}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!readiness) {
    return (
      <div className="p-6">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <p className="text-yellow-700">No readiness data available</p>
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
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Platform Readiness</h1>
          <p className="text-gray-600 mt-1">
            System health, persistence status, and safety configuration
          </p>
        </div>
        <button
          onClick={handleRefresh}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
          Refresh
        </button>
      </div>

      {/* Overall Status */}
      <div className="mb-8">
        <div className={`p-6 rounded-lg border-2 ${
          readiness.status === "ready" ? "border-green-500 bg-green-50" :
          readiness.status === "partial" ? "border-yellow-500 bg-yellow-50" :
          "border-red-500 bg-red-50"
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
              <p className="text-sm text-gray-600">
                Generated at: {new Date(readiness.generated_at).toLocaleString()}
              </p>
            </div>
          </div>

          {readiness.blockers.length > 0 && (
            <div className="mt-4 p-4 bg-red-100 rounded">
              <h3 className="font-semibold text-red-800 mb-2">Blockers (Must Fix)</h3>
              <ul className="list-disc list-inside text-red-700 text-sm">
                {readiness.blockers.map((b, i) => <li key={i}>{b}</li>)}
              </ul>
            </div>
          )}

          {readiness.warnings.length > 0 && (
            <div className="mt-4 p-4 bg-yellow-100 rounded">
              <h3 className="font-semibold text-yellow-800 mb-2">Warnings (Review Recommended)</h3>
              <ul className="list-disc list-inside text-yellow-700 text-sm">
                {readiness.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}
        </div>
      </div>

      {/* Check Sections Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Persistence Section */}
        <div className="bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-blue-500"></span>
            Persistence
          </h3>
          <div className="space-y-3">
            {persistenceChecks.map((check) => (
              <div key={check.key} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
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
        <div className="bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-purple-500"></span>
            Monitoring & Observability
          </h3>
          <div className="space-y-3">
            {monitoringChecks.map((check) => (
              <div key={check.key} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
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
            <div className="mt-4 p-4 bg-gray-50 rounded border">
              <h4 className="font-semibold text-sm mb-3">LangSmith Tracing</h4>
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
        <div className="bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500"></span>
            Safety Guards
          </h3>
          <div className="space-y-3">
            {safetyChecks.map((check) => (
              <div key={check.key} className={`flex items-start gap-3 p-3 rounded ${
                check.status === "pass" ? "bg-green-50" :
                check.status === "warn" ? "bg-yellow-50" :
                "bg-red-50"
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
        <div className="bg-white rounded-lg shadow border p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-gray-500"></span>
            Configuration
          </h3>
          <div className="space-y-3">
            {configChecks.map((check) => (
              <div key={check.key} className="flex items-start gap-3 p-3 bg-gray-50 rounded">
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
      <div className="mt-8 bg-white rounded-lg shadow border p-6">
        <h3 className="text-lg font-semibold mb-4">All Checks ({readiness.checks.length})</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left font-medium">Check</th>
                <th className="px-4 py-2 text-left font-medium">Status</th>
                <th className="px-4 py-2 text-left font-medium">Message</th>
                <th className="px-4 py-2 text-left font-medium">Required For</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {readiness.checks.map((check) => (
                <tr key={check.key} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium">{check.label}</td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
                      check.status === "pass" ? "bg-green-100 text-green-800" :
                      check.status === "warn" ? "bg-yellow-100 text-yellow-800" :
                      "bg-red-100 text-red-800"
                    }`}>
                      {check.status.toUpperCase()}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{check.message}</td>
                  <td className="px-4 py-3 text-gray-500">{check.required_for}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
