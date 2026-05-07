"use client";

import { useEffect, useMemo, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import {
  api,
  type JournalOutcomeResponse,
  type LearningLoopDecisionResult,
  type LearningLoopEvaluateRequest,
  type LearningLoopOutcome,
  type LearningLoopStatusResponse,
  type ModelStrategyUpdateResponse,
  type PerformanceDriftResponse,
  type ResearchPriorityResponse,
  type MemoryUpdateResponse,
} from "@/lib/api";
import { Play, Target, TrendingUp, Brain, Database, AlertTriangle, CheckCircle, Clock, BookOpen, Activity, RotateCw, XCircle } from "lucide-react";

const LEARNING_ACTIONS = [
  "promote_candidate",
  "keep_monitoring",
  "demote_to_paper",
  "demote_to_research",
  "block_strategy",
  "review_needed",
];

const STAGE_14_CHECKERS = ["Learning Metrics Updater", "Drift Detector", "Promotion/Demotion Rules", "Learning Loop Agent"];

const DEFAULT_OUTCOMES: LearningLoopOutcome[] = [
  {
    trade_id: "trade_1",
    outcome_label: "target_hit",
    outcome_status: "positive",
    realized_pnl: 55.9,
    r_multiple: 1.83,
    slippage_status: "pass",
    rule_compliant: true,
  },
  {
    trade_id: "trade_2",
    outcome_label: "stopped_out",
    outcome_status: "negative",
    realized_pnl: -29.9,
    r_multiple: -1.0,
    slippage_status: "pass",
    rule_compliant: true,
  },
];

function resolutionPathBadge(path: string) {
  switch (path) {
    case "target_first":
      return <span className="rounded bg-emerald-900/40 px-1.5 py-0.5 text-[10px] font-bold uppercase text-emerald-400">Target first</span>;
    case "stop_first":
      return <span className="rounded bg-red-900/40 px-1.5 py-0.5 text-[10px] font-bold uppercase text-red-400">Stop first</span>;
    case "timed_exit":
      return <span className="rounded bg-sky-900/40 px-1.5 py-0.5 text-[10px] font-bold uppercase text-sky-400">Timed exit</span>;
    case "invalidation_before_entry":
      return <span className="rounded bg-amber-900/40 px-1.5 py-0.5 text-[10px] font-bold uppercase text-amber-400">Pre-entry invalid</span>;
    default:
      return null;
  }
}

function outcomeBadge(label: string) {
  switch (label) {
    case "win":
      return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">Win</span>;
    case "loss":
      return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">Loss</span>;
    case "breakeven":
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">Breakeven</span>;
    case "avoided_loss":
      return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">Avoided Loss</span>;
    case "unknown":
      return <span className="rounded-full border border-slate-600 bg-slate-600/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-500">Unknown</span>;
    default:
      return <span className="rounded-full border border-slate-600 bg-slate-600/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-500">{label}</span>;
  }
}

function driftStatusBadge(status: string) {
  switch (status) {
    case "pass":
      return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">Pass</span>;
    case "warn":
      return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">Warn</span>;
    case "fail":
      return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">Fail</span>;
    case "insufficient_data":
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">No Data</span>;
    default:
      return <span className="rounded-full border border-slate-600 bg-slate-600/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-500">{status}</span>;
  }
}

function taskTypeIcon(type: string) {
  switch (type) {
    case "backtest":
      return <TrendingUp className="h-4 w-4 text-sky-400" />;
    case "model_evaluation":
      return <Brain className="h-4 w-4 text-purple-400" />;
    case "strategy_review":
      return <Target className="h-4 w-4 text-amber-400" />;
    case "retraining_request":
      return <RotateCw className="h-4 w-4 text-emerald-400" />;
    default:
      return <Activity className="h-4 w-4 text-slate-400" />;
  }
}

export default function LearningLoopPage() {
  const [journalEntries, setJournalEntries] = useState<JournalOutcomeResponse[]>([]);
  const [journalSummary, setJournalSummary] = useState<{ total_entries: number; wins: number; losses: number; win_rate: number } | null>(null);
  const [driftCheck, setDriftCheck] = useState<PerformanceDriftResponse | null>(null);
  const [researchPriority, setResearchPriority] = useState<ResearchPriorityResponse | null>(null);
  const [modelStrategyUpdate, setModelStrategyUpdate] = useState<ModelStrategyUpdateResponse | null>(null);
  const [memoryUpdate, setMemoryUpdate] = useState<MemoryUpdateResponse | null>(null);

  // Stage 14: Learning Loop (post-trade → learning decision)
  const [stage14Status, setStage14Status] = useState<LearningLoopStatusResponse | null>(null);
  const [stage14Decision, setStage14Decision] = useState<LearningLoopDecisionResult | null>(null);
  const [stage14OutcomesJson, setStage14OutcomesJson] = useState<string>(() => JSON.stringify(DEFAULT_OUTCOMES, null, 2));
  const [stage14Form, setStage14Form] = useState<Omit<LearningLoopEvaluateRequest, "recent_outcomes">>({
    strategy_key: "regime_aware_momentum_catalyst",
    strategy_group: "regime_aware_momentum",
    asset_class: "stock",
    horizon: "day_trading",
    workflow_key: "baseline_fast_path",
    current_status: {
      promotion_status: "paper_ready",
      proof_status: "paper_passed",
      sample_size: 12,
      current_drawdown_r: -1.5,
      last_10_avg_r: 0.42,
    },
    thresholds: {
      min_sample_size_for_promotion: 20,
      min_avg_r_for_promotion: 0.35,
      max_drawdown_r_before_demotion: -3.0,
      max_rule_violation_rate: 0.1,
      max_slippage_fail_rate: 0.15,
    },
  });
  const [stage14Busy, setStage14Busy] = useState(false);
  const [stage14Error, setStage14Error] = useState<string | null>(null);

  const [isRunningDrift, setIsRunningDrift] = useState(false);
  const [isRunningResearch, setIsRunningResearch] = useState(false);
  const [isRunningUpdate, setIsRunningUpdate] = useState(false);
  const [isStoringMemory, setIsStoringMemory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [entries, summary, drift, research, update, llStatus, llLatest] = await Promise.all([
        api.getJournalOutcomes({ limit: 10 }),
        api.getJournalSummary(),
        api.getLatestPerformanceDrift(),
        api.getLatestResearchPriority(),
        api.getLatestModelStrategyUpdate(),
        api.getLearningLoopStatus(),
        api.getLatestLearningLoopDecision(),
      ]);
      
      if (Array.isArray(entries)) setJournalEntries(entries);
      if (!("status" in summary && summary.status === "not_found")) {
        setJournalSummary(summary as { total_entries: number; wins: number; losses: number; win_rate: number });
      }
      if (!("status" in drift && drift.status === "not_found")) {
        setDriftCheck(drift as PerformanceDriftResponse);
      }
      if (!("status" in research && research.status === "not_found")) {
        setResearchPriority(research as ResearchPriorityResponse);
      }
      if (!("status" in update && update.status === "not_found")) {
        setModelStrategyUpdate(update as ModelStrategyUpdateResponse);
      }

      setStage14Status(llStatus as LearningLoopStatusResponse);
      const latestDecision = (llLatest as any)?.result ?? (llStatus as any)?.latest_decision ?? null;
      setStage14Decision(latestDecision as LearningLoopDecisionResult | null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunDrift = async () => {
    setIsRunningDrift(true);
    setError(null);
    try {
      const response = await api.runPerformanceDrift({ lookback_days: 30, min_samples: 5 });
      setDriftCheck(response);
      setSuccessMessage("Performance drift check completed");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Drift check failed");
    } finally {
      setIsRunningDrift(false);
    }
  };

  const handleRunResearch = async () => {
    setIsRunningResearch(true);
    setError(null);
    try {
      const response = await api.runResearchPriority({ lookback_days: 30, max_tasks: 10 });
      setResearchPriority(response);
      setSuccessMessage("Research priorities generated");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Research generation failed");
    } finally {
      setIsRunningResearch(false);
    }
  };

  const handleRunUpdate = async () => {
    setIsRunningUpdate(true);
    setError(null);
    try {
      const response = await api.proposeModelStrategyUpdate({ dry_run: true });
      setModelStrategyUpdate(response);
      setSuccessMessage("Model/strategy update proposals generated");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update proposal failed");
    } finally {
      setIsRunningUpdate(false);
    }
  };

  const handleStoreMemory = async () => {
    setIsStoringMemory(true);
    setError(null);
    try {
      const response = await api.storeLatestJournalToMemory();
      setMemoryUpdate(response);
      setSuccessMessage("Latest journal entry stored to memory");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Memory storage failed");
    } finally {
      setIsStoringMemory(false);
    }
  };

  const supportedLearningActions = useMemo(() => {
    const s = stage14Status?.supported_learning_actions;
    return Array.isArray(s) && s.length ? s : LEARNING_ACTIONS;
  }, [stage14Status]);

  const checkerByName = useMemo(() => {
    const map = new Map<string, { status?: string; message?: string }>();
    for (const c of stage14Status?.checker_statuses ?? []) map.set(c.checker, c);
    return map;
  }, [stage14Status]);

  const handleEvaluateLearning = async () => {
    setStage14Error(null);

    let parsed: unknown;
    try {
      parsed = JSON.parse(stage14OutcomesJson);
    } catch {
      setStage14Error("recent_outcomes JSON is invalid. Fix the JSON array before evaluating (no API call was made).");
      return;
    }

    if (!Array.isArray(parsed)) {
      setStage14Error("recent_outcomes must be a JSON array. No API call was made.");
      return;
    }

    const recent_outcomes = parsed as LearningLoopOutcome[];

    setStage14Busy(true);
    setError(null);
    try {
      const response = await api.evaluateLearningLoop({ ...stage14Form, recent_outcomes });
      setStage14Decision(response.result);
      setSuccessMessage("Stage 14 learning decision evaluated (recommendations only)");
    } catch (err) {
      setStage14Error(err instanceof Error ? err.message : "Learning decision evaluation failed");
    } finally {
      setStage14Busy(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl p-4 lg:p-8">
      <PageHeader
        eyebrow="stage 14"
        title="Learning Loop"
        description="Stage 14 AI-Agent that evaluates post-trade outcomes, drift, promotion/demotion rules, and learning metrics without using an LLM or automatically promoting to live trading."
      />

      <div className="mb-4 flex flex-wrap gap-2">
        {["US Stocks Only", "Day Trading Only", "Paper-First", "No LLM", "No Auto Live Promotion"].map((t) => (
          <span
            key={t}
            className={
              t === "No LLM" || t === "No Auto Live Promotion"
                ? "rounded-full border border-white/10 bg-slate-950/40 px-3 py-1 text-[10px] font-bold uppercase text-slate-300"
                : "rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-[10px] font-bold uppercase text-emerald-300"
            }
          >
            {t}
          </span>
        ))}
      </div>

      {/* Stage 14 Summary Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard label="Stage" value="14" accent />
        <MetricCard label="Learning Status" value={stage14Status?.learning_status?.replaceAll("_", " ") || "unknown"} />
        <MetricCard label="Latest Decision" value={stage14Decision?.learning_action?.replaceAll("_", " ") || "—"} />
        <MetricCard label="Next Action" value={stage14Decision?.next_action || stage14Status?.next_action || "—"} />
      </div>

      {/* Stage 14 Evaluator */}
      <div className="mb-6 grid gap-6 lg:grid-cols-3">
        <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4 lg:col-span-2">
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h3 className="flex items-center gap-2 text-sm font-bold uppercase text-emerald-400">
              <Play className="h-4 w-4" />
              Stage 14: Evaluate learning decision
            </h3>
            <button
              onClick={handleEvaluateLearning}
              disabled={stage14Busy}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
                stage14Busy
                  ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                  : "border border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
              }`}
            >
              {stage14Busy ? <RotateCw className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Evaluate Sample Learning Decision
            </button>
          </div>

          {stage14Error && (
            <div className="mb-3 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
              <AlertTriangle className="mr-2 inline h-4 w-4" />
              {stage14Error}
            </div>
          )}

          <div className="mb-4 flex flex-wrap gap-2">
            <button
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold uppercase text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300"
              onClick={() => {
                setStage14Form((f) => ({
                  ...f,
                  current_status: { ...f.current_status, sample_size: 12, current_drawdown_r: -1.5, last_10_avg_r: 0.25 },
                }));
              }}
            >
              Keep Monitoring Sample
            </button>
            <button
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold uppercase text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300"
              onClick={() => {
                setStage14Form((f) => ({
                  ...f,
                  current_status: { ...f.current_status, sample_size: 24, last_10_avg_r: 0.55, current_drawdown_r: -1.1, promotion_status: "paper_ready" },
                }));
                setStage14OutcomesJson(JSON.stringify(DEFAULT_OUTCOMES, null, 2));
              }}
            >
              Promote Candidate Sample
            </button>
            <button
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold uppercase text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300"
              onClick={() => {
                setStage14Form((f) => ({
                  ...f,
                  current_status: { ...f.current_status, current_drawdown_r: -4.2 },
                }));
              }}
            >
              Drawdown Demotion Sample
            </button>
            <button
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold uppercase text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300"
              onClick={() => {
                setStage14OutcomesJson(
                  JSON.stringify(
                    [
                      { ...DEFAULT_OUTCOMES[0], rule_compliant: false, outcome_label: "rule_violation", outcome_status: "negative" },
                      DEFAULT_OUTCOMES[1],
                    ],
                    null,
                    2,
                  ),
                );
              }}
            >
              Rule Violation Demotion Sample
            </button>
            <button
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold uppercase text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300"
              onClick={() => setStage14Form((f) => ({ ...f, asset_class: "crypto" }))}
            >
              Crypto Blocked Sample
            </button>
            <button
              className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs font-bold uppercase text-slate-300 hover:border-emerald-500/40 hover:text-emerald-300"
              onClick={() => setStage14OutcomesJson("[]")}
            >
              Empty Outcomes Review Sample
            </button>
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <div>
                <div className="mb-1 text-xs font-bold uppercase text-slate-500">Strategy</div>
                <div className="grid gap-2">
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                    value={stage14Form.strategy_key}
                    onChange={(e) => setStage14Form((f) => ({ ...f, strategy_key: e.target.value }))}
                  />
                  <input
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                    value={stage14Form.strategy_group}
                    onChange={(e) => setStage14Form((f) => ({ ...f, strategy_group: e.target.value }))}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.asset_class}
                      onChange={(e) => setStage14Form((f) => ({ ...f, asset_class: e.target.value }))}
                    >
                      <option value="stock">stock</option>
                      <option value="crypto">crypto</option>
                      <option value="etf">etf</option>
                      <option value="option">option</option>
                    </select>
                    <select
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.horizon}
                      onChange={(e) => setStage14Form((f) => ({ ...f, horizon: e.target.value }))}
                    >
                      <option value="day_trading">day_trading</option>
                      <option value="swing">swing</option>
                    </select>
                  </div>
                  <select
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                    value={stage14Form.workflow_key}
                    onChange={(e) => setStage14Form((f) => ({ ...f, workflow_key: e.target.value }))}
                  >
                    <option value="baseline_fast_path">baseline_fast_path</option>
                    <option value="conservative_path">conservative_path</option>
                    <option value="paper_only_path">paper_only_path</option>
                  </select>
                </div>
              </div>

              <div>
                <div className="mb-1 text-xs font-bold uppercase text-slate-500">Current status</div>
                <div className="grid gap-2">
                  <div className="grid grid-cols-2 gap-2">
                    <select
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.current_status.promotion_status}
                      onChange={(e) =>
                        setStage14Form((f) => ({ ...f, current_status: { ...f.current_status, promotion_status: e.target.value } }))
                      }
                    >
                      {["paper_ready", "paper_only", "research_only", "blocked"].map((x) => (
                        <option key={x} value={x}>
                          {x}
                        </option>
                      ))}
                    </select>
                    <select
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.current_status.proof_status}
                      onChange={(e) => setStage14Form((f) => ({ ...f, current_status: { ...f.current_status, proof_status: e.target.value } }))}
                    >
                      {["paper_passed", "paper_failed", "insufficient_data", "unknown"].map((x) => (
                        <option key={x} value={x}>
                          {x}
                        </option>
                      ))}
                    </select>
                  </div>
                  <input
                    type="number"
                    className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                    value={stage14Form.current_status.sample_size}
                    onChange={(e) => setStage14Form((f) => ({ ...f, current_status: { ...f.current_status, sample_size: Number(e.target.value) } }))}
                  />
                  <div className="grid grid-cols-2 gap-2">
                    <input
                      type="number"
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.current_status.current_drawdown_r}
                      onChange={(e) =>
                        setStage14Form((f) => ({ ...f, current_status: { ...f.current_status, current_drawdown_r: Number(e.target.value) } }))
                      }
                    />
                    <input
                      type="number"
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.current_status.last_10_avg_r}
                      onChange={(e) => setStage14Form((f) => ({ ...f, current_status: { ...f.current_status, last_10_avg_r: Number(e.target.value) } }))}
                    />
                  </div>
                </div>
              </div>

              <div>
                <div className="mb-1 text-xs font-bold uppercase text-slate-500">Thresholds</div>
                <div className="grid gap-2">
                  {(
                    [
                      ["min_sample_size_for_promotion", "min_sample_size_for_promotion"],
                      ["min_avg_r_for_promotion", "min_avg_r_for_promotion"],
                      ["max_drawdown_r_before_demotion", "max_drawdown_r_before_demotion"],
                      ["max_rule_violation_rate", "max_rule_violation_rate"],
                      ["max_slippage_fail_rate", "max_slippage_fail_rate"],
                    ] as const
                  ).map(([k, label]) => (
                    <input
                      key={k}
                      type="number"
                      className="w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 text-sm text-slate-100"
                      value={stage14Form.thresholds[k]}
                      onChange={(e) => setStage14Form((f) => ({ ...f, thresholds: { ...f.thresholds, [k]: Number(e.target.value) } }))}
                      placeholder={label}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="space-y-3">
              <div>
                <div className="mb-1 text-xs font-bold uppercase text-slate-500">Recent outcomes (JSON)</div>
                <textarea
                  className="min-h-56 w-full rounded-lg border border-slate-700 bg-slate-950/30 px-3 py-2 font-mono text-xs text-slate-100"
                  value={stage14OutcomesJson}
                  onChange={(e) => setStage14OutcomesJson(e.target.value)}
                />
                <p className="mt-2 text-xs text-slate-500">
                  For v1, paste or edit recent outcome JSON. Later this will be pulled automatically from Stage 13.
                </p>
              </div>
            </div>
          </div>

          {stage14Decision && (
            <div className="mt-4 rounded-xl border border-slate-700 bg-slate-950/20 p-4">
              <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-bold uppercase text-slate-300">Decision output</div>
                <span className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs font-bold uppercase text-slate-300">
                  llm_used: {stage14Decision.llm_used ? "true" : "false"}
                </span>
              </div>
              <div className="grid gap-2 text-xs text-slate-400 md:grid-cols-2">
                <div>decision_id: <span className="text-slate-200">{stage14Decision.decision_id}</span></div>
                <div>learning_action: <span className="text-slate-200">{stage14Decision.learning_action}</span></div>
                <div>strategy_key: <span className="text-slate-200">{stage14Decision.strategy_key}</span></div>
                <div>strategy_group: <span className="text-slate-200">{stage14Decision.strategy_group}</span></div>
                <div>asset_class: <span className="text-slate-200">{stage14Decision.asset_class}</span></div>
                <div>horizon: <span className="text-slate-200">{stage14Decision.horizon}</span></div>
                <div>created_at: <span className="text-slate-200">{stage14Decision.created_at || "—"}</span></div>
                <div>next_action: <span className="text-slate-200">{stage14Decision.next_action || "—"}</span></div>
              </div>

              <div className="mt-3 grid gap-3 md:grid-cols-2">
                <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                  <div className="mb-2 text-xs font-bold uppercase text-slate-500">Metrics</div>
                  <div className="grid gap-1 text-xs text-slate-400">
                    <div>sample_size: <span className="text-slate-200">{stage14Decision.metrics.sample_size}</span></div>
                    <div>wins/losses/flats: <span className="text-slate-200">{stage14Decision.metrics.wins}/{stage14Decision.metrics.losses}/{stage14Decision.metrics.flats}</span></div>
                    <div>win_rate: <span className="text-slate-200">{stage14Decision.metrics.win_rate}</span></div>
                    <div>avg_r_multiple: <span className="text-slate-200">{stage14Decision.metrics.avg_r_multiple}</span></div>
                    <div>avg_realized_pnl: <span className="text-slate-200">{stage14Decision.metrics.avg_realized_pnl}</span></div>
                    <div>rule_violation_rate: <span className="text-slate-200">{stage14Decision.metrics.rule_violation_rate}</span></div>
                    <div>slippage_fail_rate: <span className="text-slate-200">{stage14Decision.metrics.slippage_fail_rate}</span></div>
                    <div>current_drawdown_r: <span className="text-slate-200">{stage14Decision.metrics.current_drawdown_r}</span></div>
                  </div>
                </div>
                <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-3">
                  <div className="mb-2 text-xs font-bold uppercase text-slate-500">Drift / Promotion / Demotion</div>
                  <div className="grid gap-1 text-xs text-slate-400">
                    <div>drift_detected: <span className="text-slate-200">{String(stage14Decision.drift.drift_detected)}</span></div>
                    <div>drift_reason: <span className="text-slate-200">{stage14Decision.drift.drift_reason}</span></div>
                    <div>eligible_for_promotion: <span className="text-slate-200">{String(stage14Decision.promotion.eligible_for_promotion)}</span></div>
                    <div>promotion_target: <span className="text-slate-200">{stage14Decision.promotion.promotion_target}</span></div>
                    <div>promotion_blocked_reasons: <span className="text-slate-200">{(stage14Decision.promotion.blocked_reasons || []).join(", ") || "—"}</span></div>
                    <div>demotion_required: <span className="text-slate-200">{String(stage14Decision.demotion.demotion_required)}</span></div>
                    <div>demotion_target: <span className="text-slate-200">{stage14Decision.demotion.demotion_target}</span></div>
                    <div>demotion_reasons: <span className="text-slate-200">{(stage14Decision.demotion.reasons || []).join(", ") || "—"}</span></div>
                  </div>
                </div>
              </div>

              <div className="mt-3 text-sm text-slate-300">reason: <span className="text-slate-200">{stage14Decision.reason}</span></div>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <h3 className="mb-2 text-sm font-bold uppercase text-slate-400">Supported learning actions</h3>
            <div className="flex flex-wrap gap-2">
              {supportedLearningActions.map((a) => (
                <span key={a} className="rounded-full border border-slate-700 bg-slate-900 px-2 py-0.5 text-xs font-bold uppercase text-slate-300">
                  {a}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <h3 className="mb-2 text-sm font-bold uppercase text-slate-400">Checker status</h3>
            <div className="space-y-2">
              {STAGE_14_CHECKERS.map((c) => {
                const r = checkerByName.get(c);
                return (
                  <div key={c} className="rounded-lg bg-slate-800/40 p-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-bold text-slate-300">{c}</span>
                      <span className="rounded bg-slate-700 px-2 py-0.5 text-[10px] font-bold uppercase text-slate-300">
                        {r?.status ?? "unknown"}
                      </span>
                    </div>
                    <div className="mt-1 text-slate-500">{r?.message ?? "No details yet (evaluate a sample decision)."}</div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <h3 className="mb-2 text-sm font-bold uppercase text-slate-400">Safety guarantees</h3>
            <ul className="space-y-1 text-xs text-slate-400">
              <li>no broker calls</li>
              <li>no execution endpoints</li>
              <li>no automatic registry update</li>
              <li>no automatic live promotion</li>
              <li>no LLM reviewer in v1</li>
              <li>recommendations only</li>
            </ul>
          </div>

          <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
            <h3 className="mb-2 text-sm font-bold uppercase text-slate-400">Useful links</h3>
            <div className="flex flex-wrap gap-2 text-xs">
              <a className="rounded bg-slate-800 px-2 py-1 text-slate-300 hover:text-emerald-300" href="/post-trade-evaluation">
                Post-Trade Evaluation →
              </a>
              <a className="rounded bg-slate-800 px-2 py-1 text-slate-300 hover:text-emerald-300" href="/journal">
                Journal →
              </a>
              <a className="rounded bg-slate-800 px-2 py-1 text-slate-300 hover:text-emerald-300" href="/strategies">
                Strategies →
              </a>
              <a className="rounded bg-slate-800 px-2 py-1 text-slate-300 hover:text-emerald-300" href="/settings?tab=master_admin">
                Master Admin Controls →
              </a>
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertTriangle className="mr-2 inline h-4 w-4" />
          {error}
        </div>
      )}

      {successMessage && (
        <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
          <CheckCircle className="mr-2 inline h-4 w-4" />
          {successMessage}
        </div>
      )}

      {/* Action Buttons */}
      <div className="mb-6 flex flex-wrap gap-3">
        <button
          onClick={handleRunDrift}
          disabled={isRunningDrift}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
            isRunningDrift
              ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
              : "border border-sky-500 bg-slate-900 text-sky-400 hover:bg-sky-500 hover:text-slate-950"
          }`}
        >
          {isRunningDrift ? <RotateCw className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
          Run Drift Check
        </button>
        <button
          onClick={handleRunResearch}
          disabled={isRunningResearch}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
            isRunningResearch
              ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
              : "border border-amber-500 bg-slate-900 text-amber-400 hover:bg-amber-500 hover:text-slate-950"
          }`}
        >
          {isRunningResearch ? <RotateCw className="h-4 w-4 animate-spin" /> : <Brain className="h-4 w-4" />}
          Generate Research Priorities
        </button>
        <button
          onClick={handleRunUpdate}
          disabled={isRunningUpdate}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
            isRunningUpdate
              ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
              : "border border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
          }`}
        >
          {isRunningUpdate ? <RotateCw className="h-4 w-4 animate-spin" /> : <Target className="h-4 w-4" />}
          Propose Updates
        </button>
        <button
          onClick={handleStoreMemory}
          disabled={isStoringMemory}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
            isStoringMemory
              ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
              : "border border-purple-500 bg-slate-900 text-purple-400 hover:bg-purple-500 hover:text-slate-950"
          }`}
        >
          {isStoringMemory ? <RotateCw className="h-4 w-4 animate-spin" /> : <Database className="h-4 w-4" />}
          Store to Memory
        </button>
      </div>

      {/* Summary Cards */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard 
          label="Journal Entries" 
          value={journalSummary?.total_entries?.toString() || "0"} 
          accent 
        />
        <MetricCard 
          label="Win Rate" 
          value={journalSummary ? `${(journalSummary.win_rate * 100).toFixed(1)}%` : "N/A"} 
        />
        <MetricCard 
          label="Drift Status" 
          value={driftCheck?.status?.replace("_", " ") || "N/A"} 
        />
        <MetricCard 
          label="Open Tasks" 
          value={researchPriority?.tasks?.filter(t => t.status === "open")?.length?.toString() || "0"} 
        />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Journal Outcomes */}
        <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <BookOpen className="h-4 w-4" />
            Journal Outcomes
          </h3>
          {journalEntries.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {journalEntries.map(entry => (
                <div key={entry.id} className="rounded-lg bg-slate-800/50 p-2 text-xs">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold text-slate-300">{entry.symbol || "N/A"}</span>
                    <div className="flex flex-wrap items-center justify-end gap-1">
                      {resolutionPathBadge(entry.resolution_path)}
                      {outcomeBadge(entry.outcome_label)}
                    </div>
                  </div>
                  <div className="mt-1 flex gap-2 text-slate-500">
                    <span>R: {entry.realized_r?.toFixed(2) || "N/A"}</span>
                    <span>MFE: {entry.mfe_percent?.toFixed(1) || "N/A"}%</span>
                    <span>MAE: {entry.mae_percent?.toFixed(1) || "N/A"}%</span>
                  </div>
                  {entry.lessons.length > 0 && (
                    <div className="mt-1 text-slate-400">
                      {entry.lessons.slice(0, 2).join(" • ")}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-sm text-slate-500 py-4">No journal entries yet. Create outcomes from paper trades.</p>
          )}
        </div>

        {/* Performance Drift */}
        <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-amber-400">
            <TrendingUp className="h-4 w-4" />
            Performance Drift
          </h3>
          {driftCheck ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Status</span>
                {driftStatusBadge(driftCheck.status)}
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="rounded-lg bg-slate-800/50 p-2">
                  <span className="text-slate-500">Samples</span>
                  <div className="font-medium text-slate-300">{driftCheck.sample_count}</div>
                </div>
                <div className="rounded-lg bg-slate-800/50 p-2">
                  <span className="text-slate-500">Win Rate</span>
                  <div className="font-medium text-slate-300">
                    {driftCheck.win_rate ? `${(driftCheck.win_rate * 100).toFixed(1)}%` : "N/A"}
                  </div>
                </div>
                <div className="rounded-lg bg-slate-800/50 p-2">
                  <span className="text-slate-500">Avg R</span>
                  <div className="font-medium text-slate-300">
                    {driftCheck.average_realized_r?.toFixed(2) || "N/A"}
                  </div>
                </div>
                <div className="rounded-lg bg-slate-800/50 p-2">
                  <span className="text-slate-500">False Pos</span>
                  <div className="font-medium text-slate-300">
                    {driftCheck.false_positive_rate ? `${(driftCheck.false_positive_rate * 100).toFixed(1)}%` : "N/A"}
                  </div>
                </div>
              </div>
              {driftCheck.recommended_actions.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {driftCheck.recommended_actions.map((action, i) => (
                    <span key={i} className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-400">
                      {action}
                    </span>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <p className="text-center text-sm text-slate-500 py-4">No drift check yet. Click "Run Drift Check" to analyze performance.</p>
          )}
        </div>

        {/* Research Priorities */}
        <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-purple-400">
            <Brain className="h-4 w-4" />
            Research Priorities
          </h3>
          {researchPriority && researchPriority.tasks.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {researchPriority.tasks.slice(0, 5).map(task => (
                <div key={task.task_id} className="rounded-lg bg-slate-800/50 p-2 text-xs">
                  <div className="flex items-center gap-2">
                    {taskTypeIcon(task.task_type)}
                    <span className="font-bold text-slate-300">{task.title}</span>
                    <span className="ml-auto rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-400">
                      {task.priority_score.toFixed(0)}
                    </span>
                  </div>
                  <p className="mt-1 text-slate-500 line-clamp-2">{task.description}</p>
                  <div className="mt-1 text-slate-600">
                    Next: {task.suggested_next_step}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-center text-sm text-slate-500 py-4">No research tasks yet. Run drift check first to generate priorities.</p>
          )}
        </div>

        {/* Model/Strategy Updates */}
        <div className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-emerald-400">
            <Target className="h-4 w-4" />
            Model/Strategy Updates
          </h3>
          {modelStrategyUpdate ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Status</span>
                <span className="text-xs font-bold uppercase text-slate-300">{modelStrategyUpdate.status}</span>
              </div>
              
              {modelStrategyUpdate.strategy_weight_updates.length > 0 && (
                <div>
                  <span className="text-xs text-slate-500">Strategy Updates</span>
                  <div className="mt-1 space-y-1">
                    {modelStrategyUpdate.strategy_weight_updates.slice(0, 3).map((update, i) => (
                      <div key={i} className="flex items-center justify-between rounded bg-slate-800/50 p-1.5 text-xs">
                        <span className="text-slate-300">{update.strategy_key}</span>
                        <span className={`font-bold ${
                          update.action === "pause" ? "text-red-400" :
                          update.action === "reduce" ? "text-amber-400" :
                          "text-emerald-400"
                        }`}>
                          {update.action}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {modelStrategyUpdate.retraining_requests.length > 0 && (
                <div>
                  <span className="text-xs text-slate-500">Retraining Requests</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {modelStrategyUpdate.retraining_requests.map((req, i) => (
                      <span key={i} className="rounded bg-slate-700 px-2 py-0.5 text-xs text-slate-400">
                        {req.model_name}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              {modelStrategyUpdate.blockers.length > 0 && (
                <div className="rounded border border-red-500/30 bg-red-500/10 p-2 text-xs text-red-400">
                  {modelStrategyUpdate.blockers.join(" • ")}
                </div>
              )}
            </div>
          ) : (
            <p className="text-center text-sm text-slate-500 py-4">No update proposals yet. Generate research priorities first.</p>
          )}
        </div>
      </div>

      {/* Memory Update Status */}
      {memoryUpdate && (
        <div className={`mt-6 rounded-xl border p-4 ${
          memoryUpdate.status === "stored" ? "border-emerald-500/30 bg-emerald-500/10" :
          memoryUpdate.status === "unavailable" ? "border-amber-500/30 bg-amber-500/10" :
          "border-slate-700 bg-slate-900/50"
        }`}>
          <h3 className="mb-2 flex items-center gap-2 text-sm font-bold uppercase text-slate-400">
            <Database className="h-4 w-4" />
            Latest Memory Update
          </h3>
          <div className="flex items-center gap-4 text-sm">
            <span className="text-slate-300">Run: {memoryUpdate.run_id}</span>
            <span className={`font-bold ${
              memoryUpdate.status === "stored" ? "text-emerald-400" :
              memoryUpdate.status === "unavailable" ? "text-amber-400" :
              "text-slate-400"
            }`}>
              {memoryUpdate.status}
            </span>
            {memoryUpdate.memory_id && (
              <span className="text-slate-500">ID: {memoryUpdate.memory_id}</span>
            )}
          </div>
          {memoryUpdate.warnings.length > 0 && (
            <p className="mt-2 text-xs text-amber-400">{memoryUpdate.warnings.join(" • ")}</p>
          )}
        </div>
      )}
    </div>
  );
}
