"use client";

import { OptionsWorkspace } from "@/components/workspace/OptionsWorkspace";

export default function OptionsPage() {
  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <OptionsWorkspace />
      </div>
    </div>
  );
}
