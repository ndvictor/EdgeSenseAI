import { Activity, AlertTriangle, BarChart3, BrainCircuit, CalendarDays, CheckCircle2, Clock3, GitBranch, LineChart, RefreshCcw, ShieldCheck, Sparkles, XCircle } from "lucide-react";
import { MetricCard, PageHeader } from "@/components/Cards";

type StrategyReadiness = "ready" | "not_ready";

type StrategyCard = {
  name: string;
  readiness: StrategyReadiness;
  assetClass: string;
  timeframe: string;
  requiredModels: string[];
  lastTestReport?: string;
  retestFrequency?: string;
  nextRetest?: string;
  why?: string;
  blockers?: string[];
  status?: "Testing" | "Candidate" | "Blocked" | "Ready";
  icon: "momentum" | "star" | "vwap" | "breakout" | "inverse" | "options" | "xgboost";
};

const readyStrategies: StrategyCard[] = [
  {
    name: "15 Min Liquid Momentum",
    readiness: "ready",
    assetClass: "Equities",
    timeframe: "15 Min",
    requiredModels: ["weighted_ranker_v1", "regime_classifier_v1", "liquidity_filter_v1", "risk_veto_v1"],
    lastTestReport: "Walk-forward pass | Precision 64% | Capture 58% | False Positives 18%",
    retestFrequency: "Every 7 days",
    nextRetest: "May 21, 2025",
    status: "Ready",
    icon: "momentum",
  },
  {
    name: "Tech Quintet Momentum",
    readiness: "ready",
    assetClass: "Equities",
    timeframe: "30 Min",
    requiredModels: ["weighted_ranker_v1", "sector_strength_v1", "historical_similarity_v1", "risk_veto_v1"],
    lastTestReport: "Paper test stable | Win Rate 61% | Avg Hold 42 min",
    retestFrequency: "Every 7 days",
    nextRetest: "May 21, 2025",
    status: "Ready",
    icon: "star",
  },
  {
    name: "VWAP Reclaim",
    readiness: "ready",
    assetClass: "Equities",
    timeframe: "5 Min",
    requiredModels: ["weighted_ranker_v1", "vwap_trigger_v1", "volume_confirmation_v1", "capital_allocator_v1"],
    lastTestReport: "Intraday validation pass | Precision 67% | Max DD controlled",
    retestFrequency: "Every 3 days",
    nextRetest: "May 19, 2025",
    status: "Ready",
    icon: "vwap",
  },
];

const notReadyStrategies: StrategyCard[] = [
  {
    name: "Opening Range Breakout",
    readiness: "not_ready",
    assetClass: "Equities",
    timeframe: "15 Min",
    requiredModels: ["opening_range_detector_v1", "weighted_ranker_v1", "spread_guard_v1", "news_catalyst_v1"],
    why: "Captures high-volume institutional imbalance after the open.",
    blockers: ["Needs more paper-test days", "Open-session false breakout rate too high", "News catalyst feed still partial"],
    status: "Testing",
    icon: "breakout",
  },
  {
    name: "Double Agent Inverse ETF",
    readiness: "not_ready",
    assetClass: "ETFs",
    timeframe: "30 Min",
    requiredModels: ["regime_classifier_v1", "trend_flip_v1", "hedge_router_v1", "drawdown_guard_v1"],
    why: "Switches between long and inverse ETF exposure when regime flips.",
    blockers: ["Whipsaw risk not fully bounded", "Needs stronger trend confirmation", "Needs more drawdown testing"],
    status: "Candidate",
    icon: "inverse",
  },
  {
    name: "Options Flow Momentum",
    readiness: "not_ready",
    assetClass: "Options",
    timeframe: "15 Min",
    requiredModels: ["options_flow_parser_v1", "iv_oi_validator_v1", "underlying_confirmation_v1", "contract_quality_filter_v1"],
    why: "Uses unusual options activity to identify directional momentum setups.",
    blockers: ["Options provider not fully live", "Contract quality model incomplete", "Spread risk too high for small accounts"],
    status: "Testing",
    icon: "options",
  },
  {
    name: "XGBoost Meta Ranker Strategy",
    readiness: "not_ready",
    assetClass: "Equities",
    timeframe: "Daily",
    requiredModels: ["xgboost_ranker", "calibration_service_v1", "outcome_labeler_v1", "walk_forward_evaluator_v1"],
    why: "Supervised meta-model intended to improve candidate ranking.",
    blockers: ["XGBoost model not trained", "Needs labeled outcomes", "Calibration not complete"],
    status: "Blocked",
    icon: "xgboost",
  },
];

function StrategyIcon({ type, ready }: { type: StrategyCard["icon"]; ready: boolean }) {
  const className = `h-6 w-6 ${ready ? "text-emerald-300" : "text-amber-300"}`;
  const icons = {
    momentum: <LineChart className={className} />,
    star: <Sparkles className={className} />,
    vwap: <Activity className={className} />,
    breakout: <BarChart3 className={className} />,
    inverse: <RefreshCcw className={className} />,
    options: <GitBranch className={className} />,
    xgboost: <BrainCircuit className={className} />,
  };
  return icons[type];
}

function StatusBadge({ readiness }: { readiness: StrategyReadiness }) {
  const ready = readiness === "ready";
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-3 py-1 text-xs font-bold ${ready ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300" : "border-rose-500/40 bg-rose-500/10 text-rose-300"}`}>
      {ready ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}
      {ready ? "Ready for Prod" : "Not Ready for Prod"}
    </span>
  );
}

function Pill({ children }: { children: string }) {
  return <span className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-2 py-1 text-xs font-semibold text-blue-200">{children}</span>;
}

function SmallTag({ children }: { children: string }) {
  return <span className="rounded-md border border-slate-700 bg-slate-800 px-2 py-1 text-xs font-semibold text-slate-300">{children}</span>;
}

function ReadyStrategyCard({ strategy }: { strategy: StrategyCard }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-950/95 shadow-sm shadow-emerald-950/20">
      <div className="p-4">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-emerald-500/50 bg-emerald-500/10">
            <StrategyIcon type={strategy.icon} ready />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-xl font-black tracking-tight text-white">{strategy.name}</h3>
              <StatusBadge readiness={strategy.readiness} />
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <SmallTag>{strategy.assetClass}</SmallTag>
              <SmallTag>{strategy.timeframe}</SmallTag>
            </div>
          </div>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Required models</p>
          <div className="flex flex-wrap gap-2">
            {strategy.requiredModels.map((model) => <Pill key={model}>{model}</Pill>)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 divide-y divide-slate-800 border-t border-slate-800 md:grid-cols-3 md:divide-x md:divide-y-0">
        <div className="p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Last test report</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-200">{strategy.lastTestReport}</p>
        </div>
        <div className="p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Retest frequency</p>
          <p className="mt-2 inline-flex items-center gap-2 text-sm font-bold text-slate-200"><RefreshCcw className="h-4 w-4 text-cyan-300" />{strategy.retestFrequency}</p>
        </div>
        <div className="p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Next retest</p>
          <p className="mt-2 inline-flex items-center gap-2 text-sm font-bold text-slate-200"><CalendarDays className="h-4 w-4 text-cyan-300" />{strategy.nextRetest}</p>
        </div>
      </div>
    </article>
  );
}

function NotReadyStrategyCard({ strategy }: { strategy: StrategyCard }) {
  return (
    <article className="overflow-hidden rounded-2xl border border-slate-700 bg-slate-950/95 shadow-sm shadow-amber-950/20">
      <div className="p-4">
        <div className="flex items-start gap-4">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl border border-amber-500/60 bg-amber-500/10">
            <StrategyIcon type={strategy.icon} ready={false} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-3">
              <h3 className="text-xl font-black tracking-tight text-white">{strategy.name}</h3>
              <StatusBadge readiness={strategy.readiness} />
            </div>
            <div className="mt-2 flex flex-wrap gap-2">
              <SmallTag>{strategy.assetClass}</SmallTag>
              <SmallTag>{strategy.timeframe}</SmallTag>
            </div>
          </div>
          <div className="hidden text-right text-xs text-slate-400 md:block">
            <p>Current status</p>
            <p className={`mt-1 inline-flex items-center gap-2 font-bold ${strategy.status === "Blocked" ? "text-rose-300" : "text-amber-300"}`}>
              <span className={`h-2 w-2 rounded-full ${strategy.status === "Blocked" ? "bg-rose-400" : "bg-amber-400"}`} />
              {strategy.status}
            </p>
          </div>
        </div>

        <div className="mt-4">
          <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Required models</p>
          <div className="flex flex-wrap gap-2">
            {strategy.requiredModels.map((model) => <Pill key={model}>{model}</Pill>)}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 divide-y divide-slate-800 border-t border-slate-800 md:grid-cols-2 md:divide-x md:divide-y-0">
        <div className="p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Why this strategy</p>
          <p className="mt-2 text-sm leading-relaxed text-slate-200">{strategy.why}</p>
        </div>
        <div className="p-4">
          <p className="text-xs font-bold uppercase tracking-wide text-slate-500">Blockers</p>
          <ul className="mt-2 space-y-1 text-sm text-slate-200">
            {strategy.blockers?.map((blocker) => (
              <li key={blocker} className="flex gap-2"><span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-400" />{blocker}</li>
            ))}
          </ul>
        </div>
      </div>
    </article>
  );
}

export default function StrategiesPage() {
  const needsAttention = notReadyStrategies.filter((strategy) => strategy.status === "Blocked" || strategy.status === "Testing").length;

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-4">
        <PageHeader
          eyebrow="strategy control plane"
          title="Strategies"
          description="Production readiness and validation status for all strategy playbooks. Candidate strategies must pass testing, required models, risk gates, and owner approval before production use."
        />

        <div className="grid grid-cols-2 gap-4 xl:grid-cols-4">
          <MetricCard label="Ready for Prod" value={readyStrategies.length} accent />
          <MetricCard label="Not Ready" value={notReadyStrategies.length} />
          <MetricCard label="Avg Retest Cycle" value="7 days" />
          <MetricCard label="Needs Attention" value={needsAttention} />
        </div>

        <section className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
          <div className="grid gap-4 xl:grid-cols-2">
            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="h-8 w-1 rounded-full bg-cyan-400" />
                <h2 className="text-2xl font-black tracking-tight text-white">Ready for Prod</h2>
                <span className="rounded-full border border-emerald-500/40 bg-emerald-500/10 px-3 py-1 text-xs font-bold text-emerald-300">validated</span>
              </div>
              {readyStrategies.map((strategy) => <ReadyStrategyCard key={strategy.name} strategy={strategy} />)}
            </div>

            <div className="space-y-4">
              <div className="flex items-center gap-3">
                <span className="h-8 w-1 rounded-full bg-amber-400" />
                <h2 className="text-2xl font-black tracking-tight text-white">Not Ready for Prod</h2>
                <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-3 py-1 text-xs font-bold text-amber-300">candidate/testing</span>
              </div>
              {notReadyStrategies.map((strategy) => <NotReadyStrategyCard key={strategy.name} strategy={strategy} />)}
            </div>
          </div>
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center gap-3">
              <ShieldCheck className="h-5 w-5 text-emerald-300" />
              <h3 className="text-lg font-black text-white">Safety Rule</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">Ready status does not enable live execution. All strategies remain paper/research-only until a separate broker, risk, and approval design is implemented.</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-300" />
              <h3 className="text-lg font-black text-white">Promotion Rule</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">Not-ready strategies require model availability, paper-test evidence, blocker resolution, and owner approval before they can move into production readiness.</p>
          </div>
          <div className="rounded-2xl border border-slate-800 bg-slate-950 p-4">
            <div className="flex items-center gap-3">
              <Clock3 className="h-5 w-5 text-cyan-300" />
              <h3 className="text-lg font-black text-white">Retest Policy</h3>
            </div>
            <p className="mt-3 text-sm leading-relaxed text-slate-300">Ready strategies show their latest validation report and retest cadence. Candidate strategies should enter the research/backtest queue before promotion.</p>
          </div>
        </section>
      </div>
    </div>
  );
}
