"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { MetricCard, PageHeader } from "@/components/Cards";
import {
  api,
  type AutoRunControlState,
  type CoreAgentRegistryItem,
  type AiOpsAgentScorecard,
  type AiOpsAgentStatusResponse,
  type AiOpsAuditEvent,
  type AiOpsAuditEventsResponse,
  type AiOpsLlmUsageResponse,
  type AiOpsSchedulerJobsResponse,
  type AiOpsSummaryResponse,
  type AiOpsWorkflow,
  type AiOpsWorkflowListResponse,
  type DataSourceKind,
  type EdgeRadarRunResponse,
  type StrategyConfig,
} from "@/lib/api";

function SourceBadge({ source }: { source?: DataSourceKind | null }) {
  const value = source || "placeholder";
  const tone =
    value === "source_backed"
      ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
      : value === "demo"
        ? "border-cyan-500 bg-cyan-500/10 text-cyan-300"
        : "border-amber-500 bg-amber-500/10 text-amber-300";
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${tone}`}>{String(value).replace(/_/g, " ")}</span>;
}

function StatusBadge({ status }: { status?: string | null }) {
  const value = status || "unknown";
  const tone =
    value.includes("running") || value.includes("configured") || value.includes("completed") || value === "ok"
      ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
      : value.includes("fail") || value.includes("error") || value.includes("disabled")
        ? "border-rose-500 bg-rose-500/10 text-rose-300"
        : "border-slate-600 bg-slate-800 text-slate-300";
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${tone}`}>{value.replace(/_/g, " ")}</span>;
}

function PageShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">{children}</div>
    </div>
  );
}

function LoadingState({ label }: { label: string }) {
  return <div className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-8 text-center text-sm text-slate-300">Loading {label}...</div>;
}

function ErrorState({ error }: { error: string }) {
  return <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>;
}

function EmptyState({ label }: { label: string }) {
  return <div className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-8 text-center text-sm text-slate-300">No {label} available yet.</div>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-emerald-500">{title}</h2>
      {children}
    </section>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "Not run";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function percent(value?: number | null) {
  if (value === null || value === undefined) return "N/A";
  return `${Math.round(value * 100)}%`;
}

function money(value?: number | null) {
  if (value === null || value === undefined) return "$0.00";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 4 })}`;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asText(value: unknown, fallback = "N/A") {
  if (value === null || value === undefined || value === "") return fallback;
  if (Array.isArray(value)) return value.length ? value.join(", ") : fallback;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function workflowName(workflow: AiOpsWorkflow) {
  return workflow.workflow_name || workflow.name || "Unnamed workflow";
}

function workflowRows(data?: AiOpsWorkflowListResponse | null) {
  return data?.workflows ?? [];
}

function allAgents(data?: AiOpsAgentStatusResponse | null) {
  return [...(data?.foundation_agents ?? []), ...(data?.existing_scorecards ?? [])];
}

function notesFor(agent: AiOpsAgentScorecard) {
  return agent.scorecard_notes ?? agent.notes ?? [];
}

function AgentHealthTable({ agents }: { agents: AiOpsAgentScorecard[] }) {
  if (!agents.length) return <EmptyState label="agent status records" />;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full min-w-[1120px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr>
            <th className="px-4 py-3">Agent</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Role</th>
            <th className="px-4 py-3">Last Run</th>
            <th className="px-4 py-3">Run Count</th>
            <th className="px-4 py-3">Success Rate</th>
            <th className="px-4 py-3">Notes</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {agents.map((agent, index) => (
            <tr key={`${agent.agent_key || agent.agent_name || agent.name}-${index}`} className="hover:bg-emerald-950/20">
              <td className="px-4 py-3 font-bold text-white">{agent.agent_name || agent.name || agent.agent_key || "Unnamed agent"}</td>
              <td className="px-4 py-3"><StatusBadge status={agent.status || agent.drift_status} /></td>
              <td className="px-4 py-3 text-slate-300">{agent.role || agent.agent_key || "foundation"}</td>
              <td className="px-4 py-3 text-slate-300">{formatDate(agent.last_run_at)}</td>
              <td className="px-4 py-3 text-slate-300">{agent.run_count ?? 0}</td>
              <td className="px-4 py-3 text-slate-300">{percent(agent.success_rate)}</td>
              <td className="max-w-lg px-4 py-3 text-slate-400">{notesFor(agent).join(" ") || "No notes yet."}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function WorkflowsTable({ workflows }: { workflows: AiOpsWorkflow[] }) {
  if (!workflows.length) return <EmptyState label="configured workflows" />;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full min-w-[1120px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr>
            <th className="px-4 py-3">Workflow</th>
            <th className="px-4 py-3">Trigger</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Agents</th>
            <th className="px-4 py-3">Data Source</th>
            <th className="px-4 py-3">Last Run</th>
            <th className="px-4 py-3">Next Step</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {workflows.map((workflow) => (
            <tr key={workflowName(workflow)} className="hover:bg-emerald-950/20">
              <td className="px-4 py-3 font-bold text-white">{workflowName(workflow).replace(/_/g, " ")}</td>
              <td className="px-4 py-3 text-slate-300">{workflow.trigger || workflow.mode || workflow.entrypoint || "manual"}</td>
              <td className="px-4 py-3"><StatusBadge status={workflow.status} /></td>
              <td className="px-4 py-3 text-slate-300">{Array.isArray(workflow.agents) ? workflow.agents.join(", ") : workflow.agents ?? "Configured stack"}</td>
              <td className="px-4 py-3"><SourceBadge source={workflow.data_source} /></td>
              <td className="px-4 py-3 text-slate-300">{formatDate(workflow.last_run_at || workflow.last_run)}</td>
              <td className="max-w-lg px-4 py-3 text-slate-400">{workflow.next_step || workflow.entrypoint || "Ready for paper/research use."}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OrchestrationStatus({ summary }: { summary: AiOpsSummaryResponse }) {
  const orchestration = asRecord(summary.orchestration);
  const entries = ["langgraph", "deepagents", "litellm", "apscheduler"].map((key) => {
    const item = asRecord(orchestration[key]);
    return {
      key,
      status: asText(item.status, summary.status),
      available: asText(item.available ?? item.apscheduler_available ?? item.installed_via_requirements, "configured"),
    };
  });
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
      {entries.map((entry) => (
        <div key={entry.key} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">{entry.key}</p>
          <div className="mt-2"><StatusBadge status={entry.status} /></div>
          <p className="mt-3 text-sm text-slate-300">Availability: {entry.available}</p>
        </div>
      ))}
    </div>
  );
}

function GuardrailGrid({ summary, llm }: { summary?: AiOpsSummaryResponse | null; llm?: AiOpsLlmUsageResponse | null }) {
  const guards = [
    ["Live trading", summary?.live_trading_allowed ? "Enabled" : "Disabled"],
    ["Paper trading", "Enabled for research"],
    ["Execution agent", "Disabled"],
    ["Human approval", summary?.paper_trading_requires_approval === false ? "Not required" : "Required"],
    ["Max daily LLM cost", money(llm?.cost_limit ?? 25)],
    ["Max daily agent runs", "100"],
  ];
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-6">
      {guards.map(([label, value]) => <MetricCard key={label} label={label} value={value} />)}
    </div>
  );
}

function boolText(value: boolean) {
  return value ? "Yes" : "No";
}

function CoreAgentRegistryTable({ agents }: { agents: CoreAgentRegistryItem[] }) {
  if (!agents.length) return <EmptyState label="core agent registry entries" />;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full min-w-[1280px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr><th className="px-4 py-3">Agent</th><th className="px-4 py-3">Category</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Uses LLM</th><th className="px-4 py-3">Uses Models</th><th className="px-4 py-3">Safe Auto-run</th><th className="px-4 py-3">Asset Classes</th><th className="px-4 py-3">Timeframes</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {agents.map((agent) => (
            <tr key={agent.agent_key} className="hover:bg-emerald-950/20">
              <td className="px-4 py-3"><p className="font-bold text-white">{agent.agent_name}</p><p className="mt-1 max-w-md text-xs text-slate-400">{agent.purpose}</p></td>
              <td className="px-4 py-3 text-slate-300">{agent.category.replace(/_/g, " ")}</td>
              <td className="px-4 py-3"><StatusBadge status={agent.status} /></td>
              <td className="px-4 py-3"><StatusBadge status={boolText(agent.uses_llm)} /></td>
              <td className="px-4 py-3"><StatusBadge status={boolText(agent.uses_models)} /></td>
              <td className="px-4 py-3"><StatusBadge status={agent.safe_for_auto_run ? "safe" : "manual"} /></td>
              <td className="px-4 py-3 text-slate-300">{agent.supported_asset_classes.join(", ")}</td>
              <td className="px-4 py-3 text-slate-300">{agent.supported_timeframes.join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StrategyRegistryTable({ strategies }: { strategies: StrategyConfig[] }) {
  if (!strategies.length) return <EmptyState label="strategy registry entries" />;
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
      <table className="w-full min-w-[1280px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr><th className="px-4 py-3">Strategy</th><th className="px-4 py-3">Asset</th><th className="px-4 py-3">Timeframe</th><th className="px-4 py-3">Required Agents</th><th className="px-4 py-3">Required Models</th><th className="px-4 py-3">Paper</th><th className="px-4 py-3">Approval</th><th className="px-4 py-3">Live</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {strategies.map((strategy) => (
            <tr key={strategy.strategy_key} className="hover:bg-emerald-950/20">
              <td className="px-4 py-3"><p className="font-bold text-white">{strategy.display_name}</p><p className="mt-1 max-w-md text-xs text-slate-400">{strategy.description}</p></td>
              <td className="px-4 py-3 text-slate-300">{strategy.asset_class}</td>
              <td className="px-4 py-3 text-slate-300">{strategy.timeframe}</td>
              <td className="max-w-md px-4 py-3 text-slate-300">{strategy.required_agents.join(", ")}</td>
              <td className="px-4 py-3 text-slate-300">{strategy.required_models.join(", ")}</td>
              <td className="px-4 py-3"><StatusBadge status={strategy.paper_trading_supported ? "supported" : "disabled"} /></td>
              <td className="px-4 py-3"><StatusBadge status={strategy.requires_human_approval ? "required" : "not_required"} /></td>
              <td className="px-4 py-3"><StatusBadge status={strategy.live_trading_supported ? "enabled" : "disabled"} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AutoRunPanel({ state, onToggle, loading, error }: { state: AutoRunControlState | null; onToggle: () => void; loading: boolean; error: string | null }) {
  if (error) return <ErrorState error={error} />;
  if (!state) return <LoadingState label="auto-run status" />;
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
        <MetricCard label="Auto-run" value={state.auto_run_enabled ? "On" : "Off"} accent />
        <MetricCard label="Live Trading" value={state.live_trading_enabled ? "Enabled" : "Disabled"} />
        <MetricCard label="Paper Trading" value={state.paper_trading_enabled ? "Enabled" : "Disabled"} />
        <MetricCard label="Human Approval" value={state.require_human_approval ? "Required" : "Not required"} />
        <MetricCard label="Max Agent Runs" value={state.max_daily_agent_runs} />
        <MetricCard label="Max LLM Cost" value={money(state.max_daily_llm_cost)} />
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <button onClick={onToggle} disabled={loading} className="rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-300 disabled:opacity-60">
          {loading ? "Updating..." : state.auto_run_enabled ? "Turn Auto-run Off" : "Turn Auto-run On"}
        </button>
        <span className="text-sm text-slate-300">Live trading is read-only here and remains disabled unless the backend explicitly allows it. Paper/research workflows still require human approval.</span>
      </div>
    </div>
  );
}

function EdgeRadarPanel() {
  const [symbols, setSymbols] = useState("AMD,NVDA,AAPL,MSFT,BTC-USD");
  const [horizon, setHorizon] = useState("swing");
  const [dataSource, setDataSource] = useState("auto");
  const [accountSize, setAccountSize] = useState(5000);
  const [maxRisk, setMaxRisk] = useState(0.01);
  const [strategy, setStrategy] = useState("");
  const [result, setResult] = useState<EdgeRadarRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await api.runEdgeRadar({
        symbols: symbols.split(",").map((symbol) => symbol.trim()).filter(Boolean),
        horizon,
        data_source: dataSource,
        account_size: accountSize,
        max_risk_per_trade: maxRisk,
        strategy_preference: strategy || null,
      });
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Edge Radar run failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Panel title="Edge Radar Test Panel">
      <p className="mb-4 text-sm text-slate-300">Research and paper-only orchestration. Live trading stays disabled and suggested paper actions require approval.</p>
      <form onSubmit={submit} className="grid grid-cols-1 gap-3 lg:grid-cols-6">
        <label className="lg:col-span-2">
          <span className="text-xs uppercase tracking-wide text-slate-400">Symbols</span>
          <input value={symbols} onChange={(event) => setSymbols(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
        </label>
        <label>
          <span className="text-xs uppercase tracking-wide text-slate-400">Horizon</span>
          <select value={horizon} onChange={(event) => setHorizon(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white">
            {["intraday", "day_trade", "swing", "one_month"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          <span className="text-xs uppercase tracking-wide text-slate-400">Data Source</span>
          <select value={dataSource} onChange={(event) => setDataSource(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white">
            {["auto", "yfinance", "mock"].map((value) => <option key={value}>{value}</option>)}
          </select>
        </label>
        <label>
          <span className="text-xs uppercase tracking-wide text-slate-400">Account Size</span>
          <input type="number" value={accountSize} onChange={(event) => setAccountSize(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
        </label>
        <label>
          <span className="text-xs uppercase tracking-wide text-slate-400">Risk / Trade</span>
          <input type="number" step="0.01" value={maxRisk} onChange={(event) => setMaxRisk(Number(event.target.value))} className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white" />
        </label>
        <label className="lg:col-span-5">
          <span className="text-xs uppercase tracking-wide text-slate-400">Strategy Preference</span>
          <input value={strategy} onChange={(event) => setStrategy(event.target.value)} placeholder="Optional" className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-white placeholder:text-slate-500" />
        </label>
        <button disabled={loading} className="self-end rounded-lg border border-emerald-500 bg-emerald-500/10 px-4 py-2 text-sm font-bold text-emerald-300 disabled:opacity-60">
          {loading ? "Running..." : "Run Radar"}
        </button>
      </form>
      {error && <div className="mt-4"><ErrorState error={error} /></div>}
      {!result && !error && <div className="mt-4"><EmptyState label="Edge Radar run results" /></div>}
      {result && (
        <div className="mt-4 space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-6">
            <MetricCard label="Status" value={result.status} accent />
            <MetricCard label="Signals" value={result.detected_signals.length} />
            <MetricCard label="Approval" value={result.approval_required ? "Required" : "None"} />
            <MetricCard label="Paper Allowed" value={result.paper_trade_allowed ? "Yes" : "No"} />
            <MetricCard label="Live Allowed" value={result.live_trading_allowed ? "Yes" : "No"} />
            <MetricCard label="Cost" value={money(Number(result.cost_estimate.estimated_cost ?? 0))} />
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
            <div className="flex flex-wrap items-center gap-3">
              <SourceBadge source={result.data_source} />
              <StatusBadge status={asText(result.portfolio_manager_decision.action, "watch_only")} />
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">{result.message}</p>
          </div>
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
            <table className="w-full min-w-[920px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-emerald-600">
                <tr><th className="px-4 py-3">Agent</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Confidence</th><th className="px-4 py-3">Data Source</th><th className="px-4 py-3">Summary</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {result.agent_trace.map((event) => (
                  <tr key={event.agent_name}>
                    <td className="px-4 py-3 font-bold text-white">{event.agent_name}</td>
                    <td className="px-4 py-3"><StatusBadge status={event.status} /></td>
                    <td className="px-4 py-3 text-slate-300">{percent(event.confidence)}</td>
                    <td className="px-4 py-3"><SourceBadge source={event.data_source} /></td>
                    <td className="max-w-xl px-4 py-3 text-slate-400">{event.output_summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Panel>
  );
}

export function AiOpsOverviewPage() {
  const [summary, setSummary] = useState<AiOpsSummaryResponse | null>(null);
  const [workflows, setWorkflows] = useState<AiOpsWorkflowListResponse | null>(null);
  const [agents, setAgents] = useState<AiOpsAgentStatusResponse | null>(null);
  const [llm, setLlm] = useState<AiOpsLlmUsageResponse | null>(null);
  const [scheduler, setScheduler] = useState<AiOpsSchedulerJobsResponse | null>(null);
  const [coreRegistry, setCoreRegistry] = useState<CoreAgentRegistryItem[]>([]);
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [autoRun, setAutoRun] = useState<AutoRunControlState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoRunError, setAutoRunError] = useState<string | null>(null);
  const [autoRunLoading, setAutoRunLoading] = useState(false);
  const loading = !summary && !error;

  useEffect(() => {
    Promise.all([api.getAiOpsSummary(), api.getAiOpsWorkflows(), api.getAiOpsAgentStatus(), api.getAiOpsLlmUsage(), api.getAiOpsSchedulerJobs(), api.getAgentRegistry(), api.getStrategies(), api.getAutoRunStatus()])
      .then(([summaryData, workflowData, agentData, llmData, schedulerData, registryData, strategyData, autoRunData]) => {
        setSummary(summaryData);
        setWorkflows(workflowData);
        setAgents(agentData);
        setLlm(llmData);
        setScheduler(schedulerData);
        setCoreRegistry(registryData);
        setStrategies(strategyData);
        setAutoRun(autoRunData);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "AI Ops summary failed"));
  }, []);

  async function toggleAutoRun() {
    if (!autoRun) return;
    setAutoRunLoading(true);
    setAutoRunError(null);
    try {
      const response = await api.updateAutoRunStatus({ auto_run_enabled: !autoRun.auto_run_enabled });
      setAutoRun(response);
    } catch (err) {
      setAutoRunError(err instanceof Error ? err.message : "Auto-run update failed");
    } finally {
      setAutoRunLoading(false);
    }
  }

  const agentList = allAgents(agents);
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="Agent Ops Center" description="Operational visibility for EdgeSenseAI agent orchestration. Placeholder and demo values are labeled, and live trading remains disabled." />
      {error && <ErrorState error={error} />}
      {loading ? <LoadingState label="Agent Ops Center" /> : summary ? (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 xl:grid-cols-8">
            <MetricCard label="Active Workflows" value={workflowRows(workflows).length} accent />
            <MetricCard label="LLM Cost Today" value={money(llm?.cost_today ?? llm?.total_estimated_cost)} />
            <MetricCard label="Workflow Success Rate" value="N/A" />
            <MetricCard label="Pending Approvals" value="0" />
            <MetricCard label="Scheduler Status" value={scheduler?.status ?? "unknown"} />
            <MetricCard label="Tokens Today" value={llm?.tokens_today ?? llm?.total_estimated_tokens ?? 0} />
            <MetricCard label="Avg Latency" value="N/A" />
            <MetricCard label="Failed Runs" value={scheduler?.failed_jobs_today ?? 0} />
          </div>
          <Panel title="Orchestration Status"><OrchestrationStatus summary={summary} /></Panel>
          <Panel title="Recent Workflow Runs"><WorkflowsTable workflows={workflowRows(workflows)} /></Panel>
          <Panel title="Agent Health"><AgentHealthTable agents={agentList} /></Panel>
          <Panel title="Core Agent Registry"><CoreAgentRegistryTable agents={coreRegistry} /></Panel>
          <Panel title="Strategy Registry Summary"><StrategyRegistryTable strategies={strategies} /></Panel>
          <Panel title="Auto-run Status"><AutoRunPanel state={autoRun} onToggle={toggleAutoRun} loading={autoRunLoading} error={autoRunError} /></Panel>
          <Panel title="Safety Guardrails"><GuardrailGrid summary={summary} llm={llm} /></Panel>
          <EdgeRadarPanel />
        </div>
      ) : <EmptyState label="Agent Ops summary" />}
    </PageShell>
  );
}

export function AiOpsWorkflowsPage() {
  const [data, setData] = useState<AiOpsWorkflowListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.getAiOpsWorkflows().then(setData).catch((err) => setError(err.message)); }, []);
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="Workflows" description="Configured agent workflows and orchestration entrypoints." />
      {error ? <ErrorState error={error} /> : !data ? <LoadingState label="workflows" /> : workflowRows(data).length ? <Panel title="Configured Workflows"><WorkflowsTable workflows={workflowRows(data)} /></Panel> : <EmptyState label="workflows" />}
    </PageShell>
  );
}

export function AiOpsAgentsPage() {
  const [data, setData] = useState<AiOpsAgentStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.getAiOpsAgentStatus().then(setData).catch((err) => setError(err.message)); }, []);
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="Agents" description="Agent scorecards and newly configured orchestration foundation agents." />
      {error ? <ErrorState error={error} /> : !data ? <LoadingState label="agents" /> : allAgents(data).length ? <Panel title="Agent Status"><AgentHealthTable agents={allAgents(data)} /></Panel> : <EmptyState label="agent records" />}
    </PageShell>
  );
}

export function AiOpsLlmUsagePage() {
  const [data, setData] = useState<AiOpsLlmUsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.getAiOpsLlmUsage().then(setData).catch((err) => setError(err.message)); }, []);
  const rows = data?.usage ?? data?.models ?? [];
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="LLM Usage" description="LiteLLM gateway visibility. Placeholder records are labeled until real usage logs are wired." />
      {error ? <ErrorState error={error} /> : !data ? <LoadingState label="LLM usage" /> : (
        <div className="space-y-4">
          <div className="flex flex-wrap gap-3"><StatusBadge status={data.status} /><SourceBadge source={data.data_source} /></div>
          {data.data_source === "placeholder" && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">Placeholder notice: LiteLLM is installed, but real usage logs are not wired yet.</div>}
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MetricCard label="Gateway Status" value={data.status} accent />
            <MetricCard label="Cost Today" value={money(data.cost_today ?? data.total_estimated_cost)} />
            <MetricCard label="Cost Limit" value={money(data.cost_limit ?? 25)} />
            <MetricCard label="Tokens Today" value={data.tokens_today ?? data.total_estimated_tokens ?? 0} />
          </div>
          <Panel title="Provider And Model Mix">
            {!rows.length ? <EmptyState label="LLM usage rows" /> : (
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
                <table className="w-full min-w-[920px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-emerald-600"><tr><th className="px-4 py-3">Provider</th><th className="px-4 py-3">Model</th><th className="px-4 py-3">Agent</th><th className="px-4 py-3">Workflow</th><th className="px-4 py-3">Tokens</th><th className="px-4 py-3">Cost</th><th className="px-4 py-3">Status</th></tr></thead>
                  <tbody className="divide-y divide-slate-800">{rows.map((row, index) => <tr key={index}><td className="px-4 py-3 text-slate-300">{row.provider || data.provider || "litellm"}</td><td className="px-4 py-3 text-white">{row.model || row.model_name || "N/A"}</td><td className="px-4 py-3 text-slate-300">{row.agent || "N/A"}</td><td className="px-4 py-3 text-slate-300">{row.workflow || "N/A"}</td><td className="px-4 py-3 text-slate-300">{row.tokens ?? row.estimated_tokens ?? 0}</td><td className="px-4 py-3 text-slate-300">{money(row.cost ?? row.estimated_cost)}</td><td className="px-4 py-3"><StatusBadge status={row.status || data.status} /></td></tr>)}</tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      )}
    </PageShell>
  );
}

export function AiOpsSchedulerPage() {
  const [data, setData] = useState<AiOpsSchedulerJobsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.getAiOpsSchedulerJobs().then(setData).catch((err) => setError(err.message)); }, []);
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="Scheduler" description="APScheduler foundation status and configured job metadata." />
      {error ? <ErrorState error={error} /> : !data ? <LoadingState label="scheduler jobs" /> : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
            <MetricCard label="Scheduler Status" value={data.status} accent />
            <MetricCard label="Configured Jobs" value={data.jobs_configured ?? data.jobs.length} />
            <MetricCard label="Running Jobs" value={data.running_jobs ?? 0} />
            <MetricCard label="Failed Today" value={data.failed_jobs_today ?? 0} />
            <MetricCard label="Next Run" value={data.jobs.find((job) => job.next_run || job.next_run_at)?.next_run ?? "Not started"} />
          </div>
          <Panel title="Jobs">
            {!data.jobs.length ? <EmptyState label="scheduler jobs" /> : (
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
                <table className="w-full min-w-[1040px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-emerald-600"><tr><th className="px-4 py-3">Job ID</th><th className="px-4 py-3">Job Name</th><th className="px-4 py-3">Schedule</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Last Run</th><th className="px-4 py-3">Next Run</th><th className="px-4 py-3">Description</th></tr></thead>
                  <tbody className="divide-y divide-slate-800">{data.jobs.map((job) => <tr key={job.id}><td className="px-4 py-3 font-mono text-xs text-white">{job.id}</td><td className="px-4 py-3 text-slate-300">{job.name || job.id}</td><td className="px-4 py-3 text-slate-300">{job.schedule || job.trigger || "N/A"}</td><td className="px-4 py-3"><StatusBadge status={job.status} /></td><td className="px-4 py-3 text-slate-300">{formatDate(job.last_run_at || job.last_run)}</td><td className="px-4 py-3 text-slate-300">{formatDate(job.next_run_at || job.next_run)}</td><td className="max-w-lg px-4 py-3 text-slate-400">{job.description || `Runs ${job.workflow || "configured workflow"} when enabled.`}</td></tr>)}</tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      )}
    </PageShell>
  );
}

export function AiOpsSafetyPage() {
  const [summary, setSummary] = useState<AiOpsSummaryResponse | null>(null);
  const [llm, setLlm] = useState<AiOpsLlmUsageResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { Promise.all([api.getAiOpsSummary(), api.getAiOpsLlmUsage()]).then(([s, l]) => { setSummary(s); setLlm(l); }).catch((err) => setError(err.message)); }, []);
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="Safety" description="Agent guardrails for research and paper-only workflows." />
      {error ? <ErrorState error={error} /> : !summary ? <LoadingState label="safety guardrails" /> : (
        <div className="space-y-4">
          <Panel title="Guardrails"><GuardrailGrid summary={summary} llm={llm} /></Panel>
          <Panel title="Approval Queue"><EmptyState label="approval queue endpoint" /><p className="mt-3 text-sm text-slate-400">No real approval queue endpoint exists yet. Paper candidates from Edge Radar still require human approval before any paper action.</p></Panel>
        </div>
      )}
    </PageShell>
  );
}

export function AiOpsAuditPage() {
  const [data, setData] = useState<AiOpsAuditEventsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { api.getAiOpsAuditEvents().then(setData).catch((err) => setError(err.message)); }, []);
  return (
    <PageShell>
      <PageHeader eyebrow="agent operations" title="Audit" description="Audit events for orchestration foundation activity." />
      {error ? <ErrorState error={error} /> : !data ? <LoadingState label="audit events" /> : !data.events.length ? <EmptyState label="audit events" /> : (
        <Panel title="Audit Events">
          <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
            <table className="w-full min-w-[1040px] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-emerald-600"><tr><th className="px-4 py-3">Time</th><th className="px-4 py-3">Event Type</th><th className="px-4 py-3">Actor</th><th className="px-4 py-3">Object</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Details</th><th className="px-4 py-3">Data Source</th></tr></thead>
              <tbody className="divide-y divide-slate-800">{data.events.map((event: AiOpsAuditEvent, index) => <tr key={event.id || index}><td className="px-4 py-3 text-slate-300">{formatDate(event.created_at || event.time)}</td><td className="px-4 py-3 text-white">{event.event_type || "event"}</td><td className="px-4 py-3 text-slate-300">{event.actor || "system"}</td><td className="px-4 py-3 text-slate-300">{event.object || event.id || "orchestration"}</td><td className="px-4 py-3"><StatusBadge status={event.status || event.severity} /></td><td className="max-w-lg px-4 py-3 text-slate-400">{event.details || event.summary || "No details."}</td><td className="px-4 py-3"><SourceBadge source={event.data_source || data.data_source} /></td></tr>)}</tbody>
            </table>
          </div>
        </Panel>
      )}
    </PageShell>
  );
}
