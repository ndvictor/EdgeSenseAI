"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  BrainCircuit,
  Crosshair,
  Gauge,
  Radar,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
} from "lucide-react";

type NavItem = { label: string; href: string; icon: any };

const WORKFLOW_NAV_ITEMS: NavItem[] = [
  { label: "Command Center", href: "/command-center", icon: SlidersHorizontal },
  { label: "Market Radar", href: "/candidate-engine", icon: Radar },
  { label: "Research Lab", href: "/research-evidence", icon: BrainCircuit },
  { label: "Strategy Workflow", href: "/workflow-runbook", icon: Gauge },
  { label: "Trading Desk", href: "/paper-trading", icon: Crosshair },
  { label: "Performance & Governance", href: "/approval-queue", icon: ShieldCheck },
  { label: "Settings", href: "/settings", icon: Settings },
  { label: "Archive", href: "/edgesense/archive", icon: BookOpen },
];

const ACTIVE_ROUTE_GROUPS: Record<string, string[]> = {
  "/command-center": ["/command-center", "/platform-readiness", "/agent-runtime"],
  "/candidate-engine": ["/candidate-engine", "/market-regime", "/live-watchlist", "/signals", "/universe", "/candidates"],
  "/research-evidence": ["/research-evidence", "/backtesting", "/model/lab"],
  "/workflow-runbook": ["/workflow-runbook", "/data-quality", "/session-router", "/workflow-router", "/strategy-eligibility", "/trigger-monitoring", "/execution-planner"],
  "/paper-trading": ["/paper-trading", "/recommendations", "/tradenow", "/position-monitoring", "/close-position"],
  "/approval-queue": ["/approval-queue", "/audit-log", "/workflow-governance", "/auto-execution-monitor", "/post-trade-evaluation", "/learning-loop"],
  "/settings": ["/settings", "/data-sources"],
  "/edgesense/archive": ["/edgesense/archive"],
};

function isItemActive(pathname: string, href: string): boolean {
  const routes = ACTIVE_ROUTE_GROUPS[href] ?? [href];
  return routes.some((route) => pathname === route || pathname.startsWith(`${route}/`));
}

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
          <div className="text-xs text-slate-500">Workflow spine</div>
        </div>
      </Link>

      <nav className="flex-1 space-y-2 overflow-y-auto pr-1">
        <div className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">Main</div>
        {WORKFLOW_NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const active = isItemActive(pathname, item.href);
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
      </nav>
    </aside>
  );
}
