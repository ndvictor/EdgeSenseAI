"use client";

import { useEffect, useState } from "react";
import { api, type CommandCenterResponse } from "@/lib/api";
import { EdgeSignalGrid, MetricCard, PageHeader, RecommendationTable } from "@/components/Cards";

export default function CommandCenterPage() {
  const [data, setData] = useState<CommandCenterResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getCommandCenter().then(setData).catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-2 lg:p-3">
      <div className="mx-auto max-w-7xl">
        <PageHeader
          eyebrow="small-account cockpit"
          title="Command Center"
          description="Final recommendations and urgent edge alerts for stocks, options, and Bitcoin/Crypto. Agents monitor; models rank; the account-risk layer validates."
        />

        {error && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-700">
            {error}
          </div>
        )}

        {!data ? (
          <div className="py-6 text-center text-xs text-slate-300">Loading dashboard...</div>
        ) : (
          <div className="space-y-2">
            <div className="rounded-xl border border-emerald-600 bg-slate-950 p-3 shadow-sm">
              <h2 className="mb-2 text-sm font-semibold text-emerald-500">Portfolio Snapshot</h2>
              <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
                <MetricCard label="Buying Power" value={`$${data.account_profile.buying_power.toLocaleString()}`} accent />
                <MetricCard label="Account Equity" value={`$${data.account_profile.account_equity.toLocaleString()}`} />
                <MetricCard label="Risk / Trade" value={`${data.account_profile.max_risk_per_trade_percent}%`} />
                <MetricCard label="Min Reward/Risk" value={`${data.account_profile.min_reward_risk_ratio}R`} />
              </div>
            </div>

            <div className="rounded-xl border border-emerald-900 bg-slate-950 p-3 shadow-sm">
              <h2 className="mb-2 text-sm font-semibold text-emerald-500">Urgent Edge Alerts</h2>
              <EdgeSignalGrid signals={data.urgent_edge_alerts} />
            </div>

            <div className="rounded-xl border border-slate-700 bg-slate-950 p-3 shadow-sm">
              <h2 className="mb-2 text-sm font-semibold text-emerald-500">Top Recommendations</h2>
              <RecommendationTable recommendations={data.top_recommendations} />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
