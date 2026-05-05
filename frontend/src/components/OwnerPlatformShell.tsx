"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  BrainCircuit,
  ChevronRight,
  Crown,
  DatabaseZap,
  FlaskConical,
  Gauge,
  LineChart,
  Settings,
  Shield,
  SlidersHorizontal,
  Target,
  WalletCards,
  Zap,
  Terminal,
} from "lucide-react";
import { useAdminDashboardBundle } from "@/hooks/useAdminDashboardBundle";
import { buildInsightTexts, buildOwnerCards, buildRecommendationRows, type DashboardCard } from "@/lib/adminDashboardDerived";

type OwnerPageConfig = {
  key: string;
  title: string;
  href: string;
  group: string;
  icon: typeof Crown;
  purpose: string;
  hero: string;
};

export const ownerPages: OwnerPageConfig[] = [
  {
    key: "pnl",
    title: "P&L Command",
    href: "/owner/pnl",
    group: "Owner Command",
    icon: LineChart,
    purpose: "What is the platform doing financially?",
    hero: "Account risk profile, Alpaca paper snapshot, LLM gateway costs, and journal outcome summary from live APIs.",
  },
  {
    key: "risk",
    title: "Account Risk Center",
    href: "/owner/risk",
    group: "Owner Command",
    icon: Shield,
    purpose: "Are we risking too much relative to account goals?",
    hero: "Risk percentages and guardrails from /api/account-risk/profile plus auto-run safety flags.",
  },
  {
    key: "trading",
    title: "Trading Command Center",
    href: "/owner/trading",
    group: "Owner Command",
    icon: Target,
    purpose: "What is happening right now?",
    hero: "Command center payload, strategy ranking, regime services, live watchlist, and top action — all from backend routes.",
  },
  {
    key: "insights",
    title: "Advisor Insights",
    href: "/owner/insights",
    group: "Owner Command",
    icon: BrainCircuit,
    purpose: "Across the whole platform, what should I improve?",
    hero: "Rolls up readiness, research queue, data-source health, registry summary, LLM budget gate, and journal stats.",
  },
  {
    key: "strategy-model-performance",
    title: "Strategy & Model Performance",
    href: "/owner/strategy-model-performance",
    group: "Performance Intelligence",
    icon: BarChart3,
    purpose: "Which strategies and models are actually working?",
    hero: "Latest strategy ranking, model selection, and performance drift records — no mock win rates.",
  },
  {
    key: "llm-cost-center",
    title: "LLM Gateway & Cost Center",
    href: "/owner/llm-cost-center",
    group: "Performance Intelligence",
    icon: Zap,
    purpose: "What are agents and LLMs costing?",
    hero: "LLM gateway costs/status plus AI ops LLM usage snapshot.",
  },
  {
    key: "data-source-intelligence",
    title: "Data Source Intelligence",
    href: "/owner/data-source-intelligence",
    group: "Performance Intelligence",
    icon: DatabaseZap,
    purpose: "Is my data reliable and configured?",
    hero: "Identical provider truth as /data-sources, pulled from /api/data-sources/status.",
  },
  {
    key: "agentops",
    title: "AgentOps Center",
    href: "/owner/agentops",
    group: "Platform Operations",
    icon: Activity,
    purpose: "Are agents healthy and instrumented?",
    hero: "Core agent registry, AI ops scorecards, tracing settings, and command-center agent rows.",
  },
  {
    key: "model-lab",
    title: "Model Lab",
    href: "/owner/model-lab",
    group: "Platform Operations",
    icon: FlaskConical,
    purpose: "What can we run or simulate next?",
    hero: "Model registry payload, backtesting summary, latest model selection, and drift status.",
  },
  {
    key: "risk-capital-execution",
    title: "Risk, Capital & Execution",
    href: "/owner/risk-capital-execution",
    group: "Execution & Learning",
    icon: WalletCards,
    purpose: "Capital allocation, paper broker, and execution flags.",
    hero: "Latest capital allocation run, Alpaca paper snapshot, and auto-run controls.",
  },
  {
    key: "research-memory-journal",
    title: "Research, Memory & Journal",
    href: "/owner/research-memory-journal",
    group: "Execution & Learning",
    icon: BookOpen,
    purpose: "Learning loop status.",
    hero: "Journal summary, research-priority tasks, vector memory fields from AI ops, and drift recommendations.",
  },
  {
    key: "settings",
    title: "Owner Settings",
    href: "/owner/settings",
    group: "Settings",
    icon: Settings,
    purpose: "Safety controls and budgets as stored server-side.",
    hero: "Live view of /api/auto-run/status and /api/settings (read-only here).",
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

function MetricCard({ card }: { card: DashboardCard }) {
  return (
    <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_35px_rgba(0,0,0,0.25)] backdrop-blur">
      <div className="text-xs text-slate-500">{card.label}</div>
      <div className={`mt-3 text-2xl font-semibold tracking-tight ${card.tone ?? "text-white"}`}>{card.value}</div>
      <div className="mt-2 text-xs text-slate-500">{card.sub}</div>
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

        <div className="mt-auto border-t border-emerald-400/10 pt-6">
          <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">Platform</div>
          <div className="space-y-1.5">
            <Link
              href="/data-sources"
              className="group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/[0.04] hover:text-emerald-200"
            >
              <DatabaseZap className="h-4 w-4 text-emerald-400" />
              <span className="flex-1">Data Sources</span>
            </Link>
            <Link
              href="/command-center"
              className="group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/[0.04] hover:text-emerald-200"
            >
              <Terminal className="h-4 w-4 text-emerald-400" />
              <span className="flex-1">Engineering Console</span>
            </Link>
          </div>
        </div>
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
  const { bundle, loading, loadError, refetch } = useAdminDashboardBundle();
  const cards = buildOwnerCards(page.key, bundle);
  const recommendations = buildRecommendationRows("owner", page.key, bundle);
  const insight = buildInsightTexts("owner", page.key, bundle);

  return (
    <OwnerPlatformShell>
      <header className="mb-7 flex flex-wrap items-start justify-between gap-6">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
            <Icon className="h-4 w-4" />
            {page.group}
          </div>
          <h1 className="text-4xl font-black tracking-[-0.04em] text-white">{page.title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">{page.purpose}</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => void refetch()}
            className="rounded-xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm text-emerald-200 transition hover:bg-emerald-400/20"
          >
            Refresh data
          </button>
          <Link href="/command-center" className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
            Engineering Console
          </Link>
          <Link href="/data-sources" className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
            Data Sources
          </Link>
        </div>
      </header>

      {loadError && (
        <div className="mb-4 rounded-xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{loadError}</div>
      )}

      <section className="mb-4 rounded-2xl border border-emerald-400/15 bg-black/35 p-6 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
        <div className="flex items-center gap-5">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-400/10 text-emerald-300">
            <Icon className="h-8 w-8" />
          </div>
          <div>
            <div className="text-sm font-medium text-emerald-300">API-backed owner view</div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">{page.hero}</h2>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="py-16 text-center text-sm text-slate-400">Loading live platform endpoints…</div>
      ) : (
        <>
          <section className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
            {cards.map((card) => (
              <MetricCard key={`${page.key}-${card.label}`} card={card} />
            ))}
          </section>

          <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.05fr_1.25fr]">
            <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
              <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
                <Gauge className="h-5 w-5 text-emerald-300" /> Live context
              </div>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <div className="text-xs text-slate-500">{insight.stateTitle}</div>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{insight.stateBody}</p>
                </div>
                <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
                  <div className="text-xs text-slate-500">{insight.forecastTitle}</div>
                  <p className="mt-3 text-sm leading-6 text-slate-300">{insight.forecastBody}</p>
                </div>
              </div>
              <div className="mt-4 rounded-xl border border-white/10 bg-white/[0.025] p-4">
                <div className="text-xs text-slate-500">{insight.detailTitle}</div>
                <p className="mt-3 text-sm leading-6 text-slate-300">{insight.detailBody || "—"}</p>
              </div>
            </div>

            <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
              <div className="mb-4 flex items-center gap-2 text-lg font-semibold">
                <SlidersHorizontal className="h-5 w-5 text-emerald-300" /> Advisor queue
              </div>
              <div className="space-y-2">
                {recommendations.map((row) => (
                  <div
                    key={`${row.priority}-${row.area}-${row.recommendation.slice(0, 24)}`}
                    className="grid grid-cols-1 items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-3 text-sm lg:grid-cols-[74px_100px_1fr_120px_100px]"
                  >
                    <div className="rounded-full border border-emerald-400/20 px-3 py-1 text-center text-xs text-emerald-300">{row.priority}</div>
                    <div className="text-slate-400">{row.area}</div>
                    <div className="text-slate-200">{row.recommendation}</div>
                    <div className="text-emerald-300">{row.benefit}</div>
                    {row.action.startsWith("/") ? (
                      <Link
                        href={row.action}
                        className="rounded-lg border border-white/10 px-3 py-2 text-center text-slate-200 transition hover:border-emerald-400/30 hover:text-emerald-300"
                      >
                        Open
                      </Link>
                    ) : (
                      <span className="rounded-lg border border-white/5 px-3 py-2 text-center text-slate-500">{row.action}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </OwnerPlatformShell>
  );
}
