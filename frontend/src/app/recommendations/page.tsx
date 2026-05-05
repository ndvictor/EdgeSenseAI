"use client";

import { useEffect, useState } from "react";
import { PageHeader, MetricCard } from "@/components/Cards";
import { api, type RecommendationLifecycleRecord, type RecommendationPipelineResponse } from "@/lib/api";
import { Play, CheckCircle, XCircle, Clock, AlertTriangle, Target, Shield, Wallet, Ban, Activity, Database, BrainCircuit, Bot, DollarSign } from "lucide-react";

function statusBadge(status: string) {
  switch (status) {
    case "pending_review":
      return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-400">Pending Review</span>;
    case "approved":
      return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-400">Approved</span>;
    case "rejected":
      return <span className="rounded-full border border-red-500 bg-red-500/10 px-2 py-0.5 text-xs font-bold uppercase text-red-400">Rejected</span>;
    case "paper_trade_created":
      return <span className="rounded-full border border-blue-500 bg-blue-500/10 px-2 py-0.5 text-xs font-bold uppercase text-blue-400">Paper Trade</span>;
    case "expired":
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">Expired</span>;
    default:
      return <span className="rounded-full border border-slate-500 bg-slate-500/10 px-2 py-0.5 text-xs font-bold uppercase text-slate-400">{status}</span>;
  }
}

type ProvenanceLike = {
  data_source?: string;
  signal_source?: string;
  model_source?: string;
  model_used?: string;
  agent_source?: string;
  llm_source?: string;
  llm_used?: string;
  market_data_source?: string;
  price_source_detail?: string;
  real_market_data_used?: boolean;
  final_trade_decision_allowed?: boolean;
};

function SourceChip({ icon, label, value, warn = false }: { icon?: React.ReactNode; label: string; value?: string | boolean | null; warn?: boolean }) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${warn ? "border-amber-500/40 bg-amber-500/10" : "border-slate-700 bg-slate-800/50"}`}>
      <div className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-wide text-slate-500">
        {icon}
        {label}
      </div>
      <div className={`mt-1 text-xs font-bold ${warn ? "text-amber-300" : "text-slate-300"}`}>{String(value ?? "unknown")}</div>
    </div>
  );
}

function SourcePanel({ provenance }: { provenance?: ProvenanceLike | null }) {
  const p = provenance || {};
  return (
    <div className="mt-3 rounded-xl border border-slate-700 bg-slate-950 p-3">
      <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-emerald-400">
        <Database className="h-4 w-4" />
        Source / Model / Agent Truth
      </div>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-3 xl:grid-cols-4">
        <SourceChip icon={<Database className="h-3 w-3" />} label="Data Source" value={p.data_source ?? "pipeline_generated"} />
        <SourceChip icon={<Activity className="h-3 w-3" />} label="Signal Source" value={p.signal_source ?? "meta_model_ensemble"} />
        <SourceChip icon={<BrainCircuit className="h-3 w-3" />} label="Model Used" value={p.model_used ?? "ensemble_signal"} />
        <SourceChip icon={<Bot className="h-3 w-3" />} label="Agent Source" value={p.agent_source ?? "agent/risk/capital services"} />
        <SourceChip icon={<DollarSign className="h-3 w-3" />} label="LLM Used" value={p.llm_used ?? "none_paid_dry_run_policy"} />
        <SourceChip label="Market Data" value={p.market_data_source ?? "placeholder_current_price"} warn />
        <SourceChip label="Real Market Data" value={p.real_market_data_used ?? false} warn />
        <SourceChip label="Final Decision Allowed" value={p.final_trade_decision_allowed ?? false} warn />
      </div>
      <p className="mt-3 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs leading-relaxed text-amber-200">
        {p.price_source_detail ?? "Capital allocation may be using placeholder pricing unless backend source_provenance says otherwise."}
      </p>
    </div>
  );
}

export default function RecommendationsPage() {
  const [recommendations, setRecommendations] = useState<RecommendationLifecycleRecord[]>([]);
  const [pipelineRun, setPipelineRun] = useState<RecommendationPipelineResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const loadRecommendations = async () => {
    try {
      const response = await api.getRecommendationLifecycleList();
      if (Array.isArray(response)) {
        setRecommendations(response);
      }
    } catch {
      // Ignore errors
    }
  };

  const loadPipeline = async () => {
    try {
      const response = await api.getLatestRecommendationPipeline();
      if (!("status" in response && response.status === "not_found")) {
        setPipelineRun(response as RecommendationPipelineResponse);
      }
    } catch {
      // Ignore errors
    }
  };

  useEffect(() => {
    loadRecommendations();
    loadPipeline();
  }, []);

  const handleRunPipeline = async () => {
    setIsRunning(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const response = await api.runRecommendationPipeline({
        use_latest_ensemble: true,
        account_equity: 1000,
        buying_power: 1000,
        allow_paid_llm: false,
        dry_run: true,
      });

      setPipelineRun(response);

      if (response.recommendation) {
        setSuccessMessage(`Recommendation created for ${response.recommendation.symbol}: ${response.recommendation.action_label}`);
        loadRecommendations();
      } else {
        setError(`Pipeline completed but no recommendation: ${response.status}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setIsRunning(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveRecommendation(id);
      loadRecommendations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to approve");
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.rejectRecommendation(id);
      loadRecommendations();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reject");
    }
  };

  const pendingRecommendations = recommendations.filter(r => r.status === "pending_review");
  const approvedRecommendations = recommendations.filter(r => r.status === "approved" || r.status === "paper_trade_created");
  const rejectedRecommendations = recommendations.filter(r => r.status === "rejected" || r.status === "expired");
  const pipelineProvenance = (pipelineRun as unknown as { source_provenance?: ProvenanceLike } | null)?.source_provenance;
  const recommendation = pipelineRun?.recommendation;
  const recommendationProvenance = recommendation ? (recommendation as typeof recommendation & ProvenanceLike) : null;

  return (
    <div className="mx-auto w-full max-w-6xl p-4 lg:p-8">
      <PageHeader
        eyebrow="workflow step 14-19"
        title="Recommendations"
        description="Pipeline from LLM Budget Gate through Approval. Paper trading only - no live execution."
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

      <div className="mb-6 flex gap-3">
        <button
          onClick={handleRunPipeline}
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
              Running Pipeline...
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Run Recommendation Pipeline
            </>
          )}
        </button>
      </div>

      {pipelineRun && (
        <div className="mb-6 rounded-xl border border-slate-700 bg-slate-900/50 p-4">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-sky-400">
            <Activity className="h-4 w-4" />
            Latest Pipeline Run: {pipelineRun.run_id}
          </h3>
          <div className="grid grid-cols-2 gap-4 md:grid-cols-6">
            <div className="rounded-lg bg-slate-800/50 p-2">
              <span className="text-xs text-slate-500">LLM Gate</span>
              <div className="text-sm font-medium text-slate-300">{pipelineRun.llm_budget_gate?.status || "N/A"}</div>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-2">
              <span className="text-xs text-slate-500">Agent Validation</span>
              <div className="text-sm font-medium text-slate-300">{pipelineRun.agent_validation?.status || "N/A"}</div>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-2">
              <span className="text-xs text-slate-500">Risk Review</span>
              <div className="text-sm font-medium text-slate-300">{pipelineRun.risk_review?.status || "N/A"}</div>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-2">
              <span className="text-xs text-slate-500">No-Trade</span>
              <div className="text-sm font-medium text-slate-300">{pipelineRun.no_trade?.decision || "N/A"}</div>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-2">
              <span className="text-xs text-slate-500">Capital Alloc</span>
              <div className="text-sm font-medium text-slate-300">{pipelineRun.capital_allocation?.status || "N/A"}</div>
            </div>
            <div className="rounded-lg bg-slate-800/50 p-2">
              <span className="text-xs text-slate-500">Final Status</span>
              <div className="text-sm font-medium text-slate-300">{pipelineRun.status}</div>
            </div>
          </div>

          <SourcePanel provenance={pipelineProvenance} />

          {pipelineRun.recommendation && (
            <div className="mt-3 rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-sm font-bold text-emerald-400">{pipelineRun.recommendation.symbol}</span>
                  <span className="ml-2 text-xs text-slate-400">{pipelineRun.recommendation.action_label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-slate-500">Score: {pipelineRun.recommendation.final_signal_score}</span>
                  <span className="text-xs text-slate-500">RR: {pipelineRun.recommendation.reward_risk_ratio.toFixed(2)}</span>
                  <span className="text-xs text-slate-500">Risk: {pipelineRun.recommendation.risk_status}</span>
                </div>
              </div>
              <div className="mt-2 text-xs text-slate-400">
                Entry: ${pipelineRun.recommendation.entry_zone_low.toFixed(2)}-${pipelineRun.recommendation.entry_zone_high.toFixed(2)} |
                Stop: ${pipelineRun.recommendation.stop_loss.toFixed(2)} |
                Target: ${pipelineRun.recommendation.target_price.toFixed(2)} |
                Size: {pipelineRun.recommendation.position_size_units.toFixed(2)} units
              </div>
              <SourcePanel provenance={recommendationProvenance ?? pipelineProvenance} />
            </div>
          )}
        </div>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        <MetricCard label="Pending" value={pendingRecommendations.length.toString()} accent />
        <MetricCard label="Approved" value={approvedRecommendations.length.toString()} />
        <MetricCard label="Rejected" value={rejectedRecommendations.length.toString()} />
        <MetricCard label="Total" value={recommendations.length.toString()} />
      </div>

      {pendingRecommendations.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-amber-400">
            <Clock className="h-4 w-4" />
            Pending Review ({pendingRecommendations.length})
          </h3>
          <div className="grid gap-3">
            {pendingRecommendations.map(rec => (
              <div key={rec.id} className="rounded-xl border border-slate-700 bg-slate-900/50 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-slate-200">{rec.symbol}</span>
                    {statusBadge(rec.status)}
                    <span className="text-xs text-slate-500">{rec.action_label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleApprove(rec.id)}
                      className="flex items-center gap-1 rounded-lg border border-emerald-500 px-3 py-1 text-xs font-bold uppercase text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
                    >
                      <CheckCircle className="h-3 w-3" />
                      Approve
                    </button>
                    <button
                      onClick={() => handleReject(rec.id)}
                      className="flex items-center gap-1 rounded-lg border border-red-500 px-3 py-1 text-xs font-bold uppercase text-red-400 hover:bg-red-500 hover:text-slate-950"
                    >
                      <XCircle className="h-3 w-3" />
                      Reject
                    </button>
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400 md:grid-cols-4">
                  <div>Score: {rec.score.toFixed(1)}</div>
                  <div>Confidence: {(rec.confidence * 100).toFixed(1)}%</div>
                  <div>Horizon: {rec.horizon}</div>
                  <div>Created: {new Date(rec.created_at).toLocaleDateString()}</div>
                </div>
                <SourcePanel provenance={pipelineProvenance} />
                {rec.risk_factors.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {rec.risk_factors.map((factor, i) => (
                      <span key={i} className="rounded bg-red-500/10 px-2 py-0.5 text-xs text-red-400">{factor}</span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {approvedRecommendations.length > 0 && (
        <div className="mb-6">
          <h3 className="mb-3 flex items-center gap-2 text-sm font-bold uppercase text-emerald-400">
            <CheckCircle className="h-4 w-4" />
            Approved ({approvedRecommendations.length})
          </h3>
          <div className="grid gap-3">
            {approvedRecommendations.map(rec => (
              <div key={rec.id} className="rounded-xl border border-emerald-500/30 bg-emerald-500/5 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-lg font-bold text-slate-200">{rec.symbol}</span>
                    {statusBadge(rec.status)}
                    <span className="text-xs text-slate-500">{rec.action_label}</span>
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-slate-400 md:grid-cols-4">
                  <div>Score: {rec.score.toFixed(1)}</div>
                  <div>Confidence: {(rec.confidence * 100).toFixed(1)}%</div>
                  <div>Horizon: {rec.horizon}</div>
                  <div>Updated: {new Date(rec.updated_at).toLocaleDateString()}</div>
                </div>
                <SourcePanel provenance={pipelineProvenance} />
              </div>
            ))}
          </div>
        </div>
      )}

      {recommendations.length === 0 && !isRunning && (
        <div className="rounded-xl border border-dashed border-slate-700 bg-slate-900/30 p-8 text-center">
          <Target className="mx-auto mb-3 h-12 w-12 text-slate-600" />
          <p className="text-slate-400">No recommendations yet.</p>
          <p className="mt-1 text-sm text-slate-500">Click &quot;Run Recommendation Pipeline&quot; to generate recommendations from ensemble signals.</p>
          <div className="mt-4 flex items-center justify-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1"><Shield className="h-3 w-3" /> Risk Review</span>
            <span className="flex items-center gap-1"><Ban className="h-3 w-3" /> No-Trade Gate</span>
            <span className="flex items-center gap-1"><Wallet className="h-3 w-3" /> Capital Allocation</span>
          </div>
        </div>
      )}
    </div>
  );
}
