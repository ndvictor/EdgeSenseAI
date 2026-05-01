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
    <div className="p-6">
      {error && <div className="rounded-2xl border border-amber-500/30 bg-amber-500/10 p-4 text-amber-200">{error}</div>}
      <div className="mb-2 text-sm text-slate-500">Last updated: {lastUpdated ? new Date(lastUpdated).toLocaleString() : "loading"}</div>
      <PageHeader
        eyebrow="urgent alerts"
        title="Edge Signals"
        description="Small-account signals with fast time decay: RVOL, breakouts, options flow, mean reversion, microstructure, and crypto volatility bursts. Signals alert only after spread, liquidity, regime, and account filters."
      />
          
      <EdgeSignalGrid signals={signals} />
    </div>
  );
}
