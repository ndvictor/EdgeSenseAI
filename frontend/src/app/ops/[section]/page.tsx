"use client";

import { useParams } from "next/navigation";
import { OpsPageTemplate, getOpsPageConfig } from "@/components/OpsPlatformShell";

export default function OpsSectionPage() {
  const params = useParams();
  const section = params.section as string;
  const page = getOpsPageConfig(section);
  return <OpsPageTemplate page={page} />;
}
