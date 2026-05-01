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
    <div className="min-h-screen bg-[#f8fbf9] p-6 lg:p-10">
      <div className="max-w-7xl mx-auto">
        <PageHeader
          eyebrow="small-account cockpit"
          title="Command Center"
          description="Final recommendations and urgent edge alerts for stocks, options, and Bitcoin/Crypto. Agents monitor; models rank; the account-risk layer validates."
        />

        {error && (
          <div className="mb-6 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-amber-700">
            {error}
          </div>
        )}

        {!data ? (
          <div className="text-slate-500">Loading dashboard...</div>
        ) : (
          <div className="space-y-8">
            {/* Metrics */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="Buying Power" value={`$${data.account_profile.buying_power.toLocaleString()}`} accent />
              <MetricCard label="Account Equity" value={`$${data.account_profile.account_equity.toLocaleString()}`} />
              <MetricCard label="Risk / Trade" value={`${data.account_profile.max_risk_per_trade_percent}%`} />
              <MetricCard label="Min Reward/Risk" value={`${data.account_profile.min_reward_risk_ratio}R`} />
            </div>

            {/* Urgent Alerts */}
            <section>
              <h2 className="mb-4 text-2xl font-semibold text-slate-900">Urgent Edge Alerts</h2>
              <EdgeSignalGrid signals={data.urgent_edge_alerts} />
            </section>

            {/* Top Recommendations */}
            <section>
              <h2 className="mb-4 text-2xl font-semibold text-slate-900">Top Recommendations</h2>
              <RecommendationTable recommendations={data.top_recommendations} />
            </section>
          </div>
        )}
      </div>
    </div>
  );
}