"use client";

import Link from "next/link";
import React, { useMemo } from "react";
import type {
  WorkflowRunbookLatestSnapshot,
  WorkflowRunbookStage,
  WorkflowRunbookStageHealthRow,
} from "@/lib/api";

const STAGE_LATEST_KEY: Partial<Record<string, keyof WorkflowRunbookLatestSnapshot>> = {
  session_router: "session_router",
  workflow_router: "workflow_router",
  strategy_eligibility: "strategy_eligibility",
  trigger_monitoring: "trigger_monitoring",
  execution_planner: "execution_planner",
  trade_execution: "execution_precheck_handoff",
  position_monitoring: "position_monitoring",
  close_position: "close_position",
  post_trade_evaluation: "post_trade_evaluation",
  learning_loop: "learning_loop",
};

function chipClass(status: string): string {
  const s = status.toLowerCase();
  if (s === "present" || s === "ok" || s === "ready" || s === "complete" || s === "completed")
    return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
  if (s === "partial_existing" || s === "partial" || s === "present_partial" || s === "running")
    return "border-amber-500/45 bg-amber-500/15 text-amber-100";
  if (s === "backlog" || s === "missing" || s === "need_to_build" || s === "idle")
    return "border-slate-500/40 bg-slate-500/10 text-slate-300";
  if (s === "fail" || s === "blocked" || s === "error")
    return "border-red-500/45 bg-red-500/15 text-red-100";
  return "border-slate-600/60 bg-slate-800/40 text-slate-300";
}

function healthMap(rows: WorkflowRunbookStageHealthRow[] | undefined) {
  const m = new Map<string, WorkflowRunbookStageHealthRow>();
  for (const r of rows ?? []) m.set(r.stage_key, r);
  return m;
}

export function WorkflowStageTimeline({
  stages,
  stageHealth,
  latestBlob,
  summaryBlockers,
  summaryWarnings,
}: {
  stages: WorkflowRunbookStage[];
  stageHealth: WorkflowRunbookStageHealthRow[] | undefined;
  latestBlob: WorkflowRunbookLatestSnapshot | null;
  summaryBlockers?: string[];
  summaryWarnings?: string[];
}) {
  const h = useMemo(() => healthMap(stageHealth), [stageHealth]);
  const sorted = useMemo(() => [...stages].sort((a, b) => a.stage_number - b.stage_number), [stages]);

  return (
    <div className="rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Pipeline stages (14)</h2>
          <p className="mt-1 text-xs text-slate-500">
            Merged from <code className="text-emerald-200/80">/stages</code>,{" "}
            <code className="text-emerald-200/80">/status</code> <span className="text-slate-600">·</span> stage_health, and{" "}
            <code className="text-emerald-200/80">/latest</code> blobs. Read-only; paper-first; no broker submit from this view.
          </p>
        </div>
      </div>
      {(summaryBlockers?.length ?? 0) > 0 ? (
        <div className="mt-3 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-100/90">
          Summary blockers: {summaryBlockers!.join("; ")}
        </div>
      ) : null}
      {(summaryWarnings?.length ?? 0) > 0 ? (
        <div className="mt-3 rounded-lg border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100/90">
          Summary warnings: {summaryWarnings!.join("; ")}
        </div>
      ) : null}

      <div className="mt-4 space-y-2">
        {sorted.map((st) => {
          const row = h.get(st.stage_key);
          const latestKey = STAGE_LATEST_KEY[st.stage_key];
          const payload = latestKey && latestBlob ? (latestBlob[latestKey] as unknown) : null;
          const hasLatest = payload != null && typeof payload === "object";
          const route = (row?.ui_route?.trim() || st.frontend_route?.trim() || "") || "";

          return (
            <div
              key={`${st.stage_number}-${st.stage_key}`}
              className="rounded-xl border border-white/[0.06] bg-[#0a1018]/85 px-3 py-2.5"
            >
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="rounded bg-slate-800/80 px-2 py-0.5 font-mono text-[10px] text-slate-400">
                  {st.stage_number}
                </span>
                <span className="font-semibold text-slate-100">{st.stage_name}</span>
                <span className="text-slate-500">{st.stage_key}</span>
                {row ? (
                  <>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${chipClass(row.backend_status)}`}>
                      be: {row.backend_status}
                    </span>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${chipClass(row.frontend_status)}`}>
                      fe: {row.frontend_status}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase ${chipClass(row.latest_available ? "ok" : "missing")}`}
                    >
                      latest: {row.latest_available ? "yes" : "no"}
                    </span>
                  </>
                ) : (
                  <span className="rounded-full border border-slate-600/50 px-2 py-0.5 text-[10px] text-slate-500">
                    no stage_health row
                  </span>
                )}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2 text-[11px] text-slate-400">
                {latestKey ? (
                  <span>
                    Blob key <code className="text-emerald-200/80">{String(latestKey)}</code>:{" "}
                    <span className={hasLatest ? "text-emerald-200/90" : "text-slate-500"}>
                      {hasLatest ? "present" : "no snapshot"}
                    </span>
                  </span>
                ) : (
                  <span className="text-slate-500">No dedicated latest blob for this stage — use the UI route for live state.</span>
                )}
                {route ? (
                  <Link className="text-sky-300 hover:text-sky-200" href={route}>
                    Open {route}
                  </Link>
                ) : null}
              </div>
              {row?.next_action ? (
                <div className="mt-1.5 text-[11px] text-slate-500">
                  Next: <span className="text-slate-300">{row.next_action}</span>
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
