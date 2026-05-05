"use client";

import { StrategiesPanel } from "@/components/StrategiesPanel";
import { StrategyRegistrySummaryPane } from "@/components/StrategyRegistrySummary";
import { useState } from "react";

export default function StrategiesPage() {
  const [tab, setTab] = useState<"stages" | "registry_summary">("stages");

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px] space-y-4">
        <div className="flex flex-nowrap gap-2 overflow-x-auto whitespace-nowrap pr-2 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
          <button
            type="button"
            onClick={() => setTab("stages")}
            className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              tab === "stages"
                ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
            }`}
          >
            Strategy stages
          </button>
          <button
            type="button"
            onClick={() => setTab("registry_summary")}
            className={`shrink-0 rounded-xl px-4 py-2 text-sm font-semibold transition ${
              tab === "registry_summary"
                ? "border border-emerald-400/40 bg-emerald-500/15 text-emerald-200 shadow-[0_0_20px_rgba(16,185,129,0.12)]"
                : "border border-transparent text-slate-400 hover:border-white/10 hover:bg-white/[0.04] hover:text-slate-200"
            }`}
          >
            Registry summary
          </button>
        </div>

        {tab === "stages" ? <StrategiesPanel showHeader /> : <StrategyRegistrySummaryPane />}
      </div>
    </div>
  );
}
