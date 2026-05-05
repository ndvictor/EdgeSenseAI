"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesDisabledPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Disabled"
      description="Strategies that are paused or retired. Keep the evidence trail and the reason for disablement."
      bullets={[
        "Disable reason + evidence (overfit, drift, ops risk, etc.)",
        "Last known performance snapshot",
        "Conditions to re-enable (if any)",
        "Links to backtests/paper outcomes supporting decision",
      ]}
    />
  );
}

