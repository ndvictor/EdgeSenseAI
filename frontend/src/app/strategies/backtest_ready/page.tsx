"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesBacktestReadyPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Backtest ready"
      description="Inputs and acceptance criteria are frozen. This stage is ready to run systematic backtests without changing rules mid-run."
      bullets={[
        "Entry/exit rules locked + parameter ranges documented",
        "Data schema locked (features, survivorship, corporate actions)",
        "Metrics to report: win-rate, avg R, max DD, exposure, turnover",
        "Backtest plan queued (walk-forward, OOS split, robustness tests)",
      ]}
    />
  );
}

