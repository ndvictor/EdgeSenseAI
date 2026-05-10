"use client";

/**
 * EdgeSenseAI — DeepAgents Control Tower (clean route).
 *
 * Single-page read-only view. Calls only the audited paper-autonomy control
 * tower endpoint and renders REAL OUTPUTS from it. No raw API paths in any
 * label. No broker buttons. No live submit. No edits to other routes.
 */

import { useCallback, useEffect, useMemo, useState } from "react";

// ---------------------------------------------------------------------------
// Types matching backend/app/api/routes/paper_autonomy.py:get_control_tower
// ---------------------------------------------------------------------------

type AgentChainEntry = {
  agent: string;
  status: "idle" | "ready" | "active" | string;
  latest_id?: string | null;
};

type PaperOrder = {
  paper_order_id: string;
  symbol: string;
  strategy_key?: string | null;
  side?: string;
  order_type: string;
  time_in_force?: string;
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
  paper_order_id: string;
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
  opened_at: string;
  last_mark_price?: number | null;
  last_marked_at?: string | null;
  mfe?: number | null;
  mae?: number | null;
  closed_at?: string | null;
  exit_price?: number | null;
  exit_reason?: string | null;
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
  created_at?: string;
};

type ControlTowerAlert = {
  severity: "info" | "warn" | "error" | string;
  code: string;
  message: string;
  symbol?: string | null;
  paper_position_id?: string | null;
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

// ---------------------------------------------------------------------------
// Display helpers
// ---------------------------------------------------------------------------

const AGENT_LABELS: Record<string, string> = {
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

const AGENT_DESCRIPTIONS: Record<string, string> = {
  watchlist_builder_agent: "Selects today's symbols",
  alpha_engine_agent: "Picks the alpha trade",
  small_account_feasibility_agent: "Sizes for the account",
  execution_planner_agent: "Builds the order plan",
  execution_approval_agent: "Routes to paper simulator",
  position_monitor_agent: "Marks positions to market",
  close_review_agent: "Decides when to close",
  post_trade_evaluator_agent: "Scores each closed trade",
  learning_loop_agent: "Updates strategy learning",
};

function agentLabel(key: string): string {
  return AGENT_LABELS[key] ?? key.replaceAll("_", " ");
}

function agentDescription(key: string): string {
  return AGENT_DESCRIPTIONS[key] ?? "";
}

function fmtMoney(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  });
}

function fmtNumber(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

function fmtPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

function fmtBool(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "yes" : "no";
}

function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return date.toLocaleString();
}

function statusTone(status: string): string {
  if (status === "active") return "border-cyan-300/40 bg-cyan-400/12 text-cyan-100";
  if (status === "ready") return "border-emerald-300/30 bg-emerald-400/10 text-emerald-100";
  return "border-slate-500/30 bg-slate-500/10 text-slate-300";
}

function alertTone(severity: string): string {
  if (severity === "error") return "border-rose-400/30 bg-rose-500/10 text-rose-100";
  if (severity === "warn") return "border-amber-400/30 bg-amber-500/10 text-amber-100";
  return "border-cyan-400/25 bg-cyan-500/10 text-cyan-100";
}

// ---------------------------------------------------------------------------
// Data fetcher (single endpoint, plain-English error message)
// ---------------------------------------------------------------------------

const CONTROL_TOWER_PATH = "/api/v1/daytrading/paper-autonomy/control-tower";

type FetchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; data: ControlTowerResponse; loadedAt: string }
  | { kind: "error"; reason: "not_configured" | "unreachable" | "rejected"; detail?: string };

async function loadControlTower(): Promise<ControlTowerResponse> {
  const apiBase = process.env.NEXT_PUBLIC_API_URL;
  if (!apiBase) {
    const err = new Error("not_configured");
    err.name = "ConfigError";
    throw err;
  }
  let response: Response;
  try {
    response = await fetch(`${apiBase}${CONTROL_TOWER_PATH}`, { cache: "no-store" });
  } catch {
    const err = new Error("unreachable");
    err.name = "NetworkError";
    throw err;
  }
  if (!response.ok) {
    const err = new Error(`rejected:${response.status}`);
    err.name = "HttpError";
    throw err;
  }
  return (await response.json()) as ControlTowerResponse;
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function EdgeSenseAIControlTowerPage() {
  const [state, setState] = useState<FetchState>({ kind: "idle" });

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const data = await loadControlTower();
      setState({ kind: "ready", data, loadedAt: new Date().toISOString() });
    } catch (err) {
      const name = err instanceof Error ? err.name : "";
      const message = err instanceof Error ? err.message : String(err);
      if (name === "ConfigError") {
        setState({ kind: "error", reason: "not_configured" });
      } else if (name === "NetworkError") {
        setState({ kind: "error", reason: "unreachable" });
      } else {
        setState({ kind: "error", reason: "rejected", detail: message });
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const data = state.kind === "ready" ? state.data : null;

  return (
    <main className="min-h-screen bg-[#02080d] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_30%_15%,rgba(34,211,238,0.10),transparent_30%),radial-gradient(circle_at_85%_25%,rgba(16,185,129,0.08),transparent_28%)]" />

      <div className="relative mx-auto max-w-[1280px] px-5 py-7">
        <PageHeader
          data={data}
          loading={state.kind === "loading"}
          loadedAt={state.kind === "ready" ? state.loadedAt : null}
          onRefresh={refresh}
        />

        {state.kind === "error" ? <ErrorBanner state={state} onRetry={refresh} /> : null}

        {data ? (
          <>
            <SummaryTiles data={data} />
            <WorkflowChainCard chain={data.agent_chain} />
            <PositionsCard
              title="Open Paper Positions"
              caption="Positions opened by the paper simulator and currently being monitored. Mark price comes from the real quote service; broker is never called."
              empty="No open paper positions yet."
              positions={data.open_positions}
              variant="open"
            />
            <PositionsCard
              title="Closed Paper Positions"
              caption="Positions closed by the close-review agent. Outcomes (return, R, MFE, MAE) drive the learning loop."
              empty="No closed paper positions yet."
              positions={data.closed_positions}
              variant="closed"
            />
            <OrdersCard orders={data.orders} />
            <LearningCard outcomes={data.learning_outcomes} latest={data.latest_reviews.learning_loop} />
            <ReviewsCard reviews={data.latest_reviews} />
            <AlertsCard alerts={data.alerts} />
          </>
        ) : null}

        <FooterNote />
      </div>
    </main>
  );
}

// ---------------------------------------------------------------------------
// Sections
// ---------------------------------------------------------------------------

function PageHeader({
  data,
  loading,
  loadedAt,
  onRefresh,
}: {
  data: ControlTowerResponse | null;
  loading: boolean;
  loadedAt: string | null;
  onRefresh: () => void;
}) {
  const paperAuto = data?.paper_auto_enabled ?? false;
  return (
    <header className="mb-6 flex flex-col gap-4 rounded-3xl border border-cyan-400/15 bg-[#04111a]/85 p-6 shadow-[0_30px_120px_rgba(0,0,0,0.45)] backdrop-blur xl:flex-row xl:items-center xl:justify-between">
      <div>
        <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">EdgeSenseAI</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight text-white">DeepAgents Control Tower</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
          Read-only view of the autonomous paper trading loop. Every value below comes from the audited
          DeepAgents stores. The broker is never called from this page.
        </p>
      </div>
      <div className="flex flex-col items-stretch gap-3 xl:items-end">
        <div className="flex flex-wrap gap-2">
          <Pill tone="cyan">Real data only</Pill>
          <Pill tone={paperAuto ? "emerald" : "amber"}>{paperAuto ? "Paper auto: on" : "Paper auto: off"}</Pill>
          <Pill tone="rose">Live submit blocked</Pill>
          <Pill tone="violet">DeepAgents: {data ? "connected" : loading ? "loading" : "offline"}</Pill>
        </div>
        <div className="flex items-center gap-3 text-xs text-slate-500">
          <span>{loadedAt ? `Last loaded: ${new Date(loadedAt).toLocaleTimeString()}` : loading ? "Loading…" : "Not loaded"}</span>
          <button
            type="button"
            onClick={onRefresh}
            disabled={loading}
            className="rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-3 py-1.5 font-bold text-cyan-100 transition hover:bg-cyan-400/20 disabled:opacity-50"
          >
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>
    </header>
  );
}

function ErrorBanner({
  state,
  onRetry,
}: {
  state: { kind: "error"; reason: "not_configured" | "unreachable" | "rejected"; detail?: string };
  onRetry: () => void;
}) {
  const titles: Record<typeof state.reason, string> = {
    not_configured: "The frontend is not pointed at a backend yet.",
    unreachable: "We couldn't reach the backend.",
    rejected: "The backend responded, but with an error.",
  };
  const messages: Record<typeof state.reason, string> = {
    not_configured: "Set NEXT_PUBLIC_API_URL on the frontend deployment so this page knows which backend to call. Nothing on the page is real until that's set.",
    unreachable: "The backend is offline, asleep, or refusing this origin. No data was fetched — we did not fall back to anything synthetic.",
    rejected: state.detail
      ? `The backend rejected the request (${state.detail}). No values are shown.`
      : "The backend rejected the request. No values are shown.",
  };
  return (
    <section className="mb-6 rounded-3xl border border-amber-400/30 bg-amber-500/10 p-5 text-amber-100 shadow-[0_18px_60px_rgba(0,0,0,0.35)]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-bold">{titles[state.reason]}</h2>
          <p className="mt-1 text-sm leading-6 text-amber-100/90">{messages[state.reason]}</p>
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="shrink-0 rounded-lg border border-amber-300/40 bg-amber-400/10 px-3 py-1.5 text-xs font-bold text-amber-100 hover:bg-amber-400/20"
        >
          Try again
        </button>
      </div>
    </section>
  );
}

function SummaryTiles({ data }: { data: ControlTowerResponse }) {
  const tiles = [
    { label: "Open positions", value: data.summary.open_positions, hint: "active paper trades" },
    { label: "Closed positions", value: data.summary.closed_positions, hint: "evaluated outcomes" },
    { label: "Paper orders", value: data.summary.paper_orders, hint: "simulator ledger" },
    { label: "Approvals waiting", value: data.summary.approval_items, hint: "pending review" },
    { label: "Learning outcomes", value: data.summary.learning_outcomes, hint: "feeding the loop" },
  ];
  return (
    <section className="mb-6 grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
      {tiles.map((tile) => (
        <div
          key={tile.label}
          className="rounded-2xl border border-white/8 bg-white/[0.025] p-4 backdrop-blur"
        >
          <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-slate-500">{tile.label}</div>
          <div className="mt-2 text-3xl font-black text-white">{tile.value}</div>
          <div className="mt-1 text-xs text-slate-500">{tile.hint}</div>
        </div>
      ))}
    </section>
  );
}

function WorkflowChainCard({ chain }: { chain: AgentChainEntry[] }) {
  return (
    <Card title="Workflow Chain" subtitle="Each DeepAgent is shown with its current status. 'active' means the agent has fresh output for this run.">
      {chain.length ? (
        <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-9">
          {chain.map((entry, index) => (
            <div
              key={entry.agent}
              className={`relative rounded-2xl border p-3 ${statusTone(entry.status)}`}
            >
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-md border border-white/15 bg-black/30 font-mono text-[10px] text-slate-200">
                  {index + 1}
                </span>
                <span className="text-xs font-black uppercase tracking-[0.1em]">{entry.status}</span>
              </div>
              <div className="mt-3 text-sm font-bold text-white">{agentLabel(entry.agent)}</div>
              <div className="mt-1 text-[11px] leading-4 text-slate-400">{agentDescription(entry.agent)}</div>
              {entry.latest_id ? (
                <div className="mt-2 truncate font-mono text-[10px] text-slate-500" title={entry.latest_id}>
                  id · {entry.latest_id}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <EmptyState text="The agent chain is empty. The backend has not reported any agents yet." />
      )}
    </Card>
  );
}

function PositionsCard({
  title,
  caption,
  empty,
  positions,
  variant,
}: {
  title: string;
  caption: string;
  empty: string;
  positions: PaperPosition[];
  variant: "open" | "closed";
}) {
  return (
    <Card title={title} subtitle={caption}>
      {positions.length === 0 ? (
        <EmptyState text={empty} />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-[0.16em] text-slate-500">
                <th className="px-3 py-2">Symbol</th>
                <th className="px-3 py-2">Strategy</th>
                <th className="px-3 py-2 text-right">Shares</th>
                <th className="px-3 py-2 text-right">Entry</th>
                <th className="px-3 py-2 text-right">Stop</th>
                <th className="px-3 py-2 text-right">Target</th>
                {variant === "open" ? (
                  <>
                    <th className="px-3 py-2 text-right">Mark</th>
                    <th className="px-3 py-2 text-right">MFE / MAE</th>
                    <th className="px-3 py-2">Marked</th>
                  </>
                ) : (
                  <>
                    <th className="px-3 py-2 text-right">Exit</th>
                    <th className="px-3 py-2 text-right">Return %</th>
                    <th className="px-3 py-2 text-right">Return R</th>
                    <th className="px-3 py-2">Hit</th>
                    <th className="px-3 py-2">Closed</th>
                  </>
                )}
                <th className="px-3 py-2">Broker</th>
              </tr>
            </thead>
            <tbody>
              {positions.map((p) => (
                <tr key={p.paper_position_id} className="border-t border-white/[0.05] text-slate-200">
                  <td className="px-3 py-2 font-bold text-white">{p.symbol}</td>
                  <td className="px-3 py-2 text-slate-400">{p.strategy_key ?? "—"}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNumber(p.shares, 4)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(p.entry_price)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(p.stop_price)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(p.target_price)}</td>
                  {variant === "open" ? (
                    <>
                      <td className="px-3 py-2 text-right font-mono">{fmtMoney(p.last_mark_price ?? null)}</td>
                      <td className="px-3 py-2 text-right font-mono text-slate-400">
                        {fmtNumber(p.mfe ?? null)} / {fmtNumber(p.mae ?? null)}
                      </td>
                      <td className="px-3 py-2 text-slate-500">{fmtDateTime(p.last_marked_at ?? null)}</td>
                    </>
                  ) : (
                    <>
                      <td className="px-3 py-2 text-right font-mono">{fmtMoney(p.exit_price ?? null)}</td>
                      <td className="px-3 py-2 text-right font-mono">{fmtPercent(p.actual_return_pct ?? null)}</td>
                      <td className="px-3 py-2 text-right font-mono">{fmtNumber(p.actual_return_r ?? null)}</td>
                      <td className="px-3 py-2 text-slate-400">
                        {p.hit_target ? "target" : p.hit_stop ? "stop" : p.exit_reason ?? "—"}
                      </td>
                      <td className="px-3 py-2 text-slate-500">{fmtDateTime(p.closed_at ?? null)}</td>
                    </>
                  )}
                  <td className="px-3 py-2 text-emerald-200">{fmtBool(p.broker_called)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function OrdersCard({ orders }: { orders: PaperOrder[] }) {
  return (
    <Card
      title="Paper Order Ledger"
      subtitle="Simulated orders created by the audited execution-approval path. Real broker is never called."
    >
      {orders.length === 0 ? (
        <EmptyState text="No paper orders have been simulated yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-[0.16em] text-slate-500">
                <th className="px-3 py-2">Symbol</th>
                <th className="px-3 py-2">Strategy</th>
                <th className="px-3 py-2">Route</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Shares</th>
                <th className="px-3 py-2 text-right">Notional</th>
                <th className="px-3 py-2 text-right">Risk $</th>
                <th className="px-3 py-2 text-right">Expected R</th>
                <th className="px-3 py-2">Submitted</th>
                <th className="px-3 py-2">Broker</th>
                <th className="px-3 py-2">Created</th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.paper_order_id} className="border-t border-white/[0.05] text-slate-200">
                  <td className="px-3 py-2 font-bold text-white">{o.symbol}</td>
                  <td className="px-3 py-2 text-slate-400">{o.strategy_key ?? "—"}</td>
                  <td className="px-3 py-2 uppercase tracking-wider text-cyan-200">{o.submit_route}</td>
                  <td className="px-3 py-2 text-slate-300">{o.order_type}</td>
                  <td className="px-3 py-2 text-slate-300">{o.status}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNumber(o.shares, 4)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(o.notional)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(o.risk_dollars)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNumber(o.expected_r_after_costs ?? null)}</td>
                  <td className="px-3 py-2 text-slate-300">{fmtBool(o.submitted_order)}</td>
                  <td className="px-3 py-2 text-emerald-200">{fmtBool(o.broker_called)}</td>
                  <td className="px-3 py-2 text-slate-500">{fmtDateTime(o.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function LearningCard({
  outcomes,
  latest,
}: {
  outcomes: LearningOutcome[];
  latest: LatestReviewBlock;
}) {
  const action = pickString(latest, "learning_action");
  const reason = pickString(latest, "reason");
  return (
    <Card
      title="Learning Loop"
      subtitle="Closed paper trades feed strategy/model learning. The latest decision and recent outcomes are shown below."
    >
      <div className="mb-4 grid gap-3 md:grid-cols-2">
        <FactRow label="Latest learning action" value={action ?? "—"} />
        <FactRow label="Reason" value={reason ?? "—"} />
      </div>
      {outcomes.length === 0 ? (
        <EmptyState text="No learning outcomes yet." />
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-[10px] uppercase tracking-[0.16em] text-slate-500">
                <th className="px-3 py-2">Symbol</th>
                <th className="px-3 py-2">Strategy</th>
                <th className="px-3 py-2">Outcome</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Realized PnL</th>
                <th className="px-3 py-2 text-right">Return R</th>
                <th className="px-3 py-2">Slippage</th>
                <th className="px-3 py-2">Rule compliant</th>
                <th className="px-3 py-2">When</th>
              </tr>
            </thead>
            <tbody>
              {outcomes.map((o) => (
                <tr key={o.trade_id} className="border-t border-white/[0.05] text-slate-200">
                  <td className="px-3 py-2 font-bold text-white">{o.symbol}</td>
                  <td className="px-3 py-2 text-slate-400">{o.strategy_key}</td>
                  <td className="px-3 py-2 text-slate-200">{o.outcome_label}</td>
                  <td className="px-3 py-2 text-slate-300">{o.outcome_status}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtMoney(o.realized_pnl)}</td>
                  <td className="px-3 py-2 text-right font-mono">{fmtNumber(o.actual_return_r)}</td>
                  <td className="px-3 py-2 text-slate-300">{o.slippage_status}</td>
                  <td className="px-3 py-2 text-slate-300">{fmtBool(o.rule_compliant)}</td>
                  <td className="px-3 py-2 text-slate-500">{fmtDateTime(o.created_at ?? null)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function ReviewsCard({ reviews }: { reviews: ControlTowerResponse["latest_reviews"] }) {
  const blocks = [
    { key: "position_monitoring", label: "Position monitor", source: reviews.position_monitoring },
    { key: "close_review", label: "Close review", source: reviews.close_review },
    { key: "post_trade_evaluation", label: "Post-trade", source: reviews.post_trade_evaluation },
    { key: "learning_loop", label: "Learning loop", source: reviews.learning_loop },
  ] as const;
  return (
    <Card
      title="Latest Agent Reviews"
      subtitle="The most recent decision returned by each downstream review agent."
    >
      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        {blocks.map(({ key, label, source }) => (
          <div key={key} className="rounded-2xl border border-white/8 bg-white/[0.025] p-4">
            <div className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</div>
            {source ? (
              <ReviewSummary block={source} />
            ) : (
              <div className="mt-3 text-sm text-slate-500">No review yet.</div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}

function ReviewSummary({ block }: { block: Record<string, unknown> }) {
  const candidateKeys = [
    "decision",
    "action",
    "next_action",
    "review_decision",
    "learning_action",
    "evaluation_status",
    "status",
    "reason",
    "confidence",
    "notes",
  ];
  const rows = candidateKeys
    .map((key) => ({ key, value: block[key] }))
    .filter((row) => row.value !== undefined && row.value !== null && row.value !== "");
  if (rows.length === 0) {
    return <div className="mt-3 text-sm text-slate-400">Returned, no summary fields.</div>;
  }
  return (
    <dl className="mt-3 space-y-1.5 text-sm">
      {rows.slice(0, 5).map((row) => (
        <div key={row.key} className="flex items-start justify-between gap-3">
          <dt className="shrink-0 text-[11px] uppercase tracking-[0.12em] text-slate-500">{row.key}</dt>
          <dd className="text-right font-mono text-xs text-slate-200">{stringify(row.value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function AlertsCard({ alerts }: { alerts: ControlTowerAlert[] }) {
  return (
    <Card title="Alerts" subtitle="Issued by the read model. None of these can place a real trade.">
      {alerts.length === 0 ? (
        <EmptyState text="No alerts." />
      ) : (
        <div className="space-y-2">
          {alerts.map((alert, idx) => (
            <div
              key={`${alert.code}-${idx}`}
              className={`rounded-2xl border p-3 ${alertTone(alert.severity)}`}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-bold">{alert.message}</div>
                  <div className="mt-1 font-mono text-[10px] uppercase tracking-[0.14em] text-slate-300/70">
                    {alert.severity} · {alert.code}
                    {alert.symbol ? ` · ${alert.symbol}` : ""}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function FooterNote() {
  return (
    <footer className="mt-10 flex flex-wrap items-center justify-between gap-3 border-t border-white/5 pt-4 text-xs text-slate-500">
      <span>Read-only. No broker calls. No live submit. Real data only.</span>
      <span>EdgeSenseAI · DeepAgents Control Tower</span>
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Small UI primitives
// ---------------------------------------------------------------------------

function Card({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="mb-6 rounded-3xl border border-white/8 bg-[#04111a]/85 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.42)] backdrop-blur">
      <header className="mb-4">
        <h2 className="text-base font-black uppercase tracking-[0.12em] text-cyan-50">{title}</h2>
        {subtitle ? <p className="mt-1 text-xs leading-5 text-slate-500">{subtitle}</p> : null}
      </header>
      {children}
    </section>
  );
}

function Pill({
  tone,
  children,
}: {
  tone: "cyan" | "emerald" | "rose" | "violet" | "amber";
  children: React.ReactNode;
}) {
  const styles: Record<typeof tone, string> = {
    cyan: "border-cyan-400/30 bg-cyan-400/10 text-cyan-100",
    emerald: "border-emerald-400/30 bg-emerald-400/10 text-emerald-100",
    rose: "border-rose-400/30 bg-rose-400/10 text-rose-100",
    violet: "border-violet-400/30 bg-violet-400/10 text-violet-100",
    amber: "border-amber-400/30 bg-amber-400/10 text-amber-100",
  };
  return (
    <span className={`inline-flex items-center rounded-full border px-3 py-1 text-[10px] font-black uppercase tracking-[0.16em] ${styles[tone]}`}>
      {children}
    </span>
  );
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-5 text-sm text-slate-400">
      {text} <span className="text-slate-600">Run the autonomous workflow with paper-auto authority to populate this section.</span>
    </div>
  );
}

function FactRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5 text-sm">
      <span className="shrink-0 text-[11px] uppercase tracking-[0.14em] text-slate-500">{label}</span>
      <span className="text-right font-mono text-xs text-slate-200">{value}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tiny utilities (kept local, not exported, no shared component edits)
// ---------------------------------------------------------------------------

function pickString(source: LatestReviewBlock, key: string): string | null {
  if (!source || typeof source !== "object") return null;
  const value = (source as Record<string, unknown>)[key];
  if (value === undefined || value === null) return null;
  if (typeof value === "string") return value;
  return String(value);
}

function stringify(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  if (typeof value === "number") return value.toString();
  if (typeof value === "boolean") return value ? "yes" : "no";
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

// Avoid an unused-import warning if a future iteration drops useMemo.
void useMemo;
