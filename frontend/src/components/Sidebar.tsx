"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Crosshair,
  DatabaseZap,
  FlaskConical,
  Gauge,
  Radar,
  RefreshCw,
  Rocket,
  Route,
  Clock,
  BadgeCheck,
  BellRing,
  ClipboardCheck,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  TestTube2,
  Users,
  WalletCards,
  Zap,
} from "lucide-react";

const items = [
  { label: "Ops Center", href: "/ops-center", icon: SlidersHorizontal },
  { label: "Market Regime", href: "/market-regime", icon: BarChart3 },
  { label: "Data Sources", href: "/data-sources", icon: DatabaseZap },
  { label: "Data Quality", href: "/data-quality", icon: Activity },
  { label: "Signals Engine", href: "/signal-engine", icon: Radar },
  { label: "Candidates Engine", href: "/candidate-engine", icon: Users },
  { label: "Model", href: "/model", icon: FlaskConical },
  { label: "LLM Gateway", href: "/llm-gateway", icon: Gauge },
  { label: "Strategies", href: "/strategies", icon: Rocket },
  { label: "Strategy Eligibility", href: "/strategy-eligibility", icon: BadgeCheck },
  { label: "Trigger Monitoring", href: "/trigger-monitoring", icon: BellRing },
  { label: "Execution Planner", href: "/execution-planner", icon: ClipboardCheck },
  { label: "Backtesting", href: "/backtesting", icon: ClipboardList },
  { label: "Recommendations", href: "/recommendations", icon: Target },
  { label: "Paper Trading", href: "/paper-trading", icon: BrainCircuit },
  { label: "TradeNow", href: "/tradenow", icon: Zap },
  { label: "Auto-Execution Monitor", href: "/auto-execution-monitor", icon: SlidersHorizontal },
  { label: "Live Watchlist", href: "/live-watchlist", icon: Crosshair },
  { label: "Position Monitoring", href: "/position-monitoring", icon: Crosshair },
  { label: "Close Position", href: "/close-position", icon: ClipboardList },
  { label: "Journal", href: "/journal", icon: BookOpen },
  { label: "Learning Loop", href: "/learning-loop", icon: RefreshCw },
  { label: "Platform Readiness", href: "/platform-readiness", icon: ShieldCheck },
  { label: "Session Router", href: "/session-router", icon: Clock },
  { label: "Workflow Router", href: "/workflow-router", icon: Route },
  { label: "Lab Platform", href: "/lab", icon: TestTube2 },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-68 shrink-0 flex-col border-r border-emerald-400/10 bg-[#05080d] px-3 py-5">
      <Link href="/ops-center" className="mb-8 flex items-center gap-3 px-1">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/50 bg-emerald-400/10 text-xl font-black tracking-tight text-emerald-300">
          E
        </div>
        <div>
          <div className="text-2xl font-semibold tracking-tight text-emerald-300">EdgeSenseAI</div>
          <div className="text-xs text-slate-500">Edge intelligence</div>
        </div>
      </Link>

      <div className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">Workspaces</div>

      <nav className="space-y-1.5 overflow-y-auto pr-1">
        {items.map((item) => {
          const Icon = item.icon;
          const isAiOps = item.href === "/ai-ops";
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium transition-all ${
                active
                  ? isAiOps
                    ? "border border-emerald-400/45 bg-emerald-400/12 text-emerald-100"
                    : "border border-emerald-400/40 bg-emerald-400/10 text-white"
                  : "text-slate-300 hover:bg-white/[0.04] hover:text-emerald-200"
              }`}
            >
              <span
                className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                  active
                    ? isAiOps
                      ? "border-emerald-300/70 bg-emerald-300/10 text-emerald-200"
                      : "border-emerald-400/60 bg-emerald-400/10 text-emerald-300"
                    : "border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400"
                }`}
              >
                <Icon className="h-4 w-4" />
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
