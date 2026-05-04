"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, BrainCircuit, CheckCircle2, Cpu, DatabaseZap, FlaskConical, ShieldCheck, XCircle } from "lucide-react";
import { MetricCard, PageHeader } from "@/components/Cards";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8900";

type ModelRegistryEntry = {
  model_key: string;
  display_name: string;
  group: string;
  type: string;
  provider: string;
  status: string;
  use_case: string[];
  allowed_for_live_scoring: boolean;
  allowed_for_research_backtesting: boolean;
  allowed_for_final_trade_decision: boolean;
  requires_trained_artifact: boolean;
  trained_artifact_exists: boolean;
  evaluation_passed: boolean;
  calibration_passed: boolean;
  owner_approved: boolean;
  requires_news_text_input: boolean;
  requires_options_data: boolean;
  requires_market_data: boolean;
  requires_feature_store: boolean;
  requires_risk_gate: boolean;
  requires_human_approval: boolean;
  blocked_reason?: string | null;
  next_action: string;
  artifact_path?: string | null;
  evaluation_notes?: string | null;
  cost_profile: string;
  safety_notes: string[];
};

type ModelRegistryResponse = {
  data_source: string;
  groups: Record<string, ModelRegistryEntry[]>;
  models: ModelRegistryEntry[];
  active_model_count: number;
  candidate_model_count: number;
  untrained_internal_model_count: number;
  blocked_model_count: number;
  final_trade_decision_models_count: number;
  safety_notes: string[];
};

type ModelEligibilityResponse = {
  model_key: string;
  display_name?: string;
  group?: string;
  status?: string;
  eligible_for_active_scoring: boolean;
  missing_requirements?: string[];
  blocked_reason?: string | null;
  next_action?: string;
  safety_notes?: string[];
};

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { headers: { "Content-Type": "application/json" }, cache: "no-store" });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

function statusTone(status?: string | null) {
  const value = (status || "unknown").toLowerCase();
  if (["active", "eligible", "completed", "pass", "true"].includes(value) || value.includes("eligible")) return "border-emerald-500 bg-emerald-500/10 text-emerald-300";
  if (["candidate", "candidate_not_active", "not_trained", "warn", "research"].includes(value) || value.includes("candidate") || value.includes("not trained")) return "border-amber-500 bg-amber-500/10 text-amber-300";
  if (["blocked", "fail", "false", "not_configured", "error"].includes(value) || value.includes("blocked") || value.includes("disabled")) return "border-rose-500 bg-rose-500/10 text-rose-300";
  return "border-slate-600 bg-slate-800 text-slate-300";
}

function Badge({ value }: { value?: string | boolean | null }) {
  const text = typeof value === "boolean" ? (value ? "true" : "false") : value || "unknown";
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${statusTone(String(text))}`}>{String(text).replace(/_/g, " ")}</span>;
}

function MiniCheck({ label, value }: { label: string; value: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-lg border border-slate-800 bg-slate-950 px-3 py-2">
      <span className="text-xs text-slate-400">{label}</span>
      <span className={`inline-flex items-center gap-1 text-xs font-bold ${value ? "text-emerald-300" : "text-rose-300"}`}>
        {value ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
        {value ? "Yes" : "No"}
      </span>
    </div>
  );
}

function groupTitle(group: string) {
  return group.replace(/_/g, " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function groupIcon(group: string) {
  if (group.includes("active")) return <CheckCircle2 className="h-5 w-5 text-emerald-300" />;
  if (group.includes("pretrained")) return <BrainCircuit className="h-5 w-5 text-cyan-300" />;
  if (group.includes("open_source")) return <DatabaseZap className="h-5 w-5 text-blue-300" />;
  if (group.includes("statistical")) return <Cpu className="h-5 w-5 text-violet-300" />;
  if (group.includes("untrained") || group.includes("blocked")) return <AlertTriangle className="h-5 w-5 text-amber-300" />;
  return <FlaskConical className="h-5 w-5 text-slate-300" />;
}

function ModelCard({ model }: { model: ModelRegistryEntry }) {
  const eligible = model.allowed_for_live_scoring && model.evaluation_passed && model.calibration_passed && model.owner_approved;
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900 p-4 shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-black text-white">{model.display_name}</h3>
          <p className="mt-1 font-mono text-xs text-slate-500">{model.model_key}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge value={model.status} />
          <Badge value={model.group} />
        </div>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-2 md:grid-cols-2">
        <MiniCheck label="Live scoring" value={model.allowed_for_live_scoring} />
        <MiniCheck label="Research/backtest" value={model.allowed_for_research_backtesting} />
        <MiniCheck label="Final trade decision" value={model.allowed_for_final_trade_decision} />
        <MiniCheck label="Eligible now" value={eligible} />
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <Badge value={model.provider} />
        <Badge value={model.type} />
        <Badge value={model.cost_profile} />
      </div>

      {model.use_case?.length ? (
        <div className="mt-4">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Use case</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {model.use_case.slice(0, 5).map((item) => <span key={item} className="rounded-lg border border-blue-500/30 bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-200">{item}</span>)}
          </div>
        </div>
      ) : null}

      {model.blocked_reason ? (
        <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-200">
          <p className="font-bold">Blocked reason</p>
          <p className="mt-1 leading-relaxed">{model.blocked_reason}</p>
        </div>
      ) : null}

      <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950 p-3 text-sm text-slate-300">
        <p className="font-bold text-emerald-300">Next action</p>
        <p className="mt-1 leading-relaxed">{model.next_action}</p>
      </div>

      {model.safety_notes?.length ? (
        <ul className="mt-4 space-y-1 text-sm text-slate-400">
          {model.safety_notes.slice(0, 4).map((note) => <li key={note}>• {note}</li>)}
        </ul>
      ) : null}
    </article>
  );
}

function ModelGroup({ group, models }: { group: string; models: ModelRegistryEntry[] }) {
  if (!models?.length) return null;
  return (
    <section className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
      <div className="mb-4 flex items-center gap-3">
        {groupIcon(group)}
        <h2 className="text-xl font-black tracking-tight text-white">{groupTitle(group)}</h2>
        <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-bold text-slate-300">{models.length}</span>
      </div>
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {models.map((model) => <ModelCard key={model.model_key} model={model} />)}
      </div>
    </section>
  );
}

function GovernanceTable({ registry, xgboost }: { registry: ModelRegistryResponse; xgboost: ModelEligibilityResponse | null }) {
  const priorityKeys = ["weighted_ranker_v1", "xgboost_ranker", "qlib_research_platform", "chronos_bolt_tiny", "finbert_sentiment", "vectorbt_backtrader"];
  const rows = priorityKeys.map((key) => registry.models.find((model) => model.model_key === key)).filter(Boolean) as ModelRegistryEntry[];
  return (
    <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
      <table className="w-full min-w-[1000px] text-left text-sm">
        <thead className="text-xs uppercase tracking-wide text-emerald-600">
          <tr><th className="px-4 py-3">Model</th><th className="px-4 py-3">Group</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Eligible</th><th className="px-4 py-3">Final Decision</th><th className="px-4 py-3">Next Action</th></tr>
        </thead>
        <tbody className="divide-y divide-slate-800">
          {rows.map((model) => {
            const eligible = model.model_key === "xgboost_ranker" ? xgboost?.eligible_for_active_scoring : model.allowed_for_live_scoring;
            return (
              <tr key={model.model_key} className="hover:bg-emerald-950/20">
                <td className="px-4 py-3"><p className="font-bold text-white">{model.display_name}</p><p className="font-mono text-xs text-slate-500">{model.model_key}</p></td>
                <td className="px-4 py-3"><Badge value={model.group} /></td>
                <td className="px-4 py-3"><Badge value={model.status} /></td>
                <td className="px-4 py-3"><Badge value={Boolean(eligible)} /></td>
                <td className="px-4 py-3"><Badge value={model.allowed_for_final_trade_decision} /></td>
                <td className="max-w-xl px-4 py-3 text-slate-400">{model.model_key === "xgboost_ranker" ? xgboost?.next_action || model.next_action : model.next_action}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function ModelRegistryVisibility({ compact = false }: { compact?: boolean }) {
  const [registry, setRegistry] = useState<ModelRegistryResponse | null>(null);
  const [xgboost, setXgboost] = useState<ModelEligibilityResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([
      fetchJson<ModelRegistryResponse>("/api/model-registry"),
      fetchJson<ModelEligibilityResponse>("/api/model-registry/xgboost_ranker/eligibility"),
    ])
      .then(([registryResponse, xgboostResponse]) => {
        if (!mounted) return;
        setRegistry(registryResponse);
        setXgboost(xgboostResponse);
      })
      .catch((err) => mounted && setError(err instanceof Error ? err.message : "Model registry failed"))
      .finally(() => mounted && setLoading(false));
    return () => { mounted = false; };
  }, []);

  const candidateCount = useMemo(() => registry?.candidate_model_count ?? 0, [registry]);

  if (loading) return <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-8 text-center text-sm text-slate-300">Loading model registry...</div>;
  if (error) return <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>;
  if (!registry) return <div className="rounded-xl border border-slate-800 bg-slate-950 px-4 py-8 text-center text-sm text-slate-300">No model registry available.</div>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4 xl:grid-cols-5">
        <MetricCard label="Active Models" value={registry.active_model_count} accent />
        <MetricCard label="Candidate Models" value={candidateCount} />
        <MetricCard label="Untrained Internal" value={registry.untrained_internal_model_count} />
        <MetricCard label="Blocked Models" value={registry.blocked_model_count} />
        <MetricCard label="Final Decision Models" value={registry.final_trade_decision_models_count} />
      </div>

      <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
        <div className="mb-3 flex items-center gap-3">
          <ShieldCheck className="h-5 w-5 text-emerald-300" />
          <h2 className="text-lg font-black text-white">Model Governance Summary</h2>
        </div>
        <GovernanceTable registry={registry} xgboost={xgboost} />
        <div className="mt-4 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-200">
          <p className="font-bold">XGBoost safety gate</p>
          <p className="mt-1">XGBoost is visible but blocked. It is not trained, does not influence scoring, and cannot become active until artifact, evaluation, calibration, owner approval, and live-scoring permission gates pass.</p>
        </div>
      </div>

      {!compact ? (
        <>
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="mb-3 flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-cyan-300" />
              <h2 className="text-lg font-black text-white">Safety Notes</h2>
            </div>
            <ul className="grid gap-2 text-sm text-slate-300 md:grid-cols-2">
              {registry.safety_notes.map((note) => <li key={note} className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2">{note}</li>)}
            </ul>
          </div>
          {Object.entries(registry.groups).map(([group, models]) => <ModelGroup key={group} group={group} models={models} />)}
        </>
      ) : null}
    </div>
  );
}

export default function ModelRegistryPage() {
  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px] space-y-4">
        <PageHeader
          eyebrow="model governance"
          title="Model Registry & Eligibility"
          description="Visibility into active, candidate, pretrained, statistical, untrained, and blocked models. Candidate models are research-only until wrapper, evaluation, calibration, and owner approval gates pass."
        />
        <ModelRegistryVisibility />
      </div>
    </div>
  );
}
