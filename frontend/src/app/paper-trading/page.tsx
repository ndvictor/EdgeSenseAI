import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function PaperTradingPage() {
  return (
    <PlaceholderPage
      eyebrow="paper validation"
      title="Paper Trading"
      description="Manual-review and paper-trading validation for recommendations before any real execution is considered."
      bullets={[
        "Paper account is tied to Account Risk Center buying power and risk limits.",
        "Track recommendation entry, stop, target, expected R, and outcome.",
        "No live execution by default. Research and paper mode first.",
        "Outcomes feed Journal and future agent scorecards."
      ]}
    />
  );
}
