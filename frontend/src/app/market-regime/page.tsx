import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function MarketRegimePage() {
  return (
    <PlaceholderPage
      eyebrow="regime filter"
      title="Market Regime"
      description="Regime context for whether edge signals should be amplified, reduced, or blocked."
      bullets={[
        "VIX and realized-volatility regime for stocks and options.",
        "SPY, QQQ, sector trend, and correlation state.",
        "Bitcoin risk-on or risk-off relationship with equities.",
        "HMM regime layer: trend, chop, high-volatility, and stress states."
      ]}
    />
  );
}
