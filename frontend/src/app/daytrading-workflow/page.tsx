"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { PromotionCenterPanel, type PromotionCenterActiveSection } from "@/components/PromotionCenterPanel";
import {
  api,
  approveApprovalQueueItem,
  cancelApprovalQueueItem,
  createAgentRun,
  getAgentRuntimeAgents,
  getAgentRuntimeLatest,
  getAgentRuntimeStatus,
  getAuditLogStatus,
  getApprovalQueueItems,
  getLatestModelEvidenceRecord,
  getLatestProofRegistryRecord,
  getLatestStrategyEvidenceRecord,
  getLatestWorkflowOrchestratorRun,
  getPlatformReadinessStatus,
  getQlibStatus,
  getWorkflowGovernanceStatus,
  getWorkflowRunbookLatest,
  getWorkflowRunbookStages,
  getWorkflowRunbookStatus,
  getWorkflowSchedulerStatus,
  listAuditLogEvents,
  listWorkflowSchedules,
  listWorkflowOrchestratorRuns,
  rejectApprovalQueueItem,
  runWorkflowOrchestrator,
  type AgentRuntimeAgentDescriptor,
  type AgentRunResultRecord,
  type ApprovalQueueItemRecord,
  type OrchestratorRunRecord,
  type OrchestratorRunRequest,
} from "@/lib/api";

type TabId =
  | "home"
  | "command"
  | "workflow"
  | "watchlist"
  | "data"
  | "strategy"
  | "promotion"
  | "evidence"
  | "execution"
  | "debug"
  | "runbook"
  | "agentRuntime"
  | "approvalQueue"
  | "auditLog"
  | "governance"
  | "scheduler"
  | "platformReadiness"
  | "researchEvidence";

type FetchState<T> = {
  data: T | null;
  error: string | null;
};

type StageTimelineItem = {
  stage?: number;
  agent_key?: string;
  status?: string;
  at?: string;
  run_id?: string;
  pipeline_inputs_snapshot?: Record<string, unknown>;
} & Record<string, unknown>;

type ReadinessStatus = Record<string, unknown>;
type QlibStatus = Record<string, unknown>;
type EvidenceStatus = { status?: string; record?: Record<string, unknown> | null } & Record<string, unknown>;

type DashboardData = {
  latest: FetchState<{ status: string; run: OrchestratorRunRecord | null }>;
  runs: FetchState<{ status: string; runs: OrchestratorRunRecord[] }>;
  agentRuntimeStatus: FetchState<Record<string, unknown>>;
  agentRuntimeAgents: FetchState<{ status: string; agents: AgentRuntimeAgentDescriptor[] }>;
  agentRuntime: FetchState<Record<string, unknown>>;
  readiness: FetchState<ReadinessStatus>;
  finalReadiness: FetchState<Record<string, unknown>>;
  qlib: FetchState<QlibStatus>;
  proof: FetchState<EvidenceStatus>;
  model: FetchState<EvidenceStatus>;
  strategy: FetchState<EvidenceStatus>;
  approvals: FetchState<{ status: string; items: ApprovalQueueItemRecord[] }>;
  watchlist: FetchState<Record<string, unknown>>;
  paper: FetchState<Record<string, unknown>>;
  accountRisk: FetchState<Record<string, unknown>>;
  runbookStatus: FetchState<Record<string, unknown>>;
  runbookStages: FetchState<Record<string, unknown>>;
  runbookLatest: FetchState<Record<string, unknown>>;
  auditStatus: FetchState<Record<string, unknown>>;
  auditEvents: FetchState<Record<string, unknown>>;
  governanceStatus: FetchState<Record<string, unknown>>;
  schedulerStatus: FetchState<Record<string, unknown>>;
  schedules: FetchState<Record<string, unknown>>;
};

const PLATFORM_PAGES: Array<{ id: TabId; label: string; href: string; group: string; eyebrow: string }> = [
  { id: "home", label: "Home", href: "/daytrading-workflow", group: "Command", eyebrow: "Status" },
  { id: "command", label: "Command Center", href: "/daytrading-workflow/command-center", group: "Command", eyebrow: "Operate" },
  { id: "workflow", label: "Workflow", href: "/daytrading-workflow/workflow", group: "Autonomous Pipeline", eyebrow: "Agents" },
  { id: "watchlist", label: "Live Watchlist", href: "/daytrading-workflow/live-watchlist", group: "Autonomous Pipeline", eyebrow: "Market" },
  { id: "data", label: "Data Pipeline", href: "/daytrading-workflow/data-pipeline", group: "Autonomous Pipeline", eyebrow: "Data" },
  { id: "strategy", label: "Strategy & Models", href: "/daytrading-workflow/strategy-models", group: "Intelligence", eyebrow: "Selection" },
  { id: "promotion", label: "Promotion Center", href: "/daytrading-workflow/promotion", group: "Intelligence", eyebrow: "Promotion" },
  { id: "evidence", label: "Qlib & Evidence", href: "/daytrading-workflow/qlib-evidence", group: "Intelligence", eyebrow: "Proof" },
  { id: "execution", label: "Execution & Approval", href: "/daytrading-workflow/execution-approval", group: "Risk & Approval", eyebrow: "Gates" },
  { id: "debug", label: "Issues / Debug", href: "/daytrading-workflow/issues-debug", group: "Risk & Approval", eyebrow: "Diagnostics" },
];

function platformGroups() {
  const grouped = new Map<string, typeof PLATFORM_PAGES>();
  PLATFORM_PAGES.forEach((page) => grouped.set(page.group, [...(grouped.get(page.group) ?? []), page]));
  return Array.from(grouped.entries());
}

const HOME_SUBTABS = [
  { id: "portfolio", label: "Portfolio" },
  { id: "risk", label: "Risk" },
  { id: "positions", label: "Open positions" },
] as const;

const COMMAND_SUBTABS = [
  { id: "overview", label: "Overview" },
  { id: "actions", label: "Run workflow" },
  { id: "workflow-health", label: "Workflow health" },
  { id: "data-status", label: "Data status" },
  { id: "gates", label: "Gates & approval" },
] as const;

const WORKFLOW_SUBTABS = [
  { id: "overview", label: "Overview" },
  { id: "pipeline", label: "Pipeline" },
] as const;

const WATCHLIST_SUBTABS = [
  { id: "market", label: "Market & watchlist" },
  { id: "candidate", label: "Candidate" },
  { id: "positions", label: "Open positions" },
] as const;

const DATA_SUBTABS = [
  { id: "provider", label: "Provider" },
  { id: "metrics", label: "Pipeline metrics" },
  { id: "gaps", label: "Missing features" },
] as const;

const STRATEGY_SUBTABS = [
  { id: "strategy", label: "Strategy" },
  { id: "models", label: "Models" },
] as const;

const PROMOTION_SUBTABS = [
  { id: "overview", label: "Overview" },
  { id: "requirements", label: "Promotion requirements" },
  { id: "strategy", label: "Strategy promotion" },
  { id: "models", label: "Model promotion" },
] as const;

const EVIDENCE_SUBTABS = [
  { id: "qlib", label: "Qlib" },
  { id: "proof", label: "Proof registry" },
] as const;

const EXECUTION_SUBTABS = [
  { id: "plan", label: "Planner & approvals" },
  { id: "monitoring", label: "Paper monitoring" },
  { id: "safety", label: "Safety" },
] as const;

const DEBUG_SUBTABS = [
  { id: "issues", label: "Issues" },
  { id: "raw", label: "Raw JSON" },
] as const;

const DEFAULT_SUB_TAB: Partial<Record<TabId, string>> = {
  home: "portfolio",
  command: "overview",
  workflow: "overview",
  watchlist: "market",
  data: "provider",
  strategy: "strategy",
  promotion: "overview",
  evidence: "qlib",
  execution: "plan",
  debug: "issues",
};

function SubTabBar({
  tabs,
  active,
  onSelect,
}: {
  tabs: readonly { id: string; label: string }[];
  active: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2 border-b border-cyan-400/15 pb-3">
      {tabs.map((sub) => {
        const on = active === sub.id;
        return (
          <button
            key={sub.id}
            type="button"
            onClick={() => onSelect(sub.id)}
            className={`rounded-xl border px-4 py-2 text-sm font-semibold transition-all ${
              on
                ? "border-cyan-400/40 bg-cyan-400/10 text-white shadow-[0_0_20px_rgba(34,211,238,0.12)]"
                : "border-transparent text-white/70 hover:border-cyan-400/20 hover:bg-cyan-400/[0.06] hover:text-white"
            }`}
          >
            {sub.label}
          </button>
        );
      })}
    </div>
  );
}

function sectionFromPath(pathname: string): TabId {
  if (pathname.endsWith("/command-center")) return "command";
  if (pathname.endsWith("/workflow")) return "workflow";
  if (pathname.endsWith("/live-watchlist")) return "watchlist";
  if (pathname.endsWith("/data-pipeline")) return "data";
  if (pathname.endsWith("/strategy-models")) return "strategy";
  if (pathname.endsWith("/promotion")) return "promotion";
  if (pathname.endsWith("/qlib-evidence")) return "evidence";
  if (pathname.endsWith("/execution-approval")) return "execution";
  if (pathname.endsWith("/issues-debug")) return "debug";
  return "home";
}

const STAGES: Array<{ key: string; name: string; summary: string }> = [
  { key: "data_readiness_agent", name: "DataReadinessAgent", summary: "Checks provider data, usable symbols, freshness, feature rows, and persistence." },
  { key: "session_router_agent", name: "SessionRouterAgent", summary: "Confirms the US equities session context for day trading." },
  { key: "market_condition_agent", name: "MarketConditionAgent", summary: "Scans regime, volatility, liquidity, and market context." },
  { key: "workflow_router_agent", name: "WorkflowRouterAgent", summary: "Routes the paper-first workflow through the next safe stage." },
  { key: "watchlist_builder_agent", name: "WatchlistBuilderAgent", summary: "Builds the usable watchlist and selects the candidate symbol." },
  { key: "strategy_selection_agent", name: "StrategySelectionAgent", summary: "Ranks day-trading strategies and chooses the current strategy candidate." },
  { key: "model_selection_agent", name: "ModelSelectionAgent", summary: "Selects available model evidence for the strategy and symbol." },
  { key: "qlib_research_agent", name: "QlibResearchAgent", summary: "Checks optional Qlib research, signal, model, and backtest artifacts." },
  { key: "backtest_validation_agent", name: "BacktestValidationAgent", summary: "Validates proof and backtest evidence without faking a proven status." },
  { key: "small_account_feasibility_agent", name: "SmallAccountFeasibilityAgent", summary: "Applies $1,000 account constraints before eligibility and execution planning." },
  { key: "strategy_eligibility_agent", name: "StrategyEligibilityAgent", summary: "Confirms the selected strategy can continue through paper-first gates." },
  { key: "trigger_monitor_agent", name: "TriggerMonitorAgent", summary: "Checks whether the strategy trigger is active for the selected symbol." },
  { key: "execution_planner_agent", name: "ExecutionPlannerAgent", summary: "Plans a non-submitting paper execution with small-account risk limits." },
  { key: "execution_approval_agent", name: "ExecutionApprovalAgent", summary: "Creates or checks human approval. It does not submit broker orders." },
  { key: "position_monitor_agent", name: "PositionMonitorAgent", summary: "Monitors paper positions and thesis state in preview." },
  { key: "close_review_agent", name: "CloseReviewAgent", summary: "Reviews close or reduce conditions without broker submission." },
  { key: "post_trade_evaluator_agent", name: "PostTradeEvaluatorAgent", summary: "Evaluates paper outcomes for evidence and learning." },
  { key: "learning_loop_agent", name: "LearningLoopAgent", summary: "Feeds safe learning signals back into research and evidence." },
];

const EMPTY: DashboardData = {
  latest: { data: null, error: null },
  runs: { data: null, error: null },
  agentRuntimeStatus: { data: null, error: null },
  agentRuntimeAgents: { data: null, error: null },
  agentRuntime: { data: null, error: null },
  readiness: { data: null, error: null },
  finalReadiness: { data: null, error: null },
  qlib: { data: null, error: null },
  proof: { data: null, error: null },
  model: { data: null, error: null },
  strategy: { data: null, error: null },
  approvals: { data: null, error: null },
  watchlist: { data: null, error: null },
  paper: { data: null, error: null },
  accountRisk: { data: null, error: null },
  runbookStatus: { data: null, error: null },
  runbookStages: { data: null, error: null },
  runbookLatest: { data: null, error: null },
  auditStatus: { data: null, error: null },
  auditEvents: { data: null, error: null },
  governanceStatus: { data: null, error: null },
  schedulerStatus: { data: null, error: null },
  schedules: { data: null, error: null },
};

async function bestEffort<T>(fn: () => Promise<T>): Promise<FetchState<T>> {
  try {
    return { data: await fn(), error: null };
  } catch (error) {
    return { data: null, error: error instanceof Error ? error.message : String(error) };
  }
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asList(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function text(value: unknown, fallback = "-"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.length ? value.map((x) => text(x)).join(", ") : fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function num(value: unknown): number | null {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function money(value: unknown): string {
  const n = num(value);
  return n === null ? "-" : `$${n.toFixed(2)}`;
}

function paperBuyingPower(account: Record<string, unknown>): unknown {
  return (
    account.buying_power ??
    account.regt_buying_power ??
    account.daytrading_buying_power ??
    account.non_marginable_buying_power
  );
}

function nested(source: unknown, path: string[]): unknown {
  let current: unknown = source;
  for (const key of path) {
    current = asRecord(current)[key];
  }
  return current;
}

type ProviderAttemptSummary = {
  provider: string;
  status: string;
  detail: string;
};

type ProviderSummary = {
  symbol: string;
  provider: string;
  status: string;
  detail: string;
  quality: string;
  freshness: string;
  isNonReal: boolean;
  attempts: ProviderAttemptSummary[];
  warnings: string[];
};

function providerDisplayName(value: unknown): string {
  const provider = text(value, "unknown").toLowerCase();
  const labels: Record<string, string> = {
    yfinance: "yfinance",
    yahoo: "yfinance",
    alpaca: "Alpaca",
    polygon: "Polygon",
    smoke: "Smoke check",
  };
  return labels[provider] ?? provider;
}

function providerAttemptStatus(attempt: Record<string, unknown>): ProviderAttemptSummary {
  const provider = providerDisplayName(attempt.provider);
  const quality = text(attempt.data_quality ?? attempt.status, "unknown");
  const error = text(attempt.error, "");
  const notConfigured = asList(attempt.not_configured_fields).length > 0 || quality === "not_configured";
  const unavailable = asList(attempt.unavailable_fields).length > 0;
  if (quality === "real") {
    return {
      provider,
      status: unavailable ? "Live with limited fields" : "Configured and live",
      detail: unavailable ? `Missing optional fields: ${text(attempt.unavailable_fields)}` : "Real market data returned.",
    };
  }
  if (notConfigured) {
    return {
      provider,
      status: "Not configured",
      detail: error || "Provider credentials or enablement are missing.",
    };
  }
  return {
    provider,
    status: quality,
    detail: error || "Provider was checked during data readiness.",
  };
}

function summarizeProviderStatus(providerStatus: unknown, fallbackProvider: unknown): ProviderSummary {
  const raw = asRecord(providerStatus);
  const symbolEntry = Object.entries(raw).find(([, value]) => {
    const record = asRecord(value);
    return Boolean(record.provider || record.status || record.attempts);
  });
  const symbol = symbolEntry?.[0] ?? "selected symbol";
  const record = symbolEntry ? asRecord(symbolEntry[1]) : raw;
  const attempts = asList(record.attempts).map((attempt) => providerAttemptStatus(asRecord(attempt)));
  const provider = providerDisplayName(record.provider ?? fallbackProvider ?? attempts.find((attempt) => attempt.status.includes("live"))?.provider);
  const isNonReal = Boolean(record.is_non_real);
  const quality = text(record.quality_status, attempts.find((attempt) => attempt.status.includes("live")) ? "real" : "unknown");
  const freshness = text(record.freshness_status, "checked per run");
  const rawStatus = text(record.status, "");
  const hasLiveAttempt = attempts.some((attempt) => attempt.status.includes("live")) || (!isNonReal && rawStatus === "usable");
  const status = isNonReal ? "Blocked non-real data" : hasLiveAttempt ? "Configured and live" : rawStatus || "Not configured";
  const warnings = asList(record.warnings).map((warning) => text(warning)).filter(Boolean);

  return {
    symbol,
    provider,
    status,
    detail: isNonReal ? "Non-real market data was detected and must not be used." : hasLiveAttempt ? "Real market data is being used for workflow readiness." : "No live provider is currently usable.",
    quality,
    freshness,
    isNonReal,
    attempts,
    warnings,
  };
}

function timeline(run: OrchestratorRunRecord | null): StageTimelineItem[] {
  return asList(run?.stage_timeline).map((row) => asRecord(row) as StageTimelineItem);
}

function stageByKey(run: OrchestratorRunRecord | null): Record<string, StageTimelineItem> {
  return Object.fromEntries(timeline(run).map((row) => [String(row.agent_key || ""), row]));
}

function stageResult(row: StageTimelineItem | undefined): Record<string, unknown> {
  return asRecord(row?.pipeline_inputs_snapshot);
}

/** Blockers/warnings from this stage's pipeline snapshot only (no run-level bleed onto every card). */
function snapshotBlockers(snapshot: Record<string, unknown>): string[] {
  const merged = [
    ...asList(snapshot.small_account_blockers),
    ...asList(snapshot.evidence_blockers),
    ...asList(snapshot.alpha_blockers),
  ];
  return [...new Set(merged.map((b) => text(b)).filter(Boolean))].slice(0, 3);
}

function snapshotWarnings(snapshot: Record<string, unknown>): string[] {
  const merged = [
    ...asList(snapshot.small_account_warnings),
    ...asList(snapshot.evidence_warnings),
    ...asList(snapshot.alpha_warnings),
  ];
  return [...new Set(merged.map((w) => text(w)).filter(Boolean))].slice(0, 3);
}

function statusTone(value: unknown): string {
  const s = text(value, "").toLowerCase();
  if (["blocked", "failed", "fail", "not_ready"].includes(s)) return "border-red-400/40 bg-red-500/15 text-red-100";
  if (["warn", "warning", "degraded", "partial", "waiting approval", "paused_for_approval"].includes(s)) return "border-amber-400/40 bg-amber-500/15 text-amber-100";
  if (["running"].includes(s)) return "border-sky-400/40 bg-sky-500/15 text-sky-100";
  if (["completed", "completed_preview", "pass", "ready", "ok", "safe"].includes(s)) return "border-cyan-400/40 bg-cyan-500/15 text-cyan-100";
  return "border-slate-500/40 bg-slate-500/10 text-slate-300";
}

function stageVisualState({
  row,
  isCurrent,
  isApprovalBoundary,
  blockers,
  warnings,
}: {
  row: StageTimelineItem | undefined;
  isCurrent: boolean;
  isApprovalBoundary: boolean;
  blockers: unknown[];
  warnings: unknown[];
}) {
  const status = text(row?.status, "").toLowerCase();
  const hasRun = Boolean(row);
  const blocked = status === "blocked" || status === "failed" || blockers.length > 0;
  const warned = warnings.length > 0;

  if (blocked) {
    return {
      label: "blocked",
      card: "border-red-300/45 bg-red-500/12 shadow-[0_0_38px_rgba(248,113,113,0.18)]",
      rail: "bg-red-300 shadow-[0_0_18px_rgba(252,165,165,0.9)]",
      badge: "border-red-300/45 bg-red-500/20 text-red-100",
    };
  }
  if (isCurrent) {
    return {
      label: "running",
      card: "border-cyan-300/55 bg-cyan-400/12 shadow-[0_0_46px_rgba(34,211,238,0.26)] ring-1 ring-cyan-300/20",
      rail: "animate-pulse bg-cyan-200 shadow-[0_0_22px_rgba(165,243,252,1)]",
      badge: "border-cyan-300/45 bg-cyan-400/20 text-cyan-50",
    };
  }
  if (isApprovalBoundary) {
    return {
      label: hasRun ? "approval gate" : "approval pending",
      card: "border-amber-300/45 bg-amber-500/10 shadow-[0_0_36px_rgba(251,191,36,0.16)]",
      rail: "bg-amber-300 shadow-[0_0_18px_rgba(252,211,77,0.85)]",
      badge: "border-amber-300/45 bg-amber-500/20 text-amber-100",
    };
  }
  if (warned) {
    return {
      label: "warning",
      card: "border-amber-300/35 bg-amber-500/8 shadow-[0_0_28px_rgba(251,191,36,0.10)]",
      rail: "bg-amber-300/90 shadow-[0_0_14px_rgba(252,211,77,0.65)]",
      badge: "border-amber-300/40 bg-amber-500/16 text-amber-100",
    };
  }
  if (hasRun) {
    return {
      label: "completed",
      card: "border-cyan-300/35 bg-cyan-500/8 shadow-[0_0_30px_rgba(34,211,238,0.12)]",
      rail: "bg-cyan-300 shadow-[0_0_16px_rgba(165,243,252,0.75)]",
      badge: "border-cyan-300/40 bg-cyan-500/16 text-cyan-100",
    };
  }
  return {
    label: "pending",
    card: "border-white/10 bg-white/[0.035]",
    rail: "bg-slate-700",
    badge: "border-slate-500/40 bg-slate-500/10 text-slate-300",
  };
}

function Badge({ children, tone = "safe" }: { children: React.ReactNode; tone?: "safe" | "warn" | "blocked" | "running" | "paper" }) {
  const cls =
    tone === "blocked"
      ? "border-red-400/40 bg-red-500/15 text-red-100"
      : tone === "warn"
        ? "border-amber-400/40 bg-amber-500/15 text-amber-100"
        : tone === "running"
          ? "border-cyan-300/45 bg-cyan-400/15 text-cyan-100"
          : tone === "paper"
            ? "border-cyan-300/35 bg-cyan-400/10 text-cyan-100"
            : "border-cyan-400/40 bg-cyan-500/15 text-cyan-100";
  return <span className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-wide ${cls}`}>{children}</span>;
}

function Card({ title, subtitle, children, error }: { title: string; subtitle?: string; children: React.ReactNode; error?: string | null }) {
  return (
    <section className="rounded-3xl border border-white/10 bg-black/35 p-4 shadow-[0_24px_80px_rgba(0,0,0,0.32)] backdrop-blur-xl">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-400">{title}</h3>
          {subtitle ? <p className="mt-1 text-xs leading-5 text-slate-500">{subtitle}</p> : null}
        </div>
        {error ? <Badge tone="warn">Unavailable</Badge> : null}
      </div>
      {error ? <p className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-3 text-sm text-amber-100">{error}</p> : children}
    </section>
  );
}

function MiniTable({ rows, empty = "No records reported." }: { rows: unknown[]; empty?: string }) {
  if (!rows.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <div className="space-y-2">
      {rows.slice(0, 8).map((row, index) => {
        const record = asRecord(row);
        const title = text(record.agent_key ?? record.approval_id ?? record.audit_id ?? record.schedule_id ?? record.name ?? record.event_type ?? record.status ?? `Record ${index + 1}`);
        const subtitle = text(record.status ?? record.message ?? record.updated_at ?? record.created_at ?? record.next_action);
        return (
          <div key={`${title}-${index}`} className="rounded-2xl border border-cyan-400/10 bg-black/25 p-3">
            <div className="text-sm font-semibold text-slate-100">{title}</div>
            <div className="mt-1 text-xs text-slate-500">{subtitle}</div>
          </div>
        );
      })}
    </div>
  );
}

function ApprovalActionSelect({
  label,
  disabled,
  disabledReason,
  busy,
  onApprove,
  onDecline,
}: {
  label: string;
  disabled: boolean;
  disabledReason?: string;
  busy: boolean;
  onApprove: () => void;
  onDecline: () => void;
}) {
  return (
    <div className={`rounded-2xl border p-3 ${disabled ? "border-slate-600/35 bg-slate-900/40 opacity-55" : "border-cyan-400/20 bg-cyan-400/[0.04]"}`}>
      <div className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{label}</div>
      <select
        disabled={disabled || busy}
        defaultValue=""
        onChange={(event) => {
          const value = event.target.value;
          event.currentTarget.value = "";
          if (value === "approve") onApprove();
          if (value === "decline") onDecline();
        }}
        className="w-full rounded-xl border border-cyan-400/10 bg-black/35 px-3 py-2 text-sm font-semibold text-slate-100 outline-none disabled:cursor-not-allowed disabled:text-slate-500"
      >
        <option value="">{disabled ? "No approval needed" : "Select action"}</option>
        <option value="approve">Approve</option>
        <option value="decline">Decline</option>
      </select>
      {disabledReason ? <p className="mt-2 text-xs text-slate-500">{disabledReason}</p> : null}
    </div>
  );
}

function SafetyStatusCard({ title, status, children }: { title: string; status?: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-600/35 bg-slate-900/40 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <div className="text-xs font-bold uppercase tracking-[0.16em] text-slate-400">{title}</div>
        {status ? <Badge tone="paper">{status}</Badge> : null}
      </div>
      <p className="text-sm leading-5 text-slate-400">{children}</p>
    </div>
  );
}

function SectionHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return (
    <header className="rounded-[2rem] border border-white/10 bg-black/35 p-5 shadow-[0_28px_110px_rgba(0,0,0,0.42)] backdrop-blur-2xl">
      <div className="mb-2 text-[10px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">{eyebrow}</div>
      <h1 className="text-3xl font-black tracking-tight text-white">{title}</h1>
      <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">{description}</p>
    </header>
  );
}

function Metric({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div className="rounded-2xl border border-cyan-400/10 bg-black/25 px-3 py-2 shadow-[inset_0_1px_0_rgba(34,211,238,0.05)] backdrop-blur">
      <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</div>
      <div className={`mt-1 break-words text-sm font-semibold ${tone || "text-slate-100"}`}>{value}</div>
    </div>
  );
}

function ProviderStatusCard({ summary }: { summary: ProviderSummary }) {
  return (
    <Card title="Data Source & Status" subtitle="Human-readable provider selected by DataReadinessAgent. No raw JSON.">
      <div className="grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-cyan-300/25 bg-cyan-400/10 p-4 shadow-[0_0_28px_rgba(34,211,238,0.10)]">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-cyan-200/70">Data source used</div>
          <div className="mt-2 text-3xl font-black text-cyan-100">{summary.provider}</div>
          <p className="mt-2 text-sm leading-5 text-slate-400">{summary.detail}</p>
        </div>
        <div className="rounded-2xl border border-cyan-300/20 bg-black/25 p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <Badge tone={summary.status === "Configured and live" ? "safe" : summary.isNonReal ? "warn" : "blocked"}>{summary.status}</Badge>
            <Badge tone="paper">{summary.symbol}</Badge>
          </div>
          <div className="grid gap-2">
            <Metric label="Freshness" value={summary.freshness} tone={summary.freshness === "fresh" ? "text-cyan-100" : "text-amber-100"} />
            <Metric label="Quality" value={summary.quality} />
            <Metric label="NonReal data" value={summary.isNonReal ? "yes" : "no"} tone={summary.isNonReal ? "text-amber-100" : "text-cyan-100"} />
          </div>
        </div>
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-2xl border border-white/10 bg-black/25 p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">Provider checks</div>
          <div className="mt-3 space-y-2">
            {summary.attempts.length ? (
              summary.attempts.map((attempt) => (
                <div key={`${attempt.provider}-${attempt.status}`} className="rounded-xl border border-cyan-400/10 bg-black/25 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="font-semibold text-slate-100">{attempt.provider}</div>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${statusTone(attempt.status)}`}>{attempt.status}</span>
                  </div>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{attempt.detail}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-500">No provider attempt details reported.</p>
            )}
          </div>
        </div>
        <div className="rounded-2xl border border-amber-400/15 bg-amber-500/5 p-4">
          <div className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-100/70">Provider notes</div>
          {summary.warnings.length ? (
            <ul className="mt-3 space-y-2 text-sm leading-5 text-amber-100/90">
              {summary.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : (
            <p className="mt-3 text-sm text-slate-500">No provider warnings reported.</p>
          )}
        </div>
      </div>
    </Card>
  );
}

function IssueList({ items, empty = "None" }: { items: unknown; empty?: string }) {
  const rows = asList(items).map((item) => text(item)).filter(Boolean);
  if (!rows.length) return <p className="text-sm text-slate-500">{empty}</p>;
  return (
    <ul className="space-y-1 break-words text-sm text-slate-300">
      {rows.map((item) => (
        <li key={item} className="break-words">
          - {item}
        </li>
      ))}
    </ul>
  );
}

function DebugPanel({ title, value }: { title: string; value: unknown }) {
  return (
    <details className="rounded-2xl border border-white/10 bg-black/25 p-3">
      <summary className="cursor-pointer text-sm font-semibold text-slate-200">{title}</summary>
      <pre className="mt-3 max-h-96 overflow-auto rounded-xl bg-black/40 p-3 text-xs leading-5 text-slate-300">{JSON.stringify(value, null, 2)}</pre>
    </details>
  );
}

function RunWorkflowPanel({ onRun, busy }: { onRun: (symbols: string, stopStage: number) => Promise<void>; busy: boolean }) {
  const [symbols, setSymbols] = useState("");
  const [stopStage, setStopStage] = useState(100);
  return (
    <Card title="Run Safe Paper Workflow" subtitle="Locked to stock, day_trading, paper_first, dry_run, human approval, and allow_submit=false.">
      <div className="grid gap-3 lg:grid-cols-[1fr_180px_auto]">
        <label className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
          Symbols
          <input
            value={symbols}
            onChange={(event) => setSymbols(event.target.value.toUpperCase())}
            className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-cyan-400/50"
            placeholder="Leave blank to scan the real market"
          />
          <span className="mt-1 block text-xs normal-case tracking-normal text-slate-500">Blank means scanner/provider discovery. No non_real data or default ticker is used.</span>
        </label>
        <label className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
          Stop stage
          <select
            value={stopStage}
            onChange={(event) => setStopStage(Number(event.target.value))}
            className="mt-2 w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-cyan-400/50"
          >
            {[5, 10, 14, 18, 100].map((value) => (
              <option key={value} value={value}>
                {value === 100 ? "Full preview" : `Stage ${value}`}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          disabled={busy}
          onClick={() => onRun(symbols, stopStage)}
          className="self-end rounded-xl border border-cyan-400/50 bg-cyan-500/20 px-4 py-2 text-sm font-bold text-cyan-100 transition hover:bg-cyan-500/30 disabled:opacity-50"
        >
          {busy ? "Running..." : "Run Safe Paper Workflow"}
        </button>
      </div>
      <div className="mt-3 grid gap-2 text-xs text-slate-400 md:grid-cols-3">
        <div className="rounded-lg border border-white/10 bg-black/20 p-2">horizon: day_trading</div>
        <div className="rounded-lg border border-white/10 bg-black/20 p-2">mode: paper_first</div>
        <div className="rounded-lg border border-white/10 bg-black/20 p-2">allow_submit: false</div>
      </div>
    </Card>
  );
}

export default function DayTradingWorkflowPage() {
  const pathname = usePathname();
  const activeTab = sectionFromPath(pathname);
  const [data, setData] = useState<DashboardData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [runBusy, setRunBusy] = useState(false);
  const [runMessage, setRunMessage] = useState<string | null>(null);
  const [approvalReason, setApprovalReason] = useState("");
  const [approvalBusyId, setApprovalBusyId] = useState<string | null>(null);
  const [agentRunBusy, setAgentRunBusy] = useState(false);
  const [agentRunResult, setAgentRunResult] = useState<AgentRunResultRecord | null>(null);
  const [subTabBySection, setSubTabBySection] = useState<Partial<Record<TabId, string>>>({});
  const sectionSub = (tab: TabId) => {
    const raw = subTabBySection[tab] ?? DEFAULT_SUB_TAB[tab] ?? "overview";
    if (tab === "command" && raw === "status") return "workflow-health";
    if (tab === "promotion" && raw === "center") return "requirements";
    return raw;
  };
  const setSectionSub = (tab: TabId, id: string) => setSubTabBySection((prev) => ({ ...prev, [tab]: id }));

  const refresh = useCallback(async () => {
    setLoading(true);
    const [
      latest,
      runs,
      agentRuntimeStatus,
      agentRuntimeAgents,
      agentRuntime,
      readiness,
      finalReadiness,
      qlib,
      proof,
      model,
      strategy,
      approvals,
      watchlist,
      paper,
      accountRisk,
      runbookStatus,
      runbookStages,
      runbookLatest,
      auditStatus,
      auditEvents,
      governanceStatus,
      schedulerStatus,
      schedules,
    ] = await Promise.all([
      bestEffort(() => getLatestWorkflowOrchestratorRun()),
      bestEffort(() => listWorkflowOrchestratorRuns(20)),
      bestEffort(() => getAgentRuntimeStatus()),
      bestEffort(() => getAgentRuntimeAgents()),
      bestEffort(() => getAgentRuntimeLatest()),
      bestEffort(() => getPlatformReadinessStatus() as Promise<ReadinessStatus>),
      bestEffort(() => api.getFinalReadiness() as Promise<Record<string, unknown>>),
      bestEffort(() => getQlibStatus()),
      bestEffort(() => getLatestProofRegistryRecord() as Promise<EvidenceStatus>),
      bestEffort(() => getLatestModelEvidenceRecord() as Promise<EvidenceStatus>),
      bestEffort(() => getLatestStrategyEvidenceRecord() as Promise<EvidenceStatus>),
      bestEffort(() => getApprovalQueueItems(50)),
      bestEffort(() => api.getLiveWatchlist() as Promise<Record<string, unknown>>),
      bestEffort(() => api.getAlpacaPaperSnapshot() as Promise<Record<string, unknown>>),
      bestEffort(() => api.getAccountRisk() as Promise<Record<string, unknown>>),
      bestEffort(() => getWorkflowRunbookStatus() as Promise<Record<string, unknown>>),
      bestEffort(() => getWorkflowRunbookStages() as Promise<Record<string, unknown>>),
      bestEffort(() => getWorkflowRunbookLatest() as Promise<Record<string, unknown>>),
      bestEffort(() => getAuditLogStatus()),
      bestEffort(() => listAuditLogEvents(20) as Promise<Record<string, unknown>>),
      bestEffort(() => getWorkflowGovernanceStatus()),
      bestEffort(() => getWorkflowSchedulerStatus()),
      bestEffort(() => listWorkflowSchedules(20) as Promise<Record<string, unknown>>),
    ]);
    setData({
      latest,
      runs,
      agentRuntimeStatus,
      agentRuntimeAgents,
      agentRuntime,
      readiness,
      finalReadiness,
      qlib,
      proof,
      model,
      strategy,
      approvals,
      watchlist,
      paper,
      accountRisk,
      runbookStatus,
      runbookStages,
      runbookLatest,
      auditStatus,
      auditEvents,
      governanceStatus,
      schedulerStatus,
      schedules,
    });
    setLoading(false);
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const run = data.latest.data?.run ?? null;
  const stageMap = useMemo(() => stageByKey(run), [run]);
  const latestSnapshot = timeline(run).at(-1)?.pipeline_inputs_snapshot ?? {};
  const readinessSystems = asRecord(data.readiness.data?.systems);
  const executionGates = asRecord(readinessSystems.execution_gates);
  const dataPipeline = asRecord(readinessSystems.data_pipeline);
  const evidencePipeline = asRecord(readinessSystems.evidence_pipeline);
  const smallAccountReadiness = asRecord(readinessSystems.small_account_feasibility ?? data.finalReadiness.data?.small_account_feasibility);
  const proofRecord = asRecord(data.proof.data?.record);
  const modelRecord = asRecord(data.model.data?.record);
  const strategyRecord = asRecord(data.strategy.data?.record);
  const approvalItems = data.approvals.data?.items ?? [];
  const openPositions = asList(data.paper.data?.positions);
  const paperAccount = asRecord(data.paper.data?.account);
  const hasPaperAccount = !data.paper.error && Object.keys(paperAccount).length > 0;
  const accountRisk = asRecord(data.accountRisk.data);
  const watchlistSymbols = asList(data.watchlist.data?.symbols ?? data.watchlist.data?.watchlist ?? data.watchlist.data?.items);
  const runtimeSummary = asRecord(data.agentRuntimeStatus.data?.summary);
  const runtimeSafety = asRecord(data.agentRuntimeStatus.data?.safety);
  const runtimeAgents = data.agentRuntimeAgents.data?.agents ?? [];
  const latestAgentRuns = asRecord(data.agentRuntime.data?.latest_agent_runs_by_key);
  const runbookStages = asList(data.runbookStages.data?.stages);
  const auditEvents = asList(data.auditEvents.data?.events);
  const schedules = asList(data.schedules.data?.schedules);
  const providerSummary = summarizeProviderStatus(run?.provider_status ?? dataPipeline.provider_status, run?.provider_name ?? dataPipeline.provider_name);

  const runWorkflow = useCallback(
    async (symbolsText: string, stopStage: number) => {
      const parsedSymbols = symbolsText.split(",").map((symbol) => symbol.trim().toUpperCase()).filter(Boolean);
      if (!parsedSymbols.length) {
        setRunMessage("Scanning real market for provider-backed candidates...");
      }
      setRunBusy(true);
      setRunMessage(null);
      const payload: OrchestratorRunRequest = {
        workflow_name: "US Stock Day-Trading Paper Workflow v1",
        asset_class: "stock",
        horizon: "day_trading",
        mode: "paper_first",
        source: "runtime",
        symbols: parsedSymbols,
        max_candidates: 5,
        stop_at_stage: stopStage,
        dry_run: true,
        require_human_approval: true,
        allow_submit: false,
        simulated_position: false,
        simulated_closed_trade: false,
        metadata: { account_equity: 1000, dashboard_run: true },
      };
      try {
        const response = await runWorkflowOrchestrator(payload);
        setRunMessage(`Latest run status: ${response.run.status}`);
        await refresh();
      } catch (error) {
        setRunMessage(error instanceof Error ? error.message : String(error));
      } finally {
        setRunBusy(false);
      }
    },
    [refresh],
  );

  const approvalAction = useCallback(
    async (approvalId: string, action: "approve" | "reject" | "cancel") => {
      setApprovalBusyId(approvalId);
      setRunMessage(null);
      try {
        const body = { actor: "daytrading_operator", reason: approvalReason.trim() || null };
        if (action === "approve") await approveApprovalQueueItem(approvalId, body);
        if (action === "reject") await rejectApprovalQueueItem(approvalId, body);
        if (action === "cancel") await cancelApprovalQueueItem(approvalId, body);
        setRunMessage(`Approval ${approvalId} ${action}d. No broker order was submitted.`);
        await refresh();
      } catch (error) {
        setRunMessage(error instanceof Error ? error.message : String(error));
      } finally {
        setApprovalBusyId(null);
      }
    },
    [approvalReason, refresh],
  );

  const runSampleAgent = useCallback(
    async (agentKey: string) => {
      setAgentRunBusy(true);
      setAgentRunResult(null);
      setRunMessage(null);
      try {
        const result = await createAgentRun({
          agent_key: agentKey,
          inputs: { timestamp: new Date().toISOString(), symbol: run?.selected_symbol ?? run?.symbol ?? null },
          context: { source: "daytrading_platform" },
          dry_run: true,
          requested_stage: null,
          idempotency_key: `dt_${agentKey}_${Date.now()}`,
        });
        setAgentRunResult(result.agent_run);
        await refresh();
      } catch (error) {
        setRunMessage(error instanceof Error ? error.message : String(error));
      } finally {
        setAgentRunBusy(false);
      }
    },
    [refresh, run?.selected_symbol, run?.symbol],
  );

  const status = run?.status ?? "idle";
  const blocked = status === "blocked" || (run?.blockers?.length ?? 0) > 0;
  const waitingApproval = Boolean(run?.approval_required || run?.approval_id);
  const warning = !blocked && ((run?.warnings?.length ?? 0) > 0 || status === "paused_for_approval");

  return (
    <div className="flex min-h-screen bg-[#03070b] text-slate-100">
      <aside className="flex min-h-screen w-80 shrink-0 flex-col border-r border-cyan-400/10 bg-[#000000] px-4 py-5">
        <Link href="/daytrading-workflow" className="mb-7 flex items-center gap-3 px-1">
          <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl border border-cyan-400/50 bg-cyan-400/10 text-xl font-black text-white">
            E
            <span className="absolute -right-1 -top-1 h-3 w-3 rounded-full border border-black bg-cyan-400" />
          </div>
          <div>
            <div className="text-xl font-semibold tracking-tight text-white">Day-Trading OS</div>
            <div className="text-[11px] uppercase tracking-[0.24em] text-white/55">Hedge fund command</div>
          </div>
        </Link>

        <nav className="space-y-5 overflow-y-auto pr-1">
          {platformGroups().map(([group, pages]) => (
            <div key={group}>
              <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-white/50">{group}</div>
              <div className="space-y-1.5">
                {pages.map((page) => {
                  const active = activeTab === page.id;
                  return (
                    <Link
                      key={page.href}
                      href={page.href}
                      className={`group flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium text-white transition-all ${
                        active
                          ? "border border-cyan-400/40 bg-cyan-400/10 shadow-[0_0_30px_rgba(34,211,238,0.16)]"
                          : "border border-transparent text-white/90 hover:border-cyan-400/15 hover:bg-cyan-400/[0.04] hover:text-white"
                      }`}
                    >
                      <span className={`h-2.5 w-2.5 rounded-full ${active ? "bg-cyan-400 shadow-[0_0_16px_rgba(165,243,252,0.8)]" : "bg-cyan-400/25 group-hover:bg-cyan-400/60"}`} />
                      <span className="flex-1">{page.label}</span>
                      <span className="text-[9px] font-bold uppercase tracking-wider text-white/45">{page.eyebrow}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        <div className="mt-auto rounded-3xl border border-cyan-300/15 bg-black/25 p-4">
          <div className="mb-2 flex flex-wrap gap-2">
            <Badge tone={blocked ? "blocked" : warning ? "warn" : "safe"}>{blocked ? "Blocked" : warning ? "Warning" : "Safe"}</Badge>
            <Badge tone="paper">Paper Only</Badge>
          </div>
          <div className="text-xs leading-5 text-white/70">US stocks, day trading, paper-first, human approval. Broker submission remains blocked.</div>
        </div>
      </aside>

      <main className="relative min-h-screen flex-1 overflow-hidden bg-cyan-950">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_28%_0%,rgba(34,211,238,0.18),transparent_30%),radial-gradient(circle_at_100%_20%,rgba(34,211,238,0.10),transparent_28%),radial-gradient(circle_at_0%_100%,rgba(34,211,238,0.08),transparent_30%)]" />
        <div className="pointer-events-none absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(34,211,238,0.07)_1px,transparent_1px),linear-gradient(90deg,rgba(34,211,238,0.06)_1px,transparent_1px)] [background-size:56px_56px]" />
        <div className="relative z-10 space-y-5 p-6">
      {runMessage ? <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-3 text-sm text-cyan-100">{runMessage}</div> : null}

      {activeTab === "home" ? (
        <div className="space-y-4">
          <div className="flex flex-col gap-3 rounded-[2rem] border border-cyan-400/15 bg-[#05080d]/70 p-5 shadow-[0_28px_110px_rgba(0,0,0,0.42)] backdrop-blur-2xl lg:flex-row lg:items-end lg:justify-between">
            <div>
              <div className="mb-2 flex flex-wrap gap-2">
                <Badge tone="safe">Paper Portfolio Home</Badge>
                <Badge tone="paper">Paper Account</Badge>
              </div>
              <h1 className="text-3xl font-black tracking-tight text-white">Paper Account Home</h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                Use the tabs below for portfolio snapshot, risk limits, and open paper positions.
              </p>
            </div>
            <button
              type="button"
              onClick={() => refresh()}
              disabled={loading}
              className="rounded-xl border border-cyan-400/20 bg-cyan-400/[0.06] px-4 py-2 text-sm font-semibold text-cyan-100 hover:border-cyan-400/35 disabled:opacity-50"
            >
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          <SubTabBar tabs={HOME_SUBTABS} active={sectionSub("home")} onSelect={(id) => setSectionSub("home", id)} />

          {sectionSub("home") === "portfolio" ? (
            <Card
              title="Paper Portfolio & Paper Buying Power"
              subtitle="Paper account snapshot only. This does not represent live brokerage buying power."
              error={data.paper.error}
            >
              {hasPaperAccount ? (
                <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-3">
                  <Metric label="Paper portfolio value" value={money(paperAccount.portfolio_value ?? paperAccount.equity)} />
                  <Metric label="Paper buying power" value={money(paperBuyingPower(paperAccount))} />
                  <Metric label="Paper cash" value={money(paperAccount.cash)} />
                  <Metric label="Paper account equity" value={money(paperAccount.equity)} />
                  <Metric label="Paper account status" value={text(paperAccount.status ?? data.paper.data?.status)} />
                  <Metric label="Paper day trades used" value={text(paperAccount.daytrade_count)} />
                </div>
              ) : (
                <p className="text-sm text-slate-500">Paper account data unavailable</p>
              )}
            </Card>
          ) : null}

          {sectionSub("home") === "risk" ? (
            <Card title="Paper Account Risk" subtitle="Paper-first risk guardrails used by the autonomous workflow." error={data.accountRisk.error}>
              <div className="grid gap-2 md:grid-cols-2">
                <Metric label="Max risk / trade" value={`${text(accountRisk.max_risk_per_trade_percent)}%`} />
                <Metric label="Max daily loss" value={`${text(accountRisk.max_daily_loss_percent)}%`} />
                <Metric label="Max position size" value={`${text(accountRisk.max_position_size_percent)}%`} />
                <Metric label="Min reward:risk" value={text(accountRisk.min_reward_risk_ratio)} />
                <Metric label="Risk style" value={text(accountRisk.preferred_risk_style)} />
                <Metric label="Paper only" value={text(accountRisk.paper_only ?? true)} />
              </div>
            </Card>
          ) : null}

          {sectionSub("home") === "positions" ? (
            <Card title="Paper Open Positions" subtitle="Paper open positions if the paper account endpoint reports any." error={data.paper.error}>
              {!hasPaperAccount ? (
                <p className="text-sm text-slate-500">Paper account data unavailable</p>
              ) : openPositions.length ? (
                <div className="grid gap-3 xl:grid-cols-2">
                  {openPositions.map((position, index) => {
                    const row = asRecord(position);
                    return (
                      <div key={`${text(row.symbol, "position")}-${index}`} className="rounded-2xl border border-cyan-400/10 bg-black/25 p-4">
                        <div className="mb-3 flex items-center justify-between gap-3">
                          <div className="text-lg font-bold text-slate-50">{text(row.symbol)}</div>
                          <Badge tone="paper">{text(row.side ?? "paper")}</Badge>
                        </div>
                        <div className="grid gap-2 md:grid-cols-3">
                          <Metric label="Qty" value={text(row.qty)} />
                          <Metric label="Market value" value={money(row.market_value)} />
                          <Metric label="Current price" value={money(row.current_price)} />
                          <Metric label="Avg entry" value={money(row.avg_entry_price)} />
                          <Metric label="Unrealized P/L" value={money(row.unrealized_pl)} />
                          <Metric label="P/L %" value={row.unrealized_plpc != null ? `${(Number(row.unrealized_plpc) * 100).toFixed(2)}%` : "-"} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <p className="text-sm text-slate-500">No open paper positions reported.</p>
              )}
            </Card>
          ) : null}
        </div>
      ) : null}

      {activeTab === "command" ? (
        <div className="space-y-4">
          <header className="rounded-[2rem] border border-cyan-400/15 bg-[#05080d]/70 p-5 shadow-[0_28px_110px_rgba(0,0,0,0.42)] backdrop-blur-2xl">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
              <div>
                <div className="mb-2 flex flex-wrap gap-2">
                  <Badge tone={blocked ? "blocked" : warning ? "warn" : "safe"}>{blocked ? "Blocked" : warning ? "Warning" : "Safe"}</Badge>
                  {status === "running" ? <Badge tone="running">Running</Badge> : null}
                  {waitingApproval ? <Badge tone="warn">Waiting Approval</Badge> : null}
                  <Badge tone="paper">Paper Only</Badge>
                </div>
                <h1 className="text-3xl font-black tracking-tight text-white">Autonomous Day-Trading Command Center</h1>
                <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
                  A human-readable dashboard for the paper-first autonomous workflow. It explains what the agents are doing, what data and evidence
                  they used, and which gates are blocking or warning before any execution boundary.
                </p>
              </div>
              <button
                type="button"
                onClick={() => refresh()}
                disabled={loading}
                className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-semibold text-slate-200 hover:border-cyan-400/30 disabled:opacity-50"
              >
                {loading ? "Refreshing..." : "Refresh"}
              </button>
            </div>
          </header>

          <SubTabBar tabs={COMMAND_SUBTABS} active={sectionSub("command")} onSelect={(id) => setSectionSub("command", id)} />

          {sectionSub("command") === "overview" ? (
            <div className="grid gap-2 md:grid-cols-3 xl:grid-cols-6">
              <Metric label="Workflow status" value={status} tone={blocked ? "text-red-100" : "text-cyan-100"} />
              <Metric label="Last run time" value={text(run?.updated_at ?? run?.created_at)} />
              <Metric label="Current agent" value={text(run?.current_agent_key)} />
              <Metric label="Current stage" value={text(run?.current_stage)} />
              <Metric label="Selected symbol" value={text(run?.selected_symbol ?? run?.symbol ?? latestSnapshot.selected_symbol ?? latestSnapshot.symbol)} />
              <Metric label="Selected strategy" value={text(run?.selected_strategy_key ?? run?.strategy_key)} />
              <Metric label="Selected model" value={text(run?.selected_model_key)} />
              <Metric label="Proof status" value={text(run?.proof_status)} />
              <Metric label="Small-account decision" value={text(run?.small_account_decision)} />
              <Metric label="Approval required" value={text(run?.approval_required ?? false)} />
              <Metric label="Execution boundary" value={text(run?.execution_boundary_reached ?? false)} />
              <Metric label="submitted / broker / llm" value={`${text(run?.submitted_order ?? false)} / ${text(run?.broker_called ?? false)} / ${text(run?.llm_used ?? false)}`} />
            </div>
          ) : null}

          {sectionSub("command") === "actions" ? <RunWorkflowPanel onRun={runWorkflow} busy={runBusy} /> : null}

          {sectionSub("command") === "workflow-health" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Workflow Health" error={data.latest.error}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="status" value={status} />
                  <Metric label="current stage" value={text(run?.current_stage)} />
                  <Metric label="current agent" value={text(run?.current_agent_key)} />
                  <Metric label="last run" value={text(run?.updated_at ?? run?.created_at)} />
                  <Metric label="next action" value={text(run?.next_action)} />
                  <Metric label="blockers / warnings" value={`${run?.blockers?.length ?? 0} / ${run?.warnings?.length ?? 0}`} />
                </div>
              </Card>
              <Card title="Safety Boundary">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="paper_first" value="true" tone="text-cyan-100" />
                  <Metric label="day_trading_only" value="true" tone="text-cyan-100" />
                  <Metric label="human_approval_required" value={text(run?.approval_required ?? executionGates.require_human_approval ?? true)} />
                  <Metric label="submitted_order" value={text(run?.submitted_order ?? false)} tone={run?.submitted_order ? "text-red-100" : "text-cyan-100"} />
                  <Metric label="broker_called" value={text(run?.broker_called ?? false)} tone={run?.broker_called ? "text-red-100" : "text-cyan-100"} />
                  <Metric label="llm_used" value={text(run?.llm_used ?? false)} tone={run?.llm_used ? "text-red-100" : "text-cyan-100"} />
                  <Metric label="live_trading_blocked" value={String(!executionGates.live_trading_enabled)} />
                  <Metric label="broker_execution_blocked" value={String(!executionGates.broker_execution_enabled)} />
                </div>
              </Card>
            </div>
          ) : null}

          {sectionSub("command") === "data-status" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Data Status" error={data.readiness.error}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="source_mode" value={text(run?.source_mode)} />
                  <Metric label="using_non_real_data" value={text(run?.using_non_real_data ?? false)} />
                  <Metric label="provider_status" value={text(run?.provider_status ?? dataPipeline.provider_status)} />
                  <Metric label="provider_name" value={text(run?.provider_name ?? dataPipeline.provider_name)} />
                  <Metric label="usable_symbols" value={text(run?.usable_symbols)} />
                  <Metric label="rejected_symbols" value={text(run?.rejected_symbols)} />
                  <Metric label="snapshots / features" value={`${text(run?.latest_snapshot_count ?? 0)} / ${text(run?.feature_row_count ?? 0)}`} />
                  <Metric label="persistence / freshness / kafka" value={`${text(run?.persistence_status)} / ${text(run?.freshness_status)} / ${text(run?.kafka_status ?? "configured_optional_not_active")}`} />
                </div>
              </Card>
              <Card title="Evidence Status">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="qlib_available" value={text(run?.qlib_available ?? data.qlib.data?.qlib_available)} />
                  <Metric label="qlib_artifact_count" value={text(data.qlib.data?.artifact_count ?? nested(run, ["qlib_artifact_counts", "total"]))} />
                  <Metric label="proof_status" value={text(run?.proof_status ?? proofRecord.proof_status)} />
                  <Metric label="selected_model_key" value={text(run?.selected_model_key)} />
                  <Metric label="selected_strategy_key" value={text(run?.selected_strategy_key ?? run?.strategy_key)} />
                  <Metric label="evidence warnings/blockers" value={`${asList(run?.evidence_warnings).length} / ${asList(run?.evidence_blockers).length}`} />
                </div>
              </Card>
            </div>
          ) : null}

          {sectionSub("command") === "gates" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Small Account Gate" error={smallAccountReadiness.enabled === undefined && !run ? "No small-account run data yet." : null}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="account_equity" value={money(run?.account_equity ?? smallAccountReadiness.account_equity_default ?? 1000)} />
                  <Metric label="max_risk_dollars" value={money(run?.max_risk_dollars)} />
                  <Metric label="max_daily_loss_dollars" value={money(run?.max_daily_loss_dollars)} />
                  <Metric label="decision" value={text(run?.small_account_decision ?? smallAccountReadiness.status)} />
                  <Metric label="feasible_symbols" value={text(run?.feasible_symbols)} />
                  <Metric label="rejected_symbols" value={text(run?.small_account_rejected_symbols)} />
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div><div className="mb-1 text-xs font-semibold text-red-100">Blockers</div><IssueList items={run?.small_account_blockers} /></div>
                  <div><div className="mb-1 text-xs font-semibold text-amber-100">Warnings</div><IssueList items={run?.small_account_warnings} /></div>
                </div>
              </Card>
              <Card title="Approval / Execution" subtitle="Approval unlocks a gated workflow step. It does not submit a broker order." error={data.approvals.error}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="approval_required" value={text(run?.approval_required ?? false)} />
                  <Metric label="approval_id" value={text(run?.approval_id)} />
                  <Metric label="execution_boundary_reached" value={text(run?.execution_boundary_reached ?? false)} />
                  <Metric label="approval_items" value={approvalItems.length} />
                  <Metric label="open paper positions" value={openPositions.length} />
                  <Metric label="monitoring status" value={text(data.paper.data?.status ?? "not_available")} />
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === "workflow" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Workflow"
            title="Autonomous Agent Pipeline"
            description="Stage cards show pending, completed, running, warning, approval-gate, and blocked states from the latest orchestrator timeline."
          />
          <SubTabBar tabs={WORKFLOW_SUBTABS} active={sectionSub("workflow")} onSelect={(id) => setSectionSub("workflow", id)} />
          {sectionSub("workflow") === "overview" ? (
            <Card title="Run snapshot" subtitle="High-level state from the latest orchestrator run. Open Pipeline for per-stage detail." error={data.latest.error}>
              <div className="grid gap-2 md:grid-cols-2">
                <Metric label="status" value={status} />
                <Metric label="current stage" value={text(run?.current_stage)} />
                <Metric label="current agent" value={text(run?.current_agent_key)} />
                <Metric label="next action" value={text(run?.next_action)} />
                <Metric label="blockers / warnings" value={`${run?.blockers?.length ?? 0} / ${run?.warnings?.length ?? 0}`} />
                <Metric label="last run" value={text(run?.updated_at ?? run?.created_at)} />
              </div>
            </Card>
          ) : null}
          {sectionSub("workflow") === "pipeline" ? (
            <Card title="Pipeline Stages" subtitle="Process flow from data readiness through learning loop. Cards are driven by the latest orchestrator stage timeline.">
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-5">
                {STAGES.map((stage, index) => {
                  const row = stageMap[stage.key];
                  const snapshot = stageResult(row);
                  const isCurrent = run?.current_agent_key === stage.key;
                  const blockers = snapshotBlockers(snapshot);
                  const warnings = snapshotWarnings(snapshot);
                  const visual = stageVisualState({
                    row,
                    isCurrent,
                    isApprovalBoundary: stage.key === "execution_approval_agent",
                    blockers,
                    warnings,
                  });
                  return (
                    <div
                      key={stage.key}
                      className={`relative min-w-0 overflow-hidden rounded-xl border p-3 break-words transition-all duration-500 ${visual.card}`}
                    >
                      <div className={`absolute inset-x-0 top-0 h-0.5 ${visual.rail}`} />
                      <div className="pointer-events-none absolute -right-8 -top-8 h-16 w-16 rounded-full bg-white/5 blur-xl" />
                      <div className="mb-1.5 flex flex-wrap items-start justify-between gap-x-2 gap-y-1 text-[11px]">
                        <div className="min-w-0 font-bold uppercase tracking-[0.14em] text-slate-500">Stage {index + 1}</div>
                        <span className={`shrink-0 rounded-full border px-1.5 py-px font-bold uppercase ${visual.badge}`}>{visual.label}</span>
                      </div>
                      <div className="break-words text-[11px] font-semibold leading-snug text-slate-50">{stage.name}</div>
                      <p className="mt-1.5 min-h-8 text-[11px] leading-snug break-words text-slate-400">{stage.summary}</p>
                      <div className="mt-2 space-y-0.5 text-[11px] leading-snug break-words text-slate-300">
                        <div>
                          <span className="text-slate-500">Decision:</span>{" "}
                          {text(snapshot.small_account_decision ?? snapshot.proof_status ?? snapshot.selected_strategy_key ?? snapshot.selected_model_key ?? row?.status)}
                        </div>
                        <div>
                          <span className="text-slate-500">Key output:</span>{" "}
                          {text(snapshot.selected_symbol ?? snapshot.feasible_symbols ?? snapshot.strategy_key ?? snapshot.qlib_artifact_id ?? snapshot.latest_snapshot_count)}
                        </div>
                      </div>
                      {blockers.length ? (
                        <div className="mt-2 text-[11px] leading-snug break-words text-red-100 [&_li]:text-[11px] [&_p]:text-[11px] [&_ul]:text-[11px]">
                          <IssueList items={blockers} />
                        </div>
                      ) : null}
                      {warnings.length ? (
                        <div className="mt-2 text-[11px] leading-snug break-words text-amber-100 [&_li]:text-[11px] [&_p]:text-[11px] [&_ul]:text-[11px]">
                          <IssueList items={warnings} />
                        </div>
                      ) : null}
                      {stage.key === "execution_approval_agent" ? (
                        <div className="mt-2 rounded-md border border-amber-400/20 bg-amber-500/10 p-1.5 text-[11px] leading-snug break-words text-amber-100">
                          Approval boundary. No broker submission.
                        </div>
                      ) : null}
                    </div>
                  );
                })}
              </div>
            </Card>
          ) : null}
        </div>
      ) : null}

      {activeTab === "watchlist" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Live Watchlist"
            title="Candidates, Market Status, And Paper Monitoring"
            description="Focused view of selected symbol, scanner/watchlist outputs, market context, data readiness, and paper positions."
          />
          <SubTabBar tabs={WATCHLIST_SUBTABS} active={sectionSub("watchlist")} onSelect={(id) => setSectionSub("watchlist", id)} />
          {sectionSub("watchlist") === "market" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Market Status" error={data.watchlist.error}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="regime" value={text(latestSnapshot.regime ?? nested(latestSnapshot, ["market_context", "regime"]))} />
                  <Metric label="market condition" value={text(nested(latestSnapshot, ["market_context", "liquidity_state"]))} />
                  <Metric label="volatility" value={text(nested(latestSnapshot, ["market_context", "volatility_state"]))} />
                  <Metric label="watchlist endpoint" value={data.watchlist.error ? "unavailable" : "available"} />
                </div>
              </Card>
              <Card title="Watchlist">
                <Metric label="current watchlist symbols" value={text(watchlistSymbols.length ? watchlistSymbols : run?.symbols ?? run?.usable_symbols)} />
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div><div className="mb-1 text-xs font-semibold text-cyan-100">Usable symbols</div><IssueList items={run?.usable_symbols} empty="None yet" /></div>
                  <div><div className="mb-1 text-xs font-semibold text-red-100">Rejected symbols</div><IssueList items={run?.rejected_symbols} empty="None" /></div>
                </div>
              </Card>
            </div>
          ) : null}
          {sectionSub("watchlist") === "candidate" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Selected Candidate">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="selected symbol" value={text(run?.selected_symbol ?? run?.symbol)} />
                  <Metric label="latest price" value={money(latestSnapshot.latest_price)} />
                  <Metric label="spread bps" value={text(latestSnapshot.spread_bps)} />
                  <Metric label="avg dollar volume" value={money(latestSnapshot.avg_dollar_volume)} />
                </div>
              </Card>
            </div>
          ) : null}
          {sectionSub("watchlist") === "positions" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Paper Open Positions / Monitoring" error={data.paper.error}>
                <Metric label="paper open positions" value={hasPaperAccount ? openPositions.length : "Paper account data unavailable"} />
                <div className="mt-3 space-y-2">
                  {openPositions.length ? openPositions.map((position, index) => <div key={index} className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-300">{text(position)}</div>) : <p className="text-sm text-slate-500">No open paper positions reported.</p>}
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === "data" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Data Pipeline"
            title="Provider, Feature Store, Persistence, And Freshness"
            description="Shows the data path feeding the dry-run workflow, including provider status, feature rows, persistence mode, freshness, and optional Kafka state."
          />
          <SubTabBar tabs={DATA_SUBTABS} active={sectionSub("data")} onSelect={(id) => setSectionSub("data", id)} />
          {sectionSub("data") === "provider" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <div className="xl:col-span-2">
                <ProviderStatusCard summary={providerSummary} />
              </div>
            </div>
          ) : null}
          {sectionSub("data") === "metrics" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              {[
                ["Workflow Source Mode", run?.source_mode ?? "runtime"],
                ["Snapshot Status", `${text(run?.latest_snapshot_status)} (${text(run?.latest_snapshot_count ?? 0)})`],
                ["Feature Store Status", `${text(run?.feature_store_status ?? dataPipeline.feature_store_status)} (${text(run?.feature_row_count ?? 0)} rows)`],
                ["Persistence Status", run?.persistence_status ?? dataPipeline.persistence_status],
                ["Freshness Status", run?.freshness_status ?? dataPipeline.freshness_status],
                ["Kafka Status", run?.kafka_status ?? "Configured optional, not active in workflow"],
              ].map(([title, value]) => (
                <Card key={String(title)} title={String(title)}><Metric label="status" value={text(value)} /></Card>
              ))}
            </div>
          ) : null}
          {sectionSub("data") === "gaps" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Missing Features">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="missing snapshot" value={String(!run?.latest_snapshot_count)} />
                  <Metric label="missing price" value={String(latestSnapshot.latest_price == null)} />
                  <Metric label="missing volume" value={String(latestSnapshot.volume == null)} />
                  <Metric label="missing spread" value={String(latestSnapshot.spread_bps == null)} />
                  <Metric label="missing relative volume" value={String(latestSnapshot.relative_volume == null)} />
                  <Metric label="feature rows unavailable" value={String(!run?.feature_row_count)} />
                  <Metric label="persistence fallback used" value={String(run?.persistence_status === "memory_fallback" || dataPipeline.persistence_status === "memory_fallback")} />
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === "strategy" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Strategy & Models"
            title="Evidence-Gated Strategy And Model Selection"
            description="Shows selected strategy/model context, not-trained models, blocked models, and the normalized evidence used by the workflow."
          />
          <SubTabBar tabs={STRATEGY_SUBTABS} active={sectionSub("strategy")} onSelect={(id) => setSectionSub("strategy", id)} />
          {sectionSub("strategy") === "strategy" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Strategy">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="selected strategy" value={text(run?.selected_strategy_key ?? strategyRecord.strategy_key)} />
                  <Metric label="strategy status" value={text(strategyRecord.status ?? evidencePipeline.strategy_evidence_status)} />
                  <Metric label="strategy score" value={text(strategyRecord.strategy_score)} />
                  <Metric label="why selected" value={text(strategyRecord.regime_fit ? `regime_fit=${strategyRecord.regime_fit}` : "Selected by strategy evidence and workflow gates when available.")} />
                </div>
                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div><div className="mb-1 text-xs font-semibold text-red-100">Blockers</div><IssueList items={strategyRecord.blockers} /></div>
                  <div><div className="mb-1 text-xs font-semibold text-amber-100">Warnings</div><IssueList items={strategyRecord.warnings} /></div>
                </div>
              </Card>
            </div>
          ) : null}
          {sectionSub("strategy") === "models" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Models">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="selected model" value={text(run?.selected_model_key ?? modelRecord.model_key)} />
                  <Metric label="model family" value={text(modelRecord.model_family)} />
                  <Metric label="model status" value={text(modelRecord.status ?? evidencePipeline.model_evidence_status)} />
                  <Metric label="confidence / score / rank" value={`${text(modelRecord.confidence)} / ${text(modelRecord.score)} / ${text(modelRecord.rank)}`} />
                  <Metric label="not trained models" value={text(nested(data.model.data, ["summary", "not_trained_models"]))} />
                  <Metric label="blocked models" value={text(nested(data.model.data, ["summary", "blocked_models"]))} />
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === "promotion" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Promotion"
            title="Promotion Center"
            description="Evidence and readiness only. Does not submit orders, enable live trading, or activate strategies. Metrics come from stored evidence records only."
          />
          <SubTabBar tabs={PROMOTION_SUBTABS} active={sectionSub("promotion")} onSelect={(id) => setSectionSub("promotion", id)} />
          {sectionSub("promotion") === "overview" ? (
            <Card title="What promotion means here" subtitle="Evidence and readiness only — no order submission or live activation.">
              <p className="text-sm leading-6 text-slate-400">
                Use <span className="text-cyan-200/90">Promotion requirements</span> for the metric thresholds,{" "}
                <span className="text-cyan-200/90">Strategy promotion</span> for the strategy table, and{" "}
                <span className="text-cyan-200/90">Model promotion</span> for the model table. All data is read-only from stored evidence.
              </p>
            </Card>
          ) : null}
          <PromotionCenterPanel activeSection={sectionSub("promotion") as PromotionCenterActiveSection} />
        </div>
      ) : null}

      {activeTab === "evidence" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Qlib & Evidence"
            title="Research Evidence, Proof, Model, And Strategy Registries"
            description="Qlib is optional and safe when unavailable. Evidence supports workflow gates only and never submits orders."
          />
          <SubTabBar tabs={EVIDENCE_SUBTABS} active={sectionSub("evidence")} onSelect={(id) => setSectionSub("evidence", id)} />
          {sectionSub("evidence") === "qlib" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Qlib Research Evidence" subtitle="Qlib is optional. Qlib evidence can support research/model/backtest validation but does not execute trades." error={data.qlib.error}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="used for" value="research, model evidence, signal scoring, backtest references" />
                  <Metric label="installed/configured" value={`${text(data.qlib.data?.qlib_available)} / ${text(data.qlib.data?.configured)}`} />
                  <Metric label="artifact counts" value={text(data.qlib.data?.artifact_count ?? nested(run, ["qlib_artifact_counts", "total"]))} />
                  <Metric label="latest signal/backtest/model" value={`${text(data.qlib.data?.latest_signal_count)} / ${text(data.qlib.data?.latest_backtest_count)} / ${text(data.qlib.data?.latest_model_count)}`} />
                  <Metric label="used in workflow" value={text(run?.qlib_artifact_id ? "artifact referenced" : "not required")} />
                  <Metric label="warning" value={data.qlib.data?.qlib_available === false ? "Qlib unavailable; workflow may continue unless strategy requires Qlib evidence." : "None"} />
                </div>
              </Card>
            </div>
          ) : null}
          {sectionSub("evidence") === "proof" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Proof Registry">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="proof registry status" value={text(evidencePipeline.proof_registry_status)} />
                  <Metric label="proof_status" value={text(run?.proof_status ?? proofRecord.proof_status)} />
                  <Metric label="backtest status" value={text(proofRecord.backtest_status ?? proofRecord.proof_type)} />
                  <Metric label="paper status" value={text(proofRecord.paper_status)} />
                  <Metric label="sample size" value={text(proofRecord.sample_size)} />
                  <Metric label="avg R / max DD / win rate" value={`${text(proofRecord.avg_r_multiple)} / ${text(proofRecord.max_drawdown_r)} / ${text(proofRecord.win_rate)}`} />
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === "execution" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Execution & Approval"
            title="Paper Execution Boundary And Human Handoff"
            description="Approval unlocks a gated workflow step only. Broker order submission and live execution are not active in this autonomous workflow."
          />
          <SubTabBar tabs={EXECUTION_SUBTABS} active={sectionSub("execution")} onSelect={(id) => setSectionSub("execution", id)} />
          {sectionSub("execution") === "plan" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Execution Planner" subtitle="Approval unlocks a gated workflow step. It does not submit a broker order.">
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="planner status" value={text(stageMap.execution_planner_agent?.status ?? "not_run")} />
                  <Metric label="planned action" value={text(nested(stageMap.execution_planner_agent, ["pipeline_inputs_snapshot", "selected_symbol"]) ? "paper plan preview" : "none")} />
                  <Metric label="planned risk" value={money(latestSnapshot.planned_risk_dollars)} />
                  <Metric label="max risk dollars" value={money(run?.max_risk_dollars)} />
                  <Metric label="max daily loss" value={money(run?.max_daily_loss_dollars)} />
                  <Metric label="execution boundary reached" value={text(run?.execution_boundary_reached ?? false)} />
                </div>
              </Card>
              <Card title="Approval Items" error={data.approvals.error}>
                <Metric label="approval required" value={text(run?.approval_required ?? false)} />
                <div className="mt-3 space-y-2">
                  {approvalItems.length ? approvalItems.slice(0, 6).map((item) => (
                    <div key={item.approval_id} className="rounded-xl border border-white/10 bg-black/20 p-3 text-sm text-slate-300">
                      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                        <span className="font-mono text-cyan-200">{item.approval_id}</span>
                        <Badge tone={item.status === "pending" ? "warn" : item.status === "approved" ? "safe" : "blocked"}>{item.status}</Badge>
                      </div>
                      {item.status === "pending" ? (
                        <ApprovalActionSelect
                          label="Approve gated workflow handoff"
                          disabled={false}
                          disabledReason="Approves only the gated workflow step. No broker order is submitted."
                          busy={approvalBusyId === item.approval_id}
                          onApprove={() => approvalAction(item.approval_id, "approve")}
                          onDecline={() => approvalAction(item.approval_id, "reject")}
                        />
                      ) : null}
                    </div>
                  )) : <p className="text-sm text-slate-500">No approval items reported.</p>}
                </div>
              </Card>
            </div>
          ) : null}
          {sectionSub("execution") === "monitoring" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Paper Trades / Monitoring" error={data.paper.error}>
                <div className="grid gap-2 md:grid-cols-2">
                  <Metric label="paper open positions" value={hasPaperAccount ? openPositions.length : "Paper account data unavailable"} />
                  <Metric label="paper monitoring status" value={hasPaperAccount ? text(data.paper.data?.status ?? "available") : "Paper account data unavailable"} />
                </div>
              </Card>
            </div>
          ) : null}
          {sectionSub("execution") === "safety" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Approval Safety Status" subtitle="Broker and live controls are safety status cards only, not buttons.">
                <div className="grid gap-3 lg:grid-cols-3">
                  <SafetyStatusCard title="Broker Order Submission" status="Disabled">
                    Broker order submission is not active in the autonomous workflow.
                  </SafetyStatusCard>
                  <SafetyStatusCard title="Live Execution" status="Disabled">
                    Live execution is intentionally blocked. Paper-first workflow approval does not submit broker orders.
                  </SafetyStatusCard>
                  <SafetyStatusCard title="Approval Meaning">
                    Approval unlocks a gated workflow step only. It does not submit an order.
                  </SafetyStatusCard>
                </div>
              </Card>
            </div>
          ) : null}
        </div>
      ) : null}

      {activeTab === "runbook" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Runbook Status" subtitle="Workflow runbook data rendered inside Day-Trading OS." error={data.runbookStatus.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="status" value={text(data.runbookStatus.data?.status)} />
              <Metric label="data mode" value={text(data.runbookStatus.data?.data_mode)} />
              <Metric label="updated" value={text(data.runbookStatus.data?.updated_at)} />
              <Metric label="latest workflow status" value={text(run?.status)} />
            </div>
          </Card>
          <Card title="Runbook Latest" error={data.runbookLatest.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="workflow_run_id" value={text(run?.workflow_run_id)} />
              <Metric label="orchestrator_run_id" value={text(run?.orchestrator_run_id)} />
              <Metric label="current stage" value={text(run?.current_stage)} />
              <Metric label="next action" value={text(run?.next_action)} />
            </div>
          </Card>
          <Card title="Runbook Stages" error={data.runbookStages.error}>
            <MiniTable rows={runbookStages} empty="No runbook stages reported." />
          </Card>
        </div>
      ) : null}

      {activeTab === "agentRuntime" ? (
        <div className="space-y-4">
          <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Current Runtime Configuration" subtitle="Same runtime contract as the legacy Agent Runtime page, organized for production operations." error={data.agentRuntimeStatus.error || data.agentRuntime.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="runtime status" value={text(data.agentRuntimeStatus.data?.status)} />
              <Metric label="registered agents" value={text(data.agentRuntime.data?.registered_agents_count ?? runtimeSummary.registered_agents_count ?? runtimeAgents.length)} />
              <Metric label="workflow runs" value={text(runtimeSummary.workflow_runs_count)} />
              <Metric label="agent runs" value={text(runtimeSummary.agent_runs_count)} />
              <Metric label="persistence" value={text(data.agentRuntime.data?.persistence_mode ?? runtimeSummary.persistence_mode)} />
              <Metric label="redis mode" value={text(data.agentRuntime.data?.redis_mode ?? runtimeSummary.redis_mode)} />
              <Metric label="LLM required" value={text(runtimeSummary.llm_required)} />
              <Metric label="broker submission enabled" value={text(runtimeSummary.broker_submission_enabled)} />
              <Metric label="latest workflow" value={text(nested(data.agentRuntime.data, ["latest_workflow_run", "workflow_run_id"]))} />
              <Metric label="next action" value={text(runtimeSummary.next_action)} />
            </div>
          </Card>
          <Card title="Runtime Safety Flags">
            <div className="grid gap-2 md:grid-cols-2">
              {["no_broker_calls", "no_execution_submit", "no_llm_calls", "dry_run_default"].map((key) => (
                <Metric key={key} label={key} value={text(runtimeSafety[key])} tone={runtimeSafety[key] === false ? "text-red-100" : "text-cyan-100"} />
              ))}
            </div>
          </Card>
          </div>
          <Card title="Agent Inventory" subtitle="Registered deterministic/LLM/orchestrator agents, stage placement, tools, forbidden actions, and safety notes." error={data.agentRuntimeAgents.error}>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[1100px] border-collapse text-left text-xs">
                <thead>
                  <tr className="border-b border-cyan-400/10 text-[10px] uppercase tracking-wider text-slate-500">
                    <th className="pb-2 pr-2">agent_key</th>
                    <th className="pb-2 pr-2">display</th>
                    <th className="pb-2 pr-2">stage</th>
                    <th className="pb-2 pr-2">role</th>
                    <th className="pb-2 pr-2">type</th>
                    <th className="pb-2 pr-2">status</th>
                    <th className="pb-2 pr-2">uses_llm</th>
                    <th className="pb-2 pr-2">allowed_tools</th>
                    <th className="pb-2 pr-2">forbidden_actions</th>
                    <th className="pb-2">safety_notes</th>
                  </tr>
                </thead>
                <tbody>
                  {runtimeAgents.map((agent) => (
                    <tr key={agent.agent_key} className="border-b border-white/[0.04] align-top text-slate-300">
                      <td className="py-2 pr-2 font-mono text-cyan-200">{agent.agent_key}</td>
                      <td className="py-2 pr-2">{agent.display_name}</td>
                      <td className="py-2 pr-2">{agent.stage_number ?? "-"}</td>
                      <td className="py-2 pr-2">{agent.role}</td>
                      <td className="py-2 pr-2">{agent.agent_type}</td>
                      <td className="py-2 pr-2">{agent.status}</td>
                      <td className="py-2 pr-2">{agent.uses_llm ? "yes" : "no"}</td>
                      <td className="py-2 pr-2 font-mono text-[10px] text-slate-400">{(agent.allowed_tools ?? []).join(", ") || "-"}</td>
                      <td className="py-2 pr-2 font-mono text-[10px] text-slate-400">{(agent.forbidden_actions ?? []).join(", ") || "-"}</td>
                      <td className="py-2 text-[11px] text-slate-500">{(agent.safety_notes ?? []).join("; ") || "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
          <div className="grid gap-4 xl:grid-cols-2">
            <Card title="Latest Agent Runs" subtitle="Most recent persisted run for each registered agent.">
              <MiniTable rows={Object.values(latestAgentRuns)} empty="No agent runs reported." />
            </Card>
            <Card title="Safe Sample Agent Run" subtitle="Dry-run only. Useful for runtime smoke checks inside this platform.">
              <div className="space-y-3">
                <p className="text-sm text-slate-400">Runs `session_router_agent` by default through `/api/agent-runtime/agent-runs` with no broker, submit, or LLM decisioning.</p>
                <button
                  type="button"
                  disabled={agentRunBusy}
                  onClick={() => runSampleAgent("session_router_agent")}
                  className="rounded-xl border border-cyan-400/40 bg-cyan-400/10 px-4 py-2 text-sm font-bold text-cyan-100 disabled:opacity-50"
                >
                  {agentRunBusy ? "Running..." : "Run Safe Runtime Smoke Check"}
                </button>
                {agentRunResult ? (
                  <div className="rounded-2xl border border-cyan-400/10 bg-black/25 p-3">
                    <div className="grid gap-2 md:grid-cols-2">
                      <Metric label="run_id" value={agentRunResult.run_id} />
                      <Metric label="status" value={agentRunResult.status} />
                      <Metric label="next_agent" value={agentRunResult.next_agent ?? "-"} />
                      <Metric label="next_action" value={agentRunResult.next_action} />
                    </div>
                    <DebugPanel title="Agent decision and trace" value={{ decision: agentRunResult.decision, trace: agentRunResult.trace }} />
                  </div>
                ) : null}
              </div>
            </Card>
          </div>
        </div>
      ) : null}

      {activeTab === "approvalQueue" ? (
        <div className="space-y-4">
          <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
            Approval unlocks a gated workflow step. It does not submit a broker order, call Alpaca, or enable live execution.
          </div>
          {runMessage ? <div className="rounded-2xl border border-cyan-400/20 bg-cyan-500/10 p-3 text-sm text-cyan-100">{runMessage}</div> : null}
          <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Approval Queue" subtitle="Approvals are gates only. They do not submit broker orders." error={data.approvals.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="approval required" value={text(run?.approval_required ?? false)} />
              <Metric label="approval_id" value={text(run?.approval_id)} />
              <Metric label="execution boundary" value={text(run?.execution_boundary_reached ?? false)} />
              <Metric label="queue items" value={approvalItems.length} />
              <Metric label="pending" value={approvalItems.filter((item) => item.status === "pending").length} />
              <Metric label="approved" value={approvalItems.filter((item) => item.status === "approved").length} />
            </div>
          </Card>
          <Card title="Approval Note">
            <label className="text-xs font-semibold uppercase tracking-[0.14em] text-slate-500">
              Optional reason / note
              <input
                value={approvalReason}
                onChange={(event) => setApprovalReason(event.target.value)}
                className="mt-2 w-full rounded-xl border border-cyan-400/10 bg-black/30 px-3 py-2 text-sm normal-case tracking-normal text-slate-100 outline-none focus:border-cyan-400/50"
                placeholder="Why approve or reject this gate?"
              />
            </label>
          </Card>
          </div>
          <Card title="Approval Items" error={data.approvals.error}>
            <div className="space-y-4">
              {approvalItems.length ? approvalItems.map((item) => (
                <div key={item.approval_id} className="rounded-2xl border border-cyan-400/10 bg-black/25 p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="font-mono text-sm text-cyan-200">{item.approval_id}</div>
                      <div className="mt-1 text-xs text-slate-500">workflow <span className="font-mono text-slate-300">{item.workflow_run_id}</span></div>
                      {item.orchestrator_run_id ? <div className="text-xs text-slate-500">orchestrator <span className="font-mono text-slate-300">{item.orchestrator_run_id}</span></div> : null}
                    </div>
                    <Badge tone={item.status === "pending" ? "warn" : item.status === "approved" ? "safe" : "blocked"}>{item.status}</Badge>
                  </div>
                  <div className="mt-3 grid gap-2 md:grid-cols-4">
                    <Metric label="type" value={item.approval_type} />
                    <Metric label="required approver" value={item.required_approver ?? "-"} />
                    <Metric label="expires" value={item.expires_at ?? "-"} />
                    <Metric label="created" value={item.created_at} />
                  </div>
                  <div className="mt-3 grid gap-3 xl:grid-cols-2">
                    <div className="rounded-xl border border-cyan-400/10 bg-black/20 p-3">
                      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Requested action</div>
                      <pre className="mt-2 max-h-48 overflow-auto text-xs text-slate-300">{JSON.stringify(item.requested_action, null, 2)}</pre>
                    </div>
                    <div className="rounded-xl border border-cyan-400/10 bg-black/20 p-3">
                      <div className="text-xs font-semibold uppercase tracking-wider text-slate-500">Risk summary</div>
                      <pre className="mt-2 max-h-48 overflow-auto text-xs text-slate-300">{JSON.stringify(item.risk_summary, null, 2)}</pre>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-3 lg:grid-cols-3">
                    <ApprovalActionSelect
                      label="Approve gated workflow handoff"
                      disabled={item.status !== "pending"}
                      disabledReason={item.status !== "pending" ? `No approval needed because this item is ${item.status}.` : "Approves only the gated workflow step. No broker order is submitted."}
                      busy={approvalBusyId === item.approval_id}
                      onApprove={() => approvalAction(item.approval_id, "approve")}
                      onDecline={() => approvalAction(item.approval_id, "reject")}
                    />
                    <SafetyStatusCard title="Broker Order Submission" status="Disabled">
                      Broker order submission is not active in the autonomous workflow.
                    </SafetyStatusCard>
                    <SafetyStatusCard title="Live Execution" status="Disabled">
                      Live execution is intentionally blocked. Paper-first workflow approval does not submit broker orders.
                    </SafetyStatusCard>
                  </div>
                  <div className="mt-3">
                    <SafetyStatusCard title="Approval Meaning">
                      Approval unlocks a gated workflow step only. It does not submit an order.
                    </SafetyStatusCard>
                  </div>
                </div>
              )) : (
                <div className="rounded-2xl border border-cyan-400/10 bg-black/25 p-4">
                  <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <div className="text-lg font-semibold text-slate-100">No pending approval request</div>
                      <p className="mt-1 text-sm text-slate-500">
                        The approval controls are shown here so operators know where approvals will happen when the workflow creates a gate.
                      </p>
                    </div>
                    <Badge tone="paper">No approval needed</Badge>
                  </div>
                  <div className="grid gap-3 lg:grid-cols-3">
                    <SafetyStatusCard title="Broker Order Submission" status="Disabled">
                      Broker order submission is not active in the autonomous workflow.
                    </SafetyStatusCard>
                    <SafetyStatusCard title="Live Execution" status="Disabled">
                      Live execution is intentionally blocked. Paper-first workflow approval does not submit broker orders.
                    </SafetyStatusCard>
                    <SafetyStatusCard title="Approval Meaning">
                      Approval unlocks a gated workflow step only. It does not submit an order.
                    </SafetyStatusCard>
                  </div>
                </div>
              )}
            </div>
          </Card>
        </div>
      ) : null}

      {activeTab === "auditLog" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Audit Log Status" error={data.auditStatus.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="status" value={text(data.auditStatus.data?.status)} />
              <Metric label="updated" value={text(data.auditStatus.data?.updated_at)} />
              <Metric label="event count" value={auditEvents.length} />
              <Metric label="workflow_run_id" value={text(run?.workflow_run_id)} />
            </div>
          </Card>
          <Card title="Recent Audit Events" error={data.auditEvents.error}>
            <MiniTable rows={auditEvents} empty="No audit events reported." />
          </Card>
        </div>
      ) : null}

      {activeTab === "governance" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Governance Status" error={data.governanceStatus.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="status" value={text(data.governanceStatus.data?.status)} />
              <Metric label="workflow enabled" value={text(nested(data.readiness.data, ["systems", "execution_gates", "workflow_enabled"]))} />
              <Metric label="human approval" value={text(nested(data.readiness.data, ["systems", "execution_gates", "require_human_approval"]))} />
              <Metric label="emergency stop" value={text(nested(data.readiness.data, ["systems", "execution_gates", "emergency_stop"]))} />
            </div>
          </Card>
          <Card title="Autonomous Boundaries">
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="supported horizons" value={text(nested(data.readiness.data, ["systems", "endpoint_boundaries", "supported_horizons"]))} />
              <Metric label="blocked horizons" value={text(nested(data.readiness.data, ["systems", "endpoint_boundaries", "blocked_horizons"]))} />
              <Metric label="broker submit blocked" value={text(nested(data.readiness.data, ["systems", "endpoint_boundaries", "broker_submit_blocked"]))} />
              <Metric label="LLM decisioning blocked" value={text(nested(data.readiness.data, ["systems", "endpoint_boundaries", "llm_decisioning_blocked"]))} />
            </div>
          </Card>
        </div>
      ) : null}

      {activeTab === "scheduler" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Scheduler Status" error={data.schedulerStatus.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="status" value={text(data.schedulerStatus.data?.status)} />
              <Metric label="updated" value={text(data.schedulerStatus.data?.updated_at)} />
              <Metric label="schedules" value={schedules.length} />
              <Metric label="safe run endpoint" value="/api/workflow-orchestrator/run" />
            </div>
          </Card>
          <Card title="Schedules" error={data.schedules.error}>
            <MiniTable rows={schedules} empty="No schedules reported." />
          </Card>
        </div>
      ) : null}

      {activeTab === "platformReadiness" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Platform Readiness" error={data.readiness.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="status" value={text(data.readiness.data?.status)} />
              <Metric label="data mode" value={text(data.readiness.data?.data_mode)} />
              <Metric label="updated" value={text(data.readiness.data?.updated_at)} />
              <Metric label="next action" value={text(data.readiness.data?.next_action)} />
            </div>
          </Card>
          <Card title="Systems">
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="data pipeline" value={text(nested(data.readiness.data, ["systems", "data_pipeline", "provider_status"]))} />
              <Metric label="evidence pipeline" value={text(nested(data.readiness.data, ["systems", "evidence_pipeline", "proof_registry_status"]))} />
              <Metric label="small account" value={text(nested(data.readiness.data, ["systems", "small_account_feasibility", "status"]))} />
              <Metric label="endpoint boundary" value={text(nested(data.readiness.data, ["systems", "endpoint_boundaries", "mixed_endpoint_risk"]))} />
            </div>
          </Card>
        </div>
      ) : null}

      {activeTab === "researchEvidence" ? (
        <div className="grid gap-4 xl:grid-cols-2">
          <Card title="Proof Evidence" error={data.proof.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="proof status" value={text(run?.proof_status ?? proofRecord.proof_status)} />
              <Metric label="sample size" value={text(proofRecord.sample_size)} />
              <Metric label="avg R" value={text(proofRecord.avg_r_multiple)} />
              <Metric label="max drawdown" value={text(proofRecord.max_drawdown_r)} />
            </div>
          </Card>
          <Card title="Model & Strategy Evidence">
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="selected model" value={text(run?.selected_model_key ?? modelRecord.model_key)} />
              <Metric label="model status" value={text(modelRecord.status)} />
              <Metric label="selected strategy" value={text(run?.selected_strategy_key ?? strategyRecord.strategy_key)} />
              <Metric label="strategy status" value={text(strategyRecord.status)} />
            </div>
          </Card>
          <Card title="Qlib Evidence" subtitle="Qlib is optional and never executes trades." error={data.qlib.error}>
            <div className="grid gap-2 md:grid-cols-2">
              <Metric label="qlib available" value={text(data.qlib.data?.qlib_available)} />
              <Metric label="artifact count" value={text(data.qlib.data?.artifact_count)} />
              <Metric label="latest signals" value={text(data.qlib.data?.latest_signal_count)} />
              <Metric label="latest backtests" value={text(data.qlib.data?.latest_backtest_count)} />
            </div>
          </Card>
        </div>
      ) : null}

      {activeTab === "debug" ? (
        <div className="space-y-4">
          <SectionHeader
            eyebrow="Issues / Debug"
            title="Blockers, Warnings, Endpoint Failures, And Raw State"
            description="Debug view for failed data loads, readiness gaps, governance warnings, and collapsed raw JSON from the latest workflow run."
          />
          <SubTabBar tabs={DEBUG_SUBTABS} active={sectionSub("debug")} onSelect={(id) => setSectionSub("debug", id)} />
          {sectionSub("debug") === "issues" ? (
            <div className="grid gap-4 xl:grid-cols-2">
              <Card title="Hard Blockers"><IssueList items={[...(run?.blockers ?? []), ...asList(data.finalReadiness.data?.blockers)]} /></Card>
              <Card title="Soft Warnings"><IssueList items={[...(run?.warnings ?? []), ...asList(data.finalReadiness.data?.warnings)]} /></Card>
              <Card title="Missing / Failing Components"><IssueList items={[...asList(data.finalReadiness.data?.missing_core_units), ...Object.entries(data).filter(([, value]) => value.error).map(([key, value]) => `${key}: ${value.error}`)]} /></Card>
              <Card title="Common Workflow Issues">
                <IssueList
                  items={[
                    run?.freshness_status === "stale" ? "stale data" : null,
                    data.qlib.data?.qlib_available === false ? "Qlib unavailable" : null,
                    run?.persistence_status === "memory_fallback" ? "persistence fallback" : null,
                    run?.proof_status === "backtest_required" || run?.proof_status === "proof_required" ? "proof missing" : null,
                    run?.small_account_decision === "blocked" ? "small account blocked" : null,
                  ].filter(Boolean)}
                />
              </Card>
            </div>
          ) : null}
          {sectionSub("debug") === "raw" ? (
            <div className="space-y-4">
              <DebugPanel title="Raw orchestrator response" value={data.latest.data} />
              <DebugPanel title="Raw readiness response" value={data.readiness.data} />
              <DebugPanel title="Raw Qlib response" value={data.qlib.data} />
              <DebugPanel title="Raw evidence response" value={{ proof: data.proof.data, model: data.model.data, strategy: data.strategy.data }} />
              <DebugPanel title="Raw agent runtime latest" value={data.agentRuntime.data} />
            </div>
          ) : null}
        </div>
      ) : null}
        </div>
      </main>
    </div>
  );
}
