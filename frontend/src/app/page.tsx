"use client";

import Link from "next/link";

export default function Home() {
  return (
    <div className="min-h-screen bg-[#f8fbf9] p-8">
      <div className="max-w-4xl mx-auto text-center">
        <h1 className="text-6xl font-black tracking-tighter text-slate-900">EdgeSenseAI</h1>
        <p className="mt-4 text-xl text-slate-600">Small-account edge signal and recommendation platform</p>
        
        <Link
          href="/command-center"
          className="mt-10 inline-flex items-center gap-3 rounded-2xl bg-emerald-600 px-8 py-5 text-lg font-semibold text-white hover:bg-emerald-700 transition-colors"
        >
          Open Command Center →
        </Link>
      </div>
    </div>
  );
}