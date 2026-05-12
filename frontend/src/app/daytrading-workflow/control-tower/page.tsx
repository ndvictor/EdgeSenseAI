"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState, JsonViewer, KeyValueGrid, OperatorCard, StatusBadge } from "@/components/edgesense/OperatorCard";
import { asArray, asObject, display, formatDateTime, getValue } from "@/lib/edgesense/format";
import type { AgentChainEntry, ControlTowerResponse, JsonValue } from "@/lib/edgesense/types";

const CONTROL_TOWER_PATH = "/api/v1/daytrading/paper-autonomy/control-tower";
const AGENTS = [
  "watchlist_builder_agent",
  "alpha_engine_agent",
  "small_account_feasibility_agent",
  "execution_planner_agent",
  "execution_approval_agent / paper_simulator",
  "position_monitor_agent",
  "close_review_agent",
  "post_trade_evaluator_agent",
  "learning_loop_agent",
];

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; data: ControlTowerResponse; loadedAt: string }
  | { kind: "empty"; loadedAt: string }
  | { kind: "error"; message: string };

function backendBase(): string | null {
  const value = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "");
  return value || null;
}

async function loadControlTower(): Promise<ControlTowerResponse | null> {
  const base = backendBase();
  if (!base) throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  const response = await fetch(`${base}${CONTROL_TOWER_PATH}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`Backend rejected the request with status ${response.status}.`);
  const body = (await response.json()) as ControlTowerResponse;
  return Object.keys(body ?? {}).length > 0 ? body : null;
}

function findAgent(chain: AgentChainEntry[] | undefined, key: string): AgentChainEntry | undefined {
  const normalized = key.split(" /")[0];
  return (chain ?? []).find((entry) => entry.agent === normalized || entry.name === normalized || entry.agent === key || entry.name === key);
}

function rawReasoning(data: ControlTowerResponse | null): JsonValue | undefined {
  return data?.reasoning_outputs ?? data?.reasoning_monitor ?? data?.alpha_agent_decision ?? data?.watchlist_agent_decision;
}

function recordCount(data: ControlTowerResponse | null): number {
  return (
    asArray(data?.orders).length +
    asArray(data?.paper_orders).length +
    asArray(data?.open_positions).length +
    asArray(data?.closed_positions).length +
    asArray(data?.learning_outcomes).length
  );
}

export default function DeepAgentsControlTowerPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const data = await loadControlTower();
      const loadedAt = new Date().toISOString();
      setState(data ? { kind: "ready", data, loadedAt } : { kind: "empty", loadedAt });
    } catch (error) {
      setState({ kind: "error", message: error instanceof Error ? error.message : String(error) });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const data = state.kind === "ready" ? state.data : null;
  const summary = data?.summary ?? {};
  const evidence = asObject(data?.evidence_truth);
  const reasoning = rawReasoning(data);
  const reasoningObj = asObject(reasoning);
  const alpha = data?.alpha_recommendation ?? data?.alpha_hero;
  const alphaObj = asObject(alpha);
  const feasibility = data?.account_feasibility_decision ?? data?.feasibility_flags;
  const feasibilityObj = asObject(feasibility);
  const execution = data?.execution_plan ?? data?.execution_flags;
  const executionObj = asObject(execution);
  const loadedAt = state.kind === "ready" || state.kind === "empty" ? state.loadedAt : null;
  const hasRecords = recordCount(data) > 0;
  const testsExposed = useMemo(() => getValue(summary, ["tests_passing", "testsPassing"]), [summary]);

  return (
    <main className="min-h-screen bg-[#02080d] px-5 py-6 text-slate-100">
      <div className="mx-auto max-w-[1500px] space-y-5">
        <header className="rounded-3xl border border-cyan-400/15 bg-[#04111a]/85 p-6 shadow-[0_30px_120px_rgba(0,0,0,0.45)]">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">DeepAgents Control Tower</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-white">Autonomous Paper Loop Monitor</h1>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
                Read-only operator surface for backend paper-autonomy truth. Empty cells mean the backend did not return that field.
              </p>
            </div>
            <button type="button" onClick={refresh} className="rounded-xl border border-cyan-400/25 bg-cyan-400/10 px-4 py-2 text-sm font-bold text-cyan-100 hover:bg-cyan-400/20">Refresh</button>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <StatusBadge tone="cyan">Real Data Only</StatusBadge>
            <StatusBadge tone={data?.paper_auto_enabled ? "emerald" : "amber"}>Paper Auto: {display(data?.paper_auto_enabled)}</StatusBadge>
            <StatusBadge tone={state.kind === "ready" ? "emerald" : "slate"}>DeepAgents: {state.kind === "ready" ? "Active" : state.kind}</StatusBadge>
            <StatusBadge tone={data?.broker_called === false ? "emerald" : "amber"}>Broker Blocked: {data?.broker_called === false ? "true" : "Unavailable"}</StatusBadge>
            {testsExposed !== undefined ? <StatusBadge tone={testsExposed ? "emerald" : "amber"}>Tests Passing: {display(testsExposed)}</StatusBadge> : null}
            <StatusBadge>Last Updated: {formatDateTime(loadedAt)}</StatusBadge>
          </div>
        </header>

        {state.kind === "error" ? <OperatorCard title="Load Error"><EmptyState text={state.message} /></OperatorCard> : null}
        {state.kind === "empty" ? <OperatorCard title="Empty State"><EmptyState text="No paper autonomy records yet. Run the autonomous workflow with paper_auto authority to populate this loop." /></OperatorCard> : null}

        <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <OperatorCard title="Open Positions"><div className="text-3xl font-black text-white">{display(getValue(summary, ["open_positions"]))}</div></OperatorCard>
          <OperatorCard title="Paper Orders"><div className="text-3xl font-black text-white">{display(getValue(summary, ["paper_orders", "orders"]))}</div></OperatorCard>
          <OperatorCard title="Pending Approvals"><div className="text-3xl font-black text-white">{display(getValue(summary, ["approval_items", "pending_approvals"]))}</div></OperatorCard>
          <OperatorCard title="Learning Outcomes"><div className="text-3xl font-black text-white">{display(getValue(summary, ["learning_outcomes"]))}</div></OperatorCard>
          <OperatorCard title="Closed Positions"><div className="text-3xl font-black text-white">{display(getValue(summary, ["closed_positions"]))}</div></OperatorCard>
        </section>

        <OperatorCard title="Workflow Chain" description="Backend-reported autonomous stages. Status, confidence, and audit stay unavailable when not returned.">
          <div className="grid gap-3 md:grid-cols-3 xl:grid-cols-9">
            {AGENTS.map((agent, index) => {
              const item = findAgent(data?.agent_chain, agent);
              const status = item?.status ?? "Unavailable";
              return (
                <div key={agent} className="rounded-2xl border border-cyan-400/15 bg-[#04111a] p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="grid h-7 w-7 place-items-center rounded-lg border border-white/10 bg-black/30 font-mono text-xs text-slate-300">{index + 1}</span>
                    <StatusBadge tone={status === "active" ? "cyan" : status === "ready" ? "emerald" : "slate"}>{status}</StatusBadge>
                  </div>
                  <div className="mt-3 break-words text-xs font-bold text-white">{agent}</div>
                  <div className="mt-2 space-y-1 text-[11px] text-slate-500">
                    <div>confidence: {display(item?.confidence)}</div>
                    <div>audit: {display(item?.audit_status)}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </OperatorCard>

        <section className="grid gap-5 xl:grid-cols-2">
          <OperatorCard title="Agent Reasoning Monitor" description="Raw reasoning, audit, evidence, blockers, and warnings are preserved.">
            <KeyValueGrid rows={[
              { label: "status", value: getValue(reasoningObj, ["status", "reasoning_status", "decision"]) },
              { label: "confidence", value: getValue(reasoningObj, ["confidence", "confidence_score"]) },
              { label: "evidence_quality", value: getValue(reasoningObj, ["evidence_quality"]) },
              { label: "llm_used", value: getValue(reasoningObj, ["llm_used", "llm_used_for_trade_decision"]) },
              { label: "audit_result", value: getValue(reasoningObj, ["audit_result", "audit_status"]) },
              { label: "blockers", value: getValue(reasoningObj, ["blockers"]) },
              { label: "warnings", value: getValue(reasoningObj, ["warnings"]) },
            ]} />
            <div className="mt-4"><JsonViewer value={reasoning} /></div>
          </OperatorCard>

          <OperatorCard title="Evidence & Tool Truth" description="Only backend-returned evidence fields are shown.">
            <KeyValueGrid rows={[
              { label: "market data source", value: getValue(evidence, ["market_data_source", "provider", "provider_chain"]) },
              { label: "feature freshness", value: getValue(evidence, ["feature_freshness", "features_fresh", "latest_feature_at"]) },
              { label: "strategy registry", value: getValue(evidence, ["strategy_registry_status", "strategy_registry"]) },
              { label: "model registry", value: getValue(evidence, ["model_registry_status", "model_registry"]) },
              { label: "account state", value: getValue(evidence, ["account_state_status", "account_state"]) },
              { label: "fractional sizing tool", value: getValue(evidence, ["fractional_sizing_tool_status", "fractional_sizing_tool"]) },
              { label: "promotion evidence", value: getValue(evidence, ["promotion_evidence_status", "promotion_evidence"]) },
            ]} />
            <div className="mt-4"><JsonViewer value={data?.evidence_truth} /></div>
          </OperatorCard>

          <OperatorCard title="Alpha Recommendation">
            {alphaObj ? (
              <>
                <KeyValueGrid rows={[
                  { label: "symbol", value: getValue(alphaObj, ["symbol"]) },
                  { label: "strategy", value: getValue(alphaObj, ["strategy", "strategy_key"]) },
                  { label: "setup_type", value: getValue(alphaObj, ["setup_type"]) },
                  { label: "predicted return", value: getValue(alphaObj, ["predicted_return_pct", "predicted_return"]) },
                  { label: "expected value R", value: getValue(alphaObj, ["predicted_expected_value_r", "expected_value_r", "expected_r_after_costs"]) },
                  { label: "confidence", value: getValue(alphaObj, ["confidence", "final_score"]) },
                  { label: "timeframe", value: getValue(alphaObj, ["timeframe", "prediction_horizon_minutes"]) },
                  { label: "bull case", value: getValue(alphaObj, ["bull_case", "thesis"]) },
                  { label: "bear case", value: getValue(alphaObj, ["bear_case"]) },
                ]} />
                <div className="mt-4"><JsonViewer value={alpha} /></div>
              </>
            ) : <EmptyState text="No audited alpha recommendation available yet." />}
          </OperatorCard>

          <OperatorCard title="Account Feasibility">
            <KeyValueGrid rows={[
              { label: "buying power", value: getValue(feasibilityObj, ["buying_power", "buying_power_available"]) },
              { label: "daily risk budget", value: getValue(feasibilityObj, ["daily_risk_budget", "risk_budget_remaining"]) },
              { label: "position size shares", value: getValue(feasibilityObj, ["position_size_shares", "shares"]) },
              { label: "notional", value: getValue(feasibilityObj, ["notional", "position_notional"]) },
              { label: "expected R after costs", value: getValue(feasibilityObj, ["expected_r_after_costs"]) },
              { label: "liquidity participation", value: getValue(feasibilityObj, ["liquidity_participation", "liquidity_participation_pct"]) },
              { label: "decision", value: getValue(feasibilityObj, ["account_feasibility_decision", "decision", "status"]) },
              { label: "blockers", value: getValue(feasibilityObj, ["blockers"]) },
              { label: "warnings", value: getValue(feasibilityObj, ["warnings"]) },
            ]} />
            <div className="mt-4"><JsonViewer value={feasibility} /></div>
          </OperatorCard>

          <OperatorCard title="Execution Plan">
            <div className="mb-4"><StatusBadge tone={(getValue(executionObj, ["broker_called"]) ?? data?.broker_called) === false ? "emerald" : "amber"}>broker_called = {display(getValue(executionObj, ["broker_called"]) ?? data?.broker_called)}</StatusBadge></div>
            <KeyValueGrid rows={[
              { label: "submit_route", value: getValue(executionObj, ["submit_route"]) },
              { label: "order_type", value: getValue(executionObj, ["order_type"]) },
              { label: "entry", value: getValue(executionObj, ["entry", "entry_price"]) },
              { label: "stop", value: getValue(executionObj, ["stop", "stop_price"]) },
              { label: "target", value: getValue(executionObj, ["target", "target_price"]) },
              { label: "bracket plan", value: getValue(executionObj, ["bracket_plan"]) },
              { label: "approval requirement", value: getValue(executionObj, ["approval_requirement", "require_human_approval"]) },
              { label: "submitted_order", value: getValue(executionObj, ["submitted_order"]) ?? data?.submitted_order },
              { label: "broker_called", value: getValue(executionObj, ["broker_called"]) ?? data?.broker_called },
            ]} />
            <div className="mt-4"><JsonViewer value={execution} /></div>
          </OperatorCard>

          <OperatorCard title="Feedback Loop">
            <div className="grid gap-3 md:grid-cols-4">
              {["Alpha Recommendation", "Post-Trade Evaluator", "Learning Loop", "Promotion Review"].map((label) => (
                <div key={label} className="rounded-2xl border border-white/10 bg-black/20 p-4">
                  <div className="text-[10px] font-bold uppercase tracking-[0.14em] text-slate-500">{label}</div>
                  <div className="mt-3 text-xs text-slate-300">{hasRecords ? "Backend records available" : "Empty"}</div>
                </div>
              ))}
            </div>
            <div className="mt-4"><JsonViewer value={data?.feedback_loop ?? data?.learning_outcomes} /></div>
          </OperatorCard>
        </section>

        <OperatorCard title="Alerts / Issues" description="Blockers, warnings, approvals, stale evidence, market/session limitations, and control-path issues returned by backend.">
          {asArray(data?.alerts).length + asArray(data?.blockers).length + asArray(data?.warnings).length + asArray(data?.approvals_required).length === 0 ? (
            <EmptyState text="No alerts, blockers, warnings, or approvals were returned." />
          ) : (
            <JsonViewer value={[...asArray(data?.alerts), ...asArray(data?.blockers), ...asArray(data?.warnings), ...asArray(data?.approvals_required)]} />
          )}
        </OperatorCard>

        <OperatorCard title="Paper Autonomy Records">
          {!hasRecords ? (
            <EmptyState text="No paper autonomy records yet. Run the autonomous workflow with paper_auto authority to populate this loop." />
          ) : (
            <div className="grid gap-4 lg:grid-cols-3">
              <JsonViewer value={data?.open_positions} />
              <JsonViewer value={data?.orders ?? data?.paper_orders} />
              <JsonViewer value={data?.learning_outcomes} />
            </div>
          )}
        </OperatorCard>
      </div>
    </main>
  );
}
