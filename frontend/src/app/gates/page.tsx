"use client";

import Link from "next/link";

import { DeepAgentsCommandSidebar } from "@/components/deepagents/DeepAgentsCommandSidebar";
import { GateSettingsPanel } from "@/components/edgesense/GateSettingsPanel";

export default function TradingGatesPage() {
  return (
    <div className="flex min-h-screen bg-[#02080d] text-slate-100">
      <DeepAgentsCommandSidebar data={null} loading={false} />
      <main className="relative min-h-screen min-w-0 flex-1 overflow-y-auto">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_15%,rgba(34,211,238,0.10),transparent_30%),radial-gradient(circle_at_85%_25%,rgba(16,185,129,0.08),transparent_28%)]" />
        <div className="relative mx-auto max-w-[1280px] px-5 py-7">
          <header className="mb-6 flex flex-col gap-4 rounded-3xl border border-cyan-400/15 bg-[#04111a]/85 p-6 shadow-[0_30px_120px_rgba(0,0,0,0.45)] backdrop-blur sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">EdgeSenseAI</p>
              <h1 className="mt-2 text-2xl font-black tracking-tight text-white sm:text-3xl">Trading gates</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                Effective runtime gates from the backend (<span className="font-mono text-slate-500">GET /api/v1/daytrading/settings/gates</span>
                ). This view is the same panel as on the Control Tower, on its own route for quick access.
              </p>
            </div>
            <nav className="flex flex-wrap items-center gap-2 text-xs font-bold uppercase tracking-[0.12em]">
              <Link
                href="/"
                className="rounded-lg border border-white/10 bg-white/[0.03] px-3 py-2 text-slate-300 transition hover:border-cyan-400/30 hover:text-cyan-100"
              >
                Home
              </Link>
              <Link
                href="/EdgeSenseAI"
                className="rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-3 py-2 text-cyan-100 transition hover:bg-cyan-400/20"
              >
                Control Tower
              </Link>
            </nav>
          </header>

          <GateSettingsPanel />
        </div>
      </main>
    </div>
  );
}
