import { PlaceholderPage } from "@/components/PlaceholderPage";

export default function JournalPage() {
  return (
    <PlaceholderPage
      eyebrow="learning loop"
      title="Journal"
      description="Captures recommendation outcomes so agents and future models learn which small-account edges worked or failed."
      bullets={[
        "Record signal type, model stack, decision, account fit, and outcome.",
        "Track target-before-stop, expectancy, and false positives by signal.",
        "Build agent scorecards for feature quality and risk objections.",
        "Feed backtesting and weight optimizer with structured outcomes."
      ]}
    />
  );
}
