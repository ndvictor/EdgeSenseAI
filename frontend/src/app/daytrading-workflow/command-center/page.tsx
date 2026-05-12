"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import { GateSettingsPanel, type TradingGatesResponse } from "@/components/edgesense/GateSettingsPanel";
import { EmptyState, JsonViewer, KeyValueGrid, OperatorCard, StatusBadge } from "@/components/edgesense/OperatorCard";
import { WorkflowRunPanel } from "@/components/edgesense/WorkflowRunPanel";
import { asArray, asObject, display, formatDateTime, getValue } from "@/lib/edgesense/format";
import type { ControlTowerResponse, JsonValue, PaperAutonomyStatus, TradingMode } from "@/lib/edgesense/types";

const STATUS_PATH = "/api/v1/daytrading/paper-autonomy/status";
const CONTROL_TOWER_PATH = "/api/v1/daytrading/paper-autonomy/control-tower";
const OPEN_POSITIONS_PATH = "/api/v1/daytrading/paper-autonomy/positions/open";

function backendBase(): string | null {
  const value = process.env.NEXT_PUBLIC_API_URL?.trim().replace(/\/+$/, "");
  return value || null;
}

async function getJson<T>(path: string): Promise<T | null> {
  const base = backendBase();
  if (!base) throw new Error("NEXT_PUBLIC_API_URL is not configured.");
  const response = await fetch(`${base}${path}`, { cache: "no-store" });
  if (!response.ok) return null;
  return (await response.json()) as T;
}

type LoadState =
  | { kind: "loading" }
  | { kind: "ready"; loadedAt: string; status: PaperAutonomyStatus | null; tower: ControlTowerResponse | null; openPositions: JsonValue[] }
  | { kind: "error"; message: string };

export default function CommandCenterPage() {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [gates, setGates] = useState<TradingGatesResponse | null>(null);
  const [requestedMode, setRequestedMode] = useState<TradingMode>("paper");

  const refresh = useCallback(async () => {
    setState({ kind: "loading" });
    try {
      const [status, tower, openPayload] = await Promise.all([
        getJson<PaperAutonomyStatus>(STATUS_PATH),
        getJson<ControlTowerResponse>(CONTROL_TOWER_PATH),
        getJson<{ items?: JsonValue[]; open_positions?: JsonValue[] } | JsonValue[]>(OPEN_POSITIONS_PATH),
      ]);
      const openPositions = Array.isArray(openPayload)
        ? openPayload
        : Array.isArray(openPayload?.items)
          ? openPayload.items
          : Array.isArray(openPayload?.open_positions)
            ? openPayload.open_positions
            : [];
      setState({ kind: "ready", loadedAt: new Date().toISOString(), status, tower, openPositions });
    } catch (error) {
      setState({ kind: "error", message: error instanceof Error ? error.message : String(error) });
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const status = state.kind === "ready" ? state.status : null;
  const tower = state.kind === "ready" ? state.tower : null;
  const summary = tower?.summary ?? {};
  const flags = status?.agent_capability_flags ?? tower?.agent_capability_flags ?? {};
  const currentMode = status?.live_trading_enabled ? "live" : status?.paper_trading_enabled || tower?.paper_auto_enabled ? "paper" : "Unavailable";
  const autonomyStatus = status?.autonomy_status ?? status?.status ?? tower?.status ?? "Unavailable";
  const activeRunId = status?.active_workflow_run_id ?? status?.workflow_run_id ?? getValue(summary, ["active_workflow_run_id", "workflow_run_id"]);
  const liveEnabled = status?.live_trading_enabled ?? tower?.live_submit_enabled ?? false;
  const paperEnabled = status?.paper_trading_enabled ?? tower?.paper_auto_enabled ?? false;
  const brokerExecutionEnabled = status?.broker_execution_enabled ?? Boolean(flags.agent_can_submit_live_orders);
  const openPositions = state.kind === "ready" ? state.openPositions : [];
  const paperRunAvailable = Boolean(gates?.context.paper_run_allowed);
  const liveRunAvailable = Boolean(gates?.context.live_run_allowed);
  const selectedModeCanRun = requestedMode === "paper" ? paperRunAvailable : liveRunAvailable && liveEnabled;

  const loadedAt = state.kind === "ready" ? state.loadedAt : null;

  return (
    <main className="min-h-screen bg-[#02080d] px-5 py-6 text-slate-100">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="rounded-3xl border border-cyan-400/15 bg-[#04111a]/85 p-6 shadow-[0_30px_120px_rgba(0,0,0,0.45)]">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
            <div>
              <p className="text-[11px] font-bold uppercase tracking-[0.28em] text-cyan-300/70">Command Center</p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-white">Human Control Surface</h1>
              <p className="mt-2 max-w-4xl text-sm leading-6 text-slate-400">
                Control-only UI over existing backend gates and workflow run behavior. Missing backend controls stay disabled.
              </p>
            </div>
            <button type="button" onClick={refresh} className="rounded-xl border border-cyan-400/25 bg-cyan-400/10 px-4 py-2 text-sm font-bold text-cyan-100 hover:bg-cyan-400/20">Refresh</button>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <StatusBadge tone="cyan">Real Data Only</StatusBadge>
            <StatusBadge tone={currentMode === "paper" ? "emerald" : currentMode === "live" ? "rose" : "slate"}>Current Mode: {currentMode}</StatusBadge>
            <StatusBadge tone={tower?.broker_called === false ? "emerald" : "amber"}>broker_called: {display(tower?.broker_called)}</StatusBadge>
            <StatusBadge>Last Updated: {formatDateTime(loadedAt)}</StatusBadge>
          </div>
        </header>

        {state.kind === "error" ? <OperatorCard title="Load Error"><EmptyState text={state.message} /></OperatorCard> : null}

        <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <OperatorCard title="Trading Mode Selection" description="Mode selection is a request context for UI controls. Backend gate truth still decides what can run.">
            <div className="grid gap-3 md:grid-cols-2">
              <button
                type="button"
                onClick={() => setRequestedMode("paper")}
                className={`rounded-2xl border p-4 text-left ${requestedMode === "paper" ? "border-emerald-300/40 bg-emerald-400/10" : "border-white/10 bg-black/20"}`}
              >
                <div className="text-sm font-black text-white">Paper Trading</div>
                <div className="mt-1 text-xs text-slate-500">Confirmed by backend: {display(paperEnabled)}</div>
              </button>
              <button
                type="button"
                onClick={() => setRequestedMode("live")}
                disabled={!liveEnabled}
                className={`rounded-2xl border p-4 text-left disabled:cursor-not-allowed disabled:opacity-50 ${requestedMode === "live" ? "border-rose-300/40 bg-rose-400/10" : "border-white/10 bg-black/20"}`}
              >
                <div className="text-sm font-black text-white">Live Trading</div>
                <div className="mt-1 text-xs text-slate-500">Confirmed by backend: {display(liveEnabled)}</div>
              </button>
            </div>
            {requestedMode === "live" && !liveEnabled ? <div className="mt-4 rounded-2xl border border-amber-400/25 bg-amber-400/10 p-3 text-xs text-amber-100">Live mode is disabled because backend gates do not confirm live trading.</div> : null}
          </OperatorCard>

          <OperatorCard title="Autonomy Status">
            <KeyValueGrid rows={[
              { label: "requested mode", value: requestedMode },
              { label: "current mode", value: currentMode },
              { label: "autonomy status", value: autonomyStatus },
              { label: "active workflow run ID", value: activeRunId },
              { label: "open positions count", value: openPositions.length },
              { label: "open paper positions count", value: openPositions.length },
              { label: "pending approvals count", value: getValue(summary, ["approval_items", "pending_approvals"]) },
              { label: "paper_auto enabled", value: tower?.paper_auto_enabled },
              { label: "live trading enabled", value: liveEnabled },
              { label: "broker execution enabled", value: brokerExecutionEnabled },
              { label: "broker_called", value: tower?.broker_called },
            ]} />
          </OperatorCard>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <OperatorCard title="Run Autonomy Trading" description="This uses the existing workflow run panel and existing backend gate checks only.">
            {!selectedModeCanRun ? (
              <div className="mb-4 rounded-2xl border border-amber-400/25 bg-amber-400/10 p-3 text-xs text-amber-100">
                Run is disabled for the selected mode until backend gates confirm the capability.
              </div>
            ) : null}
            <WorkflowRunPanel gates={gates} />
          </OperatorCard>

          <OperatorCard title="Stop Autonomy Trading">
            <EmptyState text="Stop control not available in current backend deployment." />
          </OperatorCard>
        </section>

        <section className="grid gap-5 xl:grid-cols-[1fr_1fr]">
          <OperatorCard title="Open Positions Summary" description="Live positions are not shown unless backend exposes them. This view shows paper positions only.">
            {openPositions.length === 0 ? <EmptyState text="No open paper positions returned by backend." /> : <JsonViewer value={openPositions} />}
          </OperatorCard>

          <OperatorCard title="Safety / Gate Summary" description="Backend gate truth from settings and status surfaces.">
            <KeyValueGrid rows={[
              { label: "paper_trading_enabled", value: gates?.gates.paper.paper_trading_enabled ?? status?.paper_trading_enabled },
              { label: "live_trading_enabled", value: gates?.gates.live.live_trading_enabled ?? status?.live_trading_enabled },
              { label: "require_human_approval", value: gates?.gates.live.require_human_approval },
              { label: "broker_execution_enabled", value: gates?.gates.live.broker_execution_enabled ?? status?.broker_execution_enabled },
              { label: "owner authority level", value: gates?.gates.live.owner_authority_level },
              { label: "can_paper_auto_submit", value: gates?.gates.paper.agent_can_auto_submit_paper_orders ?? tower?.paper_auto_enabled },
            ]} />
          </OperatorCard>
        </section>

        <GateSettingsPanel onGatesChanged={setGates} />
        <OperatorCard title="Raw Backend Control State"><JsonViewer value={{ status, tower }} /></OperatorCard>
      </div>
    </main>
  );
}
