import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function SettingsPage() {
  return (
    <PlaceholderPage
      eyebrow="configuration"
      title="Settings"
      description="Configuration for data readiness, API providers, model availability, alerts, and safety gates."
      bullets={[
        "Data sources: market data, options data, crypto data, news and sentiment, macro/regime.",
        "Model readiness: ARIMAX, GARCH, HMM, XGBoost/LightGBM, ensemble scoring.",
        "Alert settings: live watchlist interval, edge-signal urgency, notification channel.",
        "Safety settings: paper-only mode, no live execution, max daily loss, and risk gates."
      ]}
    />
  );
}
