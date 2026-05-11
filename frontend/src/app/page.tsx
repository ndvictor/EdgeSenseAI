"use client";

import Link from "next/link";

import { DeepAgentsCommandSidebar } from "@/components/deepagents/DeepAgentsCommandSidebar";

export default function Home() {
  return (
    <div className="flex min-h-screen bg-[#02080d] text-slate-100">
      <DeepAgentsCommandSidebar data={null} loading={false} />
      <main className="relative min-h-screen min-w-0 flex-1 overflow-y-auto">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_30%_15%,rgba(34,211,238,0.10),transparent_30%),radial-gradient(circle_at_85%_25%,rgba(16,185,129,0.08),transparent_28%)]" />
        <div className="relative mx-auto flex min-h-[calc(100vh-4rem)] w-full max-w-5xl flex-col justify-center px-5 py-8 lg:px-10">
          <section className="rounded-[2rem] border border-cyan-400/15 bg-[#04111a]/85 p-8 shadow-[0_30px_120px_rgba(0,0,0,0.45)] backdrop-blur">
            <div className="mb-5 inline-flex rounded-full border border-cyan-400/20 bg-cyan-400/10 px-4 py-1.5 text-xs font-bold uppercase tracking-[0.22em] text-cyan-200">
              EdgeSenseAI
            </div>
            <h1 className="max-w-3xl text-4xl font-black tracking-[-0.04em] text-white lg:text-6xl">DeepAgents Control Tower</h1>
            <p className="mt-5 max-w-3xl text-base leading-7 text-slate-400">
              Clean, read-only access to the autonomous paper trading loop: agent chain, simulated orders, paper positions,
              learning outcomes, and alerts. Legacy workspaces have been moved out of this app surface.
            </p>

            <Link
              href="/EdgeSenseAI"
              className="mt-8 inline-flex w-fit rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-5 py-3 text-sm font-bold text-cyan-100 transition hover:border-cyan-300/50 hover:bg-cyan-400/20"
            >
              Open Control Tower →
            </Link>

            <div className="mt-8 flex flex-wrap gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">
              <span className="rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-emerald-200">Paper only</span>
              <span className="rounded-full border border-cyan-400/20 bg-cyan-400/10 px-3 py-1 text-cyan-200">Real data</span>
              <span className="rounded-full border border-rose-400/20 bg-rose-400/10 px-3 py-1 text-rose-200">Broker blocked</span>
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
