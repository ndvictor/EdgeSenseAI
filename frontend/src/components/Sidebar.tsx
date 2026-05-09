"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  BookOpen,
  FlaskConical,
  Home,
  ShieldCheck,
  Workflow,
  BriefcaseBusiness,
  Settings,
} from "lucide-react";

type NavItem = { label: string; href: string; icon: any; activeAlso?: string[]; children?: Array<{ label: string; href: string }> };

const MAIN_ITEMS: NavItem[] = [
  { label: "Home", href: "/", icon: Home },
  {
    label: "Autonomous Day-Trading",
    href: "/daytrading-workflow",
    icon: Workflow,
    children: [
      { label: "Home", href: "/daytrading-workflow" },
      { label: "Command Center", href: "/daytrading-workflow/command-center" },
      { label: "Workflow", href: "/daytrading-workflow/workflow" },
      { label: "Live Watchlist", href: "/daytrading-workflow/live-watchlist" },
      { label: "Data Pipeline", href: "/daytrading-workflow/data-pipeline" },
      { label: "Strategy & Models", href: "/daytrading-workflow/strategy-models" },
      { label: "Qlib & Evidence", href: "/daytrading-workflow/qlib-evidence" },
      { label: "Execution & Approval", href: "/daytrading-workflow/execution-approval" },
      { label: "Issues / Debug", href: "/daytrading-workflow/issues-debug" },
    ],
  },
  {
    label: "Legacy Manual Trading",
    href: "/manual-trading",
    icon: BriefcaseBusiness,
    activeAlso: [
      "/tradenow",
      "/trading-desk",
      "/command-center",
      "/candidate-engine",
      "/candidates",
      "/edge-signals",
      "/auto-execution-monitor",
    ],
  },
  {
    label: "Lab",
    href: "/lab",
    icon: FlaskConical,
    activeAlso: ["/qlib", "/model/lab", "/research-lab"],
  },
  { label: "Owner", href: "/owner", icon: Settings },
  { label: "Ops", href: "/ops", icon: ShieldCheck },
  { label: "Settings", href: "/settings", icon: BookOpen },
];

function navItemActive(pathname: string, searchParams: ReturnType<typeof useSearchParams>, item: NavItem): boolean {
  const activeAlso = item.activeAlso?.some((p) => pathname === p || pathname.startsWith(`${p}/`)) ?? false;
  if (item.href === "/qlib") {
    const tab = searchParams.get("tab");
    const onQlibTab = pathname === "/research-evidence" && (tab === null || tab === "" || tab === "qlib");
    return pathname === "/qlib" || pathname.startsWith(`${item.href}/`) || onQlibTab;
  }
  return pathname === item.href || pathname.startsWith(`${item.href}/`) || activeAlso;
}

export function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  return (
    <aside className="flex min-h-screen w-68 shrink-0 flex-col border-r border-emerald-400/10 bg-[#05080d] px-3 py-5">
      <Link href="/" className="mb-8 flex items-center gap-3 px-1">
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
          const active = navItemActive(pathname, searchParams, item);
          return (
            <div key={item.href}>
              <Link
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
              {active && item.children?.length ? (
                <div className="ml-12 mt-1 space-y-1 border-l border-emerald-400/10 pl-3">
                  {item.children.map((child) => {
                    const childActive = pathname === child.href;
                    return (
                      <Link
                        key={child.href}
                        href={child.href}
                        className={`block rounded-lg px-2 py-1.5 text-xs transition ${
                          childActive ? "bg-emerald-400/10 text-emerald-100" : "text-slate-500 hover:bg-white/[0.04] hover:text-emerald-200"
                        }`}
                      >
                        {child.label}
                      </Link>
                    );
                  })}
                </div>
              ) : null}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
