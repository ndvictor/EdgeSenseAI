"use client";

import { getOwnerPageConfig, OwnerPageTemplate } from "@/components/OwnerPlatformShell";

export default function OwnerCommandCenterPage() {
  return <OwnerPageTemplate page={getOwnerPageConfig("pnl")} />;
}
