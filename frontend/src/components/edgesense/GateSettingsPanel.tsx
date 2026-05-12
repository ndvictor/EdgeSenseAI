"use client";

/**
 * GateSettingsPanel — reasoning-first trading-gate configuration UI.
 *
 * Read-only display by default, with explicit "Edit" mode. Live gates are
 * always visible but disabled until the operator types the literal phrase
 * "ENABLE LIVE" in the confirmation field. All mutations go to
 * /api/edgesense/gates which forwards to the Azure backend.
 *
 * Convention: percent fields use the LOCKED PERCENT CONVENTION (0.5 = 0.5%).
 */

import { useCallback, useEffect, useMemo, useState } from "react";

// ---------------------------------------------------------------------------
// Types (mirror backend app/services/runtime_gate_config.py schemas)
// ---------------------------------------------------------------------------

type ReasoningGates = {
  workflow_enabled: boolean;
  agent_reasoning_enabled: boolean;
};

type PaperGates = {
  paper_trading_enabled: boolean;
  agent_can_create_paper_plans: boolean;
  agent_can_submit_paper_orders: boolean;
  agent_can_auto_submit_paper_orders: boolean;
};

type LiveGates = {
  live_trading_enabled: boolean;
  broker_execution_enabled: boolean;
  execution_agent_enabled: boolean;
  require_human_approval: boolean;
  owner_authority_level: "view_only" | "paper_manual" | "paper_auto" | "live_submit";
  agent_can_submit_live_orders: boolean;
};

type RiskGates = {
  max_risk_per_trade_pct: number;
  max_daily_loss_pct: number;
  max_position_notional_pct: number;
  max_open_positions: number;
  max_trades_per_day: number;
  min_expected_r_after_costs: number;
  max_liquidity_participation_pct: number;
};

type GateAudit = {
  updated_at: string | null;
  updated_by_email: string | null;
  change_reason: string | null;
};

export type TradingGatesSnapshot = {
  reasoning: ReasoningGates;
  paper: PaperGates;
  live: LiveGates;
  risk: RiskGates;
  audit: GateAudit;
  safety_warnings: string[];
  broker_called: false;
};

type GateMutationContext = {
  paper_run_allowed: boolean;
  paper_run_block_reasons: string[];
  live_run_allowed: boolean;
  live_run_block_reasons: string[];
};

export type TradingGatesResponse = {
  status: "ok";
  gates: TradingGatesSnapshot;
  context: GateMutationContext;
};

// ---------------------------------------------------------------------------
// Form / draft types
// ---------------------------------------------------------------------------

type Draft = {
  reasoning: ReasoningGates;
  paper: PaperGates;
  live: LiveGates;
  risk: RiskGates;
  change_reason: string;
  confirm_live: boolean;
  enable_live_phrase: string;
};

function snapshotToDraft(snapshot: TradingGatesSnapshot): Draft {
  return {
    reasoning: { ...snapshot.reasoning },
    paper: { ...snapshot.paper },
    live: { ...snapshot.live },
    risk: { ...snapshot.risk },
    change_reason: "",
    confirm_live: false,
    enable_live_phrase: "",
  };
}

const LIVE_ENABLE_PHRASE = "ENABLE LIVE";

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

export function GateSettingsPanel({
  onGatesChanged,
}: {
  onGatesChanged?: (response: TradingGatesResponse) => void;
}) {
  const [data, setData] = useState<TradingGatesResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [editing, setEditing] = useState<boolean>(false);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState<boolean>(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/edgesense/gates", { cache: "no-store" });
      if (!res.ok) {
        const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
        const reason = String(body.reason || `http_${res.status}`);
        setError(`Could not load gates: ${reason}`);
        setData(null);
        setDraft(null);
        return;
      }
      const body = (await res.json()) as TradingGatesResponse;
      setData(body);
      if (!editing) setDraft(snapshotToDraft(body.gates));
      onGatesChanged?.(body);
    } catch {
      setError("Could not load gates: network error");
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [editing, onGatesChanged]);

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const startEditing = useCallback(() => {
    if (!data) return;
    setDraft(snapshotToDraft(data.gates));
    setEditing(true);
    setError(null);
  }, [data]);

  const cancelEditing = useCallback(() => {
    if (!data) return;
    setDraft(snapshotToDraft(data.gates));
    setEditing(false);
    setError(null);
  }, [data]);

  const submit = useCallback(async () => {
    if (!draft) return;
    setSaving(true);
    setError(null);
    const payload: Record<string, unknown> = {
      // Reasoning
      workflow_enabled: draft.reasoning.workflow_enabled,
      agent_reasoning_enabled: draft.reasoning.agent_reasoning_enabled,
      // Paper
      paper_trading_enabled: draft.paper.paper_trading_enabled,
      agent_can_create_paper_plans: draft.paper.agent_can_create_paper_plans,
      agent_can_submit_paper_orders: draft.paper.agent_can_submit_paper_orders,
      agent_can_auto_submit_paper_orders: draft.paper.agent_can_auto_submit_paper_orders,
      // Live
      live_trading_enabled: draft.live.live_trading_enabled,
      broker_execution_enabled: draft.live.broker_execution_enabled,
      execution_agent_enabled: draft.live.execution_agent_enabled,
      require_human_approval: draft.live.require_human_approval,
      owner_authority_level: draft.live.owner_authority_level,
      agent_can_submit_live_orders: draft.live.agent_can_submit_live_orders,
      // Risk
      max_risk_per_trade_pct: draft.risk.max_risk_per_trade_pct,
      max_daily_loss_pct: draft.risk.max_daily_loss_pct,
      max_position_notional_pct: draft.risk.max_position_notional_pct,
      max_open_positions: draft.risk.max_open_positions,
      max_trades_per_day: draft.risk.max_trades_per_day,
      min_expected_r_after_costs: draft.risk.min_expected_r_after_costs,
      max_liquidity_participation_pct: draft.risk.max_liquidity_participation_pct,
      // Audit
      change_reason: draft.change_reason || null,
      confirm_live: draft.confirm_live,
    };

    try {
      const res = await fetch("/api/edgesense/gates", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
      if (!res.ok) {
        const detail = (body.detail || body.reason) as unknown;
        const reasons = Array.isArray((detail as { reasons?: unknown }).reasons)
          ? ((detail as { reasons: string[] }).reasons).join("; ")
          : typeof detail === "string"
          ? detail
          : JSON.stringify(detail || body);
        setError(`Save failed: ${reasons}`);
        return;
      }
      setData(body as TradingGatesResponse);
      setDraft(snapshotToDraft((body as TradingGatesResponse).gates));
      setEditing(false);
      onGatesChanged?.(body as TradingGatesResponse);
    } catch {
      setError("Save failed: network error");
    } finally {
      setSaving(false);
    }
  }, [draft, onGatesChanged]);

  const liveUnlocked = useMemo(() => {
    if (!editing || !draft) return false;
    return draft.enable_live_phrase.trim() === LIVE_ENABLE_PHRASE;
  }, [editing, draft]);

  const dirty = useMemo(() => {
    if (!data || !draft) return false;
    return JSON.stringify(snapshotToDraft(data.gates)) !== JSON.stringify({ ...draft, enable_live_phrase: "" });
  }, [data, draft]);

  return (
    <section
      id="gates"
      className="mb-6 scroll-mt-6 rounded-3xl border border-white/8 bg-[#04111a]/85 p-5 shadow-[0_18px_70px_rgba(0,0,0,0.42)] backdrop-blur"
    >
      <header className="mb-4 flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <h2 className="text-base font-black uppercase tracking-[0.12em] text-cyan-50">Trading Gates</h2>
          <p className="mt-1 max-w-3xl text-xs leading-5 text-slate-500">
            These are the runtime gates DeepAgents and the paper/live execution path read on every workflow
            run. Edits persist to the backend audit trail. Percent fields use the locked convention
            (<span className="font-mono text-slate-400">0.5</span> means <span className="font-mono text-slate-400">0.5%</span>).
            The broker is never called from this panel.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {!editing ? (
            <>
              <button
                type="button"
                onClick={refresh}
                disabled={loading}
                className="rounded-lg border border-cyan-400/25 bg-cyan-400/10 px-3 py-1.5 text-xs font-bold text-cyan-100 hover:bg-cyan-400/20 disabled:opacity-50"
              >
                {loading ? "Loading…" : "Refresh"}
              </button>
              <button
                type="button"
                onClick={startEditing}
                disabled={!data}
                className="rounded-lg border border-emerald-400/30 bg-emerald-400/10 px-3 py-1.5 text-xs font-bold text-emerald-100 hover:bg-emerald-400/20 disabled:opacity-50"
              >
                Edit gates
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={cancelEditing}
                disabled={saving}
                className="rounded-lg border border-slate-500/30 bg-slate-500/10 px-3 py-1.5 text-xs font-bold text-slate-200 hover:bg-slate-500/20 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={submit}
                disabled={saving || !dirty}
                className="rounded-lg border border-amber-400/30 bg-amber-400/10 px-3 py-1.5 text-xs font-bold text-amber-100 hover:bg-amber-400/20 disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save gates"}
              </button>
            </>
          )}
        </div>
      </header>

      {error ? (
        <div className="mb-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 p-3 text-sm text-rose-100">
          {error}
        </div>
      ) : null}

      {data?.gates.safety_warnings.length ? (
        <div className="mb-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-3 text-xs text-amber-100">
          <div className="mb-1 font-bold uppercase tracking-[0.14em]">Safety warnings</div>
          <ul className="list-disc space-y-0.5 pl-5">
            {data.gates.safety_warnings.map((w) => (
              <li key={w}>{w}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Group title="Reasoning gates" hint="Master switches for the DeepAgents pipeline.">
            <Toggle
              label="workflow_enabled"
              desc="Master kill-switch. When off the DeepAgents pipeline does not run."
              value={editing ? draft!.reasoning.workflow_enabled : data.gates.reasoning.workflow_enabled}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, reasoning: { ...d.reasoning, workflow_enabled: v } } : d))
              }
            />
            <Toggle
              label="agent_reasoning_enabled"
              desc="If false, DeepAgents reasoning is bypassed and only deterministic services run."
              value={editing ? draft!.reasoning.agent_reasoning_enabled : data.gates.reasoning.agent_reasoning_enabled}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, reasoning: { ...d.reasoning, agent_reasoning_enabled: v } } : d))
              }
            />
          </Group>

          <Group title="Paper trading gates" hint="Control simulated orders. The broker is never called.">
            <Toggle
              label="paper_trading_enabled"
              desc="Required for any paper order or paper RUN."
              value={editing ? draft!.paper.paper_trading_enabled : data.gates.paper.paper_trading_enabled}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, paper: { ...d.paper, paper_trading_enabled: v } } : d))
              }
            />
            <Toggle
              label="agent_can_create_paper_plans"
              desc="Lets the execution planner build paper plans."
              value={editing ? draft!.paper.agent_can_create_paper_plans : data.gates.paper.agent_can_create_paper_plans}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, paper: { ...d.paper, agent_can_create_paper_plans: v } } : d))
              }
            />
            <Toggle
              label="agent_can_submit_paper_orders"
              desc="Lets the paper simulator accept a plan for submission."
              value={editing ? draft!.paper.agent_can_submit_paper_orders : data.gates.paper.agent_can_submit_paper_orders}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, paper: { ...d.paper, agent_can_submit_paper_orders: v } } : d))
              }
            />
            <Toggle
              label="agent_can_auto_submit_paper_orders"
              desc="With paper_auto owner authority, runs the loop with no human approval."
              value={
                editing
                  ? draft!.paper.agent_can_auto_submit_paper_orders
                  : data.gates.paper.agent_can_auto_submit_paper_orders
              }
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, paper: { ...d.paper, agent_can_auto_submit_paper_orders: v } } : d))
              }
            />
          </Group>

          <Group
            title="Live trading gates"
            hint="Real money. Defaults are off. You must type the unlock phrase below to edit any of these."
            tone="rose"
          >
            {editing ? (
              <UnlockField
                value={draft!.enable_live_phrase}
                onChange={(v) => setDraft((d) => (d ? { ...d, enable_live_phrase: v } : d))}
                unlocked={liveUnlocked}
              />
            ) : null}
            <Toggle
              label="live_trading_enabled"
              desc="When on, paper simulator is skipped and the live broker is allowed (subject to broker_execution_enabled)."
              value={editing ? draft!.live.live_trading_enabled : data.gates.live.live_trading_enabled}
              readOnly={!editing || !liveUnlocked}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, live: { ...d.live, live_trading_enabled: v } } : d))
              }
              danger
            />
            <Toggle
              label="broker_execution_enabled"
              desc="Allows the broker adapter to be reached. Required for live trading."
              value={editing ? draft!.live.broker_execution_enabled : data.gates.live.broker_execution_enabled}
              readOnly={!editing || !liveUnlocked}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, live: { ...d.live, broker_execution_enabled: v } } : d))
              }
              danger
            />
            <Toggle
              label="execution_agent_enabled"
              desc="Independent execution agent that consumes audited plans."
              value={editing ? draft!.live.execution_agent_enabled : data.gates.live.execution_agent_enabled}
              readOnly={!editing || !liveUnlocked}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, live: { ...d.live, execution_agent_enabled: v } } : d))
              }
              danger
            />
            <Toggle
              label="require_human_approval"
              desc="Required for any broker or live route. Cannot be turned off while live is enabled."
              value={editing ? draft!.live.require_human_approval : data.gates.live.require_human_approval}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, live: { ...d.live, require_human_approval: v } } : d))
              }
            />
            <Select
              label="owner_authority_level"
              desc="paper_manual = approve each paper order. paper_auto = paper simulator runs unattended. live_submit = live broker route allowed."
              value={editing ? draft!.live.owner_authority_level : data.gates.live.owner_authority_level}
              readOnly={!editing}
              options={["view_only", "paper_manual", "paper_auto", "live_submit"]}
              onChange={(v) =>
                setDraft((d) =>
                  d
                    ? {
                        ...d,
                        live: {
                          ...d.live,
                          owner_authority_level: v as LiveGates["owner_authority_level"],
                        },
                      }
                    : d,
                )
              }
            />
            <Toggle
              label="agent_can_submit_live_orders"
              desc="Force-gated by live_trading_enabled AND broker_execution_enabled at the runtime layer."
              value={editing ? draft!.live.agent_can_submit_live_orders : data.gates.live.agent_can_submit_live_orders}
              readOnly={!editing || !liveUnlocked}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, live: { ...d.live, agent_can_submit_live_orders: v } } : d))
              }
              danger
            />
            {editing ? (
              <label className="mt-1 flex items-start gap-2 rounded-xl border border-rose-400/20 bg-rose-500/5 p-3 text-xs text-rose-100">
                <input
                  type="checkbox"
                  checked={draft!.confirm_live}
                  onChange={(e) => setDraft((d) => (d ? { ...d, confirm_live: e.target.checked } : d))}
                  className="mt-0.5"
                />
                <span>
                  I confirm enabling live trading. The backend will also re-check this confirmation and
                  require a typed phrase per workflow run.
                </span>
              </label>
            ) : null}
          </Group>

          <Group title="Risk / account gates" hint="Locked percent convention: 0.5 means 0.5%.">
            <NumberField
              label="max_risk_per_trade_pct"
              desc="Hard cap on per-trade risk vs equity."
              value={editing ? draft!.risk.max_risk_per_trade_pct : data.gates.risk.max_risk_per_trade_pct}
              suffix="%"
              step={0.1}
              readOnly={!editing}
              onChange={(v) => setDraft((d) => (d ? { ...d, risk: { ...d.risk, max_risk_per_trade_pct: v } } : d))}
            />
            <NumberField
              label="max_daily_loss_pct"
              desc="Daily loss kill-switch; blocks new orders when hit."
              value={editing ? draft!.risk.max_daily_loss_pct : data.gates.risk.max_daily_loss_pct}
              suffix="%"
              step={0.1}
              readOnly={!editing}
              onChange={(v) => setDraft((d) => (d ? { ...d, risk: { ...d.risk, max_daily_loss_pct: v } } : d))}
            />
            <NumberField
              label="max_position_notional_pct"
              desc="Max notional per position vs equity."
              value={editing ? draft!.risk.max_position_notional_pct : data.gates.risk.max_position_notional_pct}
              suffix="%"
              step={0.5}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, risk: { ...d.risk, max_position_notional_pct: v } } : d))
              }
            />
            <NumberField
              label="max_open_positions"
              desc="Concurrent positions cap."
              value={editing ? draft!.risk.max_open_positions : data.gates.risk.max_open_positions}
              step={1}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, risk: { ...d.risk, max_open_positions: Math.round(v) } } : d))
              }
            />
            <NumberField
              label="max_trades_per_day"
              desc="Per-day order cap."
              value={editing ? draft!.risk.max_trades_per_day : data.gates.risk.max_trades_per_day}
              step={1}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, risk: { ...d.risk, max_trades_per_day: Math.round(v) } } : d))
              }
            />
            <NumberField
              label="min_expected_r_after_costs"
              desc="Reject plans below this expected R multiple."
              value={editing ? draft!.risk.min_expected_r_after_costs : data.gates.risk.min_expected_r_after_costs}
              step={0.1}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, risk: { ...d.risk, min_expected_r_after_costs: v } } : d))
              }
            />
            <NumberField
              label="max_liquidity_participation_pct"
              desc="Cap participation vs average volume."
              value={editing ? draft!.risk.max_liquidity_participation_pct : data.gates.risk.max_liquidity_participation_pct}
              suffix="%"
              step={0.1}
              readOnly={!editing}
              onChange={(v) =>
                setDraft((d) => (d ? { ...d, risk: { ...d.risk, max_liquidity_participation_pct: v } } : d))
              }
            />
          </Group>

          <Group title="Audit" hint="Most recent gate mutation.">
            <Fact label="updated_at" value={data.gates.audit.updated_at ?? "—"} />
            <Fact label="updated_by_email" value={data.gates.audit.updated_by_email ?? "—"} />
            <Fact label="change_reason" value={data.gates.audit.change_reason ?? "—"} />
            {editing ? (
              <label className="block text-xs text-slate-400">
                <span className="mb-1 block uppercase tracking-[0.14em] text-slate-500">change_reason (this edit)</span>
                <input
                  type="text"
                  value={draft!.change_reason}
                  onChange={(e) => setDraft((d) => (d ? { ...d, change_reason: e.target.value } : d))}
                  placeholder="why are you changing these gates?"
                  className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-2 font-mono text-xs text-slate-100 placeholder:text-slate-600 focus:border-cyan-300/40 focus:outline-none"
                />
              </label>
            ) : null}
          </Group>

          <Group title="Run permissions (read-only)" hint="What the workflow RUN endpoint will currently allow.">
            <Fact label="paper_run_allowed" value={fmtBool(data.context.paper_run_allowed)} />
            {data.context.paper_run_block_reasons.length ? (
              <ul className="text-xs text-amber-200">
                {data.context.paper_run_block_reasons.map((r) => (
                  <li key={r}>· {r}</li>
                ))}
              </ul>
            ) : null}
            <Fact label="live_run_allowed" value={fmtBool(data.context.live_run_allowed)} />
            {data.context.live_run_block_reasons.length ? (
              <ul className="text-xs text-rose-200">
                {data.context.live_run_block_reasons.map((r) => (
                  <li key={r}>· {r}</li>
                ))}
              </ul>
            ) : null}
          </Group>
        </div>
      ) : (
        <div className="rounded-2xl border border-white/8 bg-white/[0.02] p-5 text-sm text-slate-400">
          {loading ? "Loading gates…" : "No gate data available."}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Small UI helpers (kept local to this file)
// ---------------------------------------------------------------------------

function Group({
  title,
  hint,
  tone = "slate",
  children,
}: {
  title: string;
  hint?: string;
  tone?: "slate" | "rose";
  children: React.ReactNode;
}) {
  const borderClass = tone === "rose" ? "border-rose-400/25" : "border-white/8";
  return (
    <div className={`rounded-2xl border ${borderClass} bg-white/[0.02] p-4`}>
      <div className="mb-3">
        <div className="text-[11px] font-black uppercase tracking-[0.16em] text-cyan-50">{title}</div>
        {hint ? <div className="mt-1 text-[11px] leading-5 text-slate-500">{hint}</div> : null}
      </div>
      <div className="space-y-2">{children}</div>
    </div>
  );
}

function Toggle({
  label,
  desc,
  value,
  readOnly,
  onChange,
  danger,
}: {
  label: string;
  desc: string;
  value: boolean;
  readOnly: boolean;
  onChange: (next: boolean) => void;
  danger?: boolean;
}) {
  return (
    <label
      className={`flex cursor-pointer items-start justify-between gap-3 rounded-xl border px-3 py-2.5 ${
        danger
          ? "border-rose-400/15 bg-rose-500/[0.04]"
          : "border-white/8 bg-white/[0.02]"
      } ${readOnly ? "cursor-default opacity-90" : ""}`}
    >
      <div className="min-w-0">
        <div className="font-mono text-xs font-bold text-slate-100">{label}</div>
        <div className="mt-0.5 text-[11px] leading-4 text-slate-500">{desc}</div>
      </div>
      <input
        type="checkbox"
        checked={value}
        disabled={readOnly}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 accent-cyan-400"
      />
    </label>
  );
}

function Select({
  label,
  desc,
  value,
  readOnly,
  options,
  onChange,
}: {
  label: string;
  desc: string;
  value: string;
  readOnly: boolean;
  options: string[];
  onChange: (next: string) => void;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
      <div className="font-mono text-xs font-bold text-slate-100">{label}</div>
      <div className="mt-0.5 text-[11px] leading-4 text-slate-500">{desc}</div>
      <select
        value={value}
        disabled={readOnly}
        onChange={(e) => onChange(e.target.value)}
        className="mt-2 w-full rounded-lg border border-white/10 bg-black/30 px-3 py-1.5 font-mono text-xs text-slate-100 focus:border-cyan-300/40 focus:outline-none disabled:opacity-70"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </div>
  );
}

function NumberField({
  label,
  desc,
  value,
  suffix,
  step = 1,
  readOnly,
  onChange,
}: {
  label: string;
  desc: string;
  value: number;
  suffix?: string;
  step?: number;
  readOnly: boolean;
  onChange: (next: number) => void;
}) {
  return (
    <div className="rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <div className="font-mono text-xs font-bold text-slate-100">{label}</div>
        {readOnly ? (
          <div className="font-mono text-xs text-slate-300">
            {value}
            {suffix ? ` ${suffix}` : ""}
          </div>
        ) : null}
      </div>
      <div className="mt-0.5 text-[11px] leading-4 text-slate-500">{desc}</div>
      {!readOnly ? (
        <div className="mt-2 flex items-center gap-2">
          <input
            type="number"
            step={step}
            value={Number.isFinite(value) ? value : 0}
            onChange={(e) => {
              const next = Number.parseFloat(e.target.value);
              onChange(Number.isFinite(next) ? next : 0);
            }}
            className="w-full rounded-lg border border-white/10 bg-black/30 px-3 py-1.5 font-mono text-xs text-slate-100 focus:border-cyan-300/40 focus:outline-none"
          />
          {suffix ? <span className="text-xs text-slate-400">{suffix}</span> : null}
        </div>
      ) : null}
    </div>
  );
}

function UnlockField({
  value,
  onChange,
  unlocked,
}: {
  value: string;
  onChange: (next: string) => void;
  unlocked: boolean;
}) {
  return (
    <label
      className={`block rounded-xl border px-3 py-2.5 ${
        unlocked ? "border-emerald-400/30 bg-emerald-500/5" : "border-rose-400/20 bg-rose-500/[0.04]"
      }`}
    >
      <div className="text-[11px] font-bold uppercase tracking-[0.16em] text-rose-100">
        Type {LIVE_ENABLE_PHRASE} to unlock live toggles
      </div>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="ENABLE LIVE"
        className="mt-2 w-full rounded-lg border border-white/10 bg-black/40 px-3 py-1.5 font-mono text-xs text-slate-100 focus:border-emerald-300/40 focus:outline-none"
      />
      <div className="mt-1 text-[11px] text-slate-500">
        {unlocked ? "Live toggles are unlocked for this edit." : "Live toggles stay disabled until the phrase matches exactly."}
      </div>
    </label>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-xl border border-white/8 bg-white/[0.02] px-3 py-2 text-xs">
      <span className="shrink-0 font-mono uppercase tracking-[0.14em] text-slate-500">{label}</span>
      <span className="break-all text-right font-mono text-slate-200">{value}</span>
    </div>
  );
}

function fmtBool(value: boolean | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return value ? "yes" : "no";
}
