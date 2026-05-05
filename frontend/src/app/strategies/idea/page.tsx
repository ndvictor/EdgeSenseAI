"use client";

import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StrategiesIdeaPage() {
  return (
    <PlaceholderPage
      eyebrow="strategy lifecycle"
      title="Idea"
      description="Early strategy concepts before research and validation. Capture the thesis, instruments, and constraints."
      bullets={[
        "Thesis + market condition this targets",
        "Asset class + timeframe + data dependencies",
        "What would falsify the idea quickly (kill criteria)",
        "Next step: research checklist",
      ]}
    />
  );
}

