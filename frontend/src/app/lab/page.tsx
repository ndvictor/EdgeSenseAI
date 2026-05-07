"use client";

import React, { useEffect, useMemo, useState } from "react";
import {
  getLabInventory,
  type LabInventoryResponse,
  type LabInventoryStage,
  type LabInventoryUnit,
} from "@/lib/api";

type LabTab =
  | "workflow"
  | "missing"
  | "agents"
  | "python"
  | "ml"
  | "backlog";

function inventoryCategory(unitType: string): string {
  const s = unitType.trim().toLowerCase();
  if (s.includes("orchestrator")) return "Orchestrator";
  if (s.includes("ui component")) return "UI Component";
  if (s === "state object") return "State Object";
  if (s.includes("python script / state store") || (s.includes("/ state store") && s.includes("python script"))) {
    return "Python Script";
  }
  if (s.includes("ai-agent + llm") || s.startsWith("ai-agent + llm")) return "AI-Agent + LLM";
  if (s.includes("ai-agent")) return "AI-Agent no LLM";
  if (s.includes("ml/statistics model") || s.includes("statistics model")) return "ML/Statistics Model";
  if (s.includes("python script")) return "Python Script";
  return "Python Script";
}

function isMissingStatus(status: string): boolean {
  return status === "need_to_build" || status === "need_to_build_clarify" || status === "unclear";
}

function filterUnits(units: LabInventoryUnit[], tab: LabTab): LabInventoryUnit[] {
  if (tab === "workflow") return units;
  if (tab === "missing") return units.filter((u) => isMissingStatus(u.status));
  if (tab === "agents") {
    const c = new Set(["AI-Agent no LLM", "AI-Agent + LLM"]);
    return units.filter((u) => c.has(inventoryCategory(u.type)));
  }
  if (tab === "python") return units.filter((u) => inventoryCategory(u.type) === "Python Script");
  if (tab === "ml") return units.filter((u) => inventoryCategory(u.type) === "ML/Statistics Model");
  if (tab === "backlog") return units.filter((u) => u.status === "backlog");
  return units;
}

function statusChipClass(status: string): string {
  switch (status) {
    case "present":
      return "border-emerald-500/45 bg-emerald-500/15 text-emerald-200";
    case "present_partial":
    case "partial":
      return "border-amber-500/45 bg-amber-500/15 text-amber-100";
    case "need_to_build":
    case "need_to_build_clarify":
      return "border-red-500/45 bg-red-500/15 text-red-100";
    case "backlog":
      return "border-slate-500/40 bg-slate-500/10 text-slate-300";
    case "unclear":
      return "border-violet-500/40 bg-violet-500/10 text-violet-100";
    default:
      return "border-slate-600 bg-slate-800/50 text-slate-300";
  }
}

function typeAccentChipClass(unit: LabInventoryUnit): string {
  const c = inventoryCategory(unit.type);
  if (c === "ML/Statistics Model") return "border-indigo-400/45 bg-indigo-500/10 text-indigo-100";
  if (c === "AI-Agent + LLM" || unit.uses_llm) return "border-violet-400/45 bg-violet-500/10 text-violet-100";
  return "border-slate-600/60 bg-slate-800/40 text-slate-400";
}

const TAB_LABELS: { id: LabTab; label: string }[] = [
  { id: "workflow", label: "Workflow View" },
  { id: "missing", label: "Missing Inventory" },
  { id: "agents", label: "AI-Agents" },
  { id: "python", label: "Python Scripts" },
  { id: "ml", label: "ML/Statistics Models" },
  { id: "backlog", label: "Backlog" },
];

function SummaryCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-emerald-400/15 bg-[#0a1018]/90 px-4 py-3 shadow-[0_0_0_1px_rgba(16,185,129,0.06)]">
      <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold tabular-nums text-slate-50">{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  );
}

function UnitRow({ unit }: { unit: LabInventoryUnit }) {
  return (
    <tr className="border-b border-white/[0.06] align-top text-sm last:border-0">
      <td className="py-2.5 pr-3 font-medium text-slate-100">{unit.name}</td>
      <td className="py-2.5 pr-3">
        <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${typeAccentChipClass(unit)}`}>
          {unit.type}
        </span>
      </td>
      <td className="py-2.5 pr-3 text-slate-400">{unit.needed_for_baseline ? "Yes" : "No"}</td>
      <td className="py-2.5 pr-3">
        <span className={`inline-flex rounded-lg border px-2 py-0.5 text-[11px] font-medium ${statusChipClass(unit.status)}`}>
          {unit.status_label}
        </span>
      </td>
      <td className="py-2.5 pr-3 capitalize text-slate-400">{unit.tested_status}</td>
      <td className="py-2.5 pr-3 text-slate-400">{unit.promotion_status}</td>
      <td className="py-2.5 pr-3 text-slate-400">{unit.uses_llm ? "Yes" : "No"}</td>
      <td className="py-2.5 pr-3 text-xs text-slate-400">{unit.what_it_should_do}</td>
      <td className="py-2.5 text-xs text-emerald-200/80">{unit.next_action}</td>
    </tr>
  );
}

function StageSection({ stage, tab }: { stage: LabInventoryStage; tab: LabTab }) {
  const units = useMemo(() => filterUnits(stage.units, tab), [stage.units, tab]);
  const { summary } = stage;
  const filteredSummary = useMemo(() => {
    const present = units.filter((u) => u.status === "present").length;
    const partial = units.filter((u) => u.status === "partial" || u.status === "present_partial").length;
    const missing = units.filter((u) => isMissingStatus(u.status)).length;
    const backlog = units.filter((u) => u.status === "backlog").length;
    return { total_units: units.length, present, partial, missing, backlog };
  }, [units]);

  if (units.length === 0) {
    return null;
  }

  return (
    <details
      open
      className="group rounded-2xl border border-emerald-400/10 bg-[#070c12]/95 px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
    >
      <summary className="cursor-pointer list-none py-1 [&::-webkit-details-marker]:hidden">
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <div className="flex flex-wrap items-baseline gap-2">
            <span className="text-xs font-semibold text-emerald-400/90">Stage {stage.stage_number}</span>
            <span className="text-base font-semibold text-slate-100">{stage.stage_name}</span>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
            <span>
              Units <span className="font-medium text-slate-300">{filteredSummary.total_units}</span>
              {tab !== "workflow" ? <span className="text-slate-600"> / {summary.total_units}</span> : null}
            </span>
            <span className="text-emerald-400/80">P {filteredSummary.present}</span>
            <span className="text-amber-400/80">∂ {filteredSummary.partial}</span>
            <span className="text-red-400/80">M {filteredSummary.missing}</span>
            <span className="text-slate-500">B {filteredSummary.backlog}</span>
          </div>
        </div>
      </summary>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[960px] border-collapse text-left">
          <thead>
            <tr className="border-b border-white/10 text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              <th className="pb-2 pr-3">Name</th>
              <th className="pb-2 pr-3">Type</th>
              <th className="pb-2 pr-3">Baseline</th>
              <th className="pb-2 pr-3">Status</th>
              <th className="pb-2 pr-3">Tested</th>
              <th className="pb-2 pr-3">Promotion</th>
              <th className="pb-2 pr-3">LLM</th>
              <th className="pb-2 pr-3">Purpose</th>
              <th className="pb-2">Next action</th>
            </tr>
          </thead>
          <tbody>
            {units.map((u) => (
              <UnitRow key={`${stage.stage_number}-${u.unit_id}`} unit={u} />
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

export default function LabPlatformPage() {
  const [data, setData] = useState<LabInventoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<LabTab>("workflow");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getLabInventory();
        if (!cancelled) setData(res);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load lab inventory");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-400 border-t-transparent" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="w-full p-4 lg:p-8">
        <div className="rounded-2xl border border-red-500/35 bg-red-500/10 p-4">
          <h2 className="mb-2 font-semibold text-red-200">Lab Platform</h2>
          <p className="text-sm text-red-100/90">{error ?? "No data"}</p>
        </div>
      </div>
    );
  }

  const { summary, stages, component_categories: categories } = data;

  return (
    <div className="w-full p-4 lg:p-8">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-50">Lab Platform</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">
            Inventory tracker for scripts, AI-agents, ML/statistics models, workflows, and promotion readiness.
          </p>
          <p className="mt-2 text-xs text-slate-500">
            Updated {data.updated_at} · Mode <span className="text-slate-400">{data.data_mode}</span>
          </p>
        </div>
      </div>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
        <SummaryCard label="Total Stages" value={summary.total_stages} />
        <SummaryCard label="Total Units" value={summary.total_units} />
        <SummaryCard label="Backend present" value={summary.backend_present_count ?? summary.present} />
        <SummaryCard label="Frontend present" value={summary.frontend_present_count ?? summary.present} />
        <SummaryCard label="Tested" value={summary.tested_count ?? summary.tested} hint={`Untested ${summary.untested}`} />
        <SummaryCard label="Missing" value={summary.missing_count ?? summary.missing} />
        <SummaryCard label="Needs backend" value={summary.needs_backend_count ?? summary.missing} />
        <SummaryCard label="Needs frontend" value={summary.needs_frontend_count ?? 0} />
      </div>

      <div className="mb-4 rounded-xl border border-amber-400/20 bg-amber-500/5 px-4 py-3 text-sm text-amber-100/90">
        <span className="font-semibold text-amber-200">Next action · </span>
        {summary.next_action}
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {TAB_LABELS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition ${
              tab === t.id
                ? "border-emerald-400/50 bg-emerald-400/15 text-emerald-100"
                : "border-white/10 bg-[#0a1018] text-slate-400 hover:border-emerald-400/25 hover:text-slate-200"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <div className="space-y-4">
          {stages.map((stage) => (
            <StageSection key={stage.stage_key} stage={stage} tab={tab} />
          ))}
          {stages.every((s) => filterUnits(s.units, tab).length === 0) ? (
            <div className="rounded-2xl border border-slate-700/50 bg-slate-900/40 p-6 text-center text-slate-400">
              No units match this filter.
            </div>
          ) : null}
        </div>

        <aside className="space-y-3 lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-2xl border border-emerald-400/15 bg-[#070c12] p-4">
            <h2 className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Component categories</h2>
            <p className="mt-1 text-xs text-slate-500">Roll-up of the 80 desired units by type.</p>
            <ul className="mt-4 space-y-3">
              {categories.map((c) => (
                <li
                  key={c.category}
                  className="rounded-xl border border-white/[0.06] bg-[#0a1018]/80 px-3 py-2.5 text-sm"
                >
                  <div className="font-medium text-slate-200">{c.category}</div>
                  <div className="mt-1 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-500">
                    <span>
                      Total <span className="text-slate-300">{c.total}</span>
                    </span>
                    <span className="text-emerald-400/90">P {c.present}</span>
                    <span className="text-amber-400/90">∂ {c.partial}</span>
                    <span className="text-red-400/90">M {c.missing}</span>
                    <span className="text-slate-500">B {c.backlog}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </div>
    </div>
  );
}
