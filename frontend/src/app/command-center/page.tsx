"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  getAgentRuntimeAgents,
  getAgentRuntimeLatest,
  runWorkflowOrchestrator,
  type AgentRuntimeAgentDescriptor,
  type AgentRunResultRecord,
  type CommandCenterResponse,
  type OrchestratorRunRecord,
} from "@/lib/api";
import { EdgeSignalGrid, MetricCard, RecommendationTable } from "@/components/Cards";
import { LiveWatchlistPanel } from "@/components/LiveWatchlistPanel";
import { Gauge, Users, TrendingUp, AlertTriangle, Play, Clock } from "lucide-react";

const cardShell = "rounded-2xl border border-emerald-400/15 bg-black/35 p-5 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur";

function money(value: number) {
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function percent(value: number) {
  return `${Math.round(value * 100)}%`;
}

export default function CommandCenterPage() {
  return <CommandCenterPanel />;
}

function extractSessionNotes(value: unknown): string | null {
  const visited = new Set<unknown>();

  function walk(v: unknown): string | null {
    if (v == null) return null;
    if (typeof v === "string") return null;
    if (typeof v !== "object") return null;
    if (visited.has(v)) return null;
    visited.add(v);

    if (Array.isArray(v)) {
      for (const item of v) {
        const found = walk(item);
        if (found) return found;
      }
      return null;
    }

    const obj = v as Record<string, unknown>;
    const direct = obj.session_notes ?? obj.sessionNotes;
    if (typeof direct === "string" && direct.trim()) return direct;
    if (Array.isArray(direct) && direct.length) return direct.map((x) => String(x)).join("; ");

    for (const key of Object.keys(obj)) {
      const found = walk(obj[key]);
      if (found) return found;
    }
    return null;
  }

  return walk(value);
}

function AgentRuntimeRunCard() {
  const [agents, setAgents] = useState<AgentRuntimeAgentDescriptor[]>([]);
  const [latestRun, setLatestRun] = useState<AgentRunResultRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [latest, ag] = await Promise.all([getAgentRuntimeLatest(), getAgentRuntimeAgents()]);
      const agentList = ag.agents ?? [];
      setAgents(agentList);

      const byKey = (latest as any)?.latest_agent_runs_by_key as Record<string, AgentRunResultRecord | null> | undefined;
      const first = agentList.find((a) => byKey?.[a.agent_key])?.agent_key;
      const chosen = (first ? byKey?.[first] : null) ?? null;
      setLatestRun(chosen);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agent runtime");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  const descriptor = latestRun ? agents.find((a) => a.agent_key === latestRun.agent_key) : null;
  const stageName = descriptor?.display_name ?? "—";
  const status = latestRun?.status ?? (loading ? "loading" : "—");
  const sessionNotes = latestRun ? extractSessionNotes(latestRun.decision) : null;
  const nextAction = latestRun?.next_action ?? "—";

  return (
    <section className={cardShell}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-300/80">Agent Runtime</div>
          <h2 className="mt-1 text-2xl font-black text-white">Latest agent run</h2>
          <p className="mt-2 max-w-4xl text-sm text-slate-400">
            Pulled from <code className="text-emerald-200/80">/api/agent-runtime/latest</code>. Shows stage name, agent key, status, session notes, and next action.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={load}
            className="rounded-xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-2 text-sm font-semibold text-emerald-200 hover:bg-emerald-500/15"
          >
            Refresh
          </button>
          <Link
            href="/agent-runtime"
            className="rounded-xl border border-white/10 bg-white/[0.04] px-4 py-2 text-sm font-semibold text-slate-200 hover:bg-white/[0.06]"
          >
            Open Agent Runtime →
          </Link>
        </div>
      </div>

      {error ? (
        <div className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>
      ) : null}

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-5">
        {[
          ["stage_name", stageName],
          ["agent_key", latestRun?.agent_key ?? "—"],
          ["status", status],
          ["session_notes", sessionNotes ?? "—"],
          ["next_action", nextAction],
        ].map(([k, v]) => (
          <div key={k} className="rounded-xl border border-emerald-400/15 bg-[#05080d] p-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{k}</div>
            <div className={`mt-1 text-sm font-semibold ${k === "agent_key" ? "font-mono text-emerald-200/90" : "text-slate-100"}`}>
              {loading && k !== "agent_key" && k !== "stage_name" ? "Loading…" : String(v)}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function CommandCenterPanel() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [runNotice, setRunNotice] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [tab, setTab] = useState<"candidates" | "live_watch" | "agents">("candidates");

  const loadData = async () => {
    try {
      const response = await api.getCommandCenter();
      setData(response);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunWorkflow = async () => {
    setIsRunning(true);
    setError(null);
    setRunNotice(null);
    const controller = new AbortController();
    const timeoutMs = 180_000;
    const timer = window.setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await api.runCommandCenter(controller.signal);
      setData(response);
      setRunNotice({
        kind: "success",
        text: response.cost_usage_message?.trim() || "Workflow finished. Dashboard updated.",
      });
    } catch (err) {
      const aborted = err instanceof Error && err.name === "AbortError";
      const msg = aborted
        ? `Request timed out after ${timeoutMs / 1000}s (universe + ranking can be slow). Check backend logs or try again.`
        : err instanceof Error
          ? err.message
          : "Failed to run workflow";
      setError(msg);
      setRunNotice({ kind: "error", text: msg });
    } finally {
      window.clearTimeout(timer);
      setIsRunning(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-[1600px] p-4 lg:p-8">
        <header className="mb-6">
          <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
            <Gauge className="h-4 w-4" />
            decision intelligence cockpit
          </div>
          <h1 className="text-3xl font-black tracking-[-0.03em] text-white lg:text-4xl">Command Center</h1>
          <p className="mt-2 max-w-6xl text-sm leading-relaxed text-slate-400">
            Source-backed dashboard. No hardcoded trade numbers are shown as recommendations. If real source data is unavailable, the platform shows no-action status instead of fake buy/target/stop data.
          </p>

          <div className="mt-5 flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {[
              ["candidates", "Candidates"],
              ["live_watch", "Live Watch"],
              ["agents", "Agents"],
            ].map(([key, label]) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key as typeof tab)}
                className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
                  tab === key
                    ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                    : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </header>

        {error && (
          <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
            {error}
          </div>
        )}

        <section className={`${cardShell} mb-4`}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-400">Decision workflow</p>
              <p className="mt-1 text-sm text-slate-400">
                Runs universe selection on active candidates, then ranks them (<code className="text-emerald-200/80">POST /api/command-center/run</code>). Can take 30–120s — keep this tab open until it finishes.
              </p>
            </div>
            <button
              type="button"
              onClick={() => void handleRunWorkflow()}
              disabled={isRunning}
              className={`flex shrink-0 items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold uppercase transition-all ${
                isRunning
                  ? "cursor-wait border border-emerald-400/50 bg-emerald-500/20 text-emerald-200"
                  : "border border-emerald-400/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500 hover:text-slate-950"
              }`}
            >
              {isRunning ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                  Running…
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" />
                  Run decision workflow
                </>
              )}
            </button>
          </div>
          {runNotice ? (
            <div
              className={`mt-4 rounded-xl border px-3 py-2 text-sm ${
                runNotice.kind === "success"
                  ? "border-emerald-500/35 bg-emerald-500/10 text-emerald-100"
                  : "border-rose-500/35 bg-rose-500/10 text-rose-100"
              }`}
            >
              {runNotice.kind === "success" ? "Done — " : "Error — "}
              {runNotice.text}
            </div>
          ) : null}

          {data?.data_source_confirmation ? (
            <div className="mt-4 rounded-xl border border-cyan-500/25 bg-cyan-950/20 px-4 py-3 text-sm text-slate-200">
              <p className="text-xs font-semibold uppercase tracking-wide text-cyan-300/90">Data source confirmation</p>
              <p className="mt-2 text-xs text-slate-400">
                Effective runtime feeds used for this Command Center response (quotes/features resolve from{" "}
                <code className="text-cyan-200/90">MARKET_DATA_PROVIDER</code> + priority when source is{" "}
                <code className="text-cyan-200/90">auto</code>). Configure under Settings → Configuration editor.
              </p>
              <dl className="mt-3 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
                <div>
                  <dt className="text-slate-500">Market — primary</dt>
                  <dd className="font-mono text-cyan-100">{data.data_source_confirmation.market_data_primary}</dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-slate-500">Market — fallback chain</dt>
                  <dd className="font-mono text-slate-300">{data.data_source_confirmation.market_data_fallback_chain.join(", ") || "—"}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Universe selection</dt>
                  <dd className="font-mono text-slate-300">
                    source={data.data_source_confirmation.universe_selection_source} · horizon={data.data_source_confirmation.universe_selection_horizon}
                    {data.data_source_confirmation.universe_run_id ? (
                      <span className="block truncate text-[11px] text-slate-500">run {data.data_source_confirmation.universe_run_id}</span>
                    ) : null}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Decision workflow</dt>
                  <dd className="font-mono text-slate-300">
                    source={data.data_source_confirmation.decision_workflow_source} · horizon={data.data_source_confirmation.decision_workflow_horizon}
                    {data.data_source_confirmation.decision_workflow_run_id ? (
                      <span className="block truncate text-[11px] text-slate-500">run {data.data_source_confirmation.decision_workflow_run_id}</span>
                    ) : null}
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">News feeds</dt>
                  <dd className="text-slate-300">
                    {data.data_source_confirmation.news_enabled ? "enabled" : "disabled"} · primary {data.data_source_confirmation.news_primary}
                    <span className="block truncate font-mono text-[11px] text-slate-500">
                      fallbacks: {data.data_source_confirmation.news_fallback_chain.join(", ") || "—"}
                    </span>
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Account profile data</dt>
                  <dd className="font-mono text-slate-300">{data.data_source_confirmation.account_profile_data_source}</dd>
                </div>
                <div className="sm:col-span-2 lg:col-span-3">
                  <dt className="text-slate-500">Candidate seeds → symbols after universe</dt>
                  <dd className="font-mono text-[11px] leading-relaxed text-slate-400">
                    [{data.data_source_confirmation.candidate_seeds.join(", ") || "—"}] → [
                    {data.data_source_confirmation.symbols_after_universe.join(", ") || "—"}]
                  </dd>
                </div>
              </dl>
            </div>
          ) : null}
        </section>

        {tab === "live_watch" ? (
          <LiveWatchlistPanel showHeader={false} mode="watchlist" />
        ) : tab === "agents" ? (
          <div className="space-y-4">
            <AgentRuntimeRunCard />
            <LiveWatchlistPanel showHeader={false} mode="agents" />
          </div>
        ) : !data ? (
          <div className="py-8 text-center text-sm text-slate-400">Loading candidates...</div>
        ) : (
          <div className="space-y-4">
            {data.dashboard_mode === "no_symbols_selected" ? (
              <section className={cardShell}>
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-amber-400" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-400">No candidates selected</p>
                    <h2 className="mt-1 text-2xl font-black text-white">Add symbols before running ranking</h2>
                  </div>
                </div>
                <p className="mt-4 max-w-5xl text-sm leading-relaxed text-slate-300">
                  The Command Center requires a candidate universe to rank. Add symbols from Stocks search, Watchlist, Scanner, or the Candidate Universe page before running the decision workflow.
                </p>

                {/* Navigation Cards */}
                <div className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <Link
                    href="/stocks"
                    className="flex items-center gap-4 rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur transition-colors hover:border-emerald-400/40 hover:bg-white/[0.04]"
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                      <TrendingUp className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white">Stocks</h3>
                      <p className="text-sm text-slate-400">Search tickers and add them to candidate universe</p>
                    </div>
                  </Link>

                  <Link
                    href="/candidates"
                    className="flex items-center gap-4 rounded-xl border border-emerald-400/15 bg-black/35 p-4 backdrop-blur transition-colors hover:border-emerald-400/40 hover:bg-white/[0.04]"
                  >
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400">
                      <Users className="h-6 w-6" />
                    </div>
                    <div>
                      <h3 className="font-bold text-white">Candidate Universe</h3>
                      <p className="text-sm text-slate-400">Manage candidates and run decision workflow</p>
                    </div>
                  </Link>
                </div>
              </section>
            ) : data.dashboard_mode === "candidates_ready_not_ranked" ? (
              <section className={cardShell}>
                <div className="flex items-center gap-3">
                  <Clock className="h-8 w-8 text-cyan-400" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-cyan-400">Candidates Ready</p>
                    <h2 className="mt-1 text-2xl font-black text-white">Workflow not yet run</h2>
                  </div>
                </div>
                <p className="mt-4 max-w-5xl text-sm leading-relaxed text-slate-300">
                  {data.cost_usage_message}
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    onClick={handleRunWorkflow}
                    disabled={isRunning}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
                      isRunning
                        ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                        : "border border-emerald-400/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500 hover:text-slate-950"
                    }`}
                  >
                    {isRunning ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Run Decision Workflow
                      </>
                    )}
                  </button>

                  <Link
                    href="/candidates"
                    className="flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-black/30 px-4 py-2 text-sm font-bold uppercase text-emerald-300 transition-all hover:border-emerald-400/40 hover:bg-black/40"
                  >
                    <Users className="h-4 w-4" />
                    Go to Candidates
                  </Link>
                </div>
              </section>
            ) : !data.top_action || data.top_recommendations.length === 0 ? (
              <section className={cardShell}>
                <div className="flex items-center gap-3">
                  <AlertTriangle className="h-8 w-8 text-amber-400" />
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-amber-400">No actionable recommendations</p>
                    <h2 className="mt-1 text-2xl font-black text-white">Candidates exist but none passed all gates</h2>
                  </div>
                </div>
                <p className="mt-4 max-w-5xl text-sm leading-relaxed text-slate-300">
                  Candidates were ranked but none passed the quality, model score, and risk gates required for actionable status.
                </p>

                <div className="mt-6 flex flex-wrap gap-3">
                  <button
                    onClick={handleRunWorkflow}
                    disabled={isRunning}
                    className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
                      isRunning
                        ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                        : "border border-emerald-400/40 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500 hover:text-slate-950"
                    }`}
                  >
                    {isRunning ? (
                      <>
                        <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" />
                        Re-run Workflow
                      </>
                    )}
                  </button>

                  <Link
                    href="/candidates"
                    className="flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-black/30 px-4 py-2 text-sm font-bold uppercase text-emerald-300 transition-all hover:border-emerald-400/40 hover:bg-black/40"
                  >
                    <Users className="h-4 w-4" />
                    Manage Candidates
                  </Link>
                </div>

                {/* Show source data status if available */}
                {data.source_data_status.length > 0 && (
                  <div className="mt-6">
                    <p className="mb-3 text-sm font-semibold text-slate-400">Source data status:</p>
                    <div className="grid grid-cols-1 gap-3 lg:grid-cols-5">
                      {data.source_data_status.map((source) => (
                        <div key={source.symbol} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                          <p className="text-lg font-black text-white">{source.symbol}</p>
                          <p className="mt-1 text-xs uppercase tracking-wide text-slate-500">Provider</p>
                          <p className="text-sm font-bold text-slate-300">{source.provider ?? "none"}</p>
                          <p className="mt-2 text-xs uppercase tracking-wide text-slate-500">Quality</p>
                          <p className="text-sm font-bold text-amber-300">{source.data_quality ?? "unavailable"}</p>
                          {source.error && <p className="mt-2 text-xs leading-relaxed text-slate-400">{source.error}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            ) : (
              <>
                <section className={cardShell}>
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-emerald-400">Top Source-Backed Watch Candidate</p>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <h2 className="text-4xl font-black text-white">{data.top_action.symbol}</h2>
                        <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-4 py-1 text-sm font-bold uppercase text-emerald-300">
                          {data.top_action.action_label}
                        </span>
                        <span className="rounded-full border border-cyan-500 bg-cyan-500/10 px-4 py-1 text-sm font-bold uppercase text-cyan-300">
                          {data.top_action.data_mode.replace(/_/g, " ")}
                        </span>
                      </div>
                      <p className="mt-3 max-w-5xl text-sm leading-relaxed text-slate-300">{data.top_action.final_reason}</p>
                    </div>

                    <div className="rounded-xl border border-emerald-400/20 bg-white/[0.03] px-6 py-4 text-center">
                      <p className="text-xs uppercase tracking-wide text-emerald-400">Confidence</p>
                      <p className="mt-1 text-4xl font-black text-white">{percent(data.top_action.confidence)}</p>
                      <p className="mt-1 text-sm text-slate-400">Score {data.top_action.final_score}/100</p>
                    </div>
                  </div>

                  <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-6">
                    <MetricCard label="Current" value={money(data.top_action.price_plan.current_price)} accent />
                    <MetricCard label="Watch low" value={money(data.top_action.price_plan.buy_zone_low)} />
                    <MetricCard label="Watch high" value={money(data.top_action.price_plan.buy_zone_high)} />
                    <MetricCard label="Risk level" value={money(data.top_action.price_plan.stop_loss)} />
                    <MetricCard label="Target ref" value={money(data.top_action.price_plan.target_price)} />
                    <MetricCard label="Reward/Risk" value={`${data.top_action.risk_plan.reward_risk_ratio.toFixed(1)}R`} />
                  </div>
                </section>

                <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
                  <h2 className="mb-3 text-lg font-semibold text-emerald-300">Evidence Status</h2>
                  <div className="grid grid-cols-1 gap-4 xl:grid-cols-5">
                    {data.top_action.model_votes.map((vote) => (
                      <div key={vote.model} className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                        <h3 className="text-sm font-bold text-white">{vote.model}</h3>
                        <p className="mt-2 text-2xl font-black text-emerald-400">{percent(vote.confidence)}</p>
                        <p className="mt-2 text-sm leading-relaxed text-slate-400">{vote.explanation}</p>
                        <p className="mt-3 text-xs uppercase tracking-wide text-amber-300">Status: {vote.status}</p>
                      </div>
                    ))}
                  </div>
                </section>
              </>
            )}

            <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
              <h2 className="mb-3 text-lg font-semibold text-emerald-300">Portfolio Snapshot</h2>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Buying Power" value={`$${data.account_profile.buying_power.toLocaleString()}`} accent />
                <MetricCard label="Account Equity" value={`$${data.account_profile.account_equity.toLocaleString()}`} />
                <MetricCard label="Risk / Trade" value={`${data.account_profile.max_risk_per_trade_percent}%`} />
                <MetricCard label="Min Reward/Risk" value={`${data.account_profile.min_reward_risk_ratio}R`} />
              </div>
            </section>

            {data.top_recommendations.length > 0 && (
              <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
                <h2 className="mb-3 text-lg font-semibold text-emerald-300">Source-Backed Watch Candidates</h2>
                <RecommendationTable recommendations={data.top_recommendations} />
              </section>
            )}

            {data.urgent_edge_alerts.length > 0 && (
              <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
                <h2 className="mb-3 text-lg font-semibold text-emerald-300">Urgent Edge Alerts</h2>
                <EdgeSignalGrid signals={data.urgent_edge_alerts} />
              </section>
            )}
          </div>
        )}
    </div>
  );
}
