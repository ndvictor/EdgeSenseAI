"use client";

import { useEffect, useState } from "react";
import { api, type EdgeSignal } from "@/lib/api";
import { EdgeSignalGrid, PageHeader } from "@/components/Cards";

export default function EdgeSignalsPage() {
  const [signals, setSignals] = useState<EdgeSignal[]>([]);
  const [lastUpdated, setLastUpdated] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getEdgeSignals()
      .then((data) => {
        setSignals(data.signals);
        setLastUpdated(data.last_updated);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="min-h-screen bg-slate-500 p-2 lg:p-3">
      <div className="mx-auto max-w-7xl space-y-2">
        <PageHeader
          eyebrow="urgent alerts"
          title="Edge Signals"
          description="Small-account signals with fast time decay: RVOL, breakouts, options flow, mean reversion, microstructure, and crypto volatility bursts. Signals alert only after spread, liquidity, regime, and account filters."
        />
        {error && <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">{error}</div>}
        <div className="text-[11px] text-slate-800">Last updated: {lastUpdated ? new Date(lastUpdated).toLocaleString() : "loading"}</div>
        <EdgeSignalGrid signals={signals} />
      </div>
    </div>
  );
}
