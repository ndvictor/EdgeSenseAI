"use client";

import { useEffect, useState } from "react";
import { api, type JournalSummary } from "@/lib/api";
import { MetricCard, PageHeader } from "@/components/Cards";

export default function JournalPage() {
  const [data, setData] = useState<JournalSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getJournalSummary().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="learning loop"
          title="Journal"
          description="Journal outcomes close the learning loop. Every recommendation should eventually become a labeled outcome for backtesting, scorecards, and ranker calibration."
        />

        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-200">{error}</div>}

        {!data ? (
          <div className="py-8 text-center text-sm text-slate-300">Loading journal...</div>
        ) : (
          <div className="space-y-4">
            <section className="rounded-xl border border-emerald-800 bg-slate-950 p-4 shadow-sm">
              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <MetricCard label="Entries" value={data.total_entries} accent />
                <MetricCard label="Pending Reviews" value={data.pending_reviews} />
                <MetricCard label="Winning Labels" value={data.winning_labels} />
                <MetricCard label="Losing Labels" value={data.losing_labels} />
              </div>
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Recommendation Outcome Log</h2>
              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full min-w-[1200px] text-left text-sm">
                  <thead className="bg-slate-900 text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      <th className="px-4 py-3">ID</th>
                      <th className="px-4 py-3">Symbol</th>
                      <th className="px-4 py-3">Setup</th>
                      <th className="px-4 py-3">Action</th>
                      <th className="px-4 py-3">Entry</th>
                      <th className="px-4 py-3">Stop</th>
                      <th className="px-4 py-3">Target</th>
                      <th className="px-4 py-3">Outcome</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 bg-slate-950">
                    {data.entries.map((entry) => (
                      <tr key={entry.id} className="hover:bg-slate-900">
                        <td className="px-4 py-3 text-slate-400">{entry.id}</td>
                        <td className="px-4 py-3 font-bold text-cyan-300">{entry.symbol}</td>
                        <td className="max-w-md px-4 py-3 text-slate-300">{entry.setup}</td>
                        <td className="px-4 py-3 text-emerald-300">{entry.planned_action}</td>
                        <td className="px-4 py-3 text-slate-300">{entry.entry_zone}</td>
                        <td className="px-4 py-3 text-slate-300">{entry.stop}</td>
                        <td className="px-4 py-3 text-slate-300">{entry.target}</td>
                        <td className="px-4 py-3 text-amber-300">{entry.outcome_label}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="grid grid-cols-1 gap-4 xl:grid-cols-2">
              {data.entries.map((entry) => (
                <article key={`${entry.id}-lesson`} className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
                  <h3 className="text-lg font-bold text-white">{entry.symbol} Learning Note</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-300">{entry.lesson}</p>
                  <p className="mt-3 text-xs uppercase tracking-wide text-emerald-500">Status: {entry.status.replace(/_/g, " ")}</p>
                </article>
              ))}
            </section>

            <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
              <h2 className="mb-3 text-lg font-semibold text-emerald-500">Next Steps</h2>
              <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
                {data.next_steps.map((step) => (
                  <div key={step} className="rounded-lg border border-slate-800 bg-slate-900 px-4 py-3 text-sm leading-relaxed text-slate-300">{step}</div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
