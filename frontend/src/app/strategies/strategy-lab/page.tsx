"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type MarketRegimeModelResponse, type StrategyDebateResponse, type StrategyRankingResponse, type ModelSelectionResponse, type StrategyConfig } from "@/lib/api";
import { Play, Brain, TrendingUp, AlertTriangle, CheckCircle, XCircle, Target, Activity, BookOpen, FlaskConical, ShieldAlert, ChevronDown, ChevronUp } from "lucide-react";

function scoreBadge(score: number) {
  if (score >= 70) return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">{score.toFixed(1)}</span>;
  if (score >= 50) return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">{score.toFixed(1)}</span>;
  return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">{score.toFixed(1)}</span>;
}

function regimeBadge(regime: string) {
  const colors: Record<string, string> = {
    risk_on: "border-emerald-500 bg-emerald-500/10 text-emerald-400",
    risk_off: "border-red-500 bg-red-500/10 text-red-400",
    chop: "border-amber-500 bg-amber-500/10 text-amber-400",
    momentum: "border-blue-500 bg-blue-500/10 text-blue-400",
    volatility_expansion: "border-purple-500 bg-purple-500/10 text-purple-400",
    mean_reversion: "border-slate-500 bg-slate-500/10 text-slate-400",
    unknown: "border-slate-600 bg-slate-600/10 text-slate-500",
  };
  const colorClass = colors[regime] || colors.unknown;
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-bold uppercase ${colorClass}`}>{regime.replace(/_/g, " ")}</span>;
}

function StatusBadge({ status, label }: { status: string; label?: string }) {
  const colors: Record<string, string> = {
    active: "border-emerald-500 bg-emerald-500/10 text-emerald-400",
    approved: "border-emerald-500 bg-emerald-500/10 text-emerald-400",
    candidate: "border-amber-500 bg-amber-500/10 text-amber-400",
    paused: "border-slate-500 bg-slate-500/10 text-slate-400",
    rejected: "border-red-500 bg-red-500/10 text-red-400",
  };
  const colorClass = colors[status] || colors.paused;
  return <span className={`rounded-full border px-2 py-0.5 text-xs font-bold uppercase ${colorClass}`}>{label || status}</span>;
}

function StrategyCard({ strategy, onViewPlaybook }: { strategy: StrategyConfig; onViewPlaybook: (key: string) => void }) {
  const isCandidate = strategy.status === "candidate" || strategy.promotion_status === "candidate";
  const isDisabled = strategy.disabled_reason || strategy.status === "rejected";

  return (
    <div className={`rounded-lg border p-3 ${isDisabled ? "border-red-800 bg-red-950/20" : isCandidate ? "border-amber-700 bg-amber-950/20" : "border-slate-700 bg-slate-800/50"}`}>
      <div className="flex items-start justify-between">
        <div>
          <h4 className="font-bold text-white">{strategy.display_name}</h4>
          <p className="text-xs text-slate-400">{strategy.strategy_key}</p>
        </div>
        <StatusBadge status={strategy.status || "approved"} label={isCandidate ? "Research" : strategy.status} />
      </div>
      <p className="mt-2 text-xs text-slate-300 line-clamp-2">{strategy.description}</p>
      <div className="mt-3 flex flex-wrap gap-1">
        <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-300">{strategy.asset_class}</span>
        <span className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-300">{strategy.timeframe}</span>
        {isCandidate && (
          <span className="rounded bg-amber-900/50 px-1.5 py-0.5 text-xs text-amber-300">Requires backtest</span>
        )}
        {strategy.paper_research_only && (
          <span className="rounded bg-amber-900/50 px-1.5 py-0.5 text-xs text-amber-300">Paper only</span>
        )}
        {!strategy.live_trading_supported && (
          <span className="rounded bg-red-900/50 px-1.5 py-0.5 text-xs text-red-300">Live disabled</span>
        )}
      </div>
      {strategy.disabled_reason && (
        <p className="mt-2 text-xs text-red-400">{strategy.disabled_reason}</p>
      )}
      {strategy.risk_notes && strategy.risk_notes.length > 0 && (
        <div className="mt-2 text-xs text-amber-400">
          Risk: {strategy.risk_notes.slice(0, 2).join(", ")}
        </div>
      )}
      <button
        onClick={() => onViewPlaybook(strategy.strategy_key)}
        className="mt-3 flex items-center gap-1 text-xs text-sky-400 hover:text-sky-300"
      >
        <BookOpen className="h-3 w-3" /> View Playbook
      </button>
    </div>
  );
}

function PlaybookPanel({ strategyKey, onClose }: { strategyKey: string; onClose: () => void }) {
  const [playbook, setPlaybook] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getStrategyPlaybook(strategyKey).then((data) => {
      setPlaybook(data);
      setLoading(false);
    });
  }, [strategyKey]);

  if (loading) return <div className="p-4 text-sm text-slate-400">Loading playbook...</div>;
  if (!playbook) return null;

  // Type guard for playbook properties
  const pb = playbook as Record<string, unknown>;
  const displayName = pb.display_name as string | undefined;

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="font-bold text-white">{displayName || "Unknown"} Playbook</h4>
        <button onClick={onClose} className="text-xs text-slate-400 hover:text-white">Close</button>
      </div>

      <div className="space-y-3">
        {!!pb.claim_source && (
          <div>
            <span className="text-xs text-slate-500">Source</span>
            <p className="text-xs text-slate-300">{pb.claim_source as string}</p>
          </div>
        )}

        {(pb.best_regimes as string[])?.length > 0 && (
          <div>
            <span className="text-xs text-slate-500">Best Regimes</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {(pb.best_regimes as string[]).map((r) => (
                <span key={r} className="rounded bg-emerald-900/30 px-1.5 py-0.5 text-xs text-emerald-400">{r}</span>
              ))}
            </div>
          </div>
        )}

        {(pb.bad_regimes as string[])?.length > 0 && (
          <div>
            <span className="text-xs text-slate-500">Avoid In</span>
            <div className="mt-1 flex flex-wrap gap-1">
              {(pb.bad_regimes as string[]).map((r) => (
                <span key={r} className="rounded bg-red-900/30 px-1.5 py-0.5 text-xs text-red-400">{r}</span>
              ))}
            </div>
          </div>
        )}

        {(pb.trigger_rules as string[])?.length > 0 && (
          <div>
            <span className="text-xs text-slate-500">Trigger Rules</span>
            <ul className="mt-1 list-inside list-disc text-xs text-slate-300">
              {(pb.trigger_rules as string[]).slice(0, 5).map((rule, i) => (
                <li key={i}>{rule}</li>
              ))}
            </ul>
          </div>
        )}

        {(pb.risk_notes as string[])?.length > 0 && (
          <div>
            <span className="text-xs text-slate-500">Risk Notes</span>
            <ul className="mt-1 list-inside list-disc text-xs text-amber-400">
              {(pb.risk_notes as string[]).map((note, i) => (
                <li key={i}>{note}</li>
              ))}
            </ul>
          </div>
        )}

        {(pb.promotion_requirements as string[])?.length > 0 && (
          <div>
            <span className="text-xs text-slate-500">Promotion Requirements</span>
            <ul className="mt-1 list-inside list-disc text-xs text-slate-300">
              {(pb.promotion_requirements as string[]).map((req, i) => (
                <li key={i}>{req}</li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-4 rounded bg-slate-800/50 p-2 text-xs text-slate-400">
          <span className="font-medium text-slate-300">Required Data: </span>
          {(pb.required_data_sources as string[])?.join(", ") || "None specified"}
        </div>
      </div>
    </div>
  );
}

export default function StrategyLabPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [regime, setRegime] = useState<MarketRegimeModelResponse | null>(null);
  const [debate, setDebate] = useState<StrategyDebateResponse | null>(null);
  const [ranking, setRanking] = useState<StrategyRankingResponse | null>(null);
  const [modelSelection, setModelSelection] = useState<ModelSelectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStrategies, setActiveStrategies] = useState<StrategyConfig[]>([]);
  const [candidateStrategies, setCandidateStrategies] = useState<StrategyConfig[]>([]);
  const [allStrategies, setAllStrategies] = useState<StrategyConfig[]>([]);
  const [selectedPlaybook, setSelectedPlaybook] = useState<string | null>(null);
  const [registryTab, setRegistryTab] = useState<"active" | "candidate" | "disabled">("active");

  const loadLatest = async () => {
    try {
      const [regimeRes, rankingRes, modelRes, activeRes, candidateRes, allRes] = await Promise.all([
        api.getLatestMarketRegime(),
        api.getLatestStrategyRanking(),
        api.getLatestModelSelection(),
        api.getActiveStrategies(),
        api.getCandidateStrategies(),
        api.getStrategies(),
      ]);
      if (!("status" in regimeRes && regimeRes.status === "not_found")) {
        setRegime(regimeRes as MarketRegimeModelResponse);
      }
      if (!("status" in rankingRes && rankingRes.status === "not_found")) {
        setRanking(rankingRes as StrategyRankingResponse);
      }
      if (!("status" in modelRes && modelRes.status === "not_found")) {
        setModelSelection(modelRes as ModelSelectionResponse);
      }
      setActiveStrategies(activeRes);
      setCandidateStrategies(candidateRes);
      setAllStrategies(allRes);
    } catch {
      // Ignore errors
    }
  };

  useEffect(() => {
    loadLatest();
  }, []);

  const handleRunAnalysis = async () => {
    setIsRunning(true);
    setError(null);

    try {
      // Get runtime cadence first
      const cadence = await api.getRuntimeCadence();
      const marketPhase = cadence.market_phase;
      const activeLoop = cadence.active_loop;

      // Run regime detection
      const regimeRes = await api.runMarketRegime({ horizon: "swing", allow_mock: false });
      setRegime(regimeRes);

      // Run strategy ranking (includes debate)
      const rankingRes = await api.runStrategyRanking({
        market_phase: marketPhase,
        active_loop: activeLoop,
        regime: regimeRes.regime,
        horizon: "swing",
      });
      setRanking(rankingRes);

      // Run model selection for top strategy
      if (rankingRes.top_strategy_key) {
        const modelRes = await api.runModelSelection({
          strategy_key: rankingRes.top_strategy_key,
          market_phase: marketPhase,
          active_loop: activeLoop,
          regime: regimeRes.regime,
          horizon: "swing",
          llm_budget_mode: "disabled",
        });
        setModelSelection(modelRes);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl p-4 lg:p-8">
      <PageHeader
        eyebrow="workflow step 3-7"
        title="Strategy Lab"
        description="Market Regime, Strategy Debate, Strategy Ranking, and Model Selection. No LLMs. Deterministic analysis only."
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertTriangle className="mr-2 inline h-4 w-4" />
          {error}
        </div>
      )}

      <div className="mb-6 flex gap-3">
        <button
          onClick={handleRunAnalysis}
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
              Run Strategy Analysis
            </>
          )}
        </button>
      </div>

      {/* Market Regime */}
      {regime && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <TrendingUp className="h-4 w-4" />
            Market Regime (Step 4)
          </h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <span className="text-xs text-slate-500">Regime</span>
              <div className="mt-1">{regimeBadge(regime.regime)}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Confidence</span>
              <div className="text-lg font-bold text-slate-200">{(regime.confidence * 100).toFixed(0)}%</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Trend State</span>
              <div className="text-sm font-medium text-slate-300">{regime.trend_state}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Volatility</span>
              <div className="text-sm font-medium text-slate-300">{regime.volatility_state}</div>
            </div>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            <span className="text-xs text-slate-500">Allowed:</span>
            {regime.allowed_strategy_families.map(s => (
              <span key={s} className="rounded bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">{s}</span>
            ))}
          </div>
        </div>
      )}

      {/* Strategy Ranking */}
      {ranking && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <Brain className="h-4 w-4" />
            Strategy Ranking (Steps 5-6)
          </h3>
          <div className="mb-3">
            <span className="text-xs text-slate-500">Top Strategy</span>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-emerald-400">{ranking.top_strategy_key || "None"}</span>
              {ranking.top_strategy_key && scoreBadge(ranking.ranked_strategies.find(r => r.strategy_key === ranking.top_strategy_key)?.strategy_score || 0)}
            </div>
          </div>
          <div className="grid gap-2">
            {ranking.ranked_strategies.slice(0, 5).map(s => (
              <div key={s.strategy_key} className="flex items-center justify-between rounded-lg bg-slate-800/50 p-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-slate-500">#{s.rank}</span>
                  <span className="font-medium text-slate-300">{s.strategy_key}</span>
                  <span className={`text-xs ${s.status === "active" ? "text-emerald-400" : s.status === "disabled" ? "text-red-400" : "text-amber-400"}`}>
                    {s.status}
                  </span>
                </div>
                {scoreBadge(s.strategy_score)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Model Selection */}
      {modelSelection && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <Target className="h-4 w-4" />
            Model Selection (Step 7)
          </h3>
          <div className="mb-3">
            <span className="text-xs text-slate-500">Strategy</span>
            <div className="text-lg font-bold text-slate-200">{modelSelection.strategy_key}</div>
          </div>
          <div className="mb-3">
            <span className="text-xs text-slate-500">Selected Models</span>
            <div className="mt-1 flex flex-wrap gap-2">
              {modelSelection.selected_scanner_models.map(m => (
                <span key={m.model_key} className="rounded bg-slate-700 px-2 py-1 text-xs text-slate-300">{m.model_name}</span>
              ))}
              {modelSelection.selected_scoring_models.map(m => (
                <span key={m.model_key} className="rounded bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">{m.model_name}</span>
              ))}
            </div>
          </div>
          {modelSelection.skipped_models.length > 0 && (
            <div>
              <span className="text-xs text-slate-500">Skipped</span>
              <div className="mt-1 flex flex-wrap gap-2 opacity-60">
                {modelSelection.skipped_models.slice(0, 3).map(m => (
                  <span key={m.model_key} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-500">{m.model_name}: {m.skip_reason}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {!regime && !isRunning && (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center">
          <Brain className="mx-auto mb-3 h-12 w-12 text-slate-600" />
          <p className="text-slate-400">No strategy analysis yet.</p>
          <p className="mt-1 text-sm text-slate-500">Click &quot;Run Strategy Analysis&quot; to detect regime, debate strategies, and select models.</p>
        </div>
      )}

      {/* Strategy Registry Section */}
      <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
        <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
          <FlaskConical className="h-4 w-4" />
          Strategy Registry
        </h3>

        {/* Summary Stats */}
        <div className="mb-4 grid grid-cols-3 gap-3">
          <MetricCard
            label="Active / Approved"
            value={activeStrategies.length}
            accent
          />
          <MetricCard
            label="Candidate / Research"
            value={candidateStrategies.length}
          />
          <MetricCard
            label="Disabled / Blocked"
            value={allStrategies.filter(s => s.disabled_reason || s.status === "rejected").length}
          />
        </div>

        {/* Tabs */}
        <div className="mb-4 flex gap-2">
          <button
            onClick={() => setRegistryTab("active")}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase transition-colors ${
              registryTab === "active"
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500"
                : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700"
            }`}
          >
            Active / Approved
          </button>
          <button
            onClick={() => setRegistryTab("candidate")}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase transition-colors ${
              registryTab === "candidate"
                ? "bg-amber-500/20 text-amber-400 border border-amber-500"
                : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700"
            }`}
          >
            Candidate / Research
          </button>
          <button
            onClick={() => setRegistryTab("disabled")}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase transition-colors ${
              registryTab === "disabled"
                ? "bg-red-500/20 text-red-400 border border-red-500"
                : "bg-slate-800 text-slate-400 border border-slate-700 hover:bg-slate-700"
            }`}
          >
            Disabled / Blocked
          </button>
        </div>

        {/* Playbook Panel */}
        {selectedPlaybook && (
          <div className="mb-4">
            <PlaybookPanel
              strategyKey={selectedPlaybook}
              onClose={() => setSelectedPlaybook(null)}
            />
          </div>
        )}

        {/* Strategy Cards */}
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {registryTab === "active" && activeStrategies.map((strategy) => (
            <StrategyCard
              key={strategy.strategy_key}
              strategy={strategy}
              onViewPlaybook={setSelectedPlaybook}
            />
          ))}
          {registryTab === "candidate" && candidateStrategies.map((strategy) => (
            <StrategyCard
              key={strategy.strategy_key}
              strategy={strategy}
              onViewPlaybook={setSelectedPlaybook}
            />
          ))}
          {registryTab === "disabled" && allStrategies
            .filter(s => s.disabled_reason || s.status === "rejected")
            .map((strategy) => (
              <StrategyCard
                key={strategy.strategy_key}
                strategy={strategy}
                onViewPlaybook={setSelectedPlaybook}
              />
            ))}
        </div>

        {registryTab === "active" && activeStrategies.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/30 p-6 text-center">
            <p className="text-sm text-slate-400">No active strategies found.</p>
          </div>
        )}
        {registryTab === "candidate" && candidateStrategies.length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/30 p-6 text-center">
            <p className="text-sm text-slate-400">No candidate strategies found.</p>
          </div>
        )}
        {registryTab === "disabled" && allStrategies.filter(s => s.disabled_reason || s.status === "rejected").length === 0 && (
          <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/30 p-6 text-center">
            <p className="text-sm text-slate-400">No disabled strategies found.</p>
          </div>
        )}

        {/* Legend */}
        <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-400">
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-emerald-500" /> Active
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-amber-500" /> Research Only
          </span>
          <span className="flex items-center gap-1">
            <span className="h-2 w-2 rounded-full bg-red-500" /> Disabled
          </span>
          <span className="flex items-center gap-1">
            <ShieldAlert className="h-3 w-3 text-amber-400" /> Requires Backtest
          </span>
        </div>
      </div>
    </div>
  );
}
