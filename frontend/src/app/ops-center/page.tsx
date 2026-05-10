"use client";

import { useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { LayoutGrid, Shield, Radar, Cpu, TrendingUp } from "lucide-react";
import { PageHeader } from "@/components/Cards";
import { StockSearchChart } from "@/components/StockSearchChart";

type TabKey = "ai_ops" | "command_center" | "account_risk" | "edge_signals";

const AiOpsPanel = dynamic(
  () => import("@/components/AiOps").then((m) => ({ default: m.AiOpsOverviewPage })),
  { ssr: false, loading: () => <LoadingCard label="Loading Agent OpsCenter…" /> },
);
const CommandCenterPanel = dynamic(() => import("@/app/command-center/page"), {
  ssr: false,
  loading: () => <LoadingCard label="Loading Command Center…" />,
});
const AccountRiskPanel = dynamic(() => import("@/app/account-risk/page"), {
  ssr: false,
  loading: () => <LoadingCard label="Loading Account Risk Center…" />,
});
const EdgeSignalsPanel = dynamic(() => import("@/app/edge-signals/page").then((m) => ({ default: m.EdgeSignalsPanel })), {
  ssr: false,
  loading: () => <LoadingCard label="Loading Edge Signals…" />,
});

function LoadingCard({ label }: { label: string }) {
  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-black/20 p-6 text-sm text-slate-300">
      <div className="flex items-center gap-3">
        <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-400/70" />
        <span>{label}</span>
      </div>
      <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <div className="h-20 animate-pulse rounded-xl border border-slate-800 bg-slate-950/50" />
        <div className="h-20 animate-pulse rounded-xl border border-slate-800 bg-slate-950/50" />
        <div className="h-20 animate-pulse rounded-xl border border-slate-800 bg-slate-950/50" />
      </div>
    </div>
  );
}

export default function OpsCenterPage() {
  const [active, setActive] = useState<TabKey | null>(null);

  const tabs = useMemo(
    () =>
      [
        {
          key: "ai_ops" as const,
          label: "Agent OpsCenter",
          href: "/ai-ops",
          icon: Cpu,
          desc: "Agents, workflows, safety, and scheduler operations.",
        },
        {
          key: "command_center" as const,
          label: "Command Center",
          href: "/command-center",
          icon: LayoutGrid,
          desc: "Candidates, live watchlist, and operator controls.",
        },
        {
          key: "account_risk" as const,
          label: "Account Risk Center",
          href: "/account-risk",
          icon: Shield,
          desc: "Account health, execution visibility, and settings.",
        },
        {
          key: "edge_signals" as const,
          label: "Edge Signals",
          href: "/edge-signals",
          icon: Radar,
          desc: "Signal rules, scans, and workflow readiness.",
        },
      ] as const,
    [],
  );

  const toggle = (k: TabKey) => setActive((prev) => (prev === k ? null : k));
  const defaultSymbol = (process.env.NEXT_PUBLIC_EDGESENSE_DEFAULT_STOCK_SYMBOL ?? "").trim();

  return (
    <div className="w-full min-h-full p-4 lg:p-8">
      <div className="mx-auto w-full max-w-[1600px]">
        <PageHeader
          eyebrow="workspace"
          title="Ops Center"
          description="Operator workspaces."
        />

        <div className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-4">
          {tabs.map((t) => {
            const Icon = t.icon;
            const isActive = active === t.key;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => toggle(t.key)}
                className={`group relative rounded-2xl border p-4 text-left transition focus:outline-none focus:ring-2 focus:ring-emerald-400/40 ${
                  isActive
                    ? "border-emerald-400/60 bg-emerald-400/12"
                    : "border-emerald-400/15 bg-black/15 hover:border-emerald-400/35 hover:bg-emerald-400/[0.07]"
                }`}
              >
                <div className="flex items-start gap-3">
                  <span
                    className={`mt-0.5 flex h-10 w-10 items-center justify-center rounded-xl border ${
                      isActive ? "border-emerald-400/65 bg-emerald-400/10 text-emerald-200" : "border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-300"
                    }`}
                  >
                    <Icon className="h-5 w-5" />
                  </span>
                  <div>
                    <div className="flex items-center gap-2 text-base font-semibold text-white">
                      {t.label}
                      {isActive ? <TrendingUp className="h-4 w-4 text-emerald-300" /> : null}
                    </div>
                    <div className="mt-1 text-xs text-slate-400">{t.desc}</div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        {!active ? (
          <div className="mt-4">
            <StockSearchChart
              pageEyebrow="market"
              pageTitle="Market Monitor"
              pageDescription="Candlesticks view for operator context."
              variant="embedded"
              initialSymbol={defaultSymbol}
              initialPeriod="6mo"
              initialInterval="1d"
              initialChartMode="candles"
            />
          </div>
        ) : null}

        {active ? (
          <div className="mt-4 rounded-2xl border border-emerald-400/15 bg-black/25 p-2 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
            <div className="rounded-xl border border-slate-800 bg-slate-950/40 p-2">
              {active === "ai_ops" ? <AiOpsPanel /> : null}
              {active === "command_center" ? <CommandCenterPanel /> : null}
              {active === "account_risk" ? <AccountRiskPanel /> : null}
              {active === "edge_signals" ? <EdgeSignalsPanel /> : null}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}

