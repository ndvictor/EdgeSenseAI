"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BarChart3,
  BookOpen,
  BrainCircuit,
  Cpu,
  Crosshair,
  DatabaseZap,
  Gauge,
  Inbox,
  Radar,
  Route,
  Scale,
  ScrollText,
  BadgeCheck,
  BellRing,
  ClipboardCheck,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Microscope,
  Target,
  Users,
  Zap,
} from "lucide-react";

type NavItem = { label: string; href: string; icon: any };

const MAIN_SECTIONS: Array<{ title: string; items: NavItem[] }> = [
  {
    title: "Command Center",
    items: [
      { label: "Command Center", href: "/command-center", icon: SlidersHorizontal },
      { label: "Platform Readiness", href: "/platform-readiness", icon: ShieldCheck },
      { label: "Agent Runtime", href: "/agent-runtime", icon: Cpu },
    ],
  },
  {
    title: "Market Radar",
    items: [
      { label: "Market Regime", href: "/market-regime", icon: BarChart3 },
      { label: "Data Sources", href: "/data-sources", icon: DatabaseZap },
      { label: "Data Quality", href: "/data-quality", icon: Radar },
      { label: "Candidates Engine", href: "/candidate-engine", icon: Users },
      { label: "Live Watchlist", href: "/live-watchlist", icon: Crosshair },
    ],
  },
  {
    title: "Research Lab",
    items: [
      { label: "Session Router", href: "/session-router", icon: Route },
      { label: "Workflow Router", href: "/workflow-router", icon: Route },
      { label: "Strategy Eligibility", href: "/strategy-eligibility", icon: BadgeCheck },
    ],
  },
  {
    title: "Strategy Workflow",
    items: [
      { label: "Workflow Runbook", href: "/workflow-runbook", icon: Route },
      { label: "Trigger Monitoring", href: "/trigger-monitoring", icon: BellRing },
      { label: "Execution Planner", href: "/execution-planner", icon: ClipboardCheck },
      { label: "Position Monitoring", href: "/position-monitoring", icon: Crosshair },
    ],
  },
  {
    title: "Trading Desk",
    items: [
      { label: "TradeNow", href: "/tradenow", icon: Zap },
      { label: "Auto-Execution Monitor", href: "/auto-execution-monitor", icon: ClipboardCheck },
      { label: "Close Position", href: "/close-position", icon: Target },
    ],
  },
  {
    title: "Performance & Governance",
    items: [
      { label: "Approval Queue", href: "/approval-queue", icon: Inbox },
      { label: "Audit Log", href: "/audit-log", icon: ScrollText },
      { label: "Workflow Governance", href: "/workflow-governance", icon: Scale },
      { label: "Post-Trade Evaluation", href: "/post-trade-evaluation", icon: Microscope },
      { label: "Learning Loop", href: "/learning-loop", icon: BrainCircuit },
    ],
  },
];

const SETTINGS_ITEMS: NavItem[] = [
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Archive", href: "/edgesense/archive", icon: BookOpen },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-68 shrink-0 flex-col border-r border-emerald-400/10 bg-[#05080d] px-3 py-5">
      <Link href="/command-center" className="mb-8 flex items-center gap-3 px-1">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-emerald-400/50 bg-emerald-400/10 text-xl font-black tracking-tight text-emerald-300">
          E
        </div>
        <div>
          <div className="text-2xl font-semibold tracking-tight text-emerald-300">EdgeSenseAI</div>
          <div className="text-xs text-slate-500">Edge intelligence</div>
        </div>
      </Link>

      <nav className="flex-1 space-y-4 overflow-y-auto pr-1">
        {MAIN_SECTIONS.map((section) => (
          <div key={section.title}>
            <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">
              {section.title}
            </div>
            <div className="space-y-1.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium transition-all ${
                      active
                        ? "border border-emerald-400/40 bg-emerald-400/10 text-white"
                        : "text-slate-300 hover:bg-white/[0.04] hover:text-emerald-200"
                    }`}
                  >
                    <span
                      className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                        active
                          ? "border-emerald-400/60 bg-emerald-400/10 text-emerald-300"
                          : "border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400"
                      }`}
                    >
                      <Icon className="h-4 w-4" />
                    </span>
                    {item.label}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-4 border-t border-emerald-400/10 pt-4">
        <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">Settings</div>
        <div className="space-y-1.5">
          {SETTINGS_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium transition-all ${
                  active ? "border border-emerald-400/40 bg-emerald-400/10 text-white" : "text-slate-300 hover:bg-white/[0.04] hover:text-emerald-200"
                }`}
              >
                <span
                  className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                    active ? "border-emerald-400/60 bg-emerald-400/10 text-emerald-300" : "border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400"
                  }`}
                >
                  <Icon className="h-4 w-4" />
                </span>
                {item.label}
              </Link>
            );
          })}
        </div>
      </div>
    </aside>
  );
}
