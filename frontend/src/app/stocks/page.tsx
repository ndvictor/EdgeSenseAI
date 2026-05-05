"use client";

import { StocksWorkspace } from "@/components/workspace/StocksWorkspace";

export default function StocksPage() {
  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <StocksWorkspace variant="stocks" />
      </div>
    </div>
  );
}
