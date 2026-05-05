"use client";

import { CryptoWorkspace } from "@/components/workspace/CryptoWorkspace";

export default function CryptoPage() {
  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <CryptoWorkspace />
      </div>
    </div>
  );
}
