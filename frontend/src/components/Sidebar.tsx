"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BellRing,
  Bitcoin,
  BookOpen,
  BrainCircuit,
  ClipboardList,
  Gauge,
  LineChart,
  Newspaper,
  Settings,
  ShieldCheck,
  TrendingUp,
  WalletCards,
} from "lucide-react";

const items = [
  { label: "Account Risk Center", href: "/account-risk", icon: WalletCards },
  { label: "Command Center", href: "/command-center", icon: Gauge },
  { label: "Live Watchlist", href: "/live-watchlist", icon: BellRing },
  { label: "Edge Signals", href: "/edge-signals", icon: Activity },
  { label: "Stocks", href: "/stocks", icon: TrendingUp },
  { label: "Options", href: "/options", icon: LineChart },
  { label: "Bitcoin / Crypto", href: "/crypto", icon: Bitcoin },
  { label: "Market Regime", href: "/market-regime", icon: BarChart3 },
  { label: "Backtesting", href: "/backtesting", icon: ClipboardList },
  { label: "Paper Trading", href: "/paper-trading", icon: BrainCircuit },
  { label: "Journal", href: "/journal", icon: BookOpen },
  { label: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sticky top-0 h-screen w-72 shrink-0 border-r border-white/10 bg-slate-950/90 px-4 py-5 backdrop-blur">
      <Link href="/command-center" className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-400 text-slate-950 font-black">E</div>
        <div>
          <div className="text-xl font-black tracking-tight text-white">EdgeSenseAI</div>
          <div className="text-xs text-cyan-200">small-account edge intelligence</div>
        </div>
      </Link>

      <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">Workspaces</div>
      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-semibold transition ${
                active ? "bg-emerald-500 text-white" : "text-slate-300 hover:bg-white/5 hover:text-white"
              }`}
            >
              <span className={`flex h-9 w-9 items-center justify-center rounded-xl border ${active ? "border-white/20 bg-white/10" : "border-white/10 bg-slate-900"}`}>
                <Icon className="h-4 w-4" />
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-5 left-4 right-4 rounded-2xl border border-cyan-500/20 bg-cyan-500/10 p-4 text-xs text-cyan-100">
        <div className="font-bold text-cyan-200">Research / paper mode</div>
        <p className="mt-1 text-cyan-100/70">No live execution. Agents notify; risk layer validates.</p>
      </div>
    </aside>
  );
}
