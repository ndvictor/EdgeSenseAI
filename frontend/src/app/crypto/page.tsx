import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function CryptoPage() {
  return (
    <PlaceholderPage
      eyebrow="bitcoin and crypto workflow"
      title="Bitcoin / Crypto"
      description="Crypto workflows focused first on BTC and liquid crypto opportunities across intraday, swing, and one-month horizons."
      bullets={[
        "Intraday: volatility bursts, funding, liquidations, order book imbalance, volume, and BTC momentum.",
        "Swing: momentum, funding trend, open interest, exchange flows, sentiment, and macro risk context.",
        "One month: ETF flows, liquidity, BTC dominance, macro regime, and volatility regime.",
        "Model stack: ARIMAX, Kalman Filter, GARCH, HMM, and XGBoost ensemble."
      ]}
    />
  );
}
