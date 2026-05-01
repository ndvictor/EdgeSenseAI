import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function BacktestingPage() {
  return (
    <PlaceholderPage
      eyebrow="model validation"
      title="Backtesting"
      description="Walk-forward validation, edge-signal survival testing, and weight optimization for stocks, options, and Bitcoin/Crypto."
      bullets={[
        "Winner labels: target hit before stop by horizon, not simple price-up accuracy.",
        "Optimize expectancy, profit factor, drawdown, precision, recall, and false positives.",
        "Separate profiles by asset, timeframe, account size, and regime.",
        "Future engine: grid search, Bayesian optimization, XGBoost ranker, and SHAP explanations."
      ]}
    />
  );
}
