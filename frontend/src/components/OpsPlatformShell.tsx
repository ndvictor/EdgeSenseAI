"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Activity,
  BarChart3,
  BookOpen,
  BrainCircuit,
  Building2,
  ChevronRight,
  Crown,
  DatabaseZap,
  FlaskConical,
  Gauge,
  KeyRound,
  LineChart,
  PlugZap,
  Settings,
  Shield,
  SlidersHorizontal,
  Target,
  WalletCards,
  Zap,
  Wrench,
  Server,
  Cpu,
  Layers,
  HardHat,
  Factory,
  ClipboardList,
  Cog,
  Terminal,
  Rocket,
  Monitor,
  Network,
} from "lucide-react";

type OpsPageConfig = {
  key: string;
  title: string;
  href: string;
  group: string;
  icon: typeof Crown;
  purpose: string;
  hero: string;
  cards: Array<{ label: string; value: string; sub: string; tone?: string }>;
  recommendations: Array<{ priority: string; area: string; recommendation: string; benefit: string; action: string }>;
};

export const opsPages: OpsPageConfig[] = [
  {
    key: "dashboard",
    title: "Ops Dashboard",
    href: "/ops",
    group: "Ops Command",
    icon: Monitor,
    purpose: "What is the operational status of the platform?",
    hero: "Real-time operational overview: system health, active workflows, resource utilization, and critical alerts.",
    cards: [
      { label: "System Status", value: "Healthy", sub: "All services operational", tone: "text-emerald-300" },
      { label: "Active Workflows", value: "12", sub: "Running now" },
      { label: "Queue Depth", value: "Low", sub: "Processing normally" },
      { label: "Error Rate", value: "0.1%", sub: "Within limits" },
      { label: "CPU Usage", value: "45%", sub: "Normal load" },
      { label: "Memory", value: "62%", sub: "Healthy" },
    ],
    recommendations: [
      { priority: "High", area: "Monitoring", recommendation: "Set up automated alerts for queue depth > 100", benefit: "Early warning", action: "Configure" },
      { priority: "Medium", area: "Scaling", recommendation: "Enable auto-scaling for market hours", benefit: "Handle load", action: "Enable" },
      { priority: "Low", area: "Maintenance", recommendation: "Schedule weekly system health reports", benefit: "Visibility", action: "Schedule" },
    ],
  },
  {
    key: "infrastructure",
    title: "Infrastructure",
    href: "/ops/infrastructure",
    group: "Platform Ops",
    icon: Server,
    purpose: "What is the state of our infrastructure?",
    hero: "Infrastructure management: servers, containers, databases, and network resources.",
    cards: [
      { label: "Servers", value: "8/8", sub: "All online", tone: "text-emerald-300" },
      { label: "Containers", value: "24", sub: "Active" },
      { label: "DB Connections", value: "45/100", sub: "Healthy" },
      { label: "Storage", value: "68%", sub: "OK" },
      { label: "Network I/O", value: "Normal", sub: "No issues" },
      { label: "Latency", value: "12ms", sub: "Fast" },
    ],
    recommendations: [
      { priority: "High", area: "Backup", recommendation: "Verify daily database backups are completing", benefit: "Data safety", action: "Check" },
      { priority: "Medium", area: "Security", recommendation: "Review firewall rules monthly", benefit: "Security", action: "Review" },
      { priority: "Low", area: "Optimization", recommendation: "Analyze unused compute resources", benefit: "Cost savings", action: "Analyze" },
    ],
  },
  {
    key: "workflows",
    title: "Workflow Engine",
    href: "/ops/workflows",
    group: "Platform Ops",
    icon: Layers,
    purpose: "How are workflows performing?",
    hero: "Workflow monitoring, execution tracking, and pipeline management.",
    cards: [
      { label: "Success Rate", value: "99.2%", sub: "Healthy", tone: "text-emerald-300" },
      { label: "Avg Duration", value: "2.3s", sub: "Fast" },
      { label: "Pending", value: "5", sub: "Processing" },
      { label: "Failed (24h)", value: "3", sub: "Investigate" },
      { label: "Throughput", value: "450/h", sub: "Good" },
      { label: "Retries", value: "12", sub: "Acceptable" },
    ],
    recommendations: [
      { priority: "High", area: "Reliability", recommendation: "Review failed workflow patterns", benefit: "Stability", action: "Investigate" },
      { priority: "Medium", area: "Performance", recommendation: "Optimize slow workflow steps", benefit: "Speed", action: "Optimize" },
      { priority: "Low", area: "Capacity", recommendation: "Scale workers during market open", benefit: "Throughput", action: "Scale" },
    ],
  },
  {
    key: "deployments",
    title: "Deployments",
    href: "/ops/deployments",
    group: "DevOps",
    icon: Rocket,
    purpose: "What is the deployment status?",
    hero: "Deployment pipeline, releases, rollbacks, and version management.",
    cards: [
      { label: "Last Deploy", value: "2h ago", sub: "Successful", tone: "text-emerald-300" },
      { label: "Current Version", value: "v1.4.2", sub: "Production" },
      { label: "Staging", value: "v1.5.0-rc", sub: "Ready" },
      { label: "Rollback Time", value: "<5min", sub: "Verified" },
      { label: "Tests Passing", value: "98%", sub: "Good" },
      { label: "Uptime", value: "99.9%", sub: "SLA met" },
    ],
    recommendations: [
      { priority: "High", area: "Safety", recommendation: "Always deploy to staging first", benefit: "Catch issues early", action: "Enforce" },
      { priority: "Medium", area: "Automation", recommendation: "Automate smoke tests post-deploy", benefit: "Confidence", action: "Build" },
      { priority: "Low", area: "Monitoring", recommendation: "Add deployment metrics to dashboard", benefit: "Visibility", action: "Add" },
    ],
  },
  {
    key: "monitoring",
    title: "Monitoring & Alerts",
    href: "/ops/monitoring",
    group: "Observability",
    icon: Activity,
    purpose: "Are we monitoring everything?",
    hero: "Metrics, logs, traces, and alerting configuration.",
    cards: [
      { label: "Active Alerts", value: "3", sub: "Non-critical" },
      { label: "Log Volume", value: "2.4GB/h", sub: "Normal" },
      { label: "Traces/min", value: "450", sub: "Capturing" },
      { label: "SLO Status", value: "Met", sub: "On track", tone: "text-emerald-300" },
      { label: "MTTR", value: "4m", sub: "Fast" },
      { label: "Coverage", value: "95%", sub: "Good" },
    ],
    recommendations: [
      { priority: "High", area: "Alerts", recommendation: "Tune alert thresholds to reduce noise", benefit: "Focus", action: "Tune" },
      { priority: "Medium", area: "Logs", recommendation: "Add structured logging to all services", benefit: "Debug faster", action: "Implement" },
      { priority: "Low", area: "Traces", recommendation: "Enable distributed tracing for new services", benefit: "Visibility", action: "Enable" },
    ],
  },
  {
    key: "security",
    title: "Security Ops",
    href: "/ops/security",
    group: "Observability",
    icon: Shield,
    purpose: "Is the platform secure?",
    hero: "Security monitoring, access logs, vulnerability tracking, and compliance.",
    cards: [
      { label: "Vulnerabilities", value: "2 Low", sub: "No critical", tone: "text-emerald-300" },
      { label: "Failed Logins", value: "5", sub: "Monitor" },
      { label: "SSL Expiry", value: "45 days", sub: "OK" },
      { label: "Access Reviews", value: "Current", sub: "Up to date" },
      { label: "Audit Logs", value: "Active", sub: "Recording" },
      { label: "Compliance", value: "Pass", sub: "All checks" },
    ],
    recommendations: [
      { priority: "High", area: "Vulnerabilities", recommendation: "Patch critical CVEs within 24h", benefit: "Security", action: "Enforce" },
      { priority: "Medium", area: "Access", recommendation: "Review service account permissions quarterly", benefit: "Least privilege", action: "Review" },
      { priority: "Low", area: "Training", recommendation: "Security training for all team members", benefit: "Awareness", action: "Schedule" },
    ],
  },
  {
    key: "databases",
    title: "Database Ops",
    href: "/ops/databases",
    group: "Data Platform",
    icon: DatabaseZap,
    purpose: "How are databases performing?",
    hero: "Database health, query performance, replication status, and maintenance.",
    cards: [
      { label: "Primary Status", value: "Healthy", sub: "Responding", tone: "text-emerald-300" },
      { label: "Replication Lag", value: "<1s", sub: "Good" },
      { label: "Slow Queries", value: "3", sub: "Review" },
      { label: "Index Health", value: "98%", sub: "Optimized" },
      { label: "Backup", value: "Current", sub: "6h ago" },
      { label: "Connections", value: "45/100", sub: "Healthy" },
    ],
    recommendations: [
      { priority: "High", area: "Performance", recommendation: "Optimize top 10 slow queries weekly", benefit: "Speed", action: "Monitor" },
      { priority: "Medium", area: "Capacity", recommendation: "Plan storage growth for next quarter", benefit: "No surprises", action: "Forecast" },
      { priority: "Low", area: "Maintenance", recommendation: "Schedule monthly vacuum operations", benefit: "Health", action: "Schedule" },
    ],
  },
  {
    key: "integrations",
    title: "Integrations",
    href: "/ops/integrations",
    group: "Data Platform",
    icon: PlugZap,
    purpose: "Are external integrations healthy?",
    hero: "Broker APIs, market data feeds, and third-party service connections.",
    cards: [
      { label: "Alpaca API", value: "Connected", sub: "Healthy", tone: "text-emerald-300" },
      { label: "YFinance", value: "Degraded", sub: "Limited" },
      { label: "Polygon", value: "Not Configured", sub: "Pending" },
      { label: "OpenAI", value: "OK", sub: "Responding" },
      { label: "LangSmith", value: "Active", sub: "Tracing" },
      { label: "Latency", value: "45ms", sub: "Fast" },
    ],
    recommendations: [
      { priority: "High", area: "Reliability", recommendation: "Add circuit breakers for all external APIs", benefit: "Resilience", action: "Implement" },
      { priority: "Medium", area: "Monitoring", recommendation: "Track API rate limits and quota usage", benefit: "Avoid limits", action: "Monitor" },
      { priority: "Low", area: "Fallbacks", recommendation: "Configure fallback data sources", benefit: "Continuity", action: "Configure" },
    ],
  },
  {
    key: "maintenance",
    title: "Maintenance",
    href: "/ops/maintenance",
    group: "Operations",
    icon: Wrench,
    purpose: "What maintenance is scheduled?",
    hero: "Scheduled maintenance windows, patch management, and system updates.",
    cards: [
      { label: "Next Window", value: "Sat 2AM", sub: "Scheduled" },
      { label: "Pending Patches", value: "5", sub: "Review" },
      { label: "System Updates", value: "Current", sub: "Up to date", tone: "text-emerald-300" },
      { label: "Cert Renewals", value: "OK", sub: "Auto-renew" },
      { label: "Log Rotation", value: "Active", sub: "Working" },
      { label: "Health Checks", value: "Passing", sub: "All green" },
    ],
    recommendations: [
      { priority: "High", area: "Planning", recommendation: "Announce maintenance 48h in advance", benefit: "No surprises", action: "Communicate" },
      { priority: "Medium", area: "Automation", recommendation: "Automate non-disruptive patches", benefit: "Reduce work", action: "Automate" },
      { priority: "Low", area: "Testing", recommendation: "Test rollback procedures monthly", benefit: "Preparedness", action: "Practice" },
    ],
  },
  {
    key: "settings",
    title: "Ops Settings",
    href: "/ops/settings",
    group: "Configuration",
    icon: Cog,
    purpose: "Configure operational parameters",
    hero: "Operational settings, thresholds, notification preferences, and system configuration.",
    cards: [
      { label: "Auto-Scale", value: "Enabled", sub: "Active", tone: "text-emerald-300" },
      { label: "Alert Channels", value: "3", sub: "Configured" },
      { label: "Runbooks", value: "12", sub: "Documented" },
      { label: "Thresholds", value: "Set", sub: "Calibrated" },
      { label: "Notifications", value: "On", sub: "Delivering" },
      { label: "Debug Mode", value: "Off", sub: "Production" },
    ],
    recommendations: [
      { priority: "High", area: "Safety", recommendation: "Require approval for production config changes", benefit: "Prevent errors", action: "Enforce" },
      { priority: "Medium", area: "Documentation", recommendation: "Keep runbooks updated with latest procedures", benefit: "Knowledge", action: "Maintain" },
      { priority: "Low", area: "Testing", recommendation: "Test alert channels weekly", benefit: "Reliability", action: "Verify" },
    ],
  },
];

export function getOpsPageConfig(key: string) {
  return opsPages.find((page) => page.key === key) ?? opsPages[0];
}

function opsGroups() {
  const grouped = new Map<string, OpsPageConfig[]>();
  opsPages.forEach((page) => grouped.set(page.group, [...(grouped.get(page.group) ?? []), page]));
  return Array.from(grouped.entries());
}

function Sparkline() {
  return (
    <svg viewBox="0 0 120 42" className="h-12 w-28 text-emerald-300" aria-hidden="true">
      <path d="M4 32 C16 22, 24 28, 34 19 S55 13, 66 22 S84 34, 94 15 S108 7, 116 13" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function MetricCard({ card }: { card: OpsPageConfig["cards"][number] }) {
  return (
    <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-4 shadow-[0_0_35px_rgba(0,0,0,0.25)] backdrop-blur">
      <div className="text-xs text-slate-500">{card.label}</div>
      <div className={`mt-3 text-2xl font-semibold tracking-tight ${card.tone ?? "text-white"}`}>{card.value}</div>
      <div className="mt-2 flex items-center justify-between gap-2 text-xs text-slate-500">
        <span>{card.sub}</span>
        <Sparkline />
      </div>
    </div>
  );
}

export function OpsPlatformShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="flex min-h-screen bg-emerald-950 text-white">
      <aside className="flex min-h-screen w-80 shrink-0 flex-col border-r border-emerald-400/10 bg-[#05080d] px-4 py-5 shadow-[18px_0_60px_rgba(0,0,0,0.45)]">
        <Link href="/ops" className="mb-8 flex items-center gap-3 px-1">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-emerald-400/50 bg-emerald-400/10 text-xl font-black text-emerald-300 shadow-[0_0_28px_rgba(16,185,129,0.25)]">O</div>
          <div>
            <div className="text-2xl font-semibold tracking-tight text-emerald-300">Ops Command</div>
            <div className="text-xs text-slate-500">Operational platform</div>
          </div>
        </Link>

        <nav className="space-y-5 overflow-y-auto pr-1">
          {opsGroups().map(([group, pages]) => (
            <div key={group}>
              <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">{group}</div>
              <div className="space-y-1.5">
                {pages.map((page) => {
                  const Icon = page.icon;
                  const active = pathname === page.href || (page.href === "/ops" && pathname === "/ops/");
                  return (
                    <Link
                      key={page.href}
                      href={page.href}
                      className={`group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium transition-all ${
                        active
                          ? "border border-emerald-400/40 bg-emerald-400/10 text-white shadow-[0_0_28px_rgba(16,185,129,0.12)]"
                          : "text-slate-300 hover:bg-white/[0.04] hover:text-emerald-200"
                      }`}
                    >
                      <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400">
                        <Icon className="h-4 w-4" />
                      </span>
                      <span className="flex-1">{page.title}</span>
                      <ChevronRight className="h-3 w-3 text-slate-600" />
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Cross-links to other command centers */}
        <div className="mt-auto pt-6 border-t border-emerald-400/10">
          <div className="mb-2 px-2 text-[10px] font-semibold uppercase tracking-[0.28em] text-slate-500">Other Centers</div>
          <div className="space-y-1.5">
            <Link
              href="/owner"
              className="group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/[0.04] hover:text-emerald-200"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400">
                <Crown className="h-4 w-4" />
              </span>
              <span className="flex-1">Owner Command</span>
            </Link>
            <Link
              href="/command-center"
              className="group flex items-center gap-3 rounded-xl px-2 py-2 text-sm font-medium text-slate-300 transition-all hover:bg-white/[0.04] hover:text-emerald-200"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-emerald-400/25 bg-emerald-400/[0.04] text-emerald-400">
                <Terminal className="h-4 w-4" />
              </span>
              <span className="flex-1">Engineering Console</span>
            </Link>
          </div>
        </div>
      </aside>
      <main className="relative min-h-screen flex-1 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_62%_0%,rgba(16,185,129,0.16),transparent_28%),radial-gradient(circle_at_0%_100%,rgba(20,184,166,0.08),transparent_28%)]" />
        <div className="absolute right-0 top-0 h-72 w-[55rem] rounded-full border-t border-emerald-300/30 blur-[0.2px]" />
        <div className="absolute inset-0 opacity-25 [background-image:linear-gradient(rgba(16,185,129,0.06)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.06)_1px,transparent_1px)] [background-size:54px_54px]" />
        <div className="relative z-10 p-8">{children}</div>
      </main>
    </div>
  );
}

export function OpsPageTemplate({ page }: { page: OpsPageConfig }) {
  const Icon = page.icon;

  return (
    <OpsPlatformShell>
      <header className="mb-7 flex items-start justify-between gap-6">
        <div>
          <div className="mb-3 inline-flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/[0.04] px-3 py-2 text-xs font-semibold text-emerald-300">
            <Icon className="h-4 w-4" />
            {page.group}
          </div>
          <h1 className="text-4xl font-black tracking-[-0.04em] text-white">{page.title}</h1>
          <p className="mt-2 max-w-3xl text-sm text-slate-400">{page.purpose}</p>
        </div>
        <div className="flex gap-3">
          <Link href="/owner" className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
            Owner Command
          </Link>
          <Link href="/command-center" className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-2 text-sm text-slate-300 transition hover:border-emerald-400/30 hover:text-emerald-300">
            Engineering Console
          </Link>
        </div>
      </header>

      <section className="mb-4 rounded-2xl border border-emerald-400/15 bg-black/35 p-6 shadow-[0_0_40px_rgba(0,0,0,0.35)] backdrop-blur">
        <div className="flex items-center gap-5">
          <div className="flex h-16 w-16 items-center justify-center rounded-2xl border border-emerald-400/25 bg-emerald-400/10 text-emerald-300">
            <Icon className="h-8 w-8" />
          </div>
          <div>
            <div className="text-sm font-medium text-emerald-300">Operational view</div>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight">{page.hero}</h2>
          </div>
        </div>
      </section>

      <section className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-6">
        {page.cards.map((card) => <MetricCard key={card.label} card={card} />)}
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1.05fr_1.25fr]">
        <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><Gauge className="h-5 w-5 text-emerald-300" /> System metrics & status</div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="text-xs text-slate-500">Current state</div>
              <div className="mt-3 text-xl font-semibold text-white">Operational / Nominal</div>
              <p className="mt-3 text-sm leading-6 text-slate-400">All systems running within expected parameters. No critical alerts active.</p>
            </div>
            <div className="rounded-xl border border-white/10 bg-white/[0.025] p-4">
              <div className="text-xs text-slate-500">Resource forecast</div>
              <div className="mt-3 text-xl font-semibold text-amber-300">Capacity at 45%</div>
              <p className="mt-3 text-sm leading-6 text-slate-400">Resources scaling appropriately for expected load patterns.</p>
            </div>
          </div>
          <div className="mt-4 h-52 rounded-xl border border-white/10 bg-[linear-gradient(180deg,rgba(16,185,129,0.08),rgba(0,0,0,0.15))] p-5">
            <div className="text-xs text-slate-500">Resource utilization trend</div>
            <svg viewBox="0 0 600 160" className="mt-6 h-36 w-full text-emerald-300" aria-hidden="true">
              <path d="M8 130 C80 92, 122 112, 176 76 S278 58, 332 88 S430 132, 486 54 S560 34, 592 48" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
            </svg>
          </div>
        </div>

        <div className="rounded-2xl border border-emerald-400/15 bg-black/35 p-5 backdrop-blur">
          <div className="mb-4 flex items-center gap-2 text-lg font-semibold"><SlidersHorizontal className="h-5 w-5 text-emerald-300" /> Ops recommendations</div>
          <div className="space-y-2">
            {page.recommendations.map((row) => (
              <div key={`${row.priority}-${row.area}-${row.action}`} className="grid grid-cols-[74px_120px_1fr_150px_110px] items-center gap-3 rounded-xl border border-white/10 bg-white/[0.025] px-3 py-3 text-sm">
                <div className="rounded-full border border-emerald-400/20 px-3 py-1 text-center text-xs text-emerald-300">{row.priority}</div>
                <div className="text-slate-400">{row.area}</div>
                <div className="text-slate-200">{row.recommendation}</div>
                <div className="text-emerald-300">{row.benefit}</div>
                <button className="rounded-lg border border-white/10 px-3 py-2 text-slate-200 transition hover:border-emerald-400/30 hover:text-emerald-300">{row.action}</button>
              </div>
            ))}
          </div>
        </div>
      </section>
    </OpsPlatformShell>
  );
}
