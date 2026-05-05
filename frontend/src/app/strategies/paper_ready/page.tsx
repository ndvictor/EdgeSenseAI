"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesPaperReadyPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Paper ready"
      description="Backtest passed gates and risk controls. Ready to run in paper trading with strict safety constraints."
      bullets={[
        "Paper trading checklist: sizing, order types, slippage model",
        "Monitoring plan: alerts, drift checks, anomaly detection",
        "Stop rules: max daily loss, max drawdown, max bad fills",
        "Promotion criteria to paper_trading",
      ]}
    />
  );
}

