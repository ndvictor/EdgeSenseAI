"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BellRing,
  BookOpen,
  Brain,
  BrainCircuit,
  Crown,
  FlaskConical,
  Gauge,
  Globe,
  Home,
  Radar,
  Rocket,
  Settings,
  Target,
  Users,
  WalletCards,
  Zap,
} from "lucide-react";

const items = [
  { label: "Home", href: "/", icon: Home },
  { label: "Account Risk Center", href: "/account-risk", icon: WalletCards },
  { label: "Owner Command Center", href: "/owner", icon: Crown },
  { label: "Command Center", href: "/command-center", icon: Gauge },
  { label: "TradeNow", href: "/tradenow", icon: Zap },
  { label: "Strategies", href: "/strategies", icon: Rocket },
  { label: "Universe", href: "/universe", icon: Globe },
  { label: "Strategy Lab", href: "/strategy-lab", icon: Brain },
  { label: "Signals", href: "/signals", icon: Radar },
  { label: "Recommendations", href: "/recommendations", icon: Target },
  { label: "Candidates", href: "/candidates", icon: Users },
  { label: "Agent Ops Center", href: "/ai-ops", icon: BrainCircuit },
  { label: "LLM Gateway", href: "/llm-gateway", icon: Gauge },
  { label: "Live Watchlist", href: "/live-watchlist", icon: BellRing },
  { label: "Edge Signals", href: "/edge-signals", icon: Activity },
  { label: "Model Lab", href: "/model-lab", icon: FlaskConical },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex min-h-screen w-68 shrink-0 flex-col border-r border-emerald-400/10 bg-[#05080d] px-3 py-5 shadow-[18px_0_60px_rgba(0,0,0,0.45)]">
      <Link href="/" className="mb-9 flex items-center gap-3 px-1">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-400/50 bg-emerald-400/10 text-xl font-black tracking-tight text-emerald-300 shadow-[0_0_28px_rgba(16,185,129,0.25)]">
          E
        </div>
        <div>
          <div className="text-2xl font-semibold tracking-tight text-emerald-300">EdgeSenseAI</div>
          <div className="text-xs text-slate-500">Edge intelligence</div>
        </div>
      </Link>

      <div className="mb-3 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-400">Workspaces</div>

      <nav className="space-y-1.5">
        {items.map((item) => {
          const Icon = item.icon;
          const active = pathname === item.href || (item.href !== "/" && pathname.startsWith(`${item.href}/`));

          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium transition-all ${
                active
                  ? "border border-emerald-400/40 bg-emerald-400/10 text-white shadow-[0_0_28px_rgba(16,185,129,0.12)]"
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

      <div className="mt-auto space-y-3 pt-8">
        <div className="h-px bg-gradient-to-r from-transparent via-emerald-400/20 to-transparent" />
        <Link
          href="/settings"
          className="flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/[0.04] hover:text-emerald-200"
        >
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400">
            <Settings className="h-4 w-4" />
          </span>
          Settings
        </Link>
        <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.03] p-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-slate-600 text-sm font-semibold text-white">N</div>
          <div>
            <div className="text-sm text-slate-200">Owner</div>
            <div className="text-xs text-emerald-300">Pro Plan</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
