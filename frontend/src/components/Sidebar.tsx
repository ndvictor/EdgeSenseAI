"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  BookOpen,
  BrainCircuit,
  Database,
  Import,
  Layers2,
  ListChecks,
  Rss,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Radar,
  FlaskConical,
  Workflow,
  BriefcaseBusiness,
} from "lucide-react";

type NavItem = { label: string; href: string; icon: any; activeAlso?: string[] };

const MAIN_ITEMS: NavItem[] = [
  { label: "Command Center", href: "/command-center", icon: SlidersHorizontal },
  { label: "Agent Runtime", href: "/agent-runtime", icon: BrainCircuit },
  { label: "Market Radar", href: "/market-radar", icon: Radar },
  { label: "Data source", href: "/datasource", icon: Database, activeAlso: ["/data-sources"] },
  { label: "Data ingestion", href: "/data-ingestion", icon: Import },
  { label: "Data feed", href: "/data-feed", icon: Rss },
  { label: "Data validation", href: "/data-quality", icon: ListChecks },
  { label: "Feature pipeline", href: "/feature-pipeline", icon: Layers2 },
  { label: "Research Lab", href: "/research-lab", icon: FlaskConical },
  { label: "Strategy Workflow", href: "/strategy-workflow", icon: Workflow },
  { label: "Workflow Runbook", href: "/workflow-runbook", icon: BookOpen },
  { label: "Trading Desk", href: "/trading-desk", icon: BriefcaseBusiness },
  { label: "Performance & Governance", href: "/performance-governance", icon: ShieldCheck },
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

      <nav className="flex-1 space-y-1.5 overflow-y-auto pr-1">
        {MAIN_ITEMS.map((item) => {
          const Icon = item.icon;
          const activeAlso = item.activeAlso?.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ?? false;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`) || activeAlso;
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
      </nav>
    </aside>
  );
}
