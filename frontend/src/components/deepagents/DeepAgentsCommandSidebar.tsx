"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/** Minimal fields read from control-tower for badges and safe-mode copy. */
export type ControlTowerSidebarData = {
  mode?: string;
  paper_auto_enabled?: boolean;
  live_submit_enabled?: boolean;
  summary?: {
    open_positions: number;
    approval_items: number;
  };
  evidence_truth?: {
    allowed_symbols?: string[] | null;
  } | null;
  agent_chain?: { agent: string; status: string }[];
};

function HexMark({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 36"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
    >
      <path
        d="M16 2L29 10V26L16 34L3 26V10L16 2Z"
        stroke="currentColor"
        strokeWidth="1.25"
        className="text-cyan-400/90"
      />
      <path
        d="M16 9L23 13.5V22.5L16 27L9 22.5V13.5L16 9Z"
        fill="currentColor"
        className="text-cyan-500/25"
      />
    </svg>
  );
}

function NavGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="mb-5">
      <div className="mb-2 px-3 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">{label}</div>
      <nav className="flex flex-col gap-0.5">{children}</nav>
    </div>
  );
}

function Badge({ children, tone = "neutral" }: { children: React.ReactNode; tone?: "neutral" | "live" | "active" | "muted" }) {
  const tones = {
    neutral: "border-white/10 bg-white/[0.06] text-slate-300",
    live: "border-emerald-400/35 bg-emerald-500/15 text-emerald-200",
    active: "border-cyan-400/40 bg-cyan-500/15 text-cyan-100",
    muted: "border-slate-600/40 bg-slate-800/60 text-slate-500",
  } as const;
  return (
    <span
      className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-[9px] font-black uppercase tracking-[0.12em] ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function NavRow({
  href,
  label,
  badge,
  badgeTone = "neutral",
  active,
}: {
  href: string;
  label: string;
  badge?: React.ReactNode;
  badgeTone?: "neutral" | "live" | "active" | "muted";
  active?: boolean;
}) {
  return (
    <Link
      href={href}
      className={`group flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors ${
        active
          ? "bg-cyan-500/10 text-white shadow-[inset_0_0_0_1px_rgba(34,211,238,0.22)]"
          : "text-slate-400 hover:bg-white/[0.04] hover:text-slate-200"
      }`}
    >
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {badge !== undefined && badge !== null ? <Badge tone={badgeTone}>{badge}</Badge> : null}
    </Link>
  );
}

function NavRowMuted({ label }: { label: string }) {
  return (
    <div className="flex cursor-default items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-medium text-slate-500">
      <span className="truncate">{label}</span>
    </div>
  );
}

export function DeepAgentsCommandSidebar({
  data,
  loading,
}: {
  data: ControlTowerSidebarData | null;
  loading: boolean;
}) {
  const pathname = usePathname();
  const onTower = pathname === "/EdgeSenseAI";

  const openCount = data?.summary?.open_positions;
  const approvalCount = data?.summary?.approval_items;
  const watchlistCount = Array.isArray(data?.evidence_truth?.allowed_symbols)
    ? data.evidence_truth!.allowed_symbols!.length
    : null;

  const formatCount = (n: number | undefined) => {
    if (loading && !data) return "…";
    if (n === undefined) return "—";
    return String(n);
  };

  const workflowActive = data?.agent_chain?.some((e) => e.status === "active") ?? false;

  return (
    <aside className="flex h-screen w-[272px] shrink-0 flex-col border-r border-cyan-950/40 bg-[#030a0f]">
      <div className="border-b border-white/[0.06] px-4 py-5">
        <div className="flex items-start gap-3">
          <div className="grid h-11 w-11 shrink-0 place-items-center rounded-lg border border-cyan-500/20 bg-cyan-500/5">
            <HexMark className="h-7 w-7" />
          </div>
          <div className="min-w-0 pt-0.5">
            <div className="text-[11px] font-bold uppercase leading-tight tracking-[0.18em] text-cyan-200/90">
              DeepAgents Command Center
            </div>
            <div className="mt-1 text-[9px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              Autonomous Trading OS.
            </div>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto overflow-x-hidden px-2 py-4 [scrollbar-color:rgba(34,211,238,0.2)_transparent] [scrollbar-width:thin]">
        <NavGroup label="Command">
          <NavRow
            href="/EdgeSenseAI"
            label="Control Tower"
            active={onTower}
            badge="Live"
            badgeTone="live"
          />
          <NavRow href="/" label="Command Center" active={pathname === "/"} />
          <NavRow
            href="/EdgeSenseAI#open-positions"
            label="Open Positions"
            badge={formatCount(openCount)}
          />
          <NavRow href="/EdgeSenseAI#paper-orders" label="Paper Accounts" />
        </NavGroup>

        <NavGroup label="Autonomous Pipeline">
          <NavRow
            href="/EdgeSenseAI#workflow-chain"
            label="Workflow"
            badge={workflowActive ? "Active" : undefined}
            badgeTone="active"
          />
          <NavRow href="/EdgeSenseAI#agent-reasoning" label="Agents" />
          <NavRow
            href="/EdgeSenseAI#evidence"
            label="Live Watchlist"
            badge={watchlistCount === null ? (loading ? "…" : "—") : String(watchlistCount)}
          />
          <NavRow href="/EdgeSenseAI#evidence" label="Data Pipeline" />
        </NavGroup>

        <NavGroup label="Intelligence">
          <NavRowMuted label="Strategy & Models" />
          <NavRowMuted label="Alpha Explorer" />
          <NavRowMuted label="Market Regime" />
          <NavRowMuted label="Feature Monitor" />
        </NavGroup>

        <NavGroup label="Risk & Approval">
          <NavRow href="/EdgeSenseAI#alerts" label="Risk Guardrails" />
          <NavRow
            href="/EdgeSenseAI#alerts"
            label="Approval Gates"
            badge={formatCount(approvalCount)}
          />
          <NavRow href="/EdgeSenseAI#reviews" label="Compliance Monitor" />
        </NavGroup>

        <NavGroup label="Learning Loop">
          <NavRow href="/EdgeSenseAI#reviews" label="Evaluator" />
          <NavRow href="/EdgeSenseAI#learning" label="Learning Loop" />
          <NavRow href="/EdgeSenseAI#learning" label="Promotion Center" />
        </NavGroup>

        <NavGroup label="Diagnostics">
          <NavRow href="/EdgeSenseAI#alerts" label="System Health" />
          <NavRow href="/EdgeSenseAI#alerts" label="Issues / Debug" />
          <NavRow href="/EdgeSenseAI#reviews" label="Audit Logs" />
        </NavGroup>
      </div>

      <div className="mt-auto border-t border-white/[0.06] p-3">
        <div className="rounded-xl border border-amber-500/25 bg-amber-500/[0.07] p-3">
          <div className="text-[10px] font-black uppercase tracking-[0.2em] text-amber-200/90">Safe mode</div>
          <div className="mt-2 text-[11px] font-bold uppercase tracking-[0.14em] text-slate-200">Paper only</div>
          <p className="mt-1.5 text-[11px] leading-relaxed text-slate-500">
            Paper-only mode is active for US stocks. Broker submission remains blocked.
            {data ? ` ${data.paper_auto_enabled ? "Paper auto is on." : "Paper auto is off."}` : ""}
          </p>
        </div>
      </div>
    </aside>
  );
}
