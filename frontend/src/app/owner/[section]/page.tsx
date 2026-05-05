"use client";

import { useParams } from "next/navigation";
import { getOwnerPageConfig, OwnerPageTemplate } from "@/components/OwnerPlatformShell";

export default function OwnerExecutiveSubpage() {
  const params = useParams();
  const section = params.section as string;
  return <OwnerPageTemplate page={getOwnerPageConfig(section)} />;
}
