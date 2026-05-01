import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function StocksPage() {
  return (
    <PlaceholderPage
      eyebrow="stocks workflow"
      title="Stocks"
      description="Focused stock workflows for $1K-$10K accounts across day trade, swing, and 1-month horizons."
      bullets={[
        "Day trade: RVOL, VWAP deviation, order book imbalance, short momentum, breakout/reversion alerts.",
        "Swing: momentum, breakout confirmation, sector relative strength, sentiment, options confirmation.",
        "1 month: MA20/50 trend, relative strength, earnings revisions, macro regime, volatility forecast.",
        "Model stack: ARIMAX, Kalman Filter, GARCH, HMM, XGBoost/LightGBM."
      ]}
    />
  );
}
