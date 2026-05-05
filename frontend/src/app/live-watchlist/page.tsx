"use client";

import { LiveWatchlistPanel } from "@/components/LiveWatchlistPanel";

export default function LiveWatchlistPage() {
  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <LiveWatchlistPanel />
      </div>
    </div>
  );
}
