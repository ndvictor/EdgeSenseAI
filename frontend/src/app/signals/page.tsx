"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type EventScannerResponse, type SignalScoringResponse, type MetaModelEnsembleResponse } from "@/lib/api";
import { Play, Radar, Activity, Target, AlertTriangle, CheckCircle, XCircle, Zap } from "lucide-react";

function scoreBadge(score: number) {
  if (score >= 75) return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">{score.toFixed(1)}</span>;
  if (score >= 60) return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">{score.toFixed(1)}</span>;
  return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">{score.toFixed(1)}</span>;
}

function statusBadge(status: string) {
  switch (status) {
    case "pass":
    case "completed":
      return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">{status}</span>;
    case "watch":
    case "partial":
      return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">{status}</span>;
    case "blocked":
    case "failed":
      return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">{status}</span>;
    default:
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">{status}</span>;
  }
}

export default function SignalsPage() {
  const [isRunning, setIsRunning] = useState(false);
  const [runStep, setRunStep] = useState<string | null>(null);
  const [eventScanner, setEventScanner] = useState<EventScannerResponse | null>(null);
  const [signalScoring, setSignalScoring] = useState<SignalScoringResponse | null>(null);
  const [metaModel, setMetaModel] = useState<MetaModelEnsembleResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadLatest = async () => {
    try {
      const [eventRes, scoringRes, metaRes] = await Promise.all([
        api.getLatestEventScan(),
        api.getLatestSignalScoring(),
        api.getLatestMetaModelEnsemble(),
      ]);
      if (!("status" in eventRes && eventRes.status === "not_found")) {
        setEventScanner(eventRes as EventScannerResponse);
      }
      if (!("status" in scoringRes && scoringRes.status === "not_found")) {
        setSignalScoring(scoringRes as SignalScoringResponse);
      }
      if (!("status" in metaRes && metaRes.status === "not_found")) {
        setMetaModel(metaRes as MetaModelEnsembleResponse);
      }
    } catch {
      // Ignore errors
    }
  };

  useEffect(() => {
    loadLatest();
  }, []);

  const handleRunFullPipeline = async () => {
    setIsRunning(true);
    setError(null);
    setRunStep("Event Scanner");

    try {
      // Step 1: Run Event Scanner
      const eventRes = await api.runEventScanner({
        use_latest_watchlist: true,
        use_active_trigger_rules: true,
        source: "auto",
        horizon: "swing",
        allow_mock: false,
      });
      setEventScanner(eventRes);

      if (eventRes.matched_events.length === 0) {
        setRunStep(null);
        setIsRunning(false);
        return;
      }

      // Step 2: Run Signal Scoring
      setRunStep("Signal Scoring");
      const scoringRes = await api.runSignalScoring({
        events: eventRes.matched_events,
        use_latest_events: false,
        source: "auto",
        horizon: "swing",
        allow_mock: false,
      });
      setSignalScoring(scoringRes);

      if (scoringRes.scored_signals.length === 0) {
        setRunStep(null);
        setIsRunning(false);
        return;
      }

      // Step 3: Run Meta-Model Ensemble
      setRunStep("Meta-Model Ensemble");
      const metaRes = await api.runMetaModelEnsemble({
        scored_signals: scoringRes.scored_signals,
        use_latest_scored_signals: false,
        horizon: "swing",
      });
      setMetaModel(metaRes);

      setRunStep(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setIsRunning(false);
      setRunStep(null);
    }
  };

  return (
    <div className="mx-auto w-full max-w-6xl p-4 lg:p-8">
      <PageHeader
        eyebrow="workflow step 9-11"
        title="Signals"
        description="Event Scanner, Signal Scoring, and Meta-Model Ensemble. Cheap deterministic scanning, no LLMs, no recommendations yet."
      />

      {error && (
        <div className="mb-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          <AlertTriangle className="mr-2 inline h-4 w-4" />
          {error}
        </div>
      )}

      <div className="mb-6 flex gap-3">
        <button
          onClick={handleRunFullPipeline}
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
              {runStep || "Running..."}
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Full Pipeline
            </>
          )}
        </button>
      </div>

      {/* Event Scanner */}
      {eventScanner && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <Radar className="h-4 w-4" />
            Event Scanner (Step 9)
          </h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <span className="text-xs text-slate-500">Status</span>
              <div className="mt-1">{statusBadge(eventScanner.status)}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Scanned Symbols</span>
              <div className="text-lg font-bold text-slate-200">{eventScanner.scanned_symbols.length}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Matched Events</span>
              <div className="text-lg font-bold text-emerald-400">{eventScanner.matched_events.length}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Skipped</span>
              <div className="text-lg font-bold text-slate-400">{eventScanner.skipped_symbols.length}</div>
            </div>
          </div>
          {eventScanner.matched_events.length > 0 && (
            <div className="mt-3">
              <span className="text-xs text-slate-500">Latest Events</span>
              <div className="mt-1 flex flex-wrap gap-2">
                {eventScanner.matched_events.slice(0, 5).map(e => (
                  <span key={e.event_id} className="rounded bg-slate-800 px-2 py-1 text-xs text-slate-300">
                    {e.symbol}: {e.trigger_type}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Signal Scoring */}
      {signalScoring && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <Activity className="h-4 w-4" />
            Signal Scoring (Step 10)
          </h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <div>
              <span className="text-xs text-slate-500">Status</span>
              <div className="mt-1">{statusBadge(signalScoring.status)}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Scored Signals</span>
              <div className="text-lg font-bold text-emerald-400">{signalScoring.scored_signals.length}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Skipped</span>
              <div className="text-lg font-bold text-slate-400">{signalScoring.skipped_signals.length}</div>
            </div>
          </div>
          {signalScoring.scored_signals.length > 0 && (
            <div className="mt-3 grid gap-2">
              {signalScoring.scored_signals.slice(0, 5).map(s => (
                <div key={s.signal_id} className="flex items-center justify-between rounded-lg bg-slate-800/50 p-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-300">{s.symbol}</span>
                    <span className="text-xs text-slate-500">{s.trigger_type}</span>
                    {s.skipped_models.length > 0 && (
                      <span className="text-xs text-amber-400">({s.skipped_models.length} skipped)</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-slate-500">Final:</span>
                    {scoreBadge(s.signal_score)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Meta-Model Ensemble */}
      {metaModel && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <Target className="h-4 w-4" />
            Meta-Model Ensemble (Step 11)
          </h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-5">
            <div>
              <span className="text-xs text-slate-500">Status</span>
              <div className="mt-1">{statusBadge(metaModel.status)}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Passed</span>
              <div className="text-lg font-bold text-emerald-400">{metaModel.passed_signals.length}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Watch</span>
              <div className="text-lg font-bold text-amber-400">{metaModel.watch_signals.length}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Blocked</span>
              <div className="text-lg font-bold text-red-400">{metaModel.blocked_signals.length}</div>
            </div>
            <div>
              <span className="text-xs text-slate-500">Promoted</span>
              <div className="text-lg font-bold text-sky-400">{metaModel.promoted_candidates.length}</div>
            </div>
          </div>
          {metaModel.ensemble_signals.length > 0 && (
            <div className="mt-3 grid gap-2">
              {metaModel.ensemble_signals.slice(0, 5).map(s => (
                <div key={s.symbol} className="flex items-center justify-between rounded-lg bg-slate-800/50 p-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-slate-300">{s.symbol}</span>
                    <span className="text-xs text-slate-500">{s.trigger_type}</span>
                    <span className={`text-xs ${s.status === "pass" ? "text-emerald-400" : s.status === "watch" ? "text-amber-400" : "text-red-400"}`}>
                      {s.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-xs text-slate-500">Agreement: {(s.model_agreement * 100).toFixed(0)}%</span>
                    {scoreBadge(s.final_signal_score)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!eventScanner && !isRunning && (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center">
          <Zap className="mx-auto mb-3 h-12 w-12 text-slate-600" />
          <p className="text-slate-400">No signals yet.</p>
          <p className="mt-1 text-sm text-slate-500">Click &quot;Run Full Pipeline&quot; to scan for events and score signals.</p>
        </div>
      )}
    </div>
  );
}
