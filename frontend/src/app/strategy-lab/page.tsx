"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type MarketRegimeModelResponse, type StrategyDebateResponse, type StrategyRankingResponse, type ModelSelectionResponse } from "@/lib/api";
import { Play, Brain, TrendingUp, AlertTriangle, CheckCircle, XCircle, Target, Activity } from "lucide-react";

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

export default function StrategyLabPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [regime, setRegime] = useState<MarketRegimeModelResponse | null>(null);
  const [debate, setDebate] = useState<StrategyDebateResponse | null>(null);
  const [ranking, setRanking] = useState<StrategyRankingResponse | null>(null);
  const [modelSelection, setModelSelection] = useState<ModelSelectionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLatest = async () => {
    try {
      const [regimeRes, rankingRes, modelRes] = await Promise.all([
        api.getLatestMarketRegime(),
        api.getLatestStrategyRanking(),
        api.getLatestModelSelection(),
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
    <div className="mx-auto max-w-6xl p-6">
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
    </div>
  );
}
