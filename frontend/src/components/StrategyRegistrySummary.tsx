"use client";

import { useEffect, useState } from "react";
import { MetricCard, PageHeader } from "@/components/Cards";
import { api, type StrategyConfig } from "@/lib/api";

function StatusBadge({ status }: { status: string }) {
  const value = status || "unknown";
  const tone =
    value.includes("active") || value.includes("approved") || value.includes("enabled") || value.includes("supported")
      ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
      : value.includes("candidate") || value.includes("research") || value.includes("required")
        ? "border-amber-500 bg-amber-500/10 text-amber-300"
        : value.includes("disabled") || value.includes("rejected")
          ? "border-rose-500 bg-rose-500/10 text-rose-300"
          : "border-slate-600 bg-slate-800 text-slate-300";
  return <span className={`rounded-full border px-3 py-1 text-xs font-bold uppercase ${tone}`}>{value.replace(/_/g, " ")}</span>;
}

function strategyStatusBadge(strategy: StrategyConfig) {
  const isCandidate = strategy.status === "candidate" || strategy.promotion_status === "candidate";
  const isDisabled = Boolean(strategy.disabled_reason) || strategy.status === "rejected";

  if (isDisabled) return <span className="rounded-full border border-rose-500 bg-rose-500/10 px-2 py-0.5 text-xs font-bold uppercase text-rose-300">Disabled</span>;
  if (isCandidate) return <span className="rounded-full border border-amber-500 bg-amber-500/10 px-2 py-0.5 text-xs font-bold uppercase text-amber-300">Research</span>;
  return <span className="rounded-full border border-emerald-500 bg-emerald-500/10 px-2 py-0.5 text-xs font-bold uppercase text-emerald-300">Active</span>;
}

export function StrategyRegistrySummary({ strategies }: { strategies: StrategyConfig[] }) {
  if (!strategies.length) {
    return (
      <div className="rounded-xl border border-emerald-400/15 bg-black/35 px-4 py-8 text-center text-sm text-slate-300 shadow-[0_0_28px_rgba(0,0,0,0.2)] backdrop-blur">
        No strategy registry entries available yet.
      </div>
    );
  }

  const activeCount = strategies.filter((s) => s.status !== "candidate" && s.status !== "rejected" && !s.disabled_reason).length;
  const candidateCount = strategies.filter((s) => s.status === "candidate" || s.promotion_status === "candidate").length;
  const disabledCount = strategies.filter((s) => s.disabled_reason || s.status === "rejected").length;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-3">
        <MetricCard label="Active / Approved" value={activeCount} accent />
        <MetricCard label="Candidate / Research" value={candidateCount} />
        <MetricCard label="Disabled / Blocked" value={disabledCount} />
      </div>

      <div className="overflow-x-auto rounded-xl border border-emerald-400/15 bg-black/35 shadow-[0_0_28px_rgba(0,0,0,0.2)] backdrop-blur">
        <table className="w-full min-w-[1280px] text-left text-sm">
          <thead className="text-xs uppercase tracking-wide text-emerald-400/90">
            <tr>
              <th className="px-4 py-3">Strategy</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">Asset</th>
              <th className="px-4 py-3">Timeframe</th>
              <th className="px-4 py-3">Required Agents</th>
              <th className="px-4 py-3">Required Models</th>
              <th className="px-4 py-3">Paper</th>
              <th className="px-4 py-3">Approval</th>
              <th className="px-4 py-3">Live</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-emerald-950/50">
            {strategies.map((strategy) => (
              <tr key={strategy.strategy_key} className="hover:bg-white/[0.04]">
                <td className="px-4 py-3">
                  <p className="font-bold text-white">{strategy.display_name}</p>
                  <p className="mt-1 max-w-md text-xs text-slate-400">{strategy.description}</p>
                </td>
                <td className="px-4 py-3">{strategyStatusBadge(strategy)}</td>
                <td className="px-4 py-3 text-slate-300">{strategy.asset_class}</td>
                <td className="px-4 py-3 text-slate-300">{strategy.timeframe}</td>
                <td className="max-w-md px-4 py-3 text-slate-300">{strategy.required_agents.join(", ")}</td>
                <td className="px-4 py-3 text-slate-300">{strategy.required_models.join(", ")}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={strategy.paper_trading_supported ? "supported" : "disabled"} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={strategy.requires_human_approval ? "required" : "not_required"} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={strategy.live_trading_supported ? "enabled" : "disabled"} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function StrategyRegistrySummaryPane() {
  const [strategies, setStrategies] = useState<StrategyConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getStrategies()
      .then(setStrategies)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load strategies"))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="w-full min-h-full">
      <PageHeader
        eyebrow="strategy control plane"
        title="Strategy Registry Summary"
        description="Live strategy registry pulled from `/api/strategies`. Shows status, required agents/models, and execution gates."
      />

      {error && <div className="mb-4 rounded-xl border border-rose-500/35 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
      {loading ? (
        <div className="rounded-xl border border-emerald-400/15 bg-black/35 px-4 py-8 text-center text-sm text-slate-300 shadow-[0_0_28px_rgba(0,0,0,0.2)] backdrop-blur">
          Loading strategy registry…
        </div>
      ) : (
        <StrategyRegistrySummary strategies={strategies} />
      )}
    </div>
  );
}

