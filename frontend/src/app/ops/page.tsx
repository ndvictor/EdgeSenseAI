"use client";

import { OpsPageTemplate, getOpsPageConfig } from "@/components/OpsPlatformShell";

export default function OpsHomePage() {
  const page = getOpsPageConfig("dashboard");
  return <OpsPageTemplate page={page} />;
}
