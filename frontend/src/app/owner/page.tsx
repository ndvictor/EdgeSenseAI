"use client";

import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  BookOpen,
  Building2,
  Crown,
  Database,
  FlaskConical,
  Gauge,
  LineChart,
  ListChecks,
  Shield,
  Target,
  Trophy,
  UserCheck,
  Waves,
  Zap,
} from "lucide-react";

const kpis = [
  { label: "Account Value", value: "$1,000", sub: "Small account mode", tone: "text-emerald-300" },
  { label: "Net P&L", value: "Research", sub: "Broker P&L pending", tone: "text-slate-200" },
  { label: "Buying Power", value: "$1,000", sub: "Paper/research", tone: "text-emerald-300" },
  { label: "Daily Risk Left", value: "$30", sub: "2-3% max loss", tone: "text-emerald-300" },
  { label: "Cost / P&L Ratio", value: "Watch", sub: "LLM gated", tone: "text-amber-300" },
  { label: "Mode", value: "Selective", sub: "Capital preservation", tone: "text-emerald-300" },
];

const gates = [
  { label: "Data Quality", value: "Degraded", sub: "Bid/ask missing", icon: Database, tone: "text-amber-300" },
  { label: "Spread Status", value: "Unknown", sub: "No fake spread", icon: Waves, tone: "text-amber-300" },
  { label: "Risk Gate", value: "Caution", sub: "$5-$10 risk", icon: Shield, tone: "text-amber-300" },
  { label: "Human Approval", value: "Required", sub: "Owner review", icon: UserCheck, tone: "text-emerald-300" },
  { label: "Broker Status", value: "Dry-run", sub: "Alpaca env-gated", icon: Building2, tone: "text-emerald-300" },
  { label: "Live Trading", value: "Disabled", sub: "Safety locked", icon: Activity, tone: "text-rose-300" },
];

const recommendations = [
  { priority: 1, rec: "Keep top setup watch-only until bid/ask data is available.", benefit: "Avoid bad fills", action: "Review" },
  { priority: 2, rec: "Use stock_swing as active strategy; keep tech_quintet_momentum research-only.", benefit: "Governance safe", action: "Apply" },
  { priority: 3, rec: "Route routine summaries to deterministic mode; reserve LLMs for conflicts.", benefit: "Lower cost", action: "Consider" },
  { priority: 4, rec: "Backtest pullback entries in bull quiet and bull volatile regimes.", benefit: "Better timing", action: "Queue" },
];

const researchCandidates = [
  { name: "Tech Quintet", score: 90 },
  { name: "Double Agent ETF", score: 70 },
  { name: "Opening Range", score: 65 },
];

function Sparkline() {
  return (
    <svg viewBox="0 0 120 40" className="h-10 w-24 text-emerald-300" aria-hidden="true">
      <path
        d="M4 31 C16 20, 22 28, 32 21 S50 15, 60 22 S78 32, 88 16 S103 7, 116 13"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
      />
    </svg>
  );
}

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#03070b] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_62%_0%,rgba(16,185,129,0.16),transparent_28%),radial-gradient(circle_at_0%_100%,rgba(20,184,166,0.08),transparent_28%)]" />
      <div className="absolute right-0 top-0 h-72 w-[55rem] rounded-full border-t border-emerald-300/30 blur-[0.2px]" />
      <div className="absolute right-[8%] top-8 h-80 w-[48rem] rounded-[100%] border-t border-emerald-400/25" />
      <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(16,185,129,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.06)_1px,transparent_1px)] [background-size:54px_54px]" />
      <div className="relative z-10 p-8">{children}</div>
    </div>
  );
}

function Panel({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-emerald-400/15 bg-black/35 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur ${className}`}>
      {children}
    </section>
  );
}

export default function OwnerCommandCenterPage() {
  return (
    <Shell>
      <header className="mb-7 flex items-start justify-between gap-6">
        <div>
          <h1 className="text-4xl font-black tracking-[-0.04em] text-white">Owner Command Center</h1>
          <p className="mt-2 text-sm text-slate-400">Personal trading decision OS for growth, protection, and high-quality execution.</p>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_14px_rgba(52,211,153,0.9)]" />
            Markets Open
          </div>
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-sm text-slate-200">N</div>
        </div>
      </header>

      <Panel className="mb-4 overflow-hidden p-6">
        <div className="flex items-center justify-between gap-6">
          <div className="flex items-center gap-6">
            <div className="flex h-20 w-20 items-center justify-center rounded-full border border-emerald-300/25 bg-emerald-400/10 text-emerald-300 shadow-[0_0_50px_rgba(16,185,129,0.14)]">
              <Crown className="h-10 w-10" />
            </div>
            <div>
              <div className="text-sm font-medium text-emerald-300">Best Action Right Now</div>
              <h2 className="mt-2 text-2xl font-semibold tracking-tight">Monitor top setup until trigger confirmation.</h2>
              <p className="mt-2 max-w-3xl text-sm text-slate-400">Data is degraded because bid/ask is missing. Preserve capital, keep research scanning active, and block execution until spread quality is real.</p>
            </div>
          </div>
          <Link href="/command-center" className="hidden rounded-xl border border-emerald-400/30 px-5 py-3 text-sm font-semibold text-emerald-300 transition hover:bg-emerald-400/10 md:block">
            View Full Rationale →
          </Link>
        </div>
      </Panel>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
        {kpis.map((kpi) => (
          <Panel key={kpi.label} className="p-4">
            <div className="text-xs text-slate-500">{kpi.label}</div>
            <div className={`mt-3 text-2xl font-semibold tracking-tight ${kpi.tone}`}>{kpi.value}</div>
            <div className="mt-1 flex items-center justify-between gap-3 text-xs text-slate-500">
              <span>{kpi.sub}</span>
              <Sparkline />
            </div>
          </Panel>
        ))}
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-[1.05fr_1.25fr]">
        <Panel className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-lg font-semibold"><Target className="h-5 w-5 text-emerald-300" /> Top Opportunity</div>
            <div className="rounded-xl border border-emerald-400/20 px-3 py-2 text-sm text-emerald-300">Stock Swing</div>
          </div>
          <div className="flex items-end justify-between border-b border-white/10 pb-4">
            <div>
              <div className="text-4xl font-black tracking-tight">NVDA</div>
              <div className="mt-1 text-sm text-slate-400">NVIDIA Corporation</div>
            </div>
            <div className="flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-4 py-2 text-sm text-emerald-300">
              <LineChart className="h-4 w-4" /> Momentum Breakout
            </div>
          </div>
          <div className="mt-5 grid grid-cols-2 gap-3 md:grid-cols-6">
            {[
              ["Confidence", "78", "High"],
              ["Expected", "+6.2%", "Return"],
              ["Risk", "$10", "1R cap"],
              ["R/R", "2.6R", "Target"],
              ["Trigger", "Awaiting", "Confirm"],
              ["Approval", "Pending", "Owner"],
            ].map(([label, value, sub]) => (
              <div key={label} className="rounded-xl border border-white/10 bg-white/[0.025] p-3">
                <div className="text-[11px] text-slate-500">{label}</div>
                <div className="mt-2 text-lg font-semibold text-white">{value}</div>
                <div className="text-[11px] text-slate-500">{sub}</div>
              </div>
            ))}
          </div>
          <div className="mt-4 flex items-center justify-between text-xs text-slate-500">
            <span>Pattern: Bull flag • Timeframe: Swing • Mode: Watch-only until clean spread</span>
            <Link href="/recommendations" className="rounded-lg border border-emerald-400/20 px-3 py-2 text-emerald-300 hover:bg-emerald-400/10">View Setup →</Link>
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><Shield className="h-5 w-5 text-emerald-300" /> Risk & Execution Gates</div>
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-6">
            {gates.map((gate) => {
              const Icon = gate.icon;
              return (
                <div key={gate.label} className="rounded-xl border border-white/10 bg-white/[0.025] p-4 text-center">
                  <div className="text-[11px] text-slate-500">{gate.label}</div>
                  <Icon className="mx-auto mt-4 h-8 w-8 text-emerald-300" />
                  <div className={`mt-4 text-sm font-semibold ${gate.tone}`}>{gate.value}</div>
                  <div className="mt-1 text-[11px] text-slate-500">{gate.sub}</div>
                </div>
              );
            })}
          </div>
        </Panel>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-4 xl:grid-cols-[0.95fr_1.25fr]">
        <Panel className="p-5">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><Gauge className="h-5 w-5 text-emerald-300" /> Strategy & Model Intelligence</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4 md:col-span-1">
              <div className="text-xs text-slate-500">Top Active Strategy</div>
              <div className="mt-3 text-lg font-semibold">stock_swing</div>
              <Sparkline />
              <div className="mt-3 flex justify-between text-xs text-emerald-300"><span>Win rate</span><span>Research</span></div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4 md:col-span-1">
              <div className="text-xs text-slate-500">Research Candidates</div>
              <div className="mt-3 space-y-3">
                {researchCandidates.map((item) => (
                  <div key={item.name} className="flex items-center justify-between text-sm">
                    <span className="text-slate-300">{item.name}</span>
                    <span className="rounded-full border border-emerald-400/20 px-2 py-0.5 text-emerald-300">{item.score}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4 md:col-span-1">
              <div className="text-xs text-slate-500">Active Model</div>
              <div className="mt-3 text-sm font-semibold text-emerald-300">weighted_ranker_v1</div>
              <div className="mt-4 text-xs text-slate-500">XGBoost</div>
              <div className="mt-1 text-sm text-amber-300">Not Trained</div>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4 md:col-span-1">
              <div className="text-xs text-slate-500">LLM Role</div>
              <div className="mt-3 text-lg font-semibold">Reasoning Only</div>
              <div className="mt-2 text-xs text-slate-500">No final trade decisions. Budget gated.</div>
            </div>
          </div>
        </Panel>

        <Panel className="p-5">
          <div className="mb-4 flex items-center justify-between">
            <div className="flex items-center gap-2 text-lg font-semibold"><ListChecks className="h-5 w-5 text-emerald-300" /> Advisor Recommendations</div>
            <Link href="/recommendations" className="text-sm text-emerald-300">View All →</Link>
          </div>
          <div className="space-y-2">
            {recommendations.map((item) => (
              <div key={item.priority} className="grid grid-cols-[38px_1fr_160px_110px] items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-3 text-sm">
                <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-400/15 text-emerald-300">{item.priority}</div>
                <div>
                  <div className="text-slate-200">{item.rec}</div>
                  <div className="text-xs text-slate-500">Owner-level improvement recommendation</div>
                </div>
                <div className="text-emerald-300">{item.benefit}</div>
                <button className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 transition hover:border-emerald-400/30 hover:text-emerald-300">{item.action}</button>
              </div>
            ))}
          </div>
        </Panel>
      </div>

      <Panel className="p-5">
        <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><Zap className="h-5 w-5 text-emerald-300" /> Learning Loop & Insights</div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
          <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <BookOpen className="h-7 w-7 text-emerald-300" />
            <div className="mt-3 text-sm font-semibold text-emerald-300">Journal Lesson</div>
            <p className="mt-2 text-sm text-slate-300">Waiting for cleaner breakouts improved R:R discipline in recent reviews.</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <Trophy className="h-7 w-7 text-emerald-300" />
            <div className="mt-3 text-sm font-semibold text-emerald-300">Best Performing Strategy</div>
            <p className="mt-2 text-sm text-slate-300">stock_swing remains the active baseline until more labeled outcomes exist.</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <AlertTriangle className="h-7 w-7 text-amber-300" />
            <div className="mt-3 text-sm font-semibold text-amber-300">False Positive Watch</div>
            <p className="mt-2 text-sm text-slate-300">Opening-range ideas stay research-only until backtest and paper evidence improve.</p>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
            <FlaskConical className="h-7 w-7 text-emerald-300" />
            <div className="mt-3 text-sm font-semibold text-emerald-300">Next Research Action</div>
            <p className="mt-2 text-sm text-slate-300">Backtest pullback entries by 3x2 regime before strategy promotion.</p>
          </div>
        </div>
      </Panel>
    </Shell>
  );
}
