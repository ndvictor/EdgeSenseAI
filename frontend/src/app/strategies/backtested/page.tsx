"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesBacktestedPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Backtested"
      description="Backtest complete with documented results and failure modes. Ready for paper gate if metrics and risk fit pass."
      bullets={[
        "Backtest summary: sample size, regime splits, stability",
        "Risk fit: drawdown vs account constraints, min RR adherence",
        "Overfit checks: parameter sensitivity, multiple testing",
        "Decision: advance to paper_ready or revise/disable",
      ]}
    />
  );
}

