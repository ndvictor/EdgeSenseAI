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
    <aside className="sticky top-1 h-screen w-68 shrink-0 bg-slate-800 px-4 py-2">
      <Link href="/command-center" className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-500 text-white/80 text-xl tracking-tight font-black">E</div>
        <div>
          <div className="text-xl font-black tracking-tight text-emerald-400">EdgeSenseAI</div>
          <div className="text-xs text-emerald-600">small-account edge intelligence</div>
        </div>
      </Link>

      <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.28em] text-emerald-400">Workspaces</div>
      
      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-2xl px-2 py-2 text-sm font-semibold transition-all ${
                active 
                  ? "border border-emerald-400 bg-emerald-700 text-white" 
                  : "text-emerald-400 hover:bg-slate-500 hover:text-emerald-900"
              }`}
            >
              <span className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                active 
                  ? "border-white/30 bg-white/10" 
                  : "border-emerald-500 bg-slate-600 text-emerald-300"
              }`}>
                <Icon className="h-4 w-4" />
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="absolute bottom-6 left-4 right-4 rounded-2xl border border-emerald-700 bg-slate-800 p-1 text-xs text-emerald-400">
        <div className="font-bold text-emerald-500">Research / paper mode</div>
        <p className="mt-0 text-emerald-400">No live execution. Agents notify; risk layer validates.</p>
      </div>
    </aside>
  );
}