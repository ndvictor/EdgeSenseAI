"use client";

import Link from "next/link";
import { Activity, Crown, DatabaseZap, Gauge, LogIn, Settings, TrendingUp, Waves } from "lucide-react";

const ticker = [
  { label: "SPY", value: "530.74", change: "+0.68%", positive: true },
  { label: "QQQ", value: "458.21", change: "+0.74%", positive: true },
  { label: "VIX", value: "14.82", change: "-1.33%", positive: false },
];

export default function Home() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-[#03070b] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(16,185,129,0.18),transparent_28%),radial-gradient(circle_at_0%_20%,rgba(20,184,166,0.12),transparent_30%),radial-gradient(circle_at_100%_20%,rgba(16,185,129,0.10),transparent_30%)]" />
      <div className="absolute inset-0 opacity-35 [background-image:linear-gradient(rgba(16,185,129,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.08)_1px,transparent_1px)] [background-size:64px_64px]" />
      <div className="pointer-events-none absolute left-[12%] top-[18%] h-[52rem] w-[52rem] rounded-full border border-emerald-400/10" />
      <div className="pointer-events-none absolute right-[8%] top-[16%] h-[48rem] w-[48rem] rounded-full border border-emerald-400/10" />
      <div className="pointer-events-none absolute left-1/2 top-[42%] h-px w-[80rem] -translate-x-1/2 bg-gradient-to-r from-transparent via-emerald-300/50 to-transparent shadow-[0_0_80px_rgba(16,185,129,0.45)]" />
      <div className="pointer-events-none absolute left-[8%] top-[30%] h-[34rem] w-[60rem] rotate-[18deg] rounded-[100%] border-t border-emerald-300/30 blur-[0.2px]" />
      <div className="pointer-events-none absolute right-[2%] top-[26%] h-[34rem] w-[60rem] -rotate-[18deg] rounded-[100%] border-t border-emerald-300/30 blur-[0.2px]" />

      <div className="relative z-10 flex min-h-screen flex-col px-10 py-7">
        <header className="flex items-center justify-end gap-5">
          <Link
            href="/login"
            className="flex items-center gap-2 rounded-xl border border-emerald-400/25 bg-emerald-400/[0.06] px-4 py-2 text-sm font-semibold text-emerald-300 backdrop-blur transition hover:border-emerald-300/60 hover:bg-emerald-400/10"
          >
            <LogIn className="h-4 w-4" />
            Login
          </Link>
          <div className="flex h-10 w-10 items-center justify-center rounded-full border border-white/10 bg-white/[0.03] text-slate-300">N</div>
        </header>

        <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col items-center justify-center pb-20 text-center">
          <div className="mb-8 inline-flex items-center gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.05] px-6 py-3 text-sm font-medium text-emerald-300 shadow-[0_0_35px_rgba(16,185,129,0.10)]">
            <Activity className="h-4 w-4" />
            AI-Powered. Data-Driven. Edge-Guided.
          </div>

          <h1 className="text-7xl font-black tracking-[-0.07em] md:text-8xl">
            <span className="bg-gradient-to-b from-emerald-300 via-emerald-500 to-emerald-900 bg-clip-text text-transparent">Edge</span>
            <span className="bg-gradient-to-b from-white via-slate-100 to-slate-500 bg-clip-text text-transparent">SenseAI</span>
          </h1>
          <p className="mt-7 max-w-3xl text-2xl leading-relaxed text-slate-300">
            Personal trading intelligence operating system for account growth, risk control, and high-quality trade selection.
          </p>

          <div className="mt-12 flex w-full max-w-md flex-col gap-5">
            <Link
              href="/login?next=/command-center"
              className="rounded-2xl border border-emerald-300/20 bg-gradient-to-b from-emerald-400 to-emerald-700 px-8 py-5 text-lg font-semibold text-white shadow-[0_18px_60px_rgba(16,185,129,0.26)] transition hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(16,185,129,0.34)]"
            >
              Open Command Center →
            </Link>
            <Link
              href="/login?next=/owner"
              className="rounded-2xl border border-emerald-400/35 bg-black/40 px-8 py-5 text-lg font-semibold text-emerald-300 shadow-[0_0_40px_rgba(16,185,129,0.10)] backdrop-blur transition hover:-translate-y-0.5 hover:bg-emerald-400/10"
            >
              Open Owner Command Center →
            </Link>
          </div>

          <div className="mt-16 grid w-full max-w-5xl grid-cols-1 gap-6 md:grid-cols-2">
            <Link href="/login?next=/owner" className="group rounded-3xl border border-emerald-400/20 bg-black/35 p-7 text-left backdrop-blur transition hover:border-emerald-300/45 hover:bg-emerald-400/[0.06]">
              <div className="flex items-start gap-5">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-400/10 text-emerald-300">
                  <Crown className="h-8 w-8" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-emerald-300">Owner Command</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-300">Executive dashboards, portfolio oversight, and strategic decision intelligence.</p>
                  <p className="mt-6 text-sm font-medium text-emerald-300">Open Owner Command Center →</p>
                </div>
              </div>
            </Link>
            <Link href="/login?next=/command-center" className="group rounded-3xl border border-emerald-400/20 bg-black/35 p-7 text-left backdrop-blur transition hover:border-emerald-300/45 hover:bg-emerald-400/[0.06]">
              <div className="flex items-start gap-5">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-400/10 text-emerald-300">
                  <Settings className="h-8 w-8" />
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-emerald-300">Platform Operations</h2>
                  <p className="mt-3 text-sm leading-6 text-slate-300">Manage agents, data pipelines, models, and platform performance.</p>
                  <p className="mt-6 text-sm font-medium text-emerald-300">Open Command Center →</p>
                </div>
              </div>
            </Link>
          </div>
        </main>

        <footer className="relative mx-auto mb-2 grid w-full max-w-7xl grid-cols-1 overflow-hidden rounded-2xl border border-white/10 bg-black/35 p-5 backdrop-blur md:grid-cols-6">
          {ticker.map((item) => (
            <div key={item.label} className="flex items-center gap-4 border-b border-white/10 py-2 md:border-b-0 md:border-r md:border-white/10 md:px-5">
              <TrendingUp className="h-5 w-5 text-emerald-300" />
              <div className="text-left">
                <div className="text-xs text-slate-400">{item.label}</div>
                <div className="text-sm text-white">{item.value}</div>
                <div className={`text-xs ${item.positive ? "text-emerald-300" : "text-rose-400"}`}>{item.change}</div>
              </div>
            </div>
          ))}
          <div className="flex items-center gap-4 border-b border-white/10 py-2 md:border-b-0 md:border-r md:border-white/10 md:px-5">
            <Gauge className="h-5 w-5 text-emerald-300" />
            <div className="text-left"><div className="text-xs text-slate-400">System Status</div><div className="text-sm text-emerald-300">Operational</div></div>
          </div>
          <div className="flex items-center gap-4 border-b border-white/10 py-2 md:border-b-0 md:border-r md:border-white/10 md:px-5">
            <DatabaseZap className="h-5 w-5 text-emerald-300" />
            <div className="text-left"><div className="text-xs text-slate-400">Data Feeds</div><div className="text-sm text-emerald-300">Live & Syncing</div></div>
          </div>
          <div className="flex items-center gap-4 py-2 md:px-5">
            <Waves className="h-5 w-5 text-emerald-300" />
            <div className="text-left"><div className="text-xs text-slate-400">Last Updated</div><div className="text-sm text-slate-200">10:42:31 AM ET</div></div>
          </div>
        </footer>
      </div>
    </div>
  );
}
