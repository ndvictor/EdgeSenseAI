"use client";

import { StocksWorkspace } from "@/components/workspace/StocksWorkspace";
import { OptionsWorkspace } from "@/components/workspace/OptionsWorkspace";
import { CryptoWorkspace } from "@/components/workspace/CryptoWorkspace";

export type TradeNowWorkspaceTab = "stocks" | "options" | "etf" | "crypto";

export function TradeNowWorkspacePanel({ tab }: { tab: TradeNowWorkspaceTab }) {
  switch (tab) {
    case "stocks":
      return <StocksWorkspace variant="stocks" hideChart />;
    case "etf":
      return <StocksWorkspace variant="etf" hideChart />;
    case "options":
      return <OptionsWorkspace />;
    case "crypto":
      return <CryptoWorkspace />;
    default:
      return null;
  }
}
