"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  BrainCircuit,
  Building2,
  ChevronRight,
  Crown,
  DatabaseZap,
  FlaskConical,
  Gauge,
  KeyRound,
  LineChart,
  PlugZap,
  Settings,
  Shield,
  SlidersHorizontal,
  Target,
  WalletCards,
  Zap,
} from "lucide-react";

type OwnerPageConfig = {
  key: string;
  title: string;
  href: string;
  group: string;
  icon: typeof Crown;
  purpose: string;
  hero: string;
  cards: Array<{ label: string; value: string; sub: string; tone?: string }>;
  recommendations: Array<{ priority: string; area: string; recommendation: string; benefit: string; action: string }>;
};

export const ownerPages: OwnerPageConfig[] = [
  {
    key: "pnl",
    title: "P&L Command",
    href: "/owner/pnl",
    group: "Owner Command",
    icon: LineChart,
    purpose: "What is the platform doing financially?",
    hero: "Track account value, gross P&L, platform costs, net profit, and forecasted performance.",
    cards: [
      { label: "Account Value", value: "$1,000", sub: "Broker-linked value pending", tone: "text-emerald-300" },
      { label: "Gross P&L", value: "Paper", sub: "Research mode only" },
      { label: "Total Cost", value: "Tracked", sub: "LLM + infra cost center" },
      { label: "Net Profit", value: "Pending", sub: "Needs paper/live lifecycle" },
      { label: "Cost/P&L", value: "Watch", sub: "Do not let AI cost eat edge", tone: "text-amber-300" },
      { label: "30D Forecast", value: "Blocked", sub: "Needs labeled outcomes", tone: "text-amber-300" },
    ],
    recommendations: [
      { priority: "High", area: "P&L", recommendation: "Use paper/research P&L until broker lifecycle is connected.", benefit: "Avoid fake profit", action: "Keep gated" },
      { priority: "High", area: "Cost", recommendation: "Route routine workflows to deterministic mode unless strategy conflict is detected.", benefit: "Lower AI cost", action: "Apply policy" },
      { priority: "Medium", area: "Forecast", recommendation: "Enable 7D and 30D forecasts only after enough journal outcomes exist.", benefit: "Better reliability", action: "Queue" },
    ],
  },
  {
    key: "risk",
    title: "Account Risk Center",
    href: "/owner/risk",
    group: "Owner Command",
    icon: Shield,
    purpose: "Are we risking too much relative to account goals?",
    hero: "Owner-level capital protection for a small account: risk budget, exposure, approvals, and no-trade status.",
    cards: [
      { label: "Current Risk State", value: "Caution", sub: "Small-account mode", tone: "text-amber-300" },
      { label: "Max Daily Loss", value: "$30", sub: "2-3% guardrail" },
      { label: "Max Risk/Trade", value: "$5-$10", sub: "0.5-1% target" },
      { label: "Target R/R", value: "2R+", sub: "Prefer 3R" },
      { label: "No-Trade Status", value: "Available", sub: "Can veto everything", tone: "text-emerald-300" },
      { label: "Live Trading", value: "Disabled", sub: "Read-only safety lock", tone: "text-rose-300" },
    ],
    recommendations: [
      { priority: "High", area: "Risk", recommendation: "Keep one trade/day default and two trades/day absolute max.", benefit: "Reduce churn", action: "Enforce" },
      { priority: "High", area: "Spread", recommendation: "Block execution when bid/ask is missing or spread is unknown.", benefit: "Avoid bad fills", action: "Keep blocked" },
      { priority: "Medium", area: "Watchlist", recommendation: "Reduce active setups when buying power is low.", benefit: "Focus capital", action: "Review" },
    ],
  },
  {
    key: "trading",
    title: "Trading Command Center",
    href: "/owner/trading",
    group: "Owner Command",
    icon: Target,
    purpose: "What is happening right now?",
    hero: "Live decision cockpit for holdings, watchlist, active strategy, top setup, trigger countdowns, and approval status.",
    cards: [
      { label: "Active Strategy", value: "stock_swing", sub: "Production-approved" },
      { label: "Top Setup", value: "NVDA", sub: "Awaiting trigger" },
      { label: "Market Regime", value: "Mixed", sub: "3x2 classifier pending" },
      { label: "Workflow Status", value: "Partial", sub: "Data quality degraded", tone: "text-amber-300" },
      { label: "Approval", value: "Required", sub: "Owner review" },
      { label: "Best Action", value: "Watch", sub: "No trade until spread is real", tone: "text-emerald-300" },
    ],
    recommendations: [
      { priority: "High", area: "Trigger", recommendation: "Keep top setup active only until trigger TTL expires.", benefit: "Avoid stale trades", action: "Monitor" },
      { priority: "High", area: "Execution", recommendation: "Do not rerun broker flow until data quality improves.", benefit: "Protect capital", action: "Block" },
      { priority: "Medium", area: "Regime", recommendation: "Reduce breakout confidence if QQQ breadth weakens.", benefit: "Fewer false positives", action: "Review" },
    ],
  },
  {
    key: "insights",
    title: "Advisor Insights",
    href: "/owner/insights",
    group: "Owner Command",
    icon: BrainCircuit,
    purpose: "Across the whole platform, what should I improve?",
    hero: "CEO-style recommendations across P&L, risk, cost, agents, models, strategies, data sources, journal, and backtests.",
    cards: [
      { label: "Top Improvement", value: "Data quality", sub: "Add execution-grade quotes" },
      { label: "Highest Risk", value: "Spread", sub: "Bid/ask missing", tone: "text-amber-300" },
      { label: "Best Strategy", value: "stock_swing", sub: "Active baseline" },
      { label: "Worst Bottleneck", value: "yfinance", sub: "Research-only for execution" },
      { label: "Most Costly", value: "LLM calls", sub: "Budget-gated" },
      { label: "Recommended Change", value: "Alpaca data", sub: "Critical next" },
    ],
    recommendations: [
      { priority: "High", area: "Data", recommendation: "Add Alpaca market data for bid/ask and spread validation.", benefit: "Execution readiness", action: "Build next" },
      { priority: "High", area: "Strategy", recommendation: "Pause candidate strategies from active selection until promotion evidence exists.", benefit: "Governance safe", action: "Keep policy" },
      { priority: "Medium", area: "Model", recommendation: "Train XGBoost only after 100+ labeled outcomes.", benefit: "Better ranking", action: "Queue" },
    ],
  },
  {
    key: "strategy-model-performance",
    title: "Strategy & Model Performance",
    href: "/owner/strategy-model-performance",
    group: "Performance Intelligence",
    icon: BarChart3,
    purpose: "Which strategies and models are actually working?",
    hero: "Measure strategy follow-through, false positives, model calibration, drift, cost, and net contribution.",
    cards: [
      { label: "Best Strategy", value: "stock_swing", sub: "Active baseline" },
      { label: "Worst Strategy", value: "Research TBD", sub: "Needs labels" },
      { label: "Best Model", value: "weighted_ranker_v1", sub: "Only active model" },
      { label: "XGBoost", value: "Not trained", sub: "Cannot score active trades", tone: "text-amber-300" },
      { label: "Calibration", value: "Pending", sub: "Needs outcomes" },
      { label: "Retraining", value: "Not ready", sub: "Need 100 labels" },
    ],
    recommendations: [
      { priority: "High", area: "Model", recommendation: "Keep XGBoost disabled until training/evaluation/calibration/approval gates pass.", benefit: "Avoid fake model edge", action: "Keep blocked" },
      { priority: "Medium", area: "Strategy", recommendation: "Track performance by time of day and regime before increasing scan frequency.", benefit: "Higher win rate", action: "Instrument" },
      { priority: "Medium", area: "False Positives", recommendation: "Increase liquidity penalty for low-liquidity names.", benefit: "Better signals", action: "Review" },
    ],
  },
  {
    key: "llm-cost-center",
    title: "LLM Gateway & Cost Center",
    href: "/owner/llm-cost-center",
    group: "Performance Intelligence",
    icon: Zap,
    purpose: "What are agents and LLMs costing me, and is it worth it?",
    hero: "Monitor LLM cost, tokens, model routing, agent usage, latency, failures, and recommendation quality impact.",
    cards: [
      { label: "LLM Cost Today", value: "$0", sub: "Paid calls gated" },
      { label: "Budget Remaining", value: "100%", sub: "No paid calls" },
      { label: "Cost/Workflow", value: "Low", sub: "Deterministic first" },
      { label: "Most Used", value: "None", sub: "Gateway pending" },
      { label: "LangSmith", value: "Enabled", sub: "Tracing ready" },
      { label: "Failed Calls", value: "0", sub: "Placeholder" },
    ],
    recommendations: [
      { priority: "High", area: "LLM", recommendation: "Use deterministic-only mode for routine workflows below confidence threshold.", benefit: "Save cost", action: "Apply" },
      { priority: "Medium", area: "Caching", recommendation: "Cache portfolio summaries and repeated strategy debate runs.", benefit: "Lower cost", action: "Build" },
      { priority: "Medium", area: "Research", recommendation: "Run heavy LLM summaries after-hours only.", benefit: "Hot-path speed", action: "Schedule" },
    ],
  },
  {
    key: "data-source-intelligence",
    title: "Data Source Intelligence",
    href: "/owner/data-source-intelligence",
    group: "Performance Intelligence",
    icon: DatabaseZap,
    purpose: "Is my data reliable, affordable, and scalable?",
    hero: "Owner view of provider availability, data freshness, missing fields, latency, reliability, cost, and migration priorities.",
    cards: [
      { label: "YFinance", value: "Degraded", sub: "No bid/ask", tone: "text-amber-300" },
      { label: "Alpaca Keys", value: "Configured", sub: "Execution side" },
      { label: "Polygon", value: "Pending", sub: "Critical/high" },
      { label: "Options Data", value: "Missing", sub: "High priority", tone: "text-amber-300" },
      { label: "Postgres", value: "Working", sub: "System of record" },
      { label: "pgvector", value: "Working", sub: "Memory foundation" },
    ],
    recommendations: [
      { priority: "High", area: "Data", recommendation: "Use yfinance for research only, not execution-grade spread checks.", benefit: "Data truth", action: "Keep policy" },
      { priority: "High", area: "Provider", recommendation: "Add Alpaca latest quote and bars endpoints next.", benefit: "Execution readiness", action: "Build" },
      { priority: "Medium", area: "Options", recommendation: "Add an options provider before enabling options workflows.", benefit: "Better quality", action: "Research" },
    ],
  },
  {
    key: "agentops",
    title: "AgentOps Center",
    href: "/owner/agentops",
    group: "Platform Operations",
    icon: Activity,
    purpose: "Are agents healthy, useful, expensive, or failing?",
    hero: "Management view of agent health, tool failures, latency, cost, quality, traces, and latest decisions.",
    cards: [
      { label: "Agent Health", value: "Stable", sub: "Foundation" },
      { label: "Failed Agents", value: "0", sub: "Placeholder" },
      { label: "Dry Run", value: "Enabled", sub: "Safe mode" },
      { label: "LangSmith", value: "Enabled", sub: "Tracing" },
      { label: "Tool Failures", value: "Watch", sub: "Needs deep UI" },
      { label: "Workflow Status", value: "Partial", sub: "Data gated", tone: "text-amber-300" },
    ],
    recommendations: [
      { priority: "Medium", area: "AgentOps", recommendation: "Add trace links per workflow and agent decision.", benefit: "Debug faster", action: "Build" },
      { priority: "Medium", area: "Latency", recommendation: "Keep hot path deterministic/cached.", benefit: "Faster decisions", action: "Enforce" },
      { priority: "Low", area: "Quality", recommendation: "Score each agent against follow-through outcomes.", benefit: "Better agents", action: "Queue" },
    ],
  },
  {
    key: "model-lab",
    title: "Model Lab",
    href: "/owner/model-lab",
    group: "Platform Operations",
    icon: FlaskConical,
    purpose: "Run manual simulations recommended by insights.",
    hero: "Manual lab for feature rows, model plans, blocked models, simulation history, and research actions.",
    cards: [
      { label: "Recommended Sim", value: "Pullback", sub: "3x2 regime" },
      { label: "Feature Row", value: "Pending", sub: "Provider data needed" },
      { label: "Model Plan", value: "Weighted", sub: "Baseline" },
      { label: "Blocked Models", value: "XGBoost", sub: "Not trained", tone: "text-amber-300" },
      { label: "Simulation History", value: "Partial", sub: "Foundation" },
      { label: "Next Action", value: "Backtest", sub: "Queue job" },
    ],
    recommendations: [
      { priority: "High", area: "Backtest", recommendation: "Backtest VWAP reclaim after prior-day RVOL > 3 in semiconductor stocks.", benefit: "Strategy evidence", action: "Create job" },
      { priority: "Medium", area: "Model", recommendation: "Do not run XGBoost active scoring until trained artifact exists.", benefit: "Safety", action: "Keep blocked" },
      { priority: "Medium", area: "Research", recommendation: "Send high false-positive strategies to research queue.", benefit: "Improve quality", action: "Queue" },
    ],
  },
  {
    key: "risk-capital-execution",
    title: "Risk, Capital & Execution",
    href: "/owner/risk-capital-execution",
    group: "Execution & Learning",
    icon: WalletCards,
    purpose: "Capital allocation, trade plans, paper trades, and execution safety.",
    hero: "Management-focused execution page for buying power, capital at risk, best use of capital, stale capital, and paper trade lifecycle.",
    cards: [
      { label: "Buying Power", value: "$1,000", sub: "Paper/research" },
      { label: "Capital at Risk", value: "$0", sub: "No live trades" },
      { label: "Best Use", value: "Wait", sub: "Data degraded", tone: "text-emerald-300" },
      { label: "Paper Trades", value: "Pending", sub: "Lifecycle next" },
      { label: "Execution", value: "Dry-run", sub: "Broker gated" },
      { label: "Kill Switch", value: "Ready", sub: "Policy foundation" },
    ],
    recommendations: [
      { priority: "High", area: "Execution", recommendation: "Connect approved recommendations to TradeNow manual ticket before broker paper submission.", benefit: "Controlled flow", action: "Build" },
      { priority: "High", area: "Capital", recommendation: "Preserve capital when R/R is below 2R or spread is unknown.", benefit: "Account protection", action: "Enforce" },
      { priority: "Medium", area: "Paper", recommendation: "Add order lifecycle states before paper automation.", benefit: "Auditability", action: "Build" },
    ],
  },
  {
    key: "research-memory-journal",
    title: "Research, Memory & Journal",
    href: "/owner/research-memory-journal",
    group: "Execution & Learning",
    icon: BookOpen,
    purpose: "The learning system for research, backtests, memory, journal, and outcome labels.",
    hero: "Turn every recommendation, skipped setup, blocked trade, and paper trade into a private learning dataset.",
    cards: [
      { label: "Research Questions", value: "Open", sub: "Strategy queue" },
      { label: "Backtests", value: "Pending", sub: "Engine next" },
      { label: "Journal Lessons", value: "Active", sub: "Outcome labeling" },
      { label: "Memory Hits", value: "pgvector", sub: "Foundation" },
      { label: "Labels Needed", value: "100+", sub: "For XGBoost" },
      { label: "Training Readiness", value: "Not ready", sub: "Need outcomes", tone: "text-amber-300" },
    ],
    recommendations: [
      { priority: "High", area: "Journal", recommendation: "Label the last recommendations before training any model.", benefit: "Better ML", action: "Label" },
      { priority: "Medium", area: "Memory", recommendation: "Compare current setups against similar past regimes.", benefit: "Personal edge", action: "Build search" },
      { priority: "Medium", area: "Backtest", recommendation: "Review false positives from midday breakout strategy.", benefit: "Fewer bad trades", action: "Analyze" },
    ],
  },
  {
    key: "settings",
    title: "Owner Settings",
    href: "/owner/settings",
    group: "Settings",
    icon: Settings,
    purpose: "Safety controls, integrations, API keys, runtime config, budgets, strategy overrides, and agent config.",
    hero: "Owner-facing controls for auto-run, pause all, paper trading, human approval, daily budgets, and strategy overrides.",
    cards: [
      { label: "Auto-run", value: "Off", sub: "Owner controlled" },
      { label: "Pause All", value: "Available", sub: "Emergency stop" },
      { label: "Paper Trading", value: "Gated", sub: "Approval required" },
      { label: "Human Approval", value: "Required", sub: "Do not remove" },
      { label: "Daily LLM Budget", value: "Set", sub: "Cost control" },
      { label: "Allowed Strategies", value: "Governed", sub: "Research separated" },
    ],
    recommendations: [
      { priority: "High", area: "Safety", recommendation: "Keep live trading disabled until full paper lifecycle is proven.", benefit: "Protect capital", action: "Keep disabled" },
      { priority: "High", area: "Approval", recommendation: "Keep human approval required for all order paths.", benefit: "Safety", action: "Enforce" },
      { priority: "Medium", area: "Budget", recommendation: "Set daily agent and LLM run limits before market-open scanning.", benefit: "Cost control", action: "Configure" },
    ],
  },
];

export function getOwnerPageConfig(key: string) {
  return ownerPages.find((page) => page.key === key) ?? ownerPages[0];
}

function ownerGroups() {
  const grouped = new Map<string, OwnerPageConfig[]>();
  ownerPages.forEach((page) => grouped.set(page.group, [...(grouped.get(page.group) ?? []), page]));
  return Array.from(grouped.entries());
}

function Sparkline() {
  return (
    <svg viewBox="0 0 120 42" className="h-12 w-28 text-emerald-300" aria-hidden="true">
      <path d="M4 32 C16 22, 24 28, 34 19 S55 13, 66 22 S84 34, 94 15 S108 7, 116 13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function MetricCard({ card }: { card: OwnerPageConfig["cards"][number] }) {
  return (
    <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_35px_rgba(0,0,0,0.25)] backdrop-blur">
      <div className="text-xs text-slate-500">{card.label}</div>
      <div className={`mt-3 text-2xl font-semibold tracking-tight ${card.tone ?? "text-white"}`}>{card.value}</div>
      <div className="mt-2 flex items-center justify-between gap-2 text-xs text-slate-500">
        <span>{card.sub}</span>
        <Sparkline />
      </div>
    </div>
  );
}

export function OwnerPlatformShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-emerald-950 text-white">
      <aside className="flex min-h-screen w-80 shrink-0 flex-col border-r border-emerald-400/10 bg-[#05080d] px-4 py-5 shadow-[18px_0_60px_rgba(0,0,0,0.45)]">
        <Link href="/owner" className="mb-8 flex items-center gap-3 px-1">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-400/50 bg-emerald-400/10 text-xl font-black text-emerald-300 shadow-[0_0_28px_rgba(16,185,129,0.25)]">E</div>
          <div>
            <div className="text-2xl font-semibold tracking-tight text-emerald-300">Owner Command</div>
            <div className="text-xs text-slate-500">Executive platform</div>
          </div>
        </Link>

        <nav className="space-y-5 overflow-y-auto pr-1">
          {ownerGroups().map(([group, pages]) => (
            <div key={group}>
              <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">{group}</div>
              <div className="space-y-1.5">
                {pages.map((page) => {
                  const Icon = page.icon;
                  const active = pathname === page.href || (page.href === "/owner/pnl" && pathname === "/owner");
                  return (
                    <Link
                      key={page.href}
                      href={page.href}
                      className={`group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium transition-all ${
                        active
                          ? "border border-emerald-400/40 bg-emerald-400/10 text-white shadow-[0_0_28px_rgba(16,185,129,0.12)]"
                          : "text-slate-300 hover:bg-white/[0.04] hover:text-emerald-200"
                      }`}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="flex-1">{page.title}</span>
                      <ChevronRight className="h-3 w-3 text-slate-600" />
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>
      </aside>
      <main className="relative min-h-screen flex-1 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_62%_0%,rgba(16,185,129,0.16),transparent_28%),radial-gradient(circle_at_0%_100%,rgba(20,184,166,0.08),transparent_28%)]" />
        <div className="absolute right-0 top-0 h-72 w-[55rem] rounded-full border-t border-emerald-300/30 blur-[0.2px]" />
        <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(16,185,129,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.06)_1px,transparent_1px)] [background-size:54px_54px]" />
        <div className="relative z-10 p-8">{children}</div>
      </main>
    </div>
  );
}

export function OwnerPageTemplate({ page }: { page: OwnerPageConfig }) {
  const Icon = page.icon;

  return (
    <OwnerPlatformShell>
      <header className="mb-7 flex items-start justify-between gap-6">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
            <Icon className="h-4 w-4" />
            {page.group}
          </div>
          <h1 className="text-4xl font-black tracking-[-0.04em] text-white">{page.title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">{page.purpose}</p>
        </div>
        <Link href="/command-center" className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
          Open Engineering Console
        </Link>
      </header>

      <section className="mb-4 rounded-2xl border border-emerald-400/15 bg-black/35 p-6 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
        <div className="flex items-center gap-5">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-400/10 text-emerald-300">
            <Icon className="h-8 w-8" />
          </div>
          <div>
            <div className="text-sm font-medium text-emerald-300">Owner-level answer</div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">{page.hero}</h2>
          </div>
        </div>
      </section>

      <section className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
        {page.cards.map((card) => <MetricCard key={card.label} card={card} />)}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.05fr_1.25fr]">
        <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><Gauge className="h-5 w-5 text-emerald-300" /> Trend, forecast, and breakdown</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="text-xs text-slate-500">Current state</div>
              <div className="mt-3 text-xl font-semibold text-white">Source-backed / clearly labeled</div>
              <p className="mt-3 text-sm leading-6 text-slate-400">This owner page follows the management pattern: current state, trend, forecast, insight, and action.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="text-xs text-slate-500">Forecast</div>
              <div className="mt-3 text-xl font-semibold text-amber-300">Pending evidence</div>
              <p className="mt-3 text-sm leading-6 text-slate-400">Forecasts remain placeholders until broker lifecycle, costs, and labeled outcomes are connected.</p>
            </div>
          </div>
          <div className="mt-4 h-52 rounded-xl border border-white/10 bg-[linear-gradient(180deg,rgba(16,185,129,0.08),rgba(0,0,0,0.15))] p-5">
            <div className="text-xs text-slate-500">Illustrative trend panel</div>
            <svg viewBox="0 0 600 160" className="mt-6 h-36 w-full text-emerald-300" aria-hidden="true">
              <path d="M8 130 C80 92, 122 112, 176 76 S278 58, 332 88 S430 132, 486 54 S560 34, 592 48" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
        </div>

        <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><SlidersHorizontal className="h-5 w-5 text-emerald-300" /> Advisor recommendations</div>
          <div className="space-y-2">
            {page.recommendations.map((row) => (
              <div key={`${row.priority}-${row.area}-${row.action}`} className="grid grid-cols-[74px_120px_1fr_150px_110px] items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-3 text-sm">
                <div className="rounded-full border border-emerald-400/20 px-3 py-1 text-center text-xs text-emerald-300">{row.priority}</div>
                <div className="text-slate-400">{row.area}</div>
                <div className="text-slate-200">{row.recommendation}</div>
                <div className="text-emerald-300">{row.benefit}</div>
                <button className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 transition hover:border-emerald-400/30 hover:text-emerald-300">{row.action}</button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </OwnerPlatformShell>
  );
}
