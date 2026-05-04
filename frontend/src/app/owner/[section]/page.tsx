"use client";

import { getOwnerPageConfig, OwnerPageTemplate } from "@/components/OwnerPlatformShell";

export default function OwnerExecutiveSubpage({ params }: { params: { section: string } }) {
  return <OwnerPageTemplate page={getOwnerPageConfig(params.section)} />;
}
