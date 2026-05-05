"use client";

import { Suspense } from "react";
import Link from "next/link";
import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Activity, ArrowLeft, Crown, Gauge, LogIn, Monitor, ShieldCheck } from "lucide-react";

function getSafeNext(next: string | null) {
  if (next === "/command-center" || next === "/owner" || next === "/ops") return next;
  return "/owner";
}

function getDestinationLabel(next: string | null) {
  if (next === "/command-center") return "Command Center";
  if (next === "/ops") return "Ops Command Center";
  return "Owner Command Center";
}

function LoginContent() {
  const searchParams = useSearchParams();
  const next = getSafeNext(searchParams.get("next"));
  const destinationLabel = getDestinationLabel(searchParams.get("next"));

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#03070b] text-white">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_45%,rgba(16,185,129,0.18),transparent_28%),radial-gradient(circle_at_0%_20%,rgba(20,184,166,0.12),transparent_30%),radial-gradient(circle_at_100%_20%,rgba(16,185,129,0.10),transparent_30%)]" />
      <div className="absolute inset-0 opacity-35 [background-image:linear-gradient(rgba(16,185,129,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.08)_1px,transparent_1px)] [background-size:64px_64px]" />
      <div className="pointer-events-none absolute left-[8%] top-[28%] h-[34rem] w-[60rem] rotate-[18deg] rounded-[100%] border-t border-emerald-300/30" />
      <div className="pointer-events-none absolute right-[2%] top-[24%] h-[34rem] w-[60rem] -rotate-[18deg] rounded-[100%] border-t border-emerald-300/30" />

      <div className="relative z-10 flex min-h-screen flex-col px-8 py-7">
        <header className="flex items-center justify-between">
          <Link href="/" className="inline-flex items-center gap-3 text-sm font-semibold text-slate-300 transition hover:text-emerald-300">
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>
          <div className="flex items-center gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.04] px-4 py-2 text-sm text-emerald-300">
            <Activity className="h-4 w-4" />
            Secure owner login
          </div>
        </header>

        <main className="mx-auto flex w-full max-w-6xl flex-1 items-center justify-center py-16">
          <div className="grid w-full grid-cols-1 gap-8 lg:grid-cols-[1fr_0.92fr]">
            <section className="flex flex-col justify-center">
              <div className="mb-8 inline-flex w-fit items-center gap-3 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.05] px-5 py-3 text-sm font-medium text-emerald-300">
                <Crown className="h-4 w-4" />
                EdgeSenseAI Private Access
              </div>
              <h1 className="max-w-3xl text-6xl font-black tracking-[-0.06em] text-white">
                Sign in to your trading decision OS.
              </h1>
              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
                Continue to {destinationLabel}. The platform keeps your public landing page separate from your owner and operations workspaces.
              </p>
              <div className="mt-10 grid max-w-2xl grid-cols-1 gap-4 md:grid-cols-3">
                {[
                  [ShieldCheck, "Risk-gated", "Human approval remains required."],
                  [Gauge, "Mode-aware", "Owner and operations routes stay separate."],
                  [Crown, "Personal", "Built around your account growth."],
                ].map(([Icon, title, description]) => {
                  const TypedIcon = Icon as typeof ShieldCheck;
                  return (
                    <div key={String(title)} className="rounded-2xl border border-white/10 bg-black/35 p-4 backdrop-blur">
                      <TypedIcon className="h-6 w-6 text-emerald-300" />
                      <div className="mt-4 text-sm font-semibold text-white">{title as string}</div>
                      <p className="mt-2 text-xs leading-5 text-slate-400">{description as string}</p>
                    </div>
                  );
                })}
              </div>
            </section>

            <section className="rounded-3xl border border-emerald-400/20 bg-black/45 p-8 shadow-[0_0_70px_rgba(0,0,0,0.45)] backdrop-blur">
              <div className="mb-8 flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-emerald-400/40 bg-emerald-400/10 text-xl font-black text-emerald-300">E</div>
                <div>
                  <div className="text-2xl font-semibold tracking-tight text-emerald-300">EdgeSenseAI</div>
                  <div className="text-xs text-slate-500">Owner access gateway</div>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/[0.025] p-5">
                <div className="text-sm text-slate-500">Destination</div>
                <div className="mt-2 text-xl font-semibold text-white">{destinationLabel}</div>
                <div className="mt-2 text-sm text-slate-400">After sign-in, you will be routed to {next}.</div>
              </div>

              <button
                onClick={() => signIn("google", { callbackUrl: next })}
                className="mt-7 flex w-full items-center justify-center gap-3 rounded-2xl border border-emerald-300/20 bg-gradient-to-b from-emerald-400 to-emerald-700 px-6 py-5 text-base font-semibold text-white shadow-[0_18px_60px_rgba(16,185,129,0.26)] transition hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(16,185,129,0.34)]"
              >
                <LogIn className="h-5 w-5" />
                Log in with Google
              </button>

              <div className="mt-6 rounded-2xl border border-amber-300/20 bg-amber-300/[0.04] p-4 text-sm leading-6 text-amber-100/80">
                Google auth uses placeholder environment variables until you add your real Google OAuth client ID and secret.
              </div>

              <div className="mt-6 border-t border-white/10 pt-6">
                <div className="mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">Other Access Points</div>
                <div className="grid grid-cols-1 gap-2 text-sm">
                  <Link href="/login?next=/owner" className="flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
                    <Crown className="h-4 w-4" />
                    <span>Owner Command Center</span>
                  </Link>
                  <Link href="/login?next=/command-center" className="flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
                    <Gauge className="h-4 w-4" />
                    <span>Engineering Console</span>
                  </Link>
                  <Link href="/login?next=/ops" className="flex items-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-slate-300 transition hover:border-amber-400/30 hover:text-amber-300">
                    <Monitor className="h-4 w-4" />
                    <span>Ops Command Center</span>
                  </Link>
                </div>
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#03070b]" />}>
      <LoginContent />
    </Suspense>
  );
}
