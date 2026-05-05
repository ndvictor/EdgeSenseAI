"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesPaperTradingPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Paper trading"
      description="Actively running in paper. Track outcomes, slippage, adherence to gates, and operational stability."
      bullets={[
        "Paper performance: win-rate, avg R, drawdown, turnover",
        "Operational metrics: fills, rejects, latency, spread breaches",
        "Drift monitoring and recalibration triggers",
        "Promotion criteria to prod (or disable criteria)",
      ]}
    />
  );
}

