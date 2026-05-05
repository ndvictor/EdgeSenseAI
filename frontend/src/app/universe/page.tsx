"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type UpperWorkflowResponse, type UniverseDiscoverResponse, type UniverseDiscoveryCandidate, type UniverseSelectionCandidate, type CadencePlan, type TriggerRule } from "@/lib/api";
import { Play, Globe, Target, ListFilter, TrendingUp, AlertTriangle, CheckCircle, XCircle, Clock, ArrowRight, Radar, Activity, Zap } from "lucide-react";
import Link from "next/link";

function formatDate(dateStr: string | null | undefined) {
  if (!dateStr) return "—";
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return "—";
  }
}

function scoreBadge(score: number) {
  if (score >= 70) return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">{score.toFixed(1)}</span>;
  if (score >= 50) return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">{score.toFixed(1)}</span>;
  return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">{score.toFixed(1)}</span>;
}

function directionBadge(direction: string) {
  switch (direction) {
    case "long":
      return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">Long</span>;
    case "short":
      return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">Short</span>;
    default:
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">Neutral</span>;
  }
}

function phaseBadge(phase: string) {
  const phaseColors: Record<string, string> = {
    market_closed: "border-slate-500 bg-slate-500/10 text-slate-400",
    pre_market: "border-amber-500 bg-amber-500/10 text-amber-400",
    market_open_first_30_min: "border-emerald-500 bg-emerald-500/10 text-emerald-400",
    market_open: "border-emerald-500 bg-emerald-500/10 text-emerald-400",
    midday: "border-blue-500 bg-blue-500/10 text-blue-400",
    power_hour: "border-purple-500 bg-purple-500/10 text-purple-400",
    after_hours: "border-slate-500 bg-slate-500/10 text-slate-400",
  };
  const colorClass = phaseColors[phase] || phaseColors.market_closed;
  const display = phase.replace(/_/g, " ");
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-bold uppercase ${colorClass}`}>{display}</span>;
}

export default function UniversePage() {
  const [symbolsInput, setSymbolsInput] = useState("");
  const [assetClass, setAssetClass] = useState<"stock" | "option" | "crypto">("stock");
  const [horizon, setHorizon] = useState<"day_trade" | "swing" | "one_month">("swing");
  const [source, setSource] = useState<"auto" | "yfinance" | "alpaca" | "polygon" | "mock">("auto");
  const [minScore, setMinScore] = useState(50);
  const [maxCandidates, setMaxCandidates] = useState(25);
  const [includeMock, setIncludeMock] = useState(false);
  const [promoteToCandidates, setPromoteToCandidates] = useState(false);

  // Extended workflow options
  const [buildTriggerRules, setBuildTriggerRules] = useState(true);
  const [runEventScanner, setRunEventScanner] = useState(false);
  const [runSignalScoring, setRunSignalScoring] = useState(false);
  const [runMetaModel, setRunMetaModel] = useState(false);

  const [isRunning, setIsRunning] = useState(false);
  const [isPromoting, setIsPromoting] = useState(false);
  const [latestRun, setLatestRun] = useState<UpperWorkflowResponse | null>(null);
  const [latestDiscovery, setLatestDiscovery] = useState<UniverseDiscoverResponse | null>(null);
  const [isDiscovering, setIsDiscovering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Discovery Mode
  const [discoveryGroups, setDiscoveryGroups] = useState<Record<string, boolean>>({
    premarket_gap_momentum: false,
    opening_range_breakout_group: true,
    high_rvol_momentum_group: true,
    vwap_reclaim_group: true,
    breakout_retest_group: false,
    relative_strength_rotation_group: true,
    mean_reversion_range_group: false,
    etf_stock_lag_group: false,
    earnings_news_drift_group: false,
    low_float_breakout_group: false,
  });

  const loadLatestRun = async () => {
    try {
      const response = await api.getLatestUpperWorkflow();
      if ("status" in response && response.status === "not_found") {
        setLatestRun(null);
      } else {
        setLatestRun(response as UpperWorkflowResponse);
      }
    } catch {
      setLatestRun(null);
    }
  };

  useEffect(() => {
    loadLatestRun();
  }, []);

  const handleRunSelection = async () => {
    setIsRunning(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const symbols = symbolsInput
        .split(/[\n,]+/)
        .map((s) => s.trim().toUpperCase())
        .filter((s) => s.length > 0);

      if (symbols.length === 0) {
        setError("Please enter at least one symbol");
        setIsRunning(false);
        return;
      }

      // Use Upper Workflow API with extended options
      const response = await api.runUpperWorkflow({
        symbols,
        asset_class: assetClass,
        horizon,
        source,
        allow_mock: includeMock,
        promote_to_candidate_universe: promoteToCandidates,
        build_trigger_rules: buildTriggerRules,
        run_event_scanner: runEventScanner,
        run_signal_scoring: runSignalScoring,
        run_meta_model: runMetaModel,
      });

      setLatestRun(response);

      // Build success message
      let msg = `Workflow completed: ${response.universe_selection?.selected_watchlist?.length || 0} candidates selected`;
      if (response.trigger_rules?.rules?.length) {
        msg += `, ${response.trigger_rules.rules.length} trigger rules built`;
      }
      if (response.event_scanner?.matched_events?.length) {
        msg += `, ${response.event_scanner.matched_events.length} events detected`;
      }
      if (response.signal_scoring?.scored_signals?.length) {
        msg += `, ${response.signal_scoring.scored_signals.length} signals scored`;
      }
      if (response.meta_model_ensemble?.ensemble_signals?.length) {
        msg += `, ${response.meta_model_ensemble.passed_signals.length} passed meta-model`;
      }

      setSuccessMessage(msg);
      setSymbolsInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run workflow");
    } finally {
      setIsRunning(false);
    }
  };

  const handleRunDiscovery = async () => {
    setIsDiscovering(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const symbols = symbolsInput
        .split(/[\n,]+/)
        .map((s) => s.trim().toUpperCase())
        .filter((s) => s.length > 0);

      if (symbols.length === 0) {
        setError("Please enter at least one symbol");
        setIsDiscovering(false);
        return;
      }

      const groups = Object.entries(discoveryGroups)
        .filter(([, enabled]) => enabled)
        .map(([key]) => key);

      const response = await api.runUniverseDiscovery({
        symbols,
        asset_class: assetClass,
        horizon,
        market_phase: "auto",
        scanner_groups: groups,
        source,
        allow_mock: includeMock,
        small_account_mode: true,
        promote_to_candidate_universe: false,
      });

      setLatestDiscovery(response);
      setSuccessMessage(
        `Discovery ${response.status}: ${response.selected_watchlist.length} selected, ${response.rejected_candidates.length} rejected, ${response.research_only_candidates.length} research-only`
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run universe discovery");
    } finally {
      setIsDiscovering(false);
    }
  };

  const handlePromoteToCandidates = async () => {
    if (!latestRun) return;

    setIsPromoting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // If meta-model was run, use that to promote passing signals
      let response;
      if (latestRun.meta_model_ensemble?.ensemble_signals?.length) {
        response = await api.promotePassingSignalsToCandidates(false, 60);
      } else {
        // Fall back to promoting from universe selection
        response = await api.promoteLatestUniverseSelectionToCandidates();
      }

      if (response.success) {
        setSuccessMessage(`Promoted ${response.promoted_count} symbol(s) to Candidate Universe`);
      } else {
        setError("Failed to promote candidates");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to promote to candidates");
    } finally {
      setIsPromoting(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl p-4 lg:p-8">
      <PageHeader
        eyebrow="workflow starting point"
        title="Universe Selection"
        description="Preselect and rank symbols worth monitoring. This is the STARTING POINT of the workflow - Candidate Universe is downstream. No LLMs. No hardcoded defaults."
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" />
            {error}
          </div>
        </div>
      )}

      {successMessage && (
        <div className="mb-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-4 w-4" />
            {successMessage}
          </div>
        </div>
      )}

      {/* Current Market Phase */}
      {latestRun && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <span className="text-xs font-bold uppercase text-slate-500">Market Phase</span>
              <div className="mt-1">{phaseBadge(latestRun.market_phase)}</div>
            </div>
            <div>
              <span className="text-xs font-bold uppercase text-slate-500">Active Loop</span>
              <div className="mt-1 text-sm font-medium text-slate-200">{latestRun.active_loop.replace(/_/g, " ")}</div>
            </div>
            <div>
              <span className="text-xs font-bold uppercase text-slate-500">Workflow Status</span>
              <div className="mt-1 text-sm font-medium text-slate-200">{latestRun.status}</div>
            </div>
            <div>
              <span className="text-xs font-bold uppercase text-slate-500">Stages</span>
              <div className="mt-1 text-sm font-medium text-slate-200">{latestRun.stages.filter(s => s.status === "completed").length}/{latestRun.stages.length}</div>
            </div>
          </div>
        </div>
      )}

      {/* Input Form */}
      <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
        <h3 className="mb-4 text-sm font-bold uppercase text-slate-300">Run Universe Selection</h3>

        <div className="mb-4">
          <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Symbols (comma or newline separated)</label>
          <textarea
            value={symbolsInput}
            onChange={(e) => setSymbolsInput(e.target.value)}
            placeholder="Enter symbols (e.g., TSLA, META, PLTR)..."
            className="h-24 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 placeholder:text-slate-600 focus:border-sky-500 focus:outline-none"
          />
          <p className="mt-1 text-xs text-slate-500">No default stock universe. You must explicitly provide symbols.</p>
        </div>

        <div className="mb-4 grid grid-cols-2 gap-4 md:grid-cols-4">
          <div>
            <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Horizon</label>
            <select
              value={horizon}
              onChange={(e) => setHorizon(e.target.value as any)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              <option value="day_trade">Day Trade</option>
              <option value="swing">Swing</option>
              <option value="one_month">One Month</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Data Source</label>
            <select
              value={source}
              onChange={(e) => setSource(e.target.value as any)}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
            >
              <option value="auto">Auto</option>
              <option value="yfinance">YFinance</option>
              <option value="alpaca">Alpaca</option>
              <option value="polygon">Polygon</option>
              <option value="mock">Mock (Explicit)</option>
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Min Score</label>
            <input
              type="number"
              min={0}
              max={100}
              value={minScore}
              onChange={(e) => setMinScore(parseInt(e.target.value))}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-bold uppercase text-slate-500">Max Candidates</label>
            <input
              type="number"
              min={1}
              max={100}
              value={maxCandidates}
              onChange={(e) => setMaxCandidates(parseInt(e.target.value))}
              className="w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 focus:border-sky-500 focus:outline-none"
            />
          </div>
        </div>

        <div className="mb-4 flex flex-wrap gap-4">
          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={includeMock}
              onChange={(e) => setIncludeMock(e.target.checked)}
              className="rounded border-slate-600 bg-slate-700 text-sky-500"
            />
            Include Mock Data (Explicit Opt-in)
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={promoteToCandidates}
              onChange={(e) => setPromoteToCandidates(e.target.checked)}
              className="rounded border-slate-600 bg-slate-700 text-sky-500"
            />
            Auto-promote to Candidate Universe
          </label>
        </div>

        <div className="flex flex-wrap gap-3">
          <button
            onClick={handleRunSelection}
            disabled={isRunning}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
              isRunning
                ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                : "border border-sky-500 bg-slate-900 text-sky-400 hover:bg-sky-500 hover:text-slate-950"
            }`}
          >
            {isRunning ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
                Running...
              </>
            ) : (
              <>
                <Play className="h-4 w-4" />
                Run Universe Selection
              </>
            )}
          </button>

          {latestRun && (
            <button
              onClick={handlePromoteToCandidates}
              disabled={isPromoting || (latestRun.universe_selection?.selected_watchlist?.length || 0) === 0}
              className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
                isPromoting || (latestRun.universe_selection?.selected_watchlist?.length || 0) === 0
                  ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                  : "border border-emerald-500 bg-slate-900 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
              }`}
            >
              {isPromoting ? (
                <>
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
                  Promoting...
                </>
              ) : (
                <>
                  <ArrowRight className="h-4 w-4" />
                  Promote to Candidates ({latestRun.universe_selection?.selected_watchlist?.length || 0})
                </>
              )}
            </button>
          )}

          <Link
            href="/candidates"
            className="flex items-center gap-2 rounded-xl border border-slate-600 bg-slate-900 px-4 py-2 text-sm font-bold uppercase text-slate-400 transition-all hover:border-slate-500 hover:text-slate-300"
          >
            <Target className="h-4 w-4" />
            View Candidates
          </Link>
        </div>
      </div>

      {/* Discovery Mode */}
      <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
        <h3 className="mb-2 text-sm font-bold uppercase text-slate-300">Discovery Mode (new)</h3>
        <p className="mb-4 text-sm text-slate-400">
          Generates strategy-mapped watchlist candidates with TTL and trigger rules. Discovery is always watchlist-only (execution is blocked by design).
        </p>

        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {[
            ["premarket_gap_momentum", "Pre-market Gap Momentum"],
            ["opening_range_breakout_group", "Opening Range Breakout"],
            ["high_rvol_momentum_group", "High RVOL Momentum"],
            ["vwap_reclaim_group", "VWAP Reclaim"],
            ["breakout_retest_group", "Breakout Retest"],
            ["relative_strength_rotation_group", "Relative Strength Rotation"],
            ["mean_reversion_range_group", "Mean Reversion Range"],
            ["etf_stock_lag_group", "ETF/Stock Lag"],
            ["earnings_news_drift_group", "Earnings/News Drift"],
            ["low_float_breakout_group", "Low Float Breakout (research-only)"],
          ].map(([key, label]) => (
            <label key={key} className="flex items-center gap-3 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-200">
              <input
                type="checkbox"
                checked={Boolean(discoveryGroups[key])}
                onChange={(e) => setDiscoveryGroups((prev) => ({ ...prev, [key]: e.target.checked }))}
              />
              <span>{label}</span>
            </label>
          ))}
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={handleRunDiscovery}
            disabled={isDiscovering}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-bold uppercase transition-all ${
              isDiscovering
                ? "cursor-not-allowed border border-slate-600 bg-slate-800 text-slate-500"
                : "border border-sky-400/40 bg-sky-500/10 text-sky-300 hover:bg-sky-500 hover:text-slate-950"
            }`}
          >
            {isDiscovering ? (
              <>
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-sky-400 border-t-transparent" />
                Discovering...
              </>
            ) : (
              <>
                <Radar className="h-4 w-4" />
                Run Universe Discovery
              </>
            )}
          </button>
          <span className="text-xs text-slate-500">API: /api/universe/discover</span>
        </div>

        {latestDiscovery && (
          <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-2 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="text-xs font-bold uppercase text-slate-500">Discovery</span>
                {phaseBadge(latestDiscovery.market_phase)}
                <span className="text-xs text-slate-400">{latestDiscovery.status}</span>
              </div>
              <span className="text-xs text-slate-500">Created {formatDate(latestDiscovery.created_at)}</span>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <MetricCard label="Selected" value={latestDiscovery.selected_watchlist.length} accent />
              <MetricCard label="Rejected" value={latestDiscovery.rejected_candidates.length} />
              <MetricCard label="Research-only" value={latestDiscovery.research_only_candidates.length} />
            </div>

            {latestDiscovery.selected_watchlist.length > 0 && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th className="py-2 pr-3">Symbol</th>
                      <th className="py-2 pr-3">Group</th>
                      <th className="py-2 pr-3">Strategy</th>
                      <th className="py-2 pr-3">Score</th>
                      <th className="py-2 pr-3">TTL</th>
                      <th className="py-2 pr-3">Execution</th>
                    </tr>
                  </thead>
                  <tbody className="text-slate-200">
                    {latestDiscovery.selected_watchlist.slice(0, 12).map((c: UniverseDiscoveryCandidate) => (
                      <tr key={`${c.symbol}-${c.scanner_group}`} className="border-t border-slate-800">
                        <td className="py-2 pr-3 font-semibold">{c.symbol}</td>
                        <td className="py-2 pr-3 text-slate-400">{c.scanner_group.replace(/_/g, " ")}</td>
                        <td className="py-2 pr-3 text-slate-300">{c.strategy_key}</td>
                        <td className="py-2 pr-3">{scoreBadge(c.universe_score)}</td>
                        <td className="py-2 pr-3 text-slate-400">{c.watchlist_ttl_minutes}m</td>
                        <td className="py-2 pr-3 text-rose-300">blocked</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="mt-2 text-xs text-slate-500">Showing top 12 selected. Triggers and invalidations are included in the API payload for each candidate.</p>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Latest Run Results */}
      {latestRun && (
        <>
          {/* Summary */}
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <MetricCard label="Requested" value={latestRun.universe_selection?.requested_symbols?.length?.toString() || "0"} accent />
            <MetricCard label="Ranked" value={latestRun.universe_selection?.ranked_candidates?.length?.toString() || "0"} />
            <MetricCard label="Selected" value={latestRun.universe_selection?.selected_watchlist?.length?.toString() || "0"} />
            <MetricCard label="Rejected" value={latestRun.universe_selection?.rejected_candidates?.length?.toString() || "0"} />
          </div>

          {/* Blockers & Warnings */}
          {(latestRun.blockers.length > 0 || latestRun.warnings.length > 0) && (
            <div className="mb-6 space-y-2">
              {latestRun.blockers.map((blocker, i) => (
                <div key={`blocker-${i}`} className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-2 text-sm text-red-400">
                  <div className="flex items-center gap-2">
                    <XCircle className="h-4 w-4" />
                    {blocker}
                  </div>
                </div>
              ))}
              {latestRun.warnings.map((warning, i) => (
                <div key={`warning-${i}`} className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-2 text-sm text-amber-400">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4" />
                    {warning}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Selected Watchlist */}
          {(latestRun.universe_selection?.selected_watchlist?.length || 0) > 0 && (
            <div className="mb-6">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-emerald-400">
                <CheckCircle className="h-4 w-4" />
                Selected Watchlist ({latestRun.universe_selection?.selected_watchlist?.length || 0})
              </h3>
              <div className="grid gap-3">
                {latestRun.universe_selection?.selected_watchlist?.map((candidate: UniverseSelectionCandidate) => (
                  <CandidateCard key={candidate.symbol} candidate={candidate} />
                ))}
              </div>
            </div>
          )}

          {/* Rejected Candidates */}
          {(latestRun.universe_selection?.rejected_candidates?.length || 0) > 0 && (
            <div className="mb-6">
              <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-slate-500">
                <XCircle className="h-4 w-4" />
                Rejected Candidates ({latestRun.universe_selection?.rejected_candidates?.length || 0})
              </h3>
              <div className="grid gap-3 opacity-60">
                {latestRun.universe_selection?.rejected_candidates?.slice(0, 5).map((candidate: UniverseSelectionCandidate) => (
                  <CandidateCard key={candidate.symbol} candidate={candidate} rejected />
                ))}
                {(latestRun.universe_selection?.rejected_candidates?.length || 0) > 5 && (
                  <p className="text-center text-xs text-slate-500">
                    +{(latestRun.universe_selection?.rejected_candidates?.length || 0) - 5} more rejected
                  </p>
                )}
              </div>
            </div>
          )}
        </>
      )}

      {/* Empty State */}
      {!latestRun && !isRunning && (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center">
          <Globe className="mx-auto mb-3 h-12 w-12 text-slate-600" />
          <p className="text-slate-400">No universe selection run yet.</p>
          <p className="mt-1 text-sm text-slate-500">Enter symbols above and run universe selection to create your watchlist.</p>
        </div>
      )}
    </div>
  );
}

function CandidateCard({ candidate, rejected = false }: { candidate: UniverseSelectionCandidate; rejected?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${rejected ? "border-slate-800 bg-slate-900/30" : "border-slate-700 bg-slate-900/50"}`}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-slate-800 font-bold text-slate-300">
            {candidate.symbol}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-200">{candidate.symbol}</span>
              {scoreBadge(candidate.universe_score)}
              {directionBadge(candidate.expected_direction)}
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
              <span className="flex items-center gap-1">
                <TrendingUp className="h-3 w-3" />
                Trend: {candidate.trend_score.toFixed(1)}
              </span>
              <span className="flex items-center gap-1">
                <ListFilter className="h-3 w-3" />
                Liquidity: {candidate.liquidity_score.toFixed(1)}
              </span>
              <span className="flex items-center gap-1">
                <Target className="h-3 w-3" />
                Vol Fit: {candidate.volatility_fit.toFixed(1)}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                TTL: {candidate.watchlist_ttl_minutes}m
              </span>
            </div>
          </div>
        </div>

        <div className="text-right">
          <div className="text-xs text-slate-500">Strategy</div>
          <div className="text-sm font-medium text-slate-300">{candidate.assigned_strategy}</div>
        </div>
      </div>

      {candidate.reasons.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-2">
          {candidate.reasons.map((reason, i) => (
            <span key={i} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-400">
              {reason}
            </span>
          ))}
        </div>
      )}

      {candidate.blockers.length > 0 && (
        <div className="mt-3 space-y-1">
          {candidate.blockers.map((blocker, i) => (
            <div key={i} className="flex items-center gap-1 text-xs text-red-400">
              <XCircle className="h-3 w-3" />
              {blocker}
            </div>
          ))}
        </div>
      )}

      <div className="mt-3 text-xs text-slate-600">
        <span className="font-medium">Trigger:</span> {candidate.trigger_condition}
      </div>
    </div>
  );
}
