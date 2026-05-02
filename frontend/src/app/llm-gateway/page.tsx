"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { MetricCard, PageHeader } from "@/components/Cards";
import {
  api,
  type AgentModelMapping,
  type LlmCostEstimateResponse,
  type LlmCostSummary,
  type LlmGatewayStatusResponse,
  type LlmGatewayTestCallResponse,
  type LlmModelConfig,
  type LlmProviderStatus,
  type LlmRoutingRule,
  type LlmUsageRecord,
} from "@/lib/api";

function Badge({ value }: { value?: string | boolean | null }) {
  const text = value === true ? "enabled" : value === false ? "disabled" : value || "unknown";
  const normalized = String(text).toLowerCase();
  const tone =
    normalized.includes("configured") || normalized.includes("available") || normalized === "enabled" || normalized === "ok"
      ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
      : normalized.includes("placeholder") || normalized.includes("dry") || normalized.includes("not_configured")
        ? "border-amber-500 bg-amber-500/10 text-amber-300"
        : normalized.includes("error") || normalized.includes("exceeded")
          ? "border-rose-500 bg-rose-500/10 text-rose-300"
          : "border-slate-600 bg-slate-800 text-slate-300";
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${tone}`}>{String(text).replace(/_/g, " ")}</span>;
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
      <h2 className="mb-3 text-lg font-semibold text-emerald-500">{title}</h2>
      {children}
    </section>
  );
}

function EmptyState({ label }: { label: string }) {
  return <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-8 text-center text-sm text-slate-400">No {label} available yet.</div>;
}

function ErrorState({ error }: { error: string }) {
  return <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>;
}

function money(value?: number | null) {
  return `$${(value ?? 0).toLocaleString(undefined, { maximumFractionDigits: 6 })}`;
}

function formatDate(value?: string | null) {
  if (!value) return "N/A";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

function Breakdown({ title, rows }: { title: string; rows: Record<string, number> }) {
  const entries = Object.entries(rows);
  if (!entries.length) return <EmptyState label={`${title.toLowerCase()} cost rows`} />;
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <div className="mt-3 space-y-2">
        {entries.map(([key, value]) => (
          <div key={key} className="flex items-center justify-between gap-4 text-sm">
            <span className="truncate text-slate-300">{key}</span>
            <span className="font-bold text-emerald-300">{money(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function LlmGatewayPage() {
  const [status, setStatus] = useState<LlmGatewayStatusResponse | null>(null);
  const [providers, setProviders] = useState<LlmProviderStatus[]>([]);
  const [models, setModels] = useState<LlmModelConfig[]>([]);
  const [rules, setRules] = useState<LlmRoutingRule[]>([]);
  const [usage, setUsage] = useState<LlmUsageRecord[]>([]);
  const [costs, setCosts] = useState<LlmCostSummary | null>(null);
  const [agentMap, setAgentMap] = useState<AgentModelMapping[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [estimateModel, setEstimateModel] = useState("gpt-4o-mini");
  const [promptTokens, setPromptTokens] = useState(1000);
  const [completionTokens, setCompletionTokens] = useState(500);
  const [estimate, setEstimate] = useState<LlmCostEstimateResponse | null>(null);
  const [estimateLoading, setEstimateLoading] = useState(false);
  const [testProvider, setTestProvider] = useState("local");
  const [testModel, setTestModel] = useState("local-placeholder");
  const [testPrompt, setTestPrompt] = useState("Summarize the LLM Gateway routing state.");
  const [allowPaidCall, setAllowPaidCall] = useState(false);
  const [testResult, setTestResult] = useState<LlmGatewayTestCallResponse | null>(null);
  const [testLoading, setTestLoading] = useState(false);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [statusData, providerData, modelData, ruleData, usageData, costData, mapData] = await Promise.all([
        api.getLlmGatewayStatus(),
        api.getLlmGatewayProviders(),
        api.getLlmGatewayModels(),
        api.getLlmGatewayRoutingRules(),
        api.getLlmGatewayUsage(),
        api.getLlmGatewayCosts(),
        api.getLlmGatewayAgentModelMap(),
      ]);
      setStatus(statusData);
      setProviders(providerData);
      setModels(modelData);
      setRules(ruleData);
      setUsage(usageData);
      setCosts(costData);
      setAgentMap(mapData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "LLM Gateway failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const configuredProviders = useMemo(() => providers.filter((provider) => provider.configured && provider.provider !== "local").length, [providers]);

  async function submitEstimate(event: FormEvent) {
    event.preventDefault();
    setEstimateLoading(true);
    try {
      setEstimate(await api.estimateLlmCost({ model: estimateModel, prompt_tokens: promptTokens, completion_tokens: completionTokens }));
    } finally {
      setEstimateLoading(false);
    }
  }

  async function submitTest(event: FormEvent) {
    event.preventDefault();
    setTestLoading(true);
    try {
      const response = await api.testLlmGatewayCall({ provider: testProvider, model: testModel, prompt: testPrompt, allow_paid_call: allowPaidCall });
      setTestResult(response);
      await refresh();
    } finally {
      setTestLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="llm control plane"
          title="LLM Gateway"
          description="LiteLLM routing, model provider status, token usage, cost control, budgets, and agent-to-model mapping."
        />

        {error && <div className="mb-4"><ErrorState error={error} /></div>}
        {loading ? (
          <div className="rounded-xl border border-slate-700 bg-slate-950 px-4 py-8 text-center text-sm text-slate-300">Loading LLM Gateway...</div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4 xl:grid-cols-8">
              <MetricCard label="Gateway Status" value={status?.status ?? "unknown"} accent />
              <MetricCard label="Configured Providers" value={configuredProviders} />
              <MetricCard label="LLM Cost Today" value={money(costs?.cost_today)} />
              <MetricCard label="Budget Remaining" value={money(costs?.budget_remaining ?? status?.budget_remaining)} />
              <MetricCard label="Tokens Today" value={costs?.tokens_today ?? 0} />
              <MetricCard label="Calls Today" value={costs?.calls_today ?? 0} />
              <MetricCard label="Most Used Model" value={costs?.most_used_model ?? "none"} />
              <MetricCard label="Most Expensive Agent" value={costs?.most_expensive_agent ?? "none"} />
            </div>

            <Panel title="Provider Status">
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
                {providers.map((provider) => (
                  <article key={provider.provider} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <h3 className="text-xl font-black capitalize text-white">{provider.provider.replace(/_/g, " ")}</h3>
                      <Badge value={provider.status} />
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-slate-300">{provider.message}</p>
                    <p className="mt-3 text-xs uppercase tracking-wide text-slate-500">Env vars</p>
                    <p className="mt-1 text-sm text-slate-400">{provider.required_env_vars.length ? provider.required_env_vars.join(", ") : "none required"}</p>
                  </article>
                ))}
              </div>
            </Panel>

            <Panel title="Routing Rules">
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
                <table className="w-full min-w-[1050px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-emerald-600">
                    <tr><th className="px-4 py-3">Task Type</th><th className="px-4 py-3">Preferred Provider</th><th className="px-4 py-3">Preferred Model</th><th className="px-4 py-3">Fallback Model</th><th className="px-4 py-3">Max Cost / Call</th><th className="px-4 py-3">Max Tokens</th><th className="px-4 py-3">Enabled</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {rules.map((rule) => (
                      <tr key={rule.task_type}><td className="px-4 py-3 font-bold text-white">{rule.task_type}</td><td className="px-4 py-3 text-slate-300">{rule.preferred_provider}</td><td className="px-4 py-3 text-slate-300">{rule.preferred_model}</td><td className="px-4 py-3 text-slate-300">{rule.fallback_model}</td><td className="px-4 py-3 text-slate-300">{money(rule.max_cost_per_call)}</td><td className="px-4 py-3 text-slate-300">{rule.max_tokens}</td><td className="px-4 py-3"><Badge value={rule.enabled} /></td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Agent Model Map">
              <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
                <table className="w-full min-w-[1050px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-emerald-600">
                    <tr><th className="px-4 py-3">Agent</th><th className="px-4 py-3">Default Model</th><th className="px-4 py-3">Fallback Model</th><th className="px-4 py-3">Calls Today</th><th className="px-4 py-3">Cost Today</th><th className="px-4 py-3">Max Daily Cost</th><th className="px-4 py-3">Status</th></tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {agentMap.map((row) => (
                      <tr key={row.agent_name}><td className="px-4 py-3 font-bold text-white">{row.agent_name}</td><td className="px-4 py-3 text-slate-300">{row.default_model}</td><td className="px-4 py-3 text-slate-300">{row.fallback_model}</td><td className="px-4 py-3 text-slate-300">{row.calls_today}</td><td className="px-4 py-3 text-slate-300">{money(row.current_cost_today)}</td><td className="px-4 py-3 text-slate-300">{money(row.max_daily_cost)}</td><td className="px-4 py-3"><Badge value={row.status} /></td></tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>

            <Panel title="Cost Breakdown">
              <div className="mb-3 flex flex-wrap gap-2">
                <Badge value={costs?.data_source} />
                <Badge value={costs?.pricing_source} />
              </div>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
                <Breakdown title="Cost By Provider" rows={costs?.cost_by_provider ?? {}} />
                <Breakdown title="Cost By Model" rows={costs?.cost_by_model ?? {}} />
                <Breakdown title="Cost By Agent" rows={costs?.cost_by_agent ?? {}} />
                <Breakdown title="Cost By Workflow" rows={costs?.cost_by_workflow ?? {}} />
              </div>
            </Panel>

            <Panel title="Recent LLM Calls">
              {!usage.length ? <EmptyState label="LLM calls" /> : (
                <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-900">
                  <table className="w-full min-w-[1120px] text-left text-sm">
                    <thead className="text-xs uppercase tracking-wide text-emerald-600">
                      <tr><th className="px-4 py-3">Time</th><th className="px-4 py-3">Provider</th><th className="px-4 py-3">Model</th><th className="px-4 py-3">Agent</th><th className="px-4 py-3">Workflow</th><th className="px-4 py-3">Prompt Tokens</th><th className="px-4 py-3">Completion Tokens</th><th className="px-4 py-3">Estimated Cost</th><th className="px-4 py-3">Latency</th><th className="px-4 py-3">Status</th></tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                      {usage.map((row) => (
                        <tr key={row.id}><td className="px-4 py-3 text-slate-300">{formatDate(row.timestamp)}</td><td className="px-4 py-3 text-slate-300">{row.provider}</td><td className="px-4 py-3 text-white">{row.model}</td><td className="px-4 py-3 text-slate-300">{row.agent}</td><td className="px-4 py-3 text-slate-300">{row.workflow}</td><td className="px-4 py-3 text-slate-300">{row.prompt_tokens}</td><td className="px-4 py-3 text-slate-300">{row.completion_tokens}</td><td className="px-4 py-3 text-slate-300">{money(row.estimated_cost)}</td><td className="px-4 py-3 text-slate-300">{row.latency_ms ?? 0}ms</td><td className="px-4 py-3"><Badge value={row.status} /></td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Panel>

            <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              <Panel title="Cost Estimate">
                <form onSubmit={submitEstimate} className="grid grid-cols-1 gap-3 md:grid-cols-4">
                  <label className="md:col-span-2"><span className="text-sm font-semibold text-slate-300">Model</span><select value={estimateModel} onChange={(event) => setEstimateModel(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white">{models.map((model) => <option key={model.model_name} value={model.model_name}>{model.model_name}</option>)}</select></label>
                  <label><span className="text-sm font-semibold text-slate-300">Prompt Tokens</span><input type="number" value={promptTokens} onChange={(event) => setPromptTokens(Number(event.target.value))} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" /></label>
                  <label><span className="text-sm font-semibold text-slate-300">Completion Tokens</span><input type="number" value={completionTokens} onChange={(event) => setCompletionTokens(Number(event.target.value))} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" /></label>
                  <button disabled={estimateLoading} className="rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-slate-950 disabled:opacity-60 md:col-span-4">{estimateLoading ? "Estimating..." : "Estimate Cost"}</button>
                </form>
                {estimate && <div className="mt-4 grid grid-cols-2 gap-4"><MetricCard label="Estimated Cost" value={money(estimate.estimated_cost)} accent /><MetricCard label="Pricing Source" value={estimate.pricing_source} /></div>}
              </Panel>

              <Panel title="Test Gateway">
                <form onSubmit={submitTest} className="grid grid-cols-1 gap-3 md:grid-cols-2">
                  <label><span className="text-sm font-semibold text-slate-300">Provider</span><input value={testProvider} onChange={(event) => setTestProvider(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" /></label>
                  <label><span className="text-sm font-semibold text-slate-300">Model</span><input value={testModel} onChange={(event) => setTestModel(event.target.value)} className="mt-2 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" /></label>
                  <label className="md:col-span-2"><span className="text-sm font-semibold text-slate-300">Prompt</span><textarea value={testPrompt} onChange={(event) => setTestPrompt(event.target.value)} className="mt-2 min-h-24 w-full rounded-lg border border-emerald-900 bg-slate-900 px-4 py-3 text-white" /></label>
                  <label className="flex items-center gap-3 text-sm text-slate-300"><input type="checkbox" checked={allowPaidCall} onChange={(event) => setAllowPaidCall(event.target.checked)} /> allow paid call</label>
                  <button disabled={testLoading} className="rounded-lg bg-emerald-600 px-5 py-3 text-sm font-bold text-slate-950 disabled:opacity-60">{testLoading ? "Testing..." : "Dry Run Test"}</button>
                </form>
                <p className="mt-3 text-sm text-slate-400">Default is dry-run and does not call a provider. Paid tests require explicit request and server-side enablement.</p>
                {testResult && <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900 p-4"><div className="flex flex-wrap gap-2"><Badge value={testResult.status} /><Badge value={testResult.dry_run ? "dry_run" : "paid_call"} /></div><p className="mt-3 text-sm text-slate-300">{testResult.response_text}</p>{testResult.warnings.map((warning) => <p key={warning} className="mt-2 text-sm text-amber-300">{warning}</p>)}</div>}
              </Panel>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
