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
    <div className="p-6">
      <PageHeader
        eyebrow="small-account cockpit"
        title="Command Center"
        description="Final recommendations and urgent edge alerts for stocks, options, and Bitcoin/Crypto. Agents monitor; models rank; the account-risk layer validates."
      />
      {error && <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">{error}</div>}
      {!data ? <div className="text-slate-400">Loading...</div> : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-4">
            <MetricCard label="Buying Power" value={`$${data.account_profile.buying_power.toLocaleString()}`} accent />
            <MetricCard label="Account Equity" value={`$${data.account_profile.account_equity.toLocaleString()}`} />
            <MetricCard label="Risk / Trade" value={`${data.account_profile.max_risk_per_trade_percent}%`} />
            <MetricCard label="Min Reward/Risk" value={`${data.account_profile.min_reward_risk_ratio}R`} />
          </div>
          <section>
            <h2 className="mb-3 text-xl font-black text-white">Urgent Edge Alerts</h2>
            <EdgeSignalGrid signals={data.urgent_edge_alerts} />
          </section>
          <section>
            <h2 className="mb-3 text-xl font-black text-white">Top Recommendations</h2>
            <RecommendationTable recommendations={data.top_recommendations} />
          </section>
        </div>
      )}
    </div>
  );
}
