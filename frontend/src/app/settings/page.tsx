"use client";

import { useEffect, useState } from "react";
import { api, type ModelStatusResponse } from "@/lib/api";
import { PageHeader } from "@/components/Cards";

export default function SettingsPage() {
  const [data, setData] = useState<ModelStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getModelStatus().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="configuration and model readiness"
          title="Settings"
          description="Track data readiness, model availability, alerts, and safety gates. This page makes the statistical prediction stack visible instead of hiding it behind vague dashboard text."
        />

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading model readiness...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-emerald-500">Data Mode</p>
                  <p className="mt-2 text-2xl font-black text-white">{data.data_mode.replace(/_/g, " ")}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-emerald-500">Live Prediction</p>
                  <p className="mt-2 text-2xl font-black text-white">{data.live_prediction_enabled ? "Enabled" : "Disabled"}</p>
                </div>
                <div className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <p className="text-xs uppercase tracking-wide text-emerald-500">Execution</p>
                  <p className="mt-2 text-2xl font-black text-white">Paper only</p>
                </div>
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Statistical Model Readiness</h2>
              <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
                {data.models.map((model) => (
                  <div key={model.name} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                    <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                      <div>
                        <h3 className="text-lg font-bold text-white">{model.name}</h3>
                        <p className="text-sm uppercase tracking-wide text-emerald-500">{model.category.replace(/_/g, " ")}</p>
                      </div>
                      <span className="w-fit rounded-full border border-amber-500 bg-amber-500/10 px-3 py-1 text-xs font-bold uppercase text-amber-300">
                        {model.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-slate-300">{model.purpose}</p>
                    <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
                      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Current Mode</p>
                        <p className="mt-1 text-sm text-slate-300">{model.current_mode}</p>
                      </div>
                      <div className="rounded-lg border border-slate-800 bg-slate-950 p-3">
                        <p className="text-xs uppercase tracking-wide text-slate-500">Next Step</p>
                        <p className="mt-1 text-sm text-slate-300">{model.next_step}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
