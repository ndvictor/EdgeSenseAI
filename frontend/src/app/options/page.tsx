import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function OptionsPage() {
  return (
    <PlaceholderPage
      eyebrow="options workflow"
      title="Options"
      description="Options workflows for day trading, swing, 1-month, and earnings plays with strict small-account risk filters."
      bullets={[
        "Day trade: unusual options flow, IV change, delta/gamma flow, spread and liquidity filters.",
        "Swing: IV rank, skew, term structure, put/call ratio, OI change, underlying trend.",
        "Earnings play: expected move, IV crush risk, event history, sentiment, gap risk.",
        "Small account rule: prefer defined-risk structures and reject wide spreads / low OI."
      ]}
    />
  );
}
