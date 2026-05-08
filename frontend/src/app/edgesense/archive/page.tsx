import { api, type WorkflowRunbookStagesResponse } from "@/lib/api";

export const dynamic = "force-dynamic";

type ArchiveLink = {
  label: string;
  href: string;
  note?: string;
};

const ALL_APP_ROUTES: string[] = [
  "/",
  "/account-risk",
  "/agent-runtime",
  "/ai-ops",
  "/ai-ops/agents",
  "/ai-ops/audit",
  "/ai-ops/llm-usage",
  "/ai-ops/safety",
  "/ai-ops/scheduler",
  "/ai-ops/workflows",
  "/approval-queue",
  "/audit-log",
  "/auto-execution-monitor",
  "/backtesting",
  "/candidate-engine",
  "/candidates",
  "/close-position",
  "/command-center",
  "/commandcenter",
  "/crypto",
  "/data-quality",
  "/data-sources",
  "/edge-signals",
  "/edgesense/archive",
  "/execution-planner",
  "/lab",
  "/learning-loop",
  "/live-watchlist",
  "/llm-gateway",
  "/login",
  "/market-regime",
  "/market-regime/allowed-strategies",
  "/market-regime/regime-factors",
  "/market-regime/source-truth",
  "/model",
  "/model/lab",
  "/model-registry",
  "/ops",
  "/ops-center",
  "/options",
  "/owner",
  "/paper-trading",
  "/platform-readiness",
  "/position-monitoring",
  "/post-trade-evaluation",
  "/recommendations",
  "/research-evidence",
  "/session-router",
  "/settings",
  "/signal-engine",
  "/signals",
  "/stocks",
  "/strategies",
  "/strategies/backtest_ready",
  "/strategies/backtested",
  "/strategies/disabled",
  "/strategies/idea",
  "/strategies/paper_ready",
  "/strategies/paper_trading",
  "/strategies/promoted_to_prod",
  "/strategies/research",
  "/strategies/strategy-lab",
  "/strategy-eligibility",
  "/tradenow",
  "/trigger-monitoring",
  "/universe",
  "/workflow-governance",
  "/workflow-runbook",
  "/workflow-router",
  "/workflow-scheduler",
];

const APPROVED_SIDEBAR_ROUTES: string[] = [
  // Command Center
  "/command-center",
  "/platform-readiness",
  "/agent-runtime",
  // Market Radar
  "/market-regime",
  "/candidate-engine",
  "/signals",
  "/live-watchlist",
  // Research Lab
  "/research-evidence",
  "/backtesting",
  "/model/lab",
  // Strategy Workflow
  "/workflow-runbook",
  "/strategy-eligibility",
  "/trigger-monitoring",
  "/execution-planner",
  // Trading Desk
  "/tradenow",
  "/recommendations",
  "/paper-trading",
  "/position-monitoring",
  // Performance & Governance
  "/approval-queue",
  "/audit-log",
  "/workflow-governance",
  // Settings / Archive
  "/settings",
  "/edgesense/archive",
];

function toTitleCaseRoute(route: string): string {
  const clean = route.replace(/^\//, "");
  if (!clean) return "Home";
  return clean
    .split("/")
    .map((seg) => seg.replace(/[-_]/g, " "))
    .map((seg) => (seg ? seg[0].toUpperCase() + seg.slice(1) : seg))
    .join(" / ");
}

function parseRunbookFrontendRoutes(runbook: WorkflowRunbookStagesResponse | null): string[] {
  const out: string[] = [];
  for (const st of runbook?.stages || []) {
    const raw = String(st.frontend_route || "");
    if (!raw) continue;
    // runbook uses comma-separated routes in some stages (e.g. "/data-sources, /data-quality")
    for (const part of raw.split(",")) {
      const r = part.trim();
      if (!r) continue;
      // normalize: keep path only (strip query like /settings?tab=master_admin)
      const base = r.split("?")[0];
      if (base.startsWith("/")) out.push(base);
    }
  }
  return Array.from(new Set(out));
}

function Section({ title, links }: { title: string; links: ArchiveLink[] }) {
  return (
    <section className="rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="text-lg font-semibold text-emerald-200">{title}</h2>
        <span className="text-xs text-slate-500">{links.length} links</span>
      </div>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        {links.map((l) => (
          <a
            key={l.href}
            href={l.href}
            className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-200 transition hover:bg-white/[0.06]"
          >
            <div className="flex items-center justify-between gap-3">
              <div className="font-semibold">{l.label}</div>
              <div className="font-mono text-xs text-slate-500">{l.href}</div>
            </div>
            {l.note ? <div className="mt-1 text-xs text-slate-400">{l.note}</div> : null}
          </a>
        ))}
      </div>
    </section>
  );
}

export default async function EdgeSenseArchivePage() {
  const runbookStages = await api.getWorkflowRunbookStages().catch(() => null);
  const workflowRoutes = parseRunbookFrontendRoutes(runbookStages);
  const inWorkflow = new Set<string>([...workflowRoutes, ...APPROVED_SIDEBAR_ROUTES]);

  const archiveRoutes = ALL_APP_ROUTES.filter((r) => !inWorkflow.has(r) && r !== "/");
  const archiveLinks: ArchiveLink[] = archiveRoutes
    .map((href) => ({ href, label: toTitleCaseRoute(href) }))
    .sort((a, b) => a.label.localeCompare(b.label));

  return (
    <div className="mx-auto w-full max-w-7xl p-4 lg:p-8">
      <div className="mb-6 rounded-2xl border border-emerald-400/15 bg-black/35 p-6 backdrop-blur shadow-[0_0_40px_rgba(0,0,0,0.25)]">
        <div className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-400">EdgeSense Archive</div>
        <h1 className="mt-2 text-3xl font-bold text-white">Archive (non-workflow pages)</h1>
        <p className="mt-3 text-slate-300">
          The <span className="font-semibold text-emerald-200">only source of truth</span> for the operator workflow is the{" "}
          <span className="font-mono text-slate-200">Stage 1–14</span> runbook inventory and its endpoints. This page keeps legacy/aux pages accessible
          without crowding the command-center sidebar.
        </p>
        <p className="mt-2 text-sm text-slate-400">
          Workflow spine: use <span className="font-mono text-slate-300">/workflow-runbook</span>, the stage pages (Session Router → Learning Loop), and{" "}
          <span className="font-mono text-slate-300">/platform-readiness</span>.
        </p>
        <div className="mt-4 grid grid-cols-1 gap-2 text-sm text-slate-400 md:grid-cols-3">
          <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
            <div className="text-xs text-slate-500">Runbook workflow routes</div>
            <div className="mt-1 font-mono text-slate-200">{workflowRoutes.length}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
            <div className="text-xs text-slate-500">Approved sidebar routes</div>
            <div className="mt-1 font-mono text-slate-200">{APPROVED_SIDEBAR_ROUTES.length}</div>
          </div>
          <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
            <div className="text-xs text-slate-500">Archived routes</div>
            <div className="mt-1 font-mono text-slate-200">{archiveLinks.length}</div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <Section title="Archive (auto-generated)" links={archiveLinks} />
      </div>
    </div>
  );
}

