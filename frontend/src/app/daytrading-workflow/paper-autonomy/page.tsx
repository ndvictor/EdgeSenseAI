"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useCallback, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_URL;
const CONTROL_TOWER_PATH = "/api/v1/daytrading/paper-autonomy/control-tower";

type AgentChainEntry = {
  agent: string;
  status: string;
  latest_id?: string | null;
};

type PaperOrder = {
  paper_order_id: string;
  symbol: string;
  strategy_key?: string | null;
  order_type: string;
  entry: number;
  stop: number;
  target: number;
  shares: number;
  notional: number;
  risk_dollars: number;
  expected_profit_dollars?: number | null;
  expected_r_after_costs?: number | null;
  submit_route: string;
  status: string;
  broker_called: boolean;
  submitted_order: boolean;
  created_at: string;
};

type PaperPosition = {
  paper_position_id: string;
  symbol: string;
  strategy_key?: string | null;
  entry_price: number;
  stop_price: number;
  target_price: number;
  shares: number;
  notional: number;
  risk_dollars: number;
  status: string;
  broker_called: boolean;
  last_mark_price?: number | null;
  mfe?: number | null;
  mae?: number | null;
  actual_return_pct?: number | null;
  actual_return_r?: number | null;
  hit_target?: boolean | null;
  hit_stop?: boolean | null;
  prediction_error_r?: number | null;
};

type LearningOutcome = {
  trade_id: string;
  strategy_key: string;
  symbol: string;
  outcome_label: string;
  outcome_status: string;
  realized_pnl: number;
  actual_return_r: number;
  slippage_status: string;
  rule_compliant: boolean;
};

type ControlTowerAlert = {
  severity: string;
  code: string;
  message: string;
  symbol?: string;
};

type LatestReviewBlock = Record<string, unknown> | null;

type ControlTowerResponse = {
  status: string;
  mode: string;
  broker_called: boolean;
  live_submit_enabled: boolean;
  paper_auto_enabled: boolean;
  agent_capability_flags: Record<string, boolean>;
  summary: {
    open_positions: number;
    closed_positions: number;
    paper_orders: number;
    approval_items: number;
    learning_outcomes: number;
  };
  agent_chain: AgentChainEntry[];
  orders: PaperOrder[];
  open_positions: PaperPosition[];
  closed_positions: PaperPosition[];
  learning_outcomes: LearningOutcome[];
  latest_reviews: {
    position_monitoring: LatestReviewBlock;
    close_review: LatestReviewBlock;
    post_trade_evaluation: LatestReviewBlock;
    learning_loop: LatestReviewBlock;
  };
  alerts: ControlTowerAlert[];
};

type StatCard = {
  label: string;
  value: string;
  hint: string;
  tone?: "cyan" | "green" | "red" | "violet" | "amber";
};

type NavGroup = {
  label: string;
  items: Array<{ label: string; href: string; badge?: string; active?: boolean }>;
};

const NAV_GROUPS: NavGroup[] = [
  {
    label: "Command",
    items: [
      { label: "Control Tower", href: "/daytrading-workflow/paper-autonomy", badge: "LIVE", active: true },
      { label: "Command Center", href: "/daytrading-workflow/command-center" },
      { label: "Open Positions", href: "/daytrading-workflow/execution-approval" },
      { label: "Paper Accounts", href: "/daytrading-workflow" },
    ],
  },
  {
    label: "Autonomous Pipeline",
    items: [
      { label: "Workflow", href: "/daytrading-workflow/workflow", badge: "ACTIVE" },
      { label: "Agents", href: "/daytrading-workflow/workflow" },
      { label: "Live Watchlist", href: "/daytrading-workflow/live-watchlist" },
      { label: "Data Pipeline", href: "/daytrading-workflow/data-pipeline" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "Strategy & Models", href: "/daytrading-workflow/strategy-models" },
      { label: "Alpha Explorer", href: "/daytrading-workflow/qlib-evidence" },
      { label: "Market Regime", href: "/daytrading-workflow/data-pipeline" },
      { label: "Feature Monitor", href: "/daytrading-workflow/qlib-evidence" },
    ],
  },
  {
    label: "Risk & Approval",
    items: [
      { label: "Risk Guardrails", href: "/daytrading-workflow/execution-approval" },
      { label: "Approval Gates", href: "/daytrading-workflow/execution-approval" },
      { label: "Compliance Monitor", href: "/daytrading-workflow/issues-debug" },
    ],
  },
  {
    label: "Learning Loop",
    items: [
      { label: "Evaluator", href: "/daytrading-workflow/paper-autonomy" },
      { label: "Learning Loop", href: "/daytrading-workflow/paper-autonomy" },
      { label: "Promotion Center", href: "/daytrading-workflow/promotion" },
    ],
  },
];

const STAGE_LABELS: Record<string, string> = {
  watchlist_builder_agent: "Watchlist Builder",
  alpha_engine_agent: "Alpha Engine",
  small_account_feasibility_agent: "Account Feasibility",
  execution_planner_agent: "Execution Planner",
  execution_approval_agent: "Paper Simulator",
  position_monitor_agent: "Position Monitor",
  close_review_agent: "Close Review",
  post_trade_evaluator_agent: "Post-Trade Evaluator",
  learning_loop_agent: "Learning Loop",
};

function apiUrl(path: string): string {
  if (!API_BASE) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured. Set it in frontend/.env.local.");
  }
  return `${API_BASE}${path}`;
}

async function getControlTower(): Promise<ControlTowerResponse> {
  const response = await fetch(apiUrl(CONTROL_TOWER_PATH), { cache: "no-store" });
  if (!response.ok) {
    const body = await response.text().catch(() => "");
    throw new Error(`${CONTROL_TOWER_PATH} failed with ${response.status}${body ? `: ${body.slice(0, 240)}` : ""}`);
  }
  return (await response.json()) as ControlTowerResponse;
}

function n(value: number | null | undefined, digits: number = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return value.toFixed(digits);
}

function money(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function pct(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${value.toFixed(2)}%`;
}

function flag(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "-";
  return value ? "true" : "false";
}

function labelFor(agent: string): string {
  return STAGE_LABELS[agent] ?? agent.replaceAll("_", " ");
}

function objectValue(source: LatestReviewBlock, key: string): unknown {
  if (!source || typeof source !== "object") return undefined;
  return source[key];
}

function Card({ title, eyebrow, children, className = "" }: { title: string; eyebrow?: string; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-2xl border border-cyan-400/10 bg-[#071720]/80 p-4 shadow-[0_0_0_1px_rgba(6,182,212,0.04),0_22px_80px_rgba(0,0,0,0.42)] backdrop-blur ${className}`}>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          {eyebrow ? <p className="text-[10px] font-black uppercase tracking-[0.18em] text-cyan-300/60">{eyebrow}</p> : null}
          <h2 className="text-sm font-black uppercase tracking-[0.12em] text-cyan-50">{title}</h2>
        </div>
      </div>
      {children}
    </section>
  );
}

function MiniBadge({ tone, children }: { tone: "cyan" | "green" | "red" | "violet" | "amber"; children: ReactNode }) {
  const classes = {
    cyan: "border-cyan-400/25 bg-cyan-400/10 text-cyan-100",
    green: "border-emerald-400/25 bg-emerald-400/10 text-emerald-100",
    red: "border-rose-400/25 bg-rose-400/10 text-rose-100",
    violet: "border-violet-400/25 bg-violet-400/10 text-violet-100",
    amber: "border-amber-400/25 bg-amber-400/10 text-amber-100",
  }[tone];
  return <span className={`inline-flex items-center rounded-full border px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.14em] ${classes}`}>{children}</span>;
}

function Sidebar({ data }: { data: ControlTowerResponse | null }) {
  return (
    <aside className="hidden h-screen w-[252px] shrink-0 border-r border-cyan-400/10 bg-[#031016]/95 p-4 text-slate-200 shadow-[18px_0_90px_rgba(0,0,0,0.35)] lg:sticky lg:top-0 lg:block">
      <div className="mb-6 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-xl border border-cyan-400/30 bg-cyan-400/10 text-cyan-200 shadow-[0_0_28px_rgba(34,211,238,0.16)]">DA</div>
        <div>
          <div className="text-sm font-black leading-tight text-white">DeepAgents</div>
          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-cyan-300/70">Command Center</div>
        </div>
      </div>

      <nav className="space-y-5">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="mb-2 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">{group.label}</div>
            <div className="space-y-1">
              {group.items.map((item) => (
                <Link
                  key={`${group.label}-${item.label}`}
                  href={item.href}
                  className={`flex items-center justify-between rounded-xl border px-3 py-2 text-xs font-bold transition ${
                    item.active
                      ? "border-cyan-400/25 bg-cyan-400/12 text-cyan-50"
                      : "border-transparent text-slate-400 hover:border-cyan-400/15 hover:bg-cyan-400/[0.05] hover:text-slate-100"
                  }`}
                >
                  <span>{item.label}</span>
                  {item.badge ? <span className="rounded bg-cyan-400/10 px-1.5 py-0.5 font-mono text-[9px] text-cyan-200">{item.badge}</span> : null}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="mt-6 rounded-2xl border border-emerald-400/20 bg-emerald-400/[0.06] p-3">
        <div className="text-[10px] font-black uppercase tracking-[0.18em] text-emerald-200">Safe Mode</div>
        <p className="mt-1 text-xs leading-5 text-slate-300">Paper only. No broker buttons. Live submit disabled.</p>
        <div className="mt-3 flex items-center justify-between text-xs">
          <span className="text-slate-400">Broker called</span>
          <span className="font-mono text-emerald-200">{flag(data?.broker_called ?? false)}</span>
        </div>
      </div>
    </aside>
  );
}

function Header({
  data,
  loading,
  lastRefreshed,
  onRefresh,
}: {
  data: ControlTowerResponse | null;
  loading: boolean;
  lastRefreshed: string | null;
  onRefresh: () => void;
}) {
  return (
    <header className="flex flex-col gap-4 border-b border-cyan-400/10 bg-[#041019]/70 px-5 py-5 backdrop-blur-xl xl:flex-row xl:items-center xl:justify-between">
      <div>
        <h1 className="text-2xl font-black tracking-tight text-white">DeepAgents Control Tower</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">
          Monitor reasoning, market evidence, feasibility, execution planning, paper simulation, and feedback loops in one read-only platform.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <MiniBadge tone="cyan">Real Data Only</MiniBadge>
        <MiniBadge tone={data?.paper_auto_enabled ? "cyan" : "amber"}>{data?.paper_auto_enabled ? "Paper Auto" : "Paper Auto Off"}</MiniBadge>
        <MiniBadge tone="green">DeepAgents Active</MiniBadge>
        <MiniBadge tone="red">Broker Blocked</MiniBadge>
        <MiniBadge tone="violet">{data ? `${data.agent_chain.length} Stages` : "Loading"}</MiniBadge>
      </div>
      <div className="flex items-center gap-3 text-xs text-slate-500">
        <span>{lastRefreshed ? `Last updated: ${new Date(lastRefreshed).toLocaleTimeString()}` : "Last updated: -"}</span>
        <button
          type="button"
          onClick={onRefresh}
          disabled={loading}
          className="rounded-lg border border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 font-bold text-cyan-100 disabled:opacity-50"
        >
          {loading ? "Refreshing" : "Refresh"}
        </button>
      </div>
    </header>
  );
}

function WorkflowChain({ chain }: { chain: AgentChainEntry[] }) {
  return (
    <Card title="Workflow Chain" eyebrow="1">
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3 xl:grid-cols-9">
        {chain.map((entry) => {
          const active = entry.status === "active";
          const ready = entry.status === "ready";
          return (
            <div
              key={entry.agent}
              className={`relative rounded-xl border p-3 ${
                active
                  ? "border-cyan-300/35 bg-cyan-400/[0.11] shadow-[0_0_36px_rgba(34,211,238,0.16)]"
                  : ready
                    ? "border-emerald-400/20 bg-emerald-400/[0.06]"
                    : "border-white/10 bg-white/[0.025]"
              }`}
            >
              <div className="mb-3 h-7 w-7 rounded-lg border border-cyan-400/20 bg-black/30 text-center font-mono text-sm leading-7 text-cyan-100">
                {labelFor(entry.agent).slice(0, 1)}
              </div>
              <div className="text-xs font-black leading-tight text-white">{labelFor(entry.agent)}</div>
              <div className={`mt-2 inline-flex rounded-full border px-2 py-0.5 text-[9px] font-black uppercase tracking-[0.12em] ${
                active ? "border-cyan-300/35 text-cyan-100" : ready ? "border-emerald-300/25 text-emerald-200" : "border-slate-500/25 text-slate-400"
              }`}>
                {entry.status}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

function StatGrid({ cards }: { cards: StatCard[] }) {
  return (
    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => (
        <div key={card.label} className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <div className="text-[10px] font-black uppercase tracking-[0.16em] text-slate-500">{card.label}</div>
          <div className={`mt-2 text-xl font-black ${card.tone === "red" ? "text-rose-200" : card.tone === "green" ? "text-emerald-200" : card.tone === "amber" ? "text-amber-100" : "text-cyan-100"}`}>{card.value}</div>
          <div className="mt-1 text-xs text-slate-500">{card.hint}</div>
        </div>
      ))}
    </div>
  );
}

function ReasoningMonitor({ chain }: { chain: AgentChainEntry[] }) {
  return (
    <Card title="Agent Reasoning Monitor" eyebrow="2" className="xl:col-span-4">
      <div className="space-y-2">
        {chain.map((entry) => (
          <div key={entry.agent} className="grid grid-cols-[1fr_auto_auto] items-center gap-3 rounded-lg border border-white/5 bg-white/[0.025] px-3 py-2 text-xs">
            <span className="truncate text-slate-300">{labelFor(entry.agent)}</span>
            <span className={entry.status === "active" ? "text-cyan-200" : entry.status === "ready" ? "text-emerald-200" : "text-slate-500"}>{entry.status}</span>
            <span className="font-mono text-slate-500">{entry.latest_id ?? "-"}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function EvidenceTruth({ data }: { data: ControlTowerResponse }) {
  const rows = [
    ["Market Data", "verified", "real quote service"],
    ["Paper Orders", data.summary.paper_orders ? "fresh" : "waiting", `${data.summary.paper_orders} records`],
    ["Open Positions", data.summary.open_positions ? "fresh" : "waiting", `${data.summary.open_positions} active`],
    ["Closed Outcomes", data.summary.closed_positions ? "fresh" : "waiting", `${data.summary.closed_positions} closed`],
    ["Learning Outcomes", data.summary.learning_outcomes ? "fresh" : "waiting", `${data.summary.learning_outcomes} outcomes`],
    ["Broker Execution", "blocked", "read-only UI"],
  ];
  return (
    <Card title="Evidence & Tool Truth" eyebrow="3" className="xl:col-span-3">
      <div className="space-y-2">
        {rows.map(([name, status, note]) => (
          <div key={name} className="grid grid-cols-[1fr_auto] gap-3 border-b border-white/[0.06] py-2 last:border-0">
            <div className="text-xs text-slate-300">{name}</div>
            <div className="text-right">
              <span className={`rounded px-2 py-0.5 text-[10px] font-black uppercase ${status === "blocked" ? "bg-rose-400/10 text-rose-200" : status === "verified" || status === "fresh" ? "bg-emerald-400/10 text-emerald-200" : "bg-slate-500/10 text-slate-400"}`}>{status}</span>
              <div className="mt-1 text-[11px] text-slate-500">{note}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

function AlphaRecommendation({ order }: { order: PaperOrder | null }) {
  return (
    <Card title="Alpha Recommendation" eyebrow="4" className="xl:col-span-3">
      {order ? (
        <div>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-500">Symbol</div>
              <div className="mt-1 text-3xl font-black text-white">{order.symbol}</div>
              <div className="mt-1 text-xs text-slate-400">{order.strategy_key ?? "strategy pending"}</div>
            </div>
            <div className="h-16 w-28 rounded-xl border border-cyan-400/15 bg-gradient-to-tr from-cyan-400/5 via-cyan-400/10 to-emerald-400/10" />
          </div>
          <div className="mt-4 grid grid-cols-3 gap-3 text-xs">
            <div><div className="text-slate-500">Expected R</div><div className="mt-1 font-mono text-emerald-200">{n(order.expected_r_after_costs)}</div></div>
            <div><div className="text-slate-500">Risk</div><div className="mt-1 font-mono text-amber-100">{money(order.risk_dollars)}</div></div>
            <div><div className="text-slate-500">Confidence</div><div className="mt-1 font-mono text-cyan-200">audited</div></div>
          </div>
        </div>
      ) : (
        <EmptyPanel text="No alpha-backed paper order has reached the simulator yet." />
      )}
    </Card>
  );
}

function EmptyPanel({ text }: { text: string }) {
  return <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4 text-sm text-slate-400">{text}</div>;
}

function AccountFeasibility({ order, position }: { order: PaperOrder | null; position: PaperPosition | null }) {
  return (
    <Card title="Account Feasibility" eyebrow="5" className="xl:col-span-3">
      <div className="space-y-3">
        <Metric label="Position Size" value={position ? n(position.shares, 4) : order ? n(order.shares, 4) : "-"} />
        <Metric label="Notional" value={position ? money(position.notional) : order ? money(order.notional) : "-"} />
        <Metric label="Risk Dollars" value={position ? money(position.risk_dollars) : order ? money(order.risk_dollars) : "-"} />
        <Metric label="Broker Called" value="false" danger={false} />
        <div className="rounded-xl border border-emerald-400/20 bg-emerald-400/[0.07] p-3 text-sm text-emerald-100">
          Feasibility math remains upstream and audited. This UI only reads paper records.
        </div>
      </div>
    </Card>
  );
}

function ExecutionPlan({ order }: { order: PaperOrder | null }) {
  return (
    <Card title="Execution Plan" eyebrow="6" className="xl:col-span-3">
      <div className="space-y-3">
        <Metric label="Submit Route" value={order?.submit_route ?? "none"} />
        <Metric label="Order Type" value={order?.order_type ?? "-"} />
        <Metric label="Entry" value={order ? money(order.entry) : "-"} />
        <Metric label="Stop" value={order ? money(order.stop) : "-"} />
        <Metric label="Target" value={order ? money(order.target) : "-"} />
        <Metric label="Broker Called" value="false" danger />
        <div className="rounded-xl border border-rose-400/20 bg-rose-400/[0.07] p-3 text-sm text-rose-100">
          Broker submission is blocked. Paper simulation is internal only.
        </div>
      </div>
    </Card>
  );
}

function FeedbackLoop({ latest, outcomes }: { latest: LatestReviewBlock; outcomes: LearningOutcome[] }) {
  const action = objectValue(latest, "learning_action");
  const reason = objectValue(latest, "reason");
  return (
    <Card title="Feedback Loop" eyebrow="7" className="xl:col-span-4">
      <div className="relative mx-auto mb-4 grid max-w-md grid-cols-2 gap-3">
        {["Alpha Recommendation", "Outcome Results", "Post-Trade Evaluator", "Learning Loop"].map((node) => (
          <div key={node} className="rounded-xl border border-cyan-400/15 bg-cyan-400/[0.06] p-3 text-center text-xs font-bold text-cyan-100">
            {node}
          </div>
        ))}
      </div>
      <Metric label="Latest Learning Action" value={String(action ?? "-")} />
      <Metric label="Outcomes Seen" value={String(outcomes.length)} />
      <p className="mt-3 text-sm text-slate-400">{String(reason ?? "No learning decision yet.")}</p>
    </Card>
  );
}

function AlertsIssues({ alerts }: { alerts: ControlTowerAlert[] }) {
  return (
    <Card title="Alerts / Issues" eyebrow="8" className="xl:col-span-5">
      {alerts.length ? (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
            <div key={`${alert.code}-${idx}`} className={`rounded-xl border p-3 ${alert.severity === "warn" ? "border-amber-400/25 bg-amber-400/[0.07]" : alert.severity === "error" ? "border-rose-400/25 bg-rose-400/[0.07]" : "border-cyan-400/20 bg-cyan-400/[0.06]"}`}>
              <div className="flex items-center justify-between gap-3">
                <div className="text-sm font-bold text-white">{alert.message}</div>
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-slate-400">{alert.code}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <EmptyPanel text="No blockers or warnings from the paper autonomy read model." />
      )}
    </Card>
  );
}

function Metric({ label, value, danger }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between border-b border-white/[0.06] pb-2 text-sm last:border-0">
      <span className="text-slate-500">{label}</span>
      <span className={`font-mono ${danger ? "text-rose-200" : "text-slate-100"}`}>{value}</span>
    </div>
  );
}

function CompactTable({ title, rows }: { title: string; rows: Array<Record<string, string>> }) {
  if (!rows.length) return <EmptyPanel text={`No ${title.toLowerCase()} yet.`} />;
  const columns = Object.keys(rows[0] ?? {});
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="text-left uppercase tracking-[0.14em] text-slate-500">
            {columns.map((col) => <th key={col} className="px-2 py-2">{col}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, idx) => (
            <tr key={`${title}-${idx}`} className="border-t border-white/[0.06] text-slate-300">
              {columns.map((col) => <td key={col} className="px-2 py-2 font-mono">{row[col]}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function PaperAutonomyControlTowerPage() {
  const [data, setData] = useState<ControlTowerResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastRefreshed, setLastRefreshed] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await getControlTower();
      setData(payload);
      setLastRefreshed(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const latestOrder = data?.orders[0] ?? null;
  const latestOpen = data?.open_positions[0] ?? null;
  const latestClosed = data?.closed_positions[0] ?? null;
  const latestPosition = latestOpen ?? latestClosed;
  const chain = data?.agent_chain ?? [];
  const isEmpty = Boolean(data && data.summary.paper_orders === 0 && data.summary.open_positions === 0 && data.summary.closed_positions === 0);

  const statCards = useMemo<StatCard[]>(() => [
    { label: "Paper Orders", value: String(data?.summary.paper_orders ?? 0), hint: "internal simulator ledger", tone: "cyan" },
    { label: "Open Positions", value: String(data?.summary.open_positions ?? 0), hint: "paper positions only", tone: "green" },
    { label: "Approval Items", value: String(data?.summary.approval_items ?? 0), hint: "review queue", tone: "violet" },
    { label: "Broker Called", value: "false", hint: "enforced by read model", tone: "red" },
  ], [data]);

  const ordersRows = (data?.orders ?? []).slice(0, 6).map((o) => ({
    order: o.paper_order_id,
    symbol: o.symbol,
    status: o.status,
    route: o.submit_route,
    shares: n(o.shares, 4),
    risk: money(o.risk_dollars),
    broker: flag(o.broker_called),
  }));

  const closedRows = (data?.closed_positions ?? []).slice(0, 6).map((p) => ({
    position: p.paper_position_id,
    symbol: p.symbol,
    return_r: n(p.actual_return_r, 2),
    return_pct: pct(p.actual_return_pct),
    mfe: n(p.mfe, 2),
    mae: n(p.mae, 2),
    target: flag(p.hit_target),
    stop: flag(p.hit_stop),
  }));

  return (
    <main className="min-h-screen bg-[#02090d] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_45%_10%,rgba(34,211,238,0.11),transparent_32%),radial-gradient(circle_at_80%_22%,rgba(16,185,129,0.08),transparent_28%)]" />
      <div className="relative flex min-h-screen">
        <Sidebar data={data} />
        <section className="min-w-0 flex-1">
          <Header data={data} loading={loading} lastRefreshed={lastRefreshed} onRefresh={() => void refresh()} />

          <div className="space-y-5 p-5">
            {error ? (
              <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 p-4 text-sm text-amber-100">{error}</div>
            ) : null}

            <StatGrid cards={statCards} />

            {isEmpty ? (
              <div className="rounded-2xl border border-cyan-400/15 bg-cyan-400/[0.06] p-5 text-sm text-cyan-100">
                No paper autonomy records yet. Run the autonomous workflow with paper_auto authority to populate this loop.
              </div>
            ) : null}

            <WorkflowChain chain={chain} />

            <div className="grid gap-5 xl:grid-cols-10">
              <ReasoningMonitor chain={chain} />
              {data ? <EvidenceTruth data={data} /> : <Card title="Evidence & Tool Truth" eyebrow="3" className="xl:col-span-3"><EmptyPanel text="Loading evidence..." /></Card>}
              <AlphaRecommendation order={latestOrder} />
            </div>

            <div className="grid gap-5 xl:grid-cols-12">
              <AccountFeasibility order={latestOrder} position={latestPosition} />
              <ExecutionPlan order={latestOrder} />
              {data ? <FeedbackLoop latest={data.latest_reviews.learning_loop} outcomes={data.learning_outcomes} /> : <Card title="Feedback Loop" eyebrow="7" className="xl:col-span-4"><EmptyPanel text="Loading feedback loop..." /></Card>}
              {data ? <AlertsIssues alerts={data.alerts} /> : <Card title="Alerts / Issues" eyebrow="8" className="xl:col-span-5"><EmptyPanel text="Loading alerts..." /></Card>}
            </div>

            <div className="grid gap-5 xl:grid-cols-2">
              <Card title="Paper Orders" eyebrow="Ledger">
                <CompactTable title="Paper Orders" rows={ordersRows} />
              </Card>
              <Card title="Closed Outcomes" eyebrow="Evaluator">
                <CompactTable title="Closed Outcomes" rows={closedRows} />
              </Card>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
