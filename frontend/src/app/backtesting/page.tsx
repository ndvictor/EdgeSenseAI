"use client";

import { useEffect, useState } from "react";
import { api, type BacktestingResponse } from "@/lib/api";
import { PageHeader } from "@/components/Cards";

export default function BacktestingPage() {
  const [data, setData] = useState<BacktestingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getBacktestingSummary().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="model validation"
          title="Backtesting"
          description="Backtesting validates whether signals actually work for small accounts. The objective is not accuracy. It is expectancy, target-before-stop behavior, drawdown control, and account survivability."
        />

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading backtesting plan...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <p className="text-xs uppercase tracking-wide text-emerald-500">Mode</p>
              <h2 className="mt-2 text-3xl font-black text-white">{data.mode.replace(/_/g, " ")}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-300">
                Backtest profiles define how the platform will prove that recommendations are actionable and not just attractive-looking signals.
              </p>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {data.profiles.map((profile) => (
                <article key={profile.profile_name} className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-xs uppercase tracking-wide text-emerald-500">{profile.horizon}</p>
                      <h2 className="mt-1 text-2xl font-black text-white">{profile.profile_name}</h2>
                    </div>
                    <span className="w-fit rounded-full border border-amber-500 bg-amber-500/10 px-3 py-1 text-xs font-bold uppercase text-amber-300">
                      {profile.status.replace(/_/g, " ")}
                    </span>
                  </div>

                  <p className="mt-3 text-sm leading-relaxed text-slate-300">{profile.objective}</p>

                  <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                    {profile.metrics.map((metric) => (
                      <div key={metric.name} className="rounded-lg border border-slate-800 bg-slate-900 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">{metric.name}</p>
                        <p className="mt-1 text-lg font-bold text-white">{metric.value}</p>
                        <p className="mt-1 text-xs text-slate-400">{metric.status}</p>
                      </div>
                    ))}
                  </div>

                  <div className="mt-4 rounded-lg border border-slate-800 bg-slate-900 p-3">
                    <h3 className="text-sm font-semibold text-emerald-500">Next Steps</h3>
                    <ul className="mt-2 space-y-2 text-sm leading-relaxed text-slate-300">
                      {profile.next_steps.map((step) => (
                        <li key={step}>• {step}</li>
                      ))}
                    </ul>
                  </div>
                </article>
              ))}
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
