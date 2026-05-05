"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesResearchPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Research"
      description="Deepen the idea with evidence: data sourcing, regime fit, failure modes, and explicit acceptance criteria."
      bullets={[
        "Data sources + feature plan (what must be source-backed)",
        "Regime assumptions + correlation risks",
        "Risk model and reward:risk expectations",
        "Acceptance criteria before backtest-ready",
      ]}
    />
  );
}

