"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const GROUPS = [
  {
    label: "Command",
    items: [
      { label: "Control Tower", href: "/daytrading-workflow/control-tower" },
      { label: "Command Center", href: "/daytrading-workflow/command-center" },
      { label: "Open Positions", href: "/daytrading-workflow/command-center#open-positions", muted: true },
      { label: "Paper Accounts", href: "/daytrading-workflow/command-center#paper-accounts", muted: true },
    ],
  },
  {
    label: "Autonomous Pipeline",
    items: [
      { label: "Workflow", href: "/daytrading-workflow/control-tower" },
      { label: "Agents", href: "/daytrading-workflow/control-tower" },
      { label: "Live Watchlist", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Data Pipeline", href: "/daytrading-workflow/control-tower", muted: true },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "Strategy & Models", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Alpha Explorer", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Market Regime", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Feature Monitor", href: "/daytrading-workflow/control-tower", muted: true },
    ],
  },
  {
    label: "Risk & Approval",
    items: [
      { label: "Risk Guardrails", href: "/daytrading-workflow/command-center" },
      { label: "Approval Gates", href: "/daytrading-workflow/command-center" },
      { label: "Compliance Monitor", href: "/daytrading-workflow/control-tower", muted: true },
    ],
  },
  {
    label: "Learning Loop",
    items: [
      { label: "Evaluator", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Learning Loop", href: "/daytrading-workflow/control-tower" },
      { label: "Promotion Center", href: "/daytrading-workflow/control-tower", muted: true },
    ],
  },
  {
    label: "Diagnostics",
    items: [
      { label: "System Health", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Issues / Debug", href: "/daytrading-workflow/control-tower", muted: true },
      { label: "Audit Logs", href: "/daytrading-workflow/control-tower", muted: true },
    ],
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const showOperatorShell = pathname.startsWith("/daytrading-workflow");

  if (!showOperatorShell) return <>{children}</>;

  return (
    <div className="flex min-h-screen bg-[#02080d] text-slate-100">
      <aside className="hidden h-screen w-[282px] shrink-0 overflow-y-auto border-r border-cyan-950/40 bg-[#030a0f] px-3 py-5 xl:block">
        <div className="mb-6 rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.04] p-4">
          <div className="text-[11px] font-black uppercase tracking-[0.22em] text-cyan-200">EdgeSenseAI</div>
          <div className="mt-1 text-lg font-black text-white">Operator Console</div>
          <p className="mt-2 text-xs leading-5 text-slate-500">Read-only and control-only UI over backend truth.</p>
        </div>

        {GROUPS.map((group) => (
          <div key={group.label} className="mb-5">
            <div className="mb-2 px-2 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{group.label}</div>
            <nav className="space-y-1">
              {group.items.map((item) => {
                const active = pathname === item.href || (!item.href.includes("#") && pathname.startsWith(item.href));
                return (
                  <Link
                    key={`${group.label}-${item.label}`}
                    href={item.href}
                    className={`flex items-center justify-between rounded-xl px-3 py-2 text-sm transition ${
                      active
                        ? "bg-cyan-400/10 text-white ring-1 ring-cyan-400/20"
                        : item.muted
                          ? "text-slate-600 hover:bg-white/[0.03] hover:text-slate-400"
                          : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
                    }`}
                  >
                    <span>{item.label}</span>
                    {item.muted ? <span className="rounded border border-slate-600/40 px-1.5 py-0.5 text-[9px] uppercase text-slate-500">view</span> : null}
                  </Link>
                );
              })}
            </nav>
          </div>
        ))}

        <div className="mt-6 rounded-2xl border border-amber-400/25 bg-amber-400/[0.07] p-4">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-amber-200">Safe Mode</div>
          <div className="mt-2 text-xs font-bold uppercase tracking-[0.14em] text-slate-200">Paper Only Unless Backend Confirms Otherwise</div>
          <p className="mt-2 text-xs leading-5 text-slate-500">Broker submission remains blocked unless backend gates explicitly allow it.</p>
        </div>
      </aside>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
