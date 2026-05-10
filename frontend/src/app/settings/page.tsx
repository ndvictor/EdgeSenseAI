"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { 
  api, 
  type SettingsResponse, 
  type TradingSettingsUpdate,
  type LlmGatewaySettingsUpdate,
  type MarketDataSettingsUpdate,
  type NewsSettingsUpdate,
  type PlatformFeaturesUpdate,
  type RateLimitSettingsUpdate,
  type MasterAdminSettingsUpdate,
  type RiskSettings,
  type AlpacaPaperSnapshot,
  type PlatformIntegrationChecksResponse,
  type WorkflowRunbookStatusResponse,
  type WorkflowRunbookStagesResponse,
  type PlatformReadinessStatusResponse,
  type FinalReadinessHttpResponse,
} from "@/lib/api";
import { PageHeader } from "@/components/Cards";
import { 
  WalletCards, Zap, BookOpen, Globe, Brain, Radar, Target, Users, 
  BrainCircuit, Gauge, BellRing, Activity, FlaskConical, ShieldCheck, 
  DatabaseZap, TrendingUp, LineChart, Bitcoin, BarChart3, ClipboardList,
  Settings as SettingsIcon, Activity as ActivityIcon, ClipboardCopy, Download, Loader2, Shield
} from "lucide-react";

/** Shorter run: core connectivity + a few pipelines (~10–40s typical). */
const INTEGRATION_QUICK_CHECKS = [
  "data_source_connectivity",
  "data_freshness",
  "market_snapshot",
  "feature_pipeline",
  "signal_scanner",
  "risk_check",
  "paper_order",
  "alerts",
];

export const dynamic = "force-dynamic";

function SettingsPageInner() {
  const searchParams = useSearchParams();
  const [settings, setSettings] = useState<SettingsResponse | null>(null);
  const [alpaca, setAlpaca] = useState<AlpacaPaperSnapshot | null>(null);
  const [riskDraft, setRiskDraft] = useState<RiskSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [integrationMode, setIntegrationMode] = useState<"full" | "quick">("quick");
  const [integrationSymbols, setIntegrationSymbols] = useState("");
  const [integrationRunning, setIntegrationRunning] = useState(false);
  const [integrationReport, setIntegrationReport] = useState<PlatformIntegrationChecksResponse | null>(null);
  const [integrationRunMs, setIntegrationRunMs] = useState<number | null>(null);
  const [integrationError, setIntegrationError] = useState<string | null>(null);
  const [runbookStatus, setRunbookStatus] = useState<WorkflowRunbookStatusResponse | null>(null);
  const [runbookStages, setRunbookStages] = useState<WorkflowRunbookStagesResponse | null>(null);
  const [platformReadiness, setPlatformReadiness] = useState<PlatformReadinessStatusResponse | null>(null);
  const [finalReadiness, setFinalReadiness] = useState<FinalReadinessHttpResponse | null>(null);
  const [activeTab, setActiveTab] = useState<
    "overview" | "workflow" | "readiness" | "master_admin"
  >("overview");

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (!tab) return;
    if (tab === "overview" || tab === "workflow" || tab === "readiness" || tab === "master_admin") setActiveTab(tab);
  }, [searchParams]);

  const loadSettings = () => {
    api.getSettings()
      .then(setSettings)
      .catch((err) => setError(err.message));
  };

  const loadAlpaca = () => {
    api.getAlpacaPaperSnapshot()
      .then(setAlpaca)
      .catch((err) => console.error("Failed to load Alpaca data:", err));
  };

  useEffect(() => {
    loadSettings();
    loadAlpaca();
    api.getWorkflowRunbookStatus().then(setRunbookStatus).catch(() => setRunbookStatus(null));
    api.getWorkflowRunbookStages().then(setRunbookStages).catch(() => setRunbookStages(null));
    api.getPlatformReadiness().then(setPlatformReadiness).catch(() => setPlatformReadiness(null));
    api.getFinalReadiness().then(setFinalReadiness).catch(() => setFinalReadiness(null));
  }, []);

  useEffect(() => {
    if (settings?.risk) setRiskDraft(settings.risk);
  }, [settings?.risk]);

  const riskDirty = Boolean(
    settings?.risk &&
      riskDraft &&
      (settings.risk.max_risk_per_trade_percent !== riskDraft.max_risk_per_trade_percent ||
        settings.risk.max_daily_loss_percent !== riskDraft.max_daily_loss_percent ||
        settings.risk.max_position_size_percent !== riskDraft.max_position_size_percent ||
        settings.risk.min_reward_risk_ratio !== riskDraft.min_reward_risk_ratio),
  );

  const saveRiskDraft = async () => {
    if (!settings?.risk || !riskDraft || loading || !riskDirty) return;
    setLoading(true);
    setMessage(null);
    try {
      const updated = await api.updateSettings({
        risk: {
          max_risk_per_trade_percent: riskDraft.max_risk_per_trade_percent,
          max_daily_loss_percent: riskDraft.max_daily_loss_percent,
          max_position_size_percent: riskDraft.max_position_size_percent,
          min_reward_risk_ratio: riskDraft.min_reward_risk_ratio,
        },
      });
      setSettings(updated);
      setMessage("Risk settings saved to runtime_settings.json");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update risk settings");
    } finally {
      setLoading(false);
    }
  };

  const updateTrading = async (updates: TradingSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ trading: updates });
      setSettings(updated);
      setMessage("Trading settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateLlmGateway = async (updates: LlmGatewaySettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ llm_gateway: updates });
      setSettings(updated);
      setMessage("LLM Gateway settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateMarketData = async (updates: MarketDataSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ market_data: updates });
      setSettings(updated);
      setMessage("Market Data settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateNews = async (updates: NewsSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ news: updates });
      setSettings(updated);
      setMessage("News settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updatePlatform = async (updates: PlatformFeaturesUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ platform: updates });
      setSettings(updated);
      setMessage("Platform settings updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateRateLimits = async (updates: RateLimitSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    
    try {
      const updated = await api.updateSettings({ rate_limits: updates });
      setSettings(updated);
      setMessage("Rate limits updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update setting");
    } finally {
      setLoading(false);
    }
  };

  const updateMasterAdmin = async (updates: MasterAdminSettingsUpdate) => {
    if (!settings || loading) return;
    setLoading(true);
    setMessage(null);
    try {
      const updated = await api.updateSettings({
        master_admin: {
          ...updates,
          last_updated_by: "settings_ui",
        },
      });
      setSettings(updated);
      setMessage("Master Admin controls updated successfully");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update Master Admin controls");
    } finally {
      setLoading(false);
    }
  };

  const resetSettings = async () => {
    if (loading) return;
    setLoading(true);
    try {
      const updated = await api.resetSettings();
      setSettings(updated);
      setMessage("Settings reset to defaults");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset settings");
    } finally {
      setLoading(false);
    }
  };

  const runIntegrationMatrix = async () => {
    setIntegrationRunning(true);
    setIntegrationError(null);
    setIntegrationReport(null);
    setIntegrationRunMs(null);
    const t0 = typeof performance !== "undefined" ? performance.now() : Date.now();
    try {
      const symbols = integrationSymbols.split(",").map((s) => s.trim()).filter(Boolean);
      const payload = {
        symbols,
        source: "auto" as const,
        ...(integrationMode === "quick" ? { checks: INTEGRATION_QUICK_CHECKS } : {}),
        submit_real_paper_order: false,
      };
      const res = await api.runIntegrationChecks(payload);
      setIntegrationReport(res);
      const t1 = typeof performance !== "undefined" ? performance.now() : Date.now();
      setIntegrationRunMs(Math.round(t1 - t0));
      setMessage(`Integration matrix finished (${res.status}). Run ID ${res.run_id}`);
    } catch (err) {
      setIntegrationError(err instanceof Error ? err.message : "Integration run failed");
    } finally {
      setIntegrationRunning(false);
    }
  };

  const downloadIntegrationReport = () => {
    if (!integrationReport) return;
    const blob = new Blob([JSON.stringify(integrationReport, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `integration-checks-${integrationReport.run_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const copyIntegrationReport = async () => {
    if (!integrationReport) return;
    await navigator.clipboard.writeText(JSON.stringify(integrationReport, null, 2));
    setMessage("Report copied to clipboard");
  };

  const ToggleSwitch = ({ 
    label, 
    description, 
    enabled, 
    onToggle, 
    danger = false,
    disabled = false
  }: { 
    label: string; 
    description: string; 
    enabled: boolean; 
    onToggle: () => void;
    danger?: boolean;
    disabled?: boolean;
  }) => (
    <div className={`rounded-xl border p-4 ${danger ? "border-red-800 bg-red-950/20" : "border-emerald-400/15 bg-black/35 backdrop-blur"} ${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className={`font-semibold ${danger ? "text-red-400" : "text-white"}`}>{label}</h3>
          <p className="text-sm text-slate-400">{description}</p>
        </div>
        <button
          onClick={onToggle}
          disabled={loading || disabled}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            enabled 
              ? danger ? "bg-red-600" : "bg-emerald-600"
              : "bg-slate-700"
          } ${loading ? "cursor-wait" : "cursor-pointer"}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? "translate-x-6" : "translate-x-1"
            }`}
          />
        </button>
      </div>
    </div>
  );

  const NumberInput = ({
    label,
    description,
    value,
    onChange,
    min,
    max,
    step = 1
  }: {
    label: string;
    description: string;
    value: number;
    onChange: (val: number) => void;
    min?: number;
    max?: number;
    step?: number;
  }) => (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
      <div>
        <h3 className="font-semibold text-white">{label}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <input
        type="number"
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        min={min}
        max={max}
        step={step}
        disabled={loading}
        className="mt-3 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
      />
    </div>
  );

  const TextInput = ({
    label,
    description,
    value,
    onChange,
    placeholder
  }: {
    label: string;
    description: string;
    value: string;
    onChange: (val: string) => void;
    placeholder?: string;
  }) => (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
      <div>
        <h3 className="font-semibold text-white">{label}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        disabled={loading}
        className="mt-3 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
      />
    </div>
  );

  const SelectInput = ({
    label,
    description,
    value,
    onChange,
    options
  }: {
    label: string;
    description: string;
    value: string;
    onChange: (val: string) => void;
    options: { value: string; label: string }[];
  }) => (
    <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
      <div>
        <h3 className="font-semibold text-white">{label}</h3>
        <p className="text-sm text-slate-400">{description}</p>
      </div>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={loading}
        className="mt-3 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white focus:border-emerald-500 focus:outline-none disabled:opacity-50"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="Platform Configuration"
          title="Settings"
          description="Manage platform runtime settings. Values are saved to runtime_settings.json on the backend and drive trading gates, LLM policy, market data selection, and integrations. Live trading stays locked unless human approval is required."
        />

        {error && (
          <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {error}
            <button onClick={() => setError(null)} className="ml-2 text-red-300 hover:text-red-100">Dismiss</button>
          </div>
        )}

        {/* Settings subtabs */}
        <div className="mb-4 border-b border-emerald-400/15 pb-2">
          <div className="flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {(
              [
                ["overview", "Overview"],
                ["workflow", "Workflow"],
                ["readiness", "Readiness"],
                ["master_admin", "Master Admin"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setActiveTab(id)}
                className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  activeTab === id
                    ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                    : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Overview cards */}
        {activeTab === "overview" && settings && (
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {/* Stage 1 — Workflow / gates summary */}
            <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Shield className="h-5 w-5 text-emerald-400" />
                  <h3 className="font-semibold text-emerald-300">Stage 1 — Master Admin</h3>
                </div>
                <span
                  className={`rounded-full border px-2 py-1 text-xs font-semibold ${
                    settings.master_admin.workflow_running && settings.master_admin.workflow_enabled && !settings.master_admin.emergency_stop
                      ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200"
                      : "border-white/10 bg-white/[0.03] text-slate-300"
                  }`}
                >
                  {settings.master_admin.workflow_running && settings.master_admin.workflow_enabled && !settings.master_admin.emergency_stop ? "Running" : "Stopped"}
                </span>
              </div>

              <div className="space-y-2 text-sm">
                {[
                  { label: "Workflow enabled", enabled: settings.master_admin.workflow_enabled },
                  { label: "Execution enabled", enabled: settings.master_admin.execution_enabled },
                  { label: "Emergency stop", enabled: settings.master_admin.emergency_stop, invert: true },
                  { label: "Human approval", enabled: settings.trading.require_human_approval },
                  { label: "Broker execution", enabled: settings.trading.broker_execution_enabled },
                  { label: "Paper trading", enabled: settings.trading.paper_trading_enabled },
                  { label: "Live trading", enabled: settings.trading.live_trading_enabled },
                ].map((s) => {
                  const on = s.invert ? !s.enabled : s.enabled;
                  return (
                    <div key={s.label} className="flex items-center justify-between">
                      <span className="text-slate-400">{s.label}</span>
                      <span className={`flex items-center gap-1 ${on ? "text-emerald-400" : "text-rose-400"}`}>
                        <span className={`h-2 w-2 rounded-full ${on ? "bg-emerald-500" : "bg-rose-500"}`} />
                        {on ? "On" : "Off"}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4">
                <Link
                  href="/settings?tab=master_admin"
                  className="inline-flex w-full items-center justify-center rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs font-bold uppercase text-slate-200 transition hover:bg-white/[0.06]"
                >
                  Manage configuration in Master Admin
                </Link>
              </div>
            </div>
            {(runbookStages?.stages || []).filter((s) => typeof s.stage_number === "number" && s.stage_number >= 1 && s.stage_number <= 14).map((st) => {
              const impl = String(st.implementation_status || "");
              const isPresent = impl === "present" || impl === "existing_gated";
              const isPartial = impl === "partial_existing";
              const statusLabel = isPresent ? "Configured" : isPartial ? "Partial" : "Backlog";
              const statusClass = isPresent
                ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200"
                : isPartial
                  ? "border-amber-400/40 bg-amber-500/10 text-amber-200"
                  : "border-white/10 bg-white/[0.03] text-slate-300";
              return (
                <div key={st.stage_key || st.stage_number} className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-xs font-semibold text-slate-500">Stage {st.stage_number}</div>
                      <div className="mt-1 font-semibold text-white">{st.stage_name || st.stage_key || `Stage ${st.stage_number}`}</div>
                      <div className="mt-2 text-xs text-slate-500 line-clamp-2">
                        {st.backend_endpoint_family ? `API: ${st.backend_endpoint_family}` : "API: —"}
                      </div>
                      <div className="mt-1 text-xs text-slate-500 line-clamp-1">{st.frontend_route ? `UI: ${st.frontend_route}` : "UI: —"}</div>
                    </div>
                    <span className={`shrink-0 rounded-full border px-2 py-1 text-xs font-semibold ${statusClass}`}>{statusLabel}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "workflow" && settings && (
          <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
            <div className="mb-4 flex flex-wrap items-start gap-3">
              <ClipboardList className="mt-1 h-6 w-6 shrink-0 text-emerald-400" />
              <div className="min-w-0 flex-1">
                <h2 className="text-xl font-semibold text-emerald-400">Workflow configuration status</h2>
                <p className="mt-2 text-sm text-slate-400">
                  This is a read-only rollup across the workflow spine. Make all configuration changes in{" "}
                  <Link className="text-emerald-300 hover:text-emerald-200 underline" href="/settings?tab=master_admin">
                    Master Admin
                  </Link>
                  .
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-white">Workflow runbook</div>
                    <div className="mt-1 text-xs text-slate-500">Source: `GET /api/workflow-runbook/status` + `/stages`</div>
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-1 text-xs font-semibold text-slate-300">
                    {runbookStatus?.summary?.workflow_status ? String(runbookStatus.summary.workflow_status) : "unknown"}
                  </span>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
                  <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                    <div className="text-xs text-slate-500">Total stages</div>
                    <div className="mt-1 font-mono text-slate-200">{String(runbookStatus?.summary?.total_stages ?? "—")}</div>
                  </div>
                  <div className="rounded-lg border border-white/10 bg-white/[0.02] p-3">
                    <div className="text-xs text-slate-500">Implemented</div>
                    <div className="mt-1 font-mono text-slate-200">{String(runbookStatus?.summary?.implemented_stages ?? "—")}</div>
                  </div>
                </div>
                <div className="mt-3 text-sm text-slate-400">{String(runbookStatus?.summary?.next_action ?? "—")}</div>
              </div>

              <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-white">Platform readiness</div>
                    <div className="mt-1 text-xs text-slate-500">Source: `GET /api/platform-readiness/status`</div>
                  </div>
                  <span className="rounded-full border border-white/10 bg-white/[0.03] px-2 py-1 text-xs font-semibold text-slate-300">
                    {platformReadiness?.status ? String(platformReadiness.status) : "unknown"}
                  </span>
                </div>
                <div className="mt-3 text-sm text-slate-400">{String(platformReadiness?.next_action ?? "—")}</div>
                {(platformReadiness?.missing_backend_components?.length || 0) > 0 ? (
                  <div className="mt-3 text-sm text-rose-200">
                    Missing backend: {platformReadiness?.missing_backend_components?.slice(0, 4).join(", ")}
                    {(platformReadiness?.missing_backend_components?.length || 0) > 4 ? " …" : ""}
                  </div>
                ) : null}
              </div>
            </div>

            <div className="mt-6 rounded-xl border border-emerald-400/15 bg-black/35 p-4">
              <h3 className="text-sm font-semibold text-white">Workflow chain (configured vs gated)</h3>
              <p className="mt-1 text-sm text-slate-400">
                This list mirrors your desired flow. “Configured” is derived from readiness endpoints (no execution is triggered).
              </p>
              <div className="mt-4 space-y-2">
                {[
                  { name: "Market Data", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/qlib/status" && e.present) ?? false) || settings.market_data.market_data_provider !== "not_configured" },
                  { name: "Data Quality + Timestamp Validation", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/platform-readiness/status" && e.present) ?? false) },
                  { name: "Feature Store", ok: Boolean(settings.platform.vector_memory_enabled) },
                  { name: "Qlib Research Agent", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/qlib/status" && e.present) ?? false) },
                  { name: "Model Selection Agent", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/model-evidence/status" && e.present) ?? true) },
                  { name: "Qlib Backtest Validation Agent", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/qlib/status" && e.present) ?? true) },
                  { name: "Strategy Eligibility Agent", ok: Boolean(runbookStages?.stages?.some((s) => s.stage_key === "strategy_eligibility" && String(s.implementation_status) === "present") ?? true) },
                  { name: "Signal Ensemble + Ranking", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/agent-runtime/status" && e.present) ?? false) },
                  { name: "Risk Manager", ok: Boolean(settings.master_admin.execution_enabled) },
                  { name: "Execution Planner", ok: Boolean(runbookStages?.stages?.some((s) => s.stage_key === "execution_planner" && String(s.implementation_status) === "present") ?? true) },
                  { name: "Approval Queue", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/approval-queue/status" && e.present) ?? true) },
                  { name: "Paper Trading", ok: Boolean(settings.trading.paper_trading_enabled && settings.master_admin.execution_enabled) },
                  { name: "Post-Trade Evaluation", ok: Boolean(runbookStages?.stages?.some((s) => s.stage_key === "post_trade_evaluation" && String(s.implementation_status) === "present") ?? true) },
                  { name: "Learning Loop", ok: Boolean(runbookStages?.stages?.some((s) => s.stage_key === "learning_loop" && String(s.implementation_status) === "present") ?? true) },
                  { name: "Strategy Ranking Update", ok: Boolean(finalReadiness?.endpoints?.some((e) => e.path === "/api/strategy-evidence/status" && e.present) ?? true) },
                ].map((row) => (
                  <div key={row.name} className="flex items-center justify-between gap-3 rounded-lg border border-white/10 bg-white/[0.02] px-3 py-2">
                    <div className="text-sm text-slate-300">{row.name}</div>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-xs font-semibold ${
                        row.ok ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200" : "border-rose-400/40 bg-rose-500/10 text-rose-200"
                      }`}
                    >
                      {row.ok ? "Configured" : "Not configured"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        )}

        {message && (
          <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
            {message}
            <button onClick={() => setMessage(null)} className="ml-2 text-emerald-300 hover:text-emerald-100">Dismiss</button>
          </div>
        )}

        {!settings ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading settings...</div>
        ) : (
          <div className="space-y-6">
            {/* Master Admin Control Plane */}
            {activeTab === "master_admin" && settings && (
              <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
                <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <h2 className="text-xl font-semibold text-emerald-400">Master Admin Control Plane</h2>
                    <p className="mt-2 text-sm text-slate-400">
                      Runtime safety gates for workflows and execution. Emergency stop overrides everything. Force close is a request flag only in v1 (no orders are submitted).
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      Last updated by <span className="text-slate-300">{settings.master_admin.last_updated_by || "unknown"}</span>{" "}
                      {settings.master_admin.updated_at ? (
                        <>
                          at <span className="text-slate-300">{settings.master_admin.updated_at}</span>
                        </>
                      ) : null}
                    </p>
                  </div>
                </div>

                {(() => {
                  const emergencyStop = settings.master_admin.emergency_stop;
                  const executionEnabled = settings.master_admin.execution_enabled;
                  const workflowEnabled = settings.master_admin.workflow_enabled;
                  const workflowRunning = Boolean(settings.master_admin.workflow_running);
                  const forceCloseRequested = settings.master_admin.force_close_requested;
                  const humanApproval = settings.trading.require_human_approval;
                  const brokerExecution = settings.trading.broker_execution_enabled;
                  const liveTrading = settings.trading.live_trading_enabled;
                  const paperTrading = settings.trading.paper_trading_enabled;

                  const disableAll = loading;
                  const disabledByEmergency = emergencyStop;

                  const liveDisabled =
                    disableAll ||
                    disabledByEmergency ||
                    !executionEnabled ||
                    !humanApproval ||
                    !brokerExecution;

                  return (
                    <div className="space-y-6">
                      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h3 className="font-semibold text-white">Workflow Status</h3>
                              <p className="text-sm text-slate-400">
                                {workflowRunning && workflowEnabled && !disabledByEmergency ? "Workflow running." : "Workflow stopped."} This is a runtime switch
                                (no broker submission).
                              </p>
                              <div className="mt-2 text-xs text-slate-500">
                                Gate: <span className="font-mono text-slate-300">{workflowEnabled ? "WORKFLOW_ENABLED=true" : "WORKFLOW_ENABLED=false"}</span>
                              </div>
                            </div>
                            <button
                              type="button"
                              onClick={() =>
                                updateMasterAdmin(
                                  workflowRunning ? { workflow_running: false } : { workflow_running: true, workflow_enabled: true },
                                )
                              }
                              disabled={disableAll || disabledByEmergency}
                              className={`rounded-xl border px-4 py-2 text-sm font-bold uppercase transition disabled:opacity-50 ${
                                workflowRunning
                                  ? "border-white/10 bg-white/[0.03] text-slate-200 hover:bg-white/[0.06]"
                                  : "border-emerald-400/40 bg-emerald-500/10 text-emerald-200 hover:bg-emerald-500/20"
                              }`}
                            >
                              {workflowRunning ? "Stop" : "Start"}
                            </button>
                          </div>
                        </div>
                        <ToggleSwitch
                          label="Disable All Execution"
                          description="Blocks all order submission paths (paper + live)"
                          enabled={!executionEnabled}
                          onToggle={() => updateMasterAdmin({ execution_enabled: executionEnabled ? false : true })}
                          danger={!executionEnabled}
                          disabled={disableAll || disabledByEmergency}
                        />

                        <ToggleSwitch
                          label="Require Human Approval"
                          description="All sensitive execution paths require explicit confirmation"
                          enabled={humanApproval}
                          onToggle={() => updateTrading({ require_human_approval: !humanApproval })}
                          disabled={disableAll || disabledByEmergency}
                        />

                        <ToggleSwitch
                          label="Broker Execution"
                          description="Allow broker routing when gates pass"
                          enabled={brokerExecution}
                          onToggle={() => updateTrading({ broker_execution_enabled: !brokerExecution })}
                          danger={brokerExecution}
                          disabled={disableAll || disabledByEmergency || !executionEnabled}
                        />

                        <ToggleSwitch
                          label="Paper Trading"
                          description="Enable paper order submission (simulation)"
                          enabled={paperTrading}
                          onToggle={() => updateTrading({ paper_trading_enabled: !paperTrading })}
                          disabled={disableAll || disabledByEmergency || !executionEnabled}
                        />

                        <ToggleSwitch
                          label="Live Trading"
                          description="⚠️ Dangerous. Requires human approval and broker execution enabled."
                          enabled={liveTrading}
                          onToggle={() => updateTrading({ live_trading_enabled: !liveTrading })}
                          danger
                          disabled={liveDisabled}
                        />
                      </div>

                      <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
                        <div className="flex items-start justify-between gap-4">
                          <div>
                            <h3 className="font-semibold text-white">Workflow Mode</h3>
                            <p className="text-sm text-slate-400">Select paper vs live trading mode (live remains gated by approval + broker execution).</p>
                          </div>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={() => updateTrading({ paper_trading_enabled: true, live_trading_enabled: false })}
                              disabled={disableAll || disabledByEmergency || !executionEnabled}
                              className={`rounded-lg border px-3 py-2 text-xs font-bold uppercase transition disabled:opacity-50 ${
                                paperTrading && !liveTrading
                                  ? "border-emerald-400/40 bg-emerald-500/10 text-emerald-200"
                                  : "border-white/10 bg-white/[0.03] text-slate-200 hover:bg-white/[0.06]"
                              }`}
                            >
                              Paper
                            </button>
                            <button
                              type="button"
                              onClick={() => updateTrading({ live_trading_enabled: true })}
                              disabled={liveDisabled}
                              className={`rounded-lg border px-3 py-2 text-xs font-bold uppercase transition disabled:opacity-50 ${
                                liveTrading
                                  ? "border-red-400/40 bg-red-500/10 text-red-200"
                                  : "border-white/10 bg-white/[0.03] text-slate-200 hover:bg-white/[0.06]"
                              }`}
                            >
                              Live
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
                        <h3 className="text-lg font-semibold text-emerald-200">Configuration editor</h3>
                        <p className="mt-1 text-sm text-slate-400">
                          Edit all runtime configuration here. Changes are persisted to <span className="font-mono text-slate-300">runtime_settings.json</span>.
                        </p>

                        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
                          <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                            <h4 className="font-semibold text-white">Market Data</h4>
                            <div className="mt-3 space-y-3">
                              <ToggleSwitch
                                label="Alpaca Market Data"
                                description="Use Alpaca for market data feeds"
                                enabled={settings.market_data.alpaca_market_data_enabled}
                                onToggle={() => updateMarketData({ alpaca_market_data_enabled: !settings.market_data.alpaca_market_data_enabled })}
                                disabled={disableAll}
                              />
                              <SelectInput
                                label="Market data — try first"
                                description="Primary feed for quotes/bars when source is auto; fallbacks follow Provider priority."
                                value={settings.market_data.market_data_provider}
                                onChange={(val) => updateMarketData({ market_data_provider: val })}
                                options={[
                                  { value: "alpaca", label: "Alpaca" },
                                  { value: "polygon", label: "Polygon.io" },
                                  { value: "yfinance", label: "YFinance" },
                                ]}
                              />
                              <TextInput
                                label="Market — provider priority"
                                description="Additional feeds to try in order after primary (comma-separated)."
                                value={settings.market_data.market_data_provider_priority}
                                onChange={(val) => updateMarketData({ market_data_provider_priority: val })}
                                placeholder="alpaca,polygon,yfinance"
                              />
                              <NumberInput
                                label="Timeout (seconds)"
                                description="API request timeout"
                                value={settings.market_data.market_data_provider_timeout_seconds}
                                onChange={(val) => updateMarketData({ market_data_provider_timeout_seconds: val })}
                                min={1}
                                max={60}
                              />
                            </div>
                          </div>

                          <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                            <h4 className="font-semibold text-white">LLM Gateway</h4>
                            <div className="mt-3 space-y-3">
                              <ToggleSwitch
                                label="Enable Paid Tests"
                                description="Allow paid LLM API calls for testing"
                                enabled={settings.llm_gateway.llm_gateway_enable_paid_tests}
                                onToggle={() => updateLlmGateway({ llm_gateway_enable_paid_tests: !settings.llm_gateway.llm_gateway_enable_paid_tests })}
                                disabled={disableAll}
                              />
                              <ToggleSwitch
                                label="Embeddings Paid Calls"
                                description="Enable paid embedding API calls"
                                enabled={settings.llm_gateway.embeddings_enable_paid_calls}
                                onToggle={() => updateLlmGateway({ embeddings_enable_paid_calls: !settings.llm_gateway.embeddings_enable_paid_calls })}
                                disabled={disableAll}
                              />
                              <NumberInput
                                label="Daily Budget ($)"
                                description="Maximum daily spend on LLM APIs"
                                value={settings.llm_gateway.llm_gateway_daily_budget}
                                onChange={(val) => updateLlmGateway({ llm_gateway_daily_budget: val })}
                                min={0}
                                step={1}
                              />
                              <TextInput
                                label="Cheap Model"
                                description="Default cheap/fast model for simple tasks"
                                value={settings.llm_gateway.llm_gateway_default_cheap_model}
                                onChange={(val) => updateLlmGateway({ llm_gateway_default_cheap_model: val })}
                                placeholder="gpt-4o-mini"
                              />
                              <TextInput
                                label="Reasoning Model"
                                description="Default model for complex reasoning"
                                value={settings.llm_gateway.llm_gateway_default_reasoning_model}
                                onChange={(val) => updateLlmGateway({ llm_gateway_default_reasoning_model: val })}
                                placeholder="gpt-4o"
                              />
                              <TextInput
                                label="Fallback Model"
                                description="Fallback when primary models fail"
                                value={settings.llm_gateway.llm_gateway_default_fallback_model}
                                onChange={(val) => updateLlmGateway({ llm_gateway_default_fallback_model: val })}
                                placeholder="local-placeholder"
                              />
                            </div>
                          </div>

                          <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                            <h4 className="font-semibold text-white">News</h4>
                            <div className="mt-3 space-y-3">
                              <ToggleSwitch
                                label="News Provider"
                                description="Enable news feed integration"
                                enabled={settings.news.news_provider_enabled}
                                onToggle={() => updateNews({ news_provider_enabled: !settings.news.news_provider_enabled })}
                                disabled={disableAll}
                              />
                              <SelectInput
                                label="News — try first"
                                description="First news feed to use when the app aggregates headlines; configure API keys in .env."
                                value={settings.news.news_provider_primary}
                                onChange={(val) => updateNews({ news_provider_primary: val })}
                                options={[
                                  { value: "none", label: "None" },
                                  { value: "newsapi", label: "NewsAPI" },
                                  { value: "finnhub", label: "Finnhub" },
                                  { value: "benzinga", label: "Benzinga" },
                                ]}
                              />
                              <TextInput
                                label="News — provider priority"
                                description="Other news feeds to try after the first (comma-separated). Enables multiple backends without a single dropdown."
                                value={settings.news.news_provider_priority}
                                onChange={(val) => updateNews({ news_provider_priority: val })}
                                placeholder="newsapi,finnhub,benzinga"
                              />
                              <NumberInput
                                label="Timeout (seconds)"
                                description="News API request timeout"
                                value={settings.news.news_provider_timeout_seconds}
                                onChange={(val) => updateNews({ news_provider_timeout_seconds: val })}
                                min={1}
                                max={60}
                              />
                            </div>
                          </div>

                          <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                            <h4 className="font-semibold text-white">Platform + Limits</h4>
                            <div className="mt-3 space-y-3">
                              <ToggleSwitch
                                label="LangSmith Tracing"
                                description="Send traces to LangSmith for debugging"
                                enabled={settings.platform.langsmith_tracing}
                                onToggle={() => updatePlatform({ langsmith_tracing: !settings.platform.langsmith_tracing })}
                                disabled={disableAll}
                              />
                              <ToggleSwitch
                                label="Vector Memory"
                                description="Enable pgvector-based memory storage"
                                enabled={settings.platform.vector_memory_enabled}
                                onToggle={() => updatePlatform({ vector_memory_enabled: !settings.platform.vector_memory_enabled })}
                                disabled={disableAll}
                              />
                              <NumberInput
                                label="Max Daily LLM Cost ($)"
                                description="Daily spending limit on LLM APIs"
                                value={settings.rate_limits.max_daily_llm_cost}
                                onChange={(val) => updateRateLimits({ max_daily_llm_cost: val })}
                                min={0}
                                step={1}
                              />
                              <NumberInput
                                label="Max Daily Agent Runs"
                                description="Maximum agent executions per day"
                                value={settings.rate_limits.max_daily_agent_runs}
                                onChange={(val) => updateRateLimits({ max_daily_agent_runs: val })}
                                min={1}
                                step={10}
                              />
                            </div>
                          </div>
                        </div>

                        <div className="mt-4 rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                          <div className="flex flex-wrap items-center justify-between gap-3">
                            <div>
                              <h4 className="font-semibold text-white">Account Risk</h4>
                              <p className="text-sm text-slate-400">These thresholds drive risk gating across the workflow.</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={saveRiskDraft}
                                disabled={disableAll || !riskDirty}
                                className="rounded-xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-bold uppercase text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
                              >
                                Save risk
                              </button>
                              <button
                                type="button"
                                onClick={() => setRiskDraft(settings?.risk ?? null)}
                                disabled={disableAll || !riskDirty}
                                className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-bold uppercase text-slate-300 hover:bg-white/[0.06] disabled:opacity-50"
                              >
                                Reset
                              </button>
                            </div>
                          </div>
                          {!riskDraft ? (
                            <div className="mt-3 text-sm text-slate-400">Loading risk profile…</div>
                          ) : (
                            <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                              <NumberInput
                                label="Max risk per trade (%)"
                                description="Hard cap per-trade risk as a percent of equity"
                                value={riskDraft.max_risk_per_trade_percent}
                                onChange={(val) => setRiskDraft((prev) => (prev ? { ...prev, max_risk_per_trade_percent: val } : prev))}
                                min={0.1}
                                max={10}
                                step={0.1}
                              />
                              <NumberInput
                                label="Max daily loss (%)"
                                description="Stop trading after this daily drawdown"
                                value={riskDraft.max_daily_loss_percent}
                                onChange={(val) => setRiskDraft((prev) => (prev ? { ...prev, max_daily_loss_percent: val } : prev))}
                                min={0.5}
                                max={10}
                                step={0.1}
                              />
                              <NumberInput
                                label="Max position size (%)"
                                description="Max position size as a percent of buying power"
                                value={riskDraft.max_position_size_percent}
                                onChange={(val) => setRiskDraft((prev) => (prev ? { ...prev, max_position_size_percent: val } : prev))}
                                min={1}
                                max={100}
                                step={1}
                              />
                              <NumberInput
                                label="Min reward:risk (R)"
                                description="Reject trades below this reward:risk ratio (e.g. 3R)"
                                value={riskDraft.min_reward_risk_ratio}
                                onChange={(val) => setRiskDraft((prev) => (prev ? { ...prev, min_reward_risk_ratio: val } : prev))}
                                min={1}
                                max={20}
                                step={0.5}
                              />
                            </div>
                          )}
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <ToggleSwitch
                          label="Emergency Stop"
                          description="Hard stop: blocks execution and disables live/broker execution"
                          enabled={emergencyStop}
                          onToggle={() => updateMasterAdmin({ emergency_stop: !emergencyStop })}
                          danger
                          disabled={disableAll}
                        />
                        <div className="rounded-xl border border-red-800 bg-red-950/20 p-4">
                          <div className="flex items-center justify-between gap-4">
                            <div>
                              <h3 className="font-semibold text-red-400">Clear Emergency Stop</h3>
                              <p className="text-sm text-slate-400">Re-enable controls after confirming safety.</p>
                            </div>
                            <button
                              type="button"
                              onClick={() => updateMasterAdmin({ emergency_stop: false })}
                              disabled={disableAll || !emergencyStop}
                              className="rounded-xl border border-red-400/40 bg-red-500/10 px-4 py-2 text-sm font-bold uppercase text-red-200 hover:bg-red-500/20 disabled:opacity-50"
                            >
                              Clear
                            </button>
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
                        <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur">
                          <div className="flex items-center justify-between gap-4">
                            <div>
                              <h3 className="font-semibold text-white">Request Force Close Positions</h3>
                              <p className="text-sm text-slate-400">v1: request flag only (no orders submitted).</p>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() => updateMasterAdmin({ force_close_requested: true })}
                                disabled={disableAll || disabledByEmergency || forceCloseRequested}
                                className="rounded-xl border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm font-bold uppercase text-emerald-200 hover:bg-emerald-500/20 disabled:opacity-50"
                              >
                                Request
                              </button>
                              <button
                                type="button"
                                onClick={() => updateMasterAdmin({ force_close_requested: false })}
                                disabled={disableAll || !forceCloseRequested}
                                className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm font-bold uppercase text-slate-200 hover:bg-white/[0.06] disabled:opacity-50"
                              >
                                Clear
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })()}
              </section>
            )}

            {/* Configuration edits are centralized in Master Admin.
               The Overview/Workflow/Readiness tabs provide source-of-truth summaries. */}

            {/* Integration readiness matrix (Alpaca + stack QA) */}
            {activeTab === "readiness" && settings && (
            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
              <div className="mb-4 flex flex-wrap items-start gap-3">
                <Shield className="mt-1 h-6 w-6 shrink-0 text-emerald-400" />
                <div className="min-w-0 flex-1">
                  <h2 className="text-xl font-semibold text-emerald-400">Integration readiness matrix</h2>
                  <p className="mt-2 text-sm text-slate-400">
                    Runs backend checks against your configured keys (Alpaca paper, Polygon, Finnhub, FRED, etc.), then walks
                    the workflow spine (data → candidates → risk → execution preview) under the same gates shown in Master Admin.{" "}
                    <span className="text-slate-300">
                      Cursor&apos;s Alpaca MCP only helps agents inside the IDE; it does not replace this report. The platform
                      always tests through the EdgeSenseAI API using the same environment variables as the backend.
                    </span>
                  </p>
                  <p className="mt-2 text-sm text-slate-500">
                    Related source-of-truth endpoints:{" "}
                    <span className="text-slate-300 font-mono">/api/workflow-runbook/status</span>,{" "}
                    <span className="text-slate-300 font-mono">/api/platform-readiness/status</span>,{" "}
                    <span className="text-slate-300 font-mono">/api/final-readiness/status</span>.
                  </p>
                  <p className="mt-2 text-sm text-slate-500">
                    Typical duration: <span className="text-slate-300">quick preset ~15–45s</span>,{" "}
                    <span className="text-slate-300">full matrix ~45–120s</span> (network and provider rate limits dominate).
                    Request timeout is 3 minutes.
                  </p>
                </div>
              </div>

              <div className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                  <h3 className="font-semibold text-white">Run scope</h3>
                  <p className="mt-1 text-sm text-slate-400">Quick runs fewer checks; full runs the entire catalog (~18 checks).</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setIntegrationMode("quick")}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                        integrationMode === "quick"
                          ? "border border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
                          : "border border-white/10 text-slate-400 hover:bg-white/[0.04]"
                      }`}
                    >
                      Quick
                    </button>
                    <button
                      type="button"
                      onClick={() => setIntegrationMode("full")}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium ${
                        integrationMode === "full"
                          ? "border border-emerald-400/50 bg-emerald-500/15 text-emerald-200"
                          : "border border-white/10 text-slate-400 hover:bg-white/[0.04]"
                      }`}
                    >
                      Full matrix
                    </button>
                  </div>
                </div>
                <div className="rounded-xl border border-emerald-400/15 bg-black/35 p-4">
                  <h3 className="font-semibold text-white">Symbols</h3>
                  <p className="mt-1 text-sm text-slate-400">Comma-separated tickers for snapshots, scanner, and universe probes.</p>
                  <input
                    type="text"
                    value={integrationSymbols}
                    onChange={(e) => setIntegrationSymbols(e.target.value)}
                    disabled={integrationRunning}
                    placeholder="Optional symbols; blank checks configured services only"
                    className="mt-2 w-full rounded-lg border border-emerald-400/20 bg-black/40 px-3 py-2 text-sm text-white"
                  />
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={runIntegrationMatrix}
                  disabled={integrationRunning}
                  className="inline-flex items-center gap-2 rounded-xl border border-emerald-400/40 bg-emerald-500/15 px-5 py-2.5 text-sm font-bold uppercase tracking-wide text-emerald-200 hover:bg-emerald-500/25 disabled:opacity-50"
                >
                  {integrationRunning ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" /> Running…
                    </>
                  ) : (
                    "Run integration checks"
                  )}
                </button>
                {integrationRunMs !== null && (
                  <span className="text-sm text-slate-400">Wall time: {(integrationRunMs / 1000).toFixed(1)}s</span>
                )}
              </div>

              {integrationError && (
                <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {integrationError}
                </div>
              )}

              {integrationReport && (
                <div className="mt-6 space-y-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full px-3 py-1 text-xs font-semibold uppercase ${
                        integrationReport.status === "pass"
                          ? "bg-emerald-500/20 text-emerald-300"
                          : integrationReport.status === "warn"
                            ? "bg-amber-500/20 text-amber-200"
                            : "bg-red-500/20 text-red-200"
                      }`}
                    >
                      Overall: {integrationReport.status}
                    </span>
                    <span className="text-xs text-slate-500">run_id {integrationReport.run_id}</span>
                    <button
                      type="button"
                      onClick={copyIntegrationReport}
                      className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1 text-xs text-slate-300 hover:bg-white/[0.06]"
                    >
                      <ClipboardCopy className="h-3.5 w-3.5" /> Copy JSON
                    </button>
                    <button
                      type="button"
                      onClick={downloadIntegrationReport}
                      className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-3 py-1 text-xs text-slate-300 hover:bg-white/[0.06]"
                    >
                      <Download className="h-3.5 w-3.5" /> Download
                    </button>
                  </div>

                  {(integrationReport.blockers.length > 0 || integrationReport.warnings.length > 0) && (
                    <div className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-4 text-sm">
                      {integrationReport.blockers.length > 0 && (
                        <p className="text-red-200">
                          <span className="font-semibold">Blockers:</span> {integrationReport.blockers.join(" · ")}
                        </p>
                      )}
                      {integrationReport.warnings.length > 0 && (
                        <p className={integrationReport.blockers.length ? "mt-2 text-amber-100" : "text-amber-100"}>
                          <span className="font-semibold">Warnings:</span> {integrationReport.warnings.join(" · ")}
                        </p>
                      )}
                    </div>
                  )}

                  <div className="overflow-x-auto rounded-xl border border-emerald-400/10">
                    <table className="min-w-full text-left text-sm">
                      <thead className="border-b border-emerald-400/15 bg-black/40 text-slate-400">
                        <tr>
                          <th className="px-3 py-2 font-medium">Check</th>
                          <th className="px-3 py-2 font-medium">Where</th>
                          <th className="px-3 py-2 font-medium">Status</th>
                          <th className="px-3 py-2 font-medium">Message</th>
                          <th className="px-3 py-2 font-medium">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {integrationReport.checks.map((row) => (
                          <tr key={row.key} className="border-b border-white/[0.06] hover:bg-white/[0.02]">
                            <td className="px-3 py-2 align-top text-white">{row.label}</td>
                            <td className="px-3 py-2 align-top text-slate-400">{row.belongs_to}</td>
                            <td className="px-3 py-2 align-top">
                              <span
                                className={`rounded px-2 py-0.5 text-xs font-semibold uppercase ${
                                  row.status === "pass"
                                    ? "bg-emerald-500/15 text-emerald-300"
                                    : row.status === "warn"
                                      ? "bg-amber-500/15 text-amber-200"
                                      : row.status === "fail"
                                        ? "bg-red-500/15 text-red-200"
                                        : "bg-slate-600/30 text-slate-300"
                                }`}
                              >
                                {row.status}
                              </span>
                            </td>
                            <td className="max-w-md px-3 py-2 align-top text-slate-300">{row.message}</td>
                            <td className="whitespace-nowrap px-3 py-2 align-top text-slate-500">
                              {row.duration_ms ? `${Math.round(row.duration_ms)} ms` : "—"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
            )}

            {/* Platform + Rate limit configuration is intentionally managed via Master Admin only. */}

            {/* Account snapshot belongs in Account Risk Center. */}

            {/* Actions */}
            <section className="flex gap-4">
              <button
                onClick={resetSettings}
                disabled={loading}
                className="rounded-lg border border-white/15 bg-white/[0.06] px-4 py-2 text-sm text-slate-200 hover:bg-white/10 disabled:opacity-50"
              >
                Reset to Defaults
              </button>
              <button
                onClick={loadSettings}
                disabled={loading}
                className="rounded-lg border border-emerald-400/40 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-300 hover:bg-emerald-500/20 disabled:opacity-50"
              >
                Refresh Settings
              </button>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="w-full min-h-full p-4 lg:p-8 text-sm text-slate-300">Loading settings...</div>}>
      <SettingsPageInner />
    </Suspense>
  );
}

// Settings Card Component for Tab-specific Settings Display
function SettingsCard({ 
  title, 
  href, 
  icon: Icon, 
  settings 
}: { 
  title: string; 
  href: string; 
  icon: typeof WalletCards; 
  settings: { label: string; enabled: boolean }[];
}) {
  return (
    <Link 
      href={href}
      className="group rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur transition hover:border-emerald-400/40 hover:bg-white/[0.05]"
    >
      <div className="mb-3 flex items-center gap-2">
        <Icon className="h-5 w-5 text-emerald-400" />
        <h3 className="font-semibold text-emerald-300">{title}</h3>
      </div>
      <div className="space-y-2">
        {settings.map((setting) => (
          <div key={setting.label} className="flex items-center justify-between text-sm">
            <span className="text-slate-400">{setting.label}</span>
            <span className={`flex items-center gap-1 ${setting.enabled ? "text-emerald-400" : "text-rose-400"}`}>
              {setting.enabled ? (
                <>
                  <span className="h-2 w-2 rounded-full bg-emerald-500"></span>
                  On
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-rose-500"></span>
                  Off
                </>
              )}
            </span>
          </div>
        ))}
      </div>
    </Link>
  );
}
