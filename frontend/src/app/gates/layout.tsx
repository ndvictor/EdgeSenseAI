import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Trading Gates | EdgeSenseAI",
  description: "Runtime trading gates: reasoning, paper, live, risk limits, and audit metadata.",
};

export default function GatesLayout({ children }: { children: React.ReactNode }) {
  return children;
}
