"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type JournalOutcomeResponse, type PerformanceDriftResponse, type ResearchPriorityResponse, type ModelStrategyUpdateResponse, type MemoryUpdateResponse } from "@/lib/api";
import { Play, Target, TrendingUp, Brain, Database, AlertTriangle, CheckCircle, Clock, BookOpen, Activity, RotateCw, XCircle } from "lucide-react";

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
  const [isRunningDrift, setIsRunningDrift] = useState(false);
  const [isRunningResearch, setIsRunningResearch] = useState(false);
  const [isRunningUpdate, setIsRunningUpdate] = useState(false);
  const [isStoringMemory, setIsStoringMemory] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const [entries, summary, drift, research, update] = await Promise.all([
        api.getJournalOutcomes({ limit: 10 }),
        api.getJournalSummary(),
        api.getLatestPerformanceDrift(),
        api.getLatestResearchPriority(),
        api.getLatestModelStrategyUpdate(),
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

  return (
    <div className="mx-auto w-full max-w-6xl p-4 lg:p-8">
      <PageHeader
        eyebrow="workflow steps 20-24"
        title="Learning Loop"
        description="Closed-loop learning: Journal outcomes → Performance drift → Research priorities → Model/strategy updates → Memory storage."
      />

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
