"use client";

import { PageHeader } from "@/components/Cards";
import { StockSearchChart } from "@/components/StockSearchChart";

export default function StocksPage() {
  return (
    <div className="min-h-screen bg-slate-500 p-4 lg:p-6">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="stocks data workspace"
          title="Stocks"
          description="Search a ticker, select a data source, and inspect source-backed price history. Prototype model/risk workflows are preserved in Model Lab and backend endpoints, but this page no longer shows hardcoded AMD model values as dashboard truth."
        />

        <div className="space-y-4">
          <StockSearchChart />

          <section className="rounded-xl border border-slate-700 bg-slate-950 p-4 shadow-sm">
            <h2 className="mb-3 text-lg font-semibold text-emerald-500">Stock Workflow Guardrails</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {[
                ["Source First", "The chart and metrics must come from the selected source. Auto uses configured real providers only. Mock is explicit testing only."],
                ["Feature Pipeline", "Feature/model/risk workflows must run from source-backed feature rows, not hardcoded AMD defaults."],
                ["Actionable Output", "A buy/watch decision should only appear after source data, feature agents, trained model scoring, and risk checks pass."],
              ].map(([title, body]) => (
                <div key={title} className="rounded-xl border border-slate-800 bg-slate-900 p-4">
                  <h3 className="text-lg font-bold text-white">{title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-slate-400">{body}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
