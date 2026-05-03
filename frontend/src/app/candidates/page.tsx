"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type CandidateUniverseEntry, type DecisionWorkflowRunResponse } from "@/lib/api";
import { Play, Trash2, X, Users, TrendingUp, AlertTriangle, CheckCircle, ScanLine, Radio } from "lucide-react";

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return "—";
  }
}

function statusBadge(status: string) {
  switch (status) {
    case "active":
      return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">Active</span>;
    case "paused":
      return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">Paused</span>;
    case "removed":
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">Removed</span>;
    default:
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">{status}</span>;
  }
}

function sourceTypeLabel(sourceType: string) {
  switch (sourceType) {
    case "manual": return "Manual";
    case "watchlist": return "Watchlist";
    case "scanner": return "Scanner";
    case "stock_search": return "Stock Search";
    case "strategy_workflow": return "Strategy Workflow";
    default: return sourceType;
  }
}

export default function CandidatesPage() {
  const [candidates, setCandidates] = useState<CandidateUniverseEntry[]>([]);
  const [summary, setSummary] = useState<{ active_count: number; total_candidates: number; persistence_mode?: "postgres" | "memory" }>({ active_count: 0, total_candidates: 0 });
  const [loading, setLoading] = useState(true);
  const [isRunningWorkflow, setIsRunningWorkflow] = useState(false);
  const [isPromotingScanner, setIsPromotingScanner] = useState(false);
  const [isPromotingWatchlist, setIsPromotingWatchlist] = useState(false);
  const [workflowResult, setWorkflowResult] = useState<DecisionWorkflowRunResponse | null>(null);
  const [recommendations, setRecommendations] = useState<Array<Record<string, unknown>>>([]);
  const [error, setError] = useState<string | null>(null);

  const loadCandidates = async () => {
    try {
      const response = await api.getCandidateUniverse();
      setCandidates(response.candidates);
      setSummary({
        active_count: response.summary.active_count,
        total_candidates: response.summary.total_candidates,
      });
    } catch (err) {
      setError("Failed to load candidates");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCandidates();
  }, []);

  const handleRemove = async (symbol: string) => {
    try {
      await api.removeCandidate(symbol);
      await loadCandidates();
    } catch (err) {
      setError(`Failed to remove ${symbol}`);
    }
  };

  const handleClearAll = async () => {
    if (!confirm("Are you sure you want to clear all candidates?")) return;
    try {
      await api.clearCandidates();
      await loadCandidates();
    } catch (err) {
      setError("Failed to clear candidates");
    }
  };

  const handleRunWorkflow = async () => {
    setIsRunningWorkflow(true);
    setWorkflowResult(null);
    setError(null);

    try {
      const result = await api.runCandidateUniverseWorkflow();
      setWorkflowResult(result);
      await loadCandidates(); // Refresh to update last_ranked_at
      await loadRecommendations(); // Refresh recommendations
    } catch (err) {
      setError("Failed to run decision workflow");
    } finally {
      setIsRunningWorkflow(false);
    }
  };

  const loadRecommendations = async () => {
    try {
      const response = await api.getRecommendationLifecycle("pending_review", undefined, 20);
      setRecommendations(response);
    } catch (err) {
      // Silent fail - recommendations are optional
    }
  };

  const handlePromoteScanner = async () => {
    setIsPromotingScanner(true);
    setError(null);

    try {
      const result = await api.promoteScannerToCandidates({ min_score: 60, max_candidates: 25 });
      if (result.success) {
        await loadCandidates();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError("Failed to promote scanner results. Run a market scan first.");
    } finally {
      setIsPromotingScanner(false);
    }
  };

  const handlePromoteWatchlist = async () => {
    setIsPromotingWatchlist(true);
    setError(null);

    try {
      // For now, we'll use a default set - in production this would come from user selection
      const result = await api.promoteWatchlistToCandidates({ priority_score: 50 });
      if (result.success) {
        await loadCandidates();
      } else {
        setError(result.message);
      }
    } catch (err) {
      setError("Failed to promote watchlist symbols");
    } finally {
      setIsPromotingWatchlist(false);
    }
  };

  useEffect(() => {
    loadRecommendations();
  }, []);

  const activeCandidates = candidates.filter((c) => c.status === "active");

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="trading intelligence pipeline"
          title="Candidate Universe"
          description="Manage symbols for the decision workflow. Add candidates from Stocks, Watchlist, or Scanner. Run the decision workflow to rank and evaluate them."
        />

        {error && (
          <div className="mb-4 rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-700">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4" />
              {error}
            </div>
          </div>
        )}

        {/* Summary Cards */}
        <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
          <MetricCard label="Total Candidates" value={summary.total_candidates.toString()} accent />
          <MetricCard label="Active" value={summary.active_count.toString()} />
          <MetricCard label="Ready to Rank" value={activeCandidates.length.toString()} />
          <MetricCard
            label="Persistence"
            value={summary.persistence_mode === "postgres" ? "PostgreSQL" : "Memory"}
          />
        </div>

        {/* Action Buttons */}
        <div className="mb-6 flex flex-wrap gap-3">
          <button
            onClick={handleRunWorkflow}
            disabled={isRunningWorkflow || activeCandidates.length === 0}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
              isRunningWorkflow || activeCandidates.length === 0
                ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                : "border border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
            }`}
          >
            {isRunningWorkflow ? (
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

          <button
            onClick={handlePromoteScanner}
            disabled={isPromotingScanner}
            className={`flex items-center gap-2 rounded-xl border border-cyan-500 bg-slate-900 px-4 py-2 text-sm font-bold uppercase text-cyan-400 transition-all ${isPromotingScanner ? "cursor-not-allowed opacity-50" : "hover:bg-cyan-500 hover:text-slate-950"}`}
            title="Promote matched signals from latest scanner run"
          >
            {isPromotingScanner ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
            ) : (
              <ScanLine className="h-4 w-4" />
            )}
            Promote Scanner
          </button>

          <button
            onClick={handlePromoteWatchlist}
            disabled={isPromotingWatchlist}
            className={`flex items-center gap-2 rounded-xl border border-blue-500 bg-slate-900 px-4 py-2 text-sm font-bold uppercase text-blue-400 transition-all ${isPromotingWatchlist ? "cursor-not-allowed opacity-50" : "hover:bg-blue-500 hover:text-slate-950"}`}
            title="Promote symbols from watchlist"
          >
            {isPromotingWatchlist ? (
              <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-400 border-t-transparent" />
            ) : (
              <Radio className="h-4 w-4" />
            )}
            Promote Watchlist
          </button>

          {activeCandidates.length > 0 && (
            <button
              onClick={handleClearAll}
              className="flex items-center gap-2 rounded-xl border border-amber-500 bg-slate-900 px-4 py-2 text-sm font-bold uppercase text-amber-400 transition-all hover:bg-amber-500 hover:text-slate-950"
            >
              <Trash2 className="h-4 w-4" />
              Clear All
            </button>
          )}
        </div>

        {/* Workflow Result */}
        {workflowResult && (
          <section className="mb-6 rounded-xl border border-emerald-500 bg-slate-950 p-4 shadow-sm">
            <div className="flex items-center gap-2">
              {workflowResult.status === "no_symbols_selected" ? (
                <AlertTriangle className="h-5 w-5 text-amber-400" />
              ) : workflowResult.top_action ? (
                <CheckCircle className="h-5 w-5 text-emerald-400" />
              ) : (
                <TrendingUp className="h-5 w-5 text-slate-400" />
              )}
              <h3 className="text-lg font-bold text-white">Decision Workflow Result</h3>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-4 md:grid-cols-4">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Run ID</p>
                <p className="text-sm font-bold text-slate-300">{workflowResult.run_id}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Status</p>
                <p className="text-sm font-bold text-slate-300">{workflowResult.status}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Symbols</p>
                <p className="text-sm font-bold text-slate-300">{workflowResult.symbols_requested.length}</p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-500">Duration</p>
                <p className="text-sm font-bold text-slate-300">{workflowResult.duration_ms}ms</p>
              </div>
            </div>
            {workflowResult.top_action && (
              <div className="mt-4 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
                <p className="text-xs uppercase tracking-wide text-emerald-500">Top Action</p>
                <p className="text-lg font-bold text-white">{workflowResult.top_action.symbol}</p>
                <p className="text-sm text-emerald-300">{workflowResult.top_action.action_label} • Score {workflowResult.top_action.final_score}/100</p>
              </div>
            )}
            {workflowResult.blockers.length > 0 && (
              <div className="mt-3 space-y-1">
                {workflowResult.blockers.map((blocker, idx) => (
                  <p key={idx} className="text-sm text-amber-400">
                    <AlertTriangle className="mr-1 inline h-3 w-3" />
                    {blocker}
                  </p>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Candidates Table */}
        <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-500" />
              <h2 className="text-lg font-semibold text-emerald-500">Active Candidates</h2>
            </div>
            {loading && <span className="text-xs text-slate-400">Loading...</span>}
          </div>

          {activeCandidates.length === 0 ? (
            <div className="rounded-lg border border-slate-800 bg-slate-900 p-8 text-center">
              <p className="text-slate-400">No active candidates</p>
              <p className="mt-2 text-sm text-slate-500">
                Add symbols from the Stocks page or other sources to build your candidate universe.
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800 text-left text-xs uppercase tracking-wide text-slate-500">
                    <th className="pb-3 pl-4">Symbol</th>
                    <th className="pb-3">Source</th>
                    <th className="pb-3">Horizon</th>
                    <th className="pb-3">Priority</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3">Created</th>
                    <th className="pb-3">Last Ranked</th>
                    <th className="pb-3 pr-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="text-sm">
                  {activeCandidates.map((candidate) => (
                    <tr key={candidate.id} className="border-b border-slate-800/50 hover:bg-slate-900/50">
                      <td className="py-3 pl-4 font-bold text-white">{candidate.symbol}</td>
                      <td className="py-3 text-slate-300">
                        <span className="text-xs">{sourceTypeLabel(candidate.source_type)}</span>
                        {candidate.source_detail && (
                          <p className="text-[10px] text-slate-500">{candidate.source_detail}</p>
                        )}
                      </td>
                      <td className="py-3 text-slate-300">{candidate.horizon}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          <div className="h-2 w-16 rounded-full bg-slate-800">
                            <div
                              className="h-2 rounded-full bg-emerald-500"
                              style={{ width: `${candidate.priority_score}%` }}
                            />
                          </div>
                          <span className="text-xs text-slate-400">{candidate.priority_score.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="py-3">{statusBadge(candidate.status)}</td>
                      <td className="py-3 text-xs text-slate-400">{formatDate(candidate.created_at)}</td>
                      <td className="py-3 text-xs text-slate-400">{formatDate(candidate.last_ranked_at)}</td>
                      <td className="py-3 pr-4 text-right">
                        <button
                          onClick={() => handleRemove(candidate.symbol)}
                          className="rounded-lg border border-amber-500/30 p-1.5 text-amber-400 transition-colors hover:bg-amber-500/10"
                          title="Remove from universe"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Pending Recommendations Section */}
        {recommendations.length > 0 && (
          <section className="mt-6 rounded-xl border border-emerald-700 bg-slate-950 p-4 shadow-sm">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-semibold text-emerald-500">Pending Recommendations ({recommendations.length})</h2>
            </div>
            <div className="space-y-3">
              {recommendations.slice(0, 5).map((rec) => (
                <div key={rec.id as string} className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-3">
                  <div>
                    <p className="font-bold text-white">{rec.symbol as string}</p>
                    <p className="text-xs text-slate-400">Score: {rec.score as number}/100 • Confidence: {((rec.confidence as number) * 100).toFixed(0)}%</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={async () => {
                        try {
                          await api.approveRecommendation(rec.id as string);
                          await loadRecommendations();
                        } catch (err) {
                          setError("Failed to approve recommendation");
                        }
                      }}
                      className="rounded-lg border border-emerald-500 px-3 py-1 text-xs font-bold uppercase text-emerald-400 transition-all hover:bg-emerald-500 hover:text-slate-950"
                    >
                      Approve
                    </button>
                    <button
                      onClick={async () => {
                        try {
                          await api.rejectRecommendation(rec.id as string);
                          await loadRecommendations();
                        } catch (err) {
                          setError("Failed to reject recommendation");
                        }
                      }}
                      className="rounded-lg border border-amber-500 px-3 py-1 text-xs font-bold uppercase text-amber-400 transition-all hover:bg-amber-500 hover:text-slate-950"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Notes Section */}
        <section className="mt-6 rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
          <h3 className="mb-2 text-sm font-semibold text-slate-300">How it works</h3>
          <ul className="space-y-1 text-sm text-slate-400">
            <li>• Add symbols to the candidate universe from the Stocks page, Scanner, or Watchlist</li>
            <li>• Click &quot;Run Decision Workflow&quot; to rank candidates using source-backed data and models</li>
            <li>• Candidates are scored on feature quality, model outputs, and risk metrics</li>
            <li>• Only candidates passing all gates become actionable recommendations</li>
            <li>• Promote Scanner: Adds matched signals from latest market scan</li>
            <li>• Promote Watchlist: Adds symbols from your watchlists</li>
          </ul>
        </section>
      </div>
    </div>
  );
}
