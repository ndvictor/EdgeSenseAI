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
  DatabaseZap,
  FlaskConical,
  Gauge,
  LineChart,
  Settings,
  TrendingUp,
  WalletCards,
} from "lucide-react";

const items = [
  { label: "Account Risk Center", href: "/account-risk", icon: WalletCards },
  { label: "Command Center", href: "/command-center", icon: Gauge },
  { label: "Live Watchlist", href: "/live-watchlist", icon: BellRing },
  { label: "Edge Signals", href: "/edge-signals", icon: Activity },
  { label: "Model Lab", href: "/model-lab", icon: FlaskConical },
  { label: "Data Sources", href: "/data-sources", icon: DatabaseZap },
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
    <aside className="sticky top-1 h-screen w-68 shrink-0 bg-slate-950 px-1 py-2">
      <Link href="/command-center" className="mb-8 flex items-center gap-3">
        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-emerald-600 text-slate-950 text-xl tracking-tight font-black">E</div>
        <div>
          <div className="text-2xl tracking-tight text-emerald-400">EdgeSenseAI</div>
          <div className="text-xs text-slate-500">Edge intelligence</div>
        </div>
      </Link>

      <div className="mb-3 px-3 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-300">Workspaces</div>
      
      <nav className="space-y-1">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-4 rounded-2xl px-2 py-2 text-sm font-semibold transition-all ${
                active 
                  ? "border border-emerald-800 bg-slate-700 text-emerald-400" 
                  : "text-slate-300 hover:bg-slate-600 hover:text-emerald-600"
              }`}
            >
              <span className={`flex h-9 w-9 items-center justify-center rounded-xl border transition-colors ${
                active 
                  ? "border-emerald-600 bg-slate-600" 
                  : "border-emerald-500 bg-slate-800 text-emerald-700"
              }`}>
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
