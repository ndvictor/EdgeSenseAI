import type { AdminDashboardBundle } from "@/hooks/useAdminDashboardBundle";
import type { DataSourceStatus } from "@/lib/api";

export type DashboardCard = { label: string; value: string; sub: string; tone?: string };
export type DashboardRecRow = {
  priority: string;
  area: string;
  recommendation: string;
  benefit: string;
  action: string;
};

function money(n: number) {
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function pct(n: number) {
  return `${Math.round(n * 100)}%`;
}

function toneForCheck(status: string | undefined): string | undefined {
  if (status === "pass") return "text-emerald-300";
  if (status === "warn") return "text-amber-300";
  if (status === "fail") return "text-rose-300";
  return undefined;
}

function sourceByKey(bundle: AdminDashboardBundle, key: string): DataSourceStatus | undefined {
  return bundle.dataSources?.sources.find((s) => s.key === key);
}

function pickSources(bundle: AdminDashboardBundle, limit: number): DataSourceStatus[] {
  const list = bundle.dataSources?.sources ?? [];
  return list.slice(0, limit);
}

export function buildOpsCards(pageKey: string, b: AdminDashboardBundle): DashboardCard[] {
  switch (pageKey) {
    case "dashboard":
      return [
        {
          label: "Platform readiness",
          value: b.platformReadiness?.status ?? "—",
          sub: b.platformReadiness ? `Updated ${new Date(b.platformReadiness.generated_at).toLocaleString()}` : "API: /api/platform-readiness",
          tone:
            b.platformReadiness?.status === "ready"
              ? "text-emerald-300"
              : b.platformReadiness?.status === "partial"
                ? "text-amber-300"
                : b.platformReadiness
                  ? "text-rose-300"
                  : undefined,
        },
        {
          label: "AI ops status",
          value: b.aiOpsSummary?.status ?? "—",
          sub: b.aiOpsSummary?.data_source ? `Source: ${b.aiOpsSummary.data_source}` : "API: /api/ai-ops/summary",
        },
        {
          label: "Workflow definitions",
          value: String(b.aiOpsWorkflows?.workflows?.length ?? "—"),
          sub: "API: /api/ai-ops/workflows",
        },
        {
          label: "Scheduler jobs",
          value: String(b.aiOpsScheduler?.jobs?.length ?? b.aiOpsScheduler?.jobs_configured ?? "—"),
          sub: b.aiOpsScheduler?.status ? `Scheduler ${b.aiOpsScheduler.status}` : "API: /api/ai-ops/scheduler/jobs",
        },
        {
          label: "Data freshness gate",
          value: b.dataFreshness?.status ?? "—",
          sub: b.dataFreshness ? `Checked ${new Date(b.dataFreshness.checked_at).toLocaleString()}` : "API: /api/data-freshness/latest",
          tone: toneForCheck(b.dataFreshness?.status),
        },
        {
          label: "Runtime phase (ET)",
          value: b.runtimePhase?.market_phase ?? "—",
          sub: b.runtimeCadence?.active_loop ? `Loop: ${b.runtimeCadence.active_loop}` : "API: /api/runtime/phase",
        },
      ];
    case "infrastructure":
      return [
        {
          label: "Postgres (AI ops)",
          value: b.aiOpsSummary?.postgres_persistence_status ?? "—",
          sub: "From /api/ai-ops/summary",
          tone: b.aiOpsSummary?.postgres_persistence_status?.toLowerCase().includes("ok") ? "text-emerald-300" : undefined,
        },
        {
          label: "pgvector / memory",
          value: b.aiOpsSummary?.pgvector_status ?? b.aiOpsSummary?.vector_memory_status ?? "—",
          sub: b.aiOpsSummary?.recent_memory_count != null ? `Recent memories: ${b.aiOpsSummary.recent_memory_count}` : "AI ops summary",
        },
        {
          label: "Data sources OK",
          value: String(b.dataSources?.connected_sources ?? "—") + " / " + String(b.dataSources?.total_sources ?? "—"),
          sub: "Connected or test-ready vs total",
        },
        {
          label: "Tracing",
          value: b.tracing?.mode ?? (b.tracing?.enabled ? "on" : "off"),
          sub: b.tracing?.project_configured ? "LangSmith project set" : "API: /api/tracing/status",
        },
        {
          label: "Live trading (policy)",
          value: b.runtimePhase?.live_trading_allowed ? "allowed (flag)" : "disallowed",
          sub: "API: /api/runtime/phase",
          tone: b.runtimePhase?.live_trading_allowed ? "text-amber-300" : "text-emerald-300",
        },
        {
          label: "Human approval",
          value: b.runtimePhase?.human_approval_required ? "required" : "optional",
          sub: "API: /api/runtime/phase",
        },
      ];
    case "workflows": {
      const runs = b.strategyWorkflowRuns ?? [];
      const latest = runs[0];
      const wf = b.aiOpsWorkflows?.workflows ?? [];
      const partial = wf.filter((w) => (w.status ?? "").toLowerCase().includes("partial")).length;
      return [
        {
          label: "Defined workflows",
          value: String(wf.length),
          sub: "AI ops catalog",
        },
        {
          label: "Partial / attention",
          value: String(partial),
          sub: "Statuses containing partial",
        },
        {
          label: "Latest strategy workflow",
          value: latest?.workflow_run_id?.slice(0, 8) ?? "—",
          sub: latest?.status ? `Status ${latest.status}` : "API: /api/strategy-workflows/runs",
        },
        {
          label: "Strategy ranking (latest)",
          value: b.strategyRanking?.top_strategy_key ?? "—",
          sub: b.strategyRanking?.status ? `Run ${b.strategyRanking.status}` : "API: /api/strategy-ranking/latest",
        },
        {
          label: "Model selection strategy",
          value: b.modelSelection?.strategy_key ?? "—",
          sub: b.modelSelection?.status ?? "API: /api/model-selection/latest",
        },
        {
          label: "LLM usage (AI ops)",
          value: b.aiOpsLlmUsage?.status ?? "—",
          sub:
            b.aiOpsLlmUsage?.cost_today != null
              ? `Est. cost today $${Number(b.aiOpsLlmUsage.cost_today).toFixed(4)}`
              : "/api/ai-ops/llm-usage",
        },
      ];
    }
    case "deployments":
      return [
        {
          label: "Release metadata",
          value: "Not exposed",
          sub: "No /api/deployments in this stack; use your CI for versions",
        },
        {
          label: "Last readiness check",
          value: b.platformReadiness ? new Date(b.platformReadiness.generated_at).toLocaleString() : "—",
          sub: "/api/platform-readiness",
        },
        {
          label: "Platform verdict",
          value: b.platformReadiness?.status ?? "—",
          sub: String(b.platformReadiness?.blockers?.length ?? 0) + " blockers",
          tone: b.platformReadiness?.status === "ready" ? "text-emerald-300" : b.platformReadiness ? "text-amber-300" : undefined,
        },
        {
          label: "Tracing bundle",
          value: b.tracing?.langsmith_installed ? "LangSmith pkg" : "—",
          sub: b.tracing?.api_key_configured ? "API key configured" : "Tracing status",
        },
        {
          label: "Data source layer",
          value: String(b.dataSources?.connected_sources ?? "—") + "/" + String(b.dataSources?.total_sources ?? "—"),
          sub: "Connected vs total from /api/data-sources/status",
        },
        {
          label: "Auto-run control",
          value: b.autoRun?.status ?? "—",
          sub: b.autoRun?.data_source ? `Source ${b.autoRun.data_source}` : "/api/auto-run/status",
        },
      ];
    case "monitoring":
      return [
        {
          label: "Readiness checks",
          value: b.platformReadiness ? `${b.platformReadiness.checks.filter((c) => c.status === "pass").length}/${b.platformReadiness.checks.length} pass` : "—",
          sub: "/api/platform-readiness",
        },
        {
          label: "Tracing mode",
          value: b.tracing?.mode ?? "—",
          sub: b.tracing?.enabled ? "enabled" : "disabled",
        },
        {
          label: "Data freshness",
          value: b.dataFreshness?.status ?? "—",
          sub: b.dataFreshness ? `${b.dataFreshness.results?.length ?? 0} symbols in last run` : "latest gate",
          tone: toneForCheck(b.dataFreshness?.status),
        },
        {
          label: "AI ops",
          value: b.aiOpsSummary?.status ?? "—",
          sub: b.aiOpsSummary?.generated_at ? new Date(b.aiOpsSummary.generated_at).toLocaleString() : "",
        },
        {
          label: "Scheduler",
          value: b.aiOpsScheduler?.status ?? "—",
          sub: String(b.aiOpsScheduler?.jobs?.length ?? 0) + " jobs",
        },
        {
          label: "Failed jobs (today)",
          value: String(b.aiOpsScheduler?.failed_jobs_today ?? "—"),
          sub: "From scheduler summary",
        },
      ];
    case "security":
      return [
        {
          label: "Live trading",
          value: b.autoRun?.live_trading_enabled ? "enabled (control)" : "disabled",
          sub: "/api/auto-run/status",
          tone: b.autoRun?.live_trading_enabled ? "text-amber-300" : "text-emerald-300",
        },
        {
          label: "Human approval",
          value: b.autoRun?.require_human_approval ? "required" : "off",
          sub: "/api/auto-run/status",
        },
        {
          label: "Paper trading",
          value: b.autoRun?.paper_trading_enabled ? "enabled" : "disabled",
          sub: "/api/auto-run/status",
        },
        {
          label: "Readiness blockers",
          value: String(b.platformReadiness?.blockers?.length ?? "—"),
          sub: "Platform gate",
        },
        {
          label: "Broker execution (settings)",
          value: b.settings?.trading?.broker_execution_enabled ? "enabled" : "disabled",
          sub: "/api/settings",
        },
        {
          label: "LangSmith tracing flag",
          value: b.settings?.platform?.langsmith_tracing ? "on" : "off",
          sub: "/api/settings",
        },
      ];
    case "databases":
      return [
        {
          label: "Postgres persistence",
          value: b.aiOpsSummary?.postgres_persistence_status ?? "—",
          sub: "AI ops summary",
        },
        {
          label: "pgvector",
          value: b.aiOpsSummary?.pgvector_status ?? "—",
          sub: (b.aiOpsSummary?.embedding_provider)
            ? "Embeddings: " + String(b.aiOpsSummary.embedding_provider)
            : "",
        },
        {
          label: "Postgres (data sources)",
          value: sourceByKey(b, "postgres")?.status?.replace(/_/g, " ") ?? sourceByKey(b, "postgresql")?.status?.replace(/_/g, " ") ?? "—",
          sub: sourceByKey(b, "postgres")?.message ?? sourceByKey(b, "postgresql")?.message ?? "/api/data-sources/status",
        },
        {
          label: "Redis (if listed)",
          value: sourceByKey(b, "redis")?.status?.replace(/_/g, " ") ?? "—",
          sub: sourceByKey(b, "redis")?.message ?? "optional component",
        },
        {
          label: "Vector memory",
          value: b.aiOpsSummary?.vector_memory_status ?? "—",
          sub: "AI ops",
        },
        {
          label: "Memory rows (recent)",
          value: String(b.aiOpsSummary?.recent_memory_count ?? "—"),
          sub: "Approximate from summary",
        },
      ];
    case "integrations": {
      const picks = pickSources(b, 6);
      if (!picks.length) {
        return [{ label: "Data sources", value: "—", sub: "No sources in /api/data-sources/status response" }];
      }
      return picks.map((s, i) => ({
        label: String(s.name || s.key || "Source " + String(i + 1)),
        value: s.status.replace(/_/g, " "),
        sub: s.message?.slice(0, 80) || (s.configured ? "configured" : "not configured"),
        tone: ["connected", "configured", "installed"].includes(s.status)
          ? "text-emerald-300"
          : s.status?.includes("error")
            ? "text-rose-300"
            : "text-amber-300",
      }));
    }
    case "maintenance":
      return [
        {
          label: "Data freshness checked",
          value: b.dataFreshness ? new Date(b.dataFreshness.checked_at).toLocaleString() : "—",
          sub: b.dataFreshness?.source ?? "latest run",
        },
        {
          label: "Freshness verdict",
          value: b.dataFreshness?.status ?? "—",
          sub: String(b.dataFreshness?.warnings?.length ?? 0) + " warnings",
          tone: toneForCheck(b.dataFreshness?.status),
        },
        {
          label: "Market phase",
          value: b.runtimePhase?.market_phase ?? "—",
          sub: b.runtimePhase?.current_time_et ?? "",
        },
        {
          label: "Is trading day",
          value: b.runtimePhase?.is_trading_day == null ? "—" : b.runtimePhase.is_trading_day ? "yes" : "no",
          sub: "/api/runtime/phase",
        },
        {
          label: "Scheduler updated",
          value: b.aiOpsScheduler?.updated_at ? new Date(b.aiOpsScheduler.updated_at).toLocaleString() : "—",
          sub: "AI ops scheduler",
        },
        {
          label: "Platform snapshot",
          value: b.platformReadiness?.status ?? "—",
          sub: b.platformReadiness?.generated_at ? new Date(b.platformReadiness.generated_at).toLocaleString() : "",
        },
      ];
    case "settings":
      return [
        {
          label: "Auto-run",
          value: b.autoRun?.auto_run_enabled ? "on" : "off",
          sub: "/api/auto-run/status",
        },
        {
          label: "Max daily LLM (control)",
          value: b.autoRun != null ? money(b.autoRun.max_daily_llm_cost) : "—",
          sub: "Auto-run control plane",
        },
        {
          label: "LLM daily budget (settings)",
          value: b.settings != null ? money(b.settings.llm_gateway.llm_gateway_daily_budget) : "—",
          sub: "/api/settings",
        },
        {
          label: "Max agent runs / day",
          value: String(b.autoRun?.max_daily_agent_runs ?? "—"),
          sub: "/api/auto-run/status",
        },
        {
          label: "Market data provider",
          value: b.settings?.market_data.market_data_provider ?? "—",
          sub: b.settings?.market_data.alpaca_market_data_enabled ? "Alpaca data on" : "check settings",
        },
        {
          label: "Vector memory",
          value: b.settings?.platform.vector_memory_enabled ? "enabled" : "disabled",
          sub: "/api/settings",
        },
      ];
    default:
      return buildOpsCards("dashboard", b);
  }
}

export function buildOwnerCards(pageKey: string, b: AdminDashboardBundle): DashboardCard[] {
  switch (pageKey) {
    case "pnl":
      return [
        {
          label: "Account equity (risk profile)",
          value: b.accountRisk != null ? money(b.accountRisk.account_equity) : "—",
          sub: b.accountRisk?.source ?? "/api/account-risk/profile",
        },
        {
          label: "Buying power",
          value: b.accountRisk != null ? money(b.accountRisk.buying_power) : "—",
          sub: "Cash " + (b.accountRisk != null ? money(b.accountRisk.cash) : "—"),
        },
        {
          label: "Alpaca portfolio value",
          value: b.alpacaPaper?.account?.portfolio_value != null ? money(b.alpacaPaper.account.portfolio_value) : "—",
          sub: b.alpacaPaper?.message ?? "/api/paper-trading/alpaca",
        },
        {
          label: "LLM cost today",
          value: b.llmCosts != null ? money(b.llmCosts.cost_today) : "—",
          sub: b.llmCosts ? "Budget " + money(b.llmCosts.daily_budget) : "/api/llm-gateway/costs",
        },
        {
          label: "Journal entries",
          value: String(b.journalSummary?.total_entries ?? "—"),
          sub: b.journalSummary ? "Win rate " + pct(b.journalSummary.win_rate) : "/api/journal/outcomes/summary",
        },
        {
          label: "Paper mode",
          value: b.accountRisk?.paper_only !== false ? "yes" : "no",
          sub: "Account risk profile",
        },
      ];
    case "risk":
      return [
        {
          label: "Max daily loss",
          value: b.accountRisk != null ? pct(b.accountRisk.max_daily_loss_percent) : "—",
          sub: "Of account",
        },
        {
          label: "Max risk / trade",
          value: b.accountRisk != null ? pct(b.accountRisk.max_risk_per_trade_percent) : "—",
          sub: "/api/account-risk/profile",
        },
        {
          label: "Min reward:risk",
          value: b.accountRisk != null ? String(b.accountRisk.min_reward_risk_ratio) + "R" : "—",
          sub: b.accountRisk?.preferred_risk_style ?? "",
        },
        {
          label: "Live trading (control)",
          value: b.autoRun?.live_trading_enabled ? "on" : "off",
          sub: "/api/auto-run/status",
          tone: b.autoRun?.live_trading_enabled ? "text-amber-300" : "text-emerald-300",
        },
        {
          label: "Human approval",
          value: b.autoRun?.require_human_approval ? "required" : "off",
          sub: "/api/auto-run/status",
        },
        {
          label: "Account mode",
          value: b.accountRisk?.account_mode ?? "—",
          sub: b.accountRisk?.last_updated ? new Date(b.accountRisk.last_updated).toLocaleString() : "",
        },
      ];
    case "trading":
      return [
        {
          label: "Top strategy (ranking)",
          value: b.strategyRanking?.top_strategy_key ?? "—",
          sub: b.strategyRanking?.regime ? "Regime context " + String(b.strategyRanking.regime) : "/api/strategy-ranking/latest",
        },
        {
          label: "Command center mode",
          value: b.commandCenter?.dashboard_mode ?? "—",
          sub: b.commandCenter?.cost_usage_message?.slice(0, 60) ?? "/api/command-center",
        },
        {
          label: "Market regime (service)",
          value: b.marketRegime?.regime_state ?? "—",
          sub: b.marketRegime?.strategy_bias ?? "/api/market-regime",
        },
        {
          label: "Regime model (latest)",
          value: b.latestMarketRegimeModel?.regime ?? "—",
          sub: b.latestMarketRegimeModel?.trend_state ?? "/api/market-regime/model/latest",
        },
        {
          label: "Watchlist candidates",
          value: String(b.liveWatchlist?.candidates?.length ?? "—"),
          sub: b.liveWatchlist?.summary?.last_updated
            ? "Updated " + String(b.liveWatchlist.summary.last_updated)
            : "/api/live-watchlist/latest",
        },
        {
          label: "Top action symbol",
          value: b.commandCenter?.top_action?.symbol ?? "—",
          sub: b.commandCenter?.top_action?.action_label ?? b.commandCenter?.top_action?.action ?? "no primary action",
        },
      ];
    case "insights": {
      const failChecks = b.platformReadiness?.checks.filter((c) => c.status === "fail").length ?? 0;
      const warnChecks = b.platformReadiness?.checks.filter((c) => c.status === "warn").length ?? 0;
      return [
        {
          label: "Platform status",
          value: b.platformReadiness?.status ?? "—",
          sub: String(failChecks) + " failed checks | " + String(warnChecks) + " warnings",
          tone: toneForCheck(failChecks ? "fail" : warnChecks ? "warn" : "pass"),
        },
        {
          label: "Open research tasks",
          value: String(b.researchPriority?.tasks.filter((t) => t.status === "open").length ?? "—"),
          sub: "/api/research-priority/latest",
        },
        {
          label: "Data sources degraded",
          value: String(b.dataSources?.sources.filter((s) => s.status === "partial" || s.status === "error").length ?? "—"),
          sub: "Partial or error statuses",
        },
        {
          label: "Strategy registry",
          value: b.strategyRegistrySummary ? String(b.strategyRegistrySummary.production_ready_count) + " prod-ready" : "—",
          sub: b.strategyRegistrySummary
            ? String(b.strategyRegistrySummary.candidate_count) + " candidates"
            : "/api/strategies/summary",
        },
        {
          label: "LLM budget tier (gate)",
          value: b.llmBudgetGate?.selected_tier ?? "—",
          sub: b.llmBudgetGate?.reason?.slice(0, 60) ?? "/api/llm-budget-gate/latest",
        },
        {
          label: "Journal labeled",
          value: String(b.journalSummary?.total_entries ?? "—"),
          sub:
            "Wins " +
            String(b.journalSummary?.wins ?? "—") +
            " | Losses " +
            String(b.journalSummary?.losses ?? "—"),
        },
      ];
    }
    case "strategy-model-performance":
      return [
        {
          label: "Top ranked strategy",
          value: b.strategyRanking?.top_strategy_key ?? "—",
          sub: b.strategyRanking?.active_strategies?.length
            ? "Active: " + b.strategyRanking.active_strategies.join(", ")
            : "",
        },
        {
          label: "Model selection",
          value: b.modelSelection?.strategy_key ?? "—",
          sub: b.modelSelection?.reason?.slice(0, 80) ?? "/api/model-selection/latest",
        },
        {
          label: "Drift status",
          value: b.performanceDrift?.status ?? "—",
          sub: b.performanceDrift ? `Samples ${b.performanceDrift.sample_count}` : "/api/performance-drift/latest",
          tone: toneForCheck(b.performanceDrift?.status === "pass" ? "pass" : b.performanceDrift?.status === "warn" ? "warn" : "fail"),
        },
        {
          label: "Win rate (drift)",
          value: b.performanceDrift?.win_rate != null ? pct(b.performanceDrift.win_rate) : "—",
          sub: "Calibration run",
        },
        {
          label: "Affected strategies",
          value: b.performanceDrift?.affected_strategies?.length ? b.performanceDrift.affected_strategies.join(", ") : "—",
          sub: "From drift report",
        },
        {
          label: "Skipped models",
          value: String(b.modelSelection?.skipped_models?.length ?? "—"),
          sub: "Latest model selection",
        },
      ];
    case "llm-cost-center":
      return [
        {
          label: "Cost today",
          value: b.llmCosts != null ? money(b.llmCosts.cost_today) : "—",
          sub: "/api/llm-gateway/costs",
        },
        {
          label: "Budget remaining",
          value: b.llmCosts != null ? money(b.llmCosts.budget_remaining) : "—",
          sub: b.llmCosts?.pricing_source ?? "",
        },
        {
          label: "Calls today",
          value: String(b.llmCosts?.calls_today ?? "—"),
          sub: "Tokens " + String(b.llmCosts?.tokens_today ?? "—"),
        },
        {
          label: "Gateway budget status",
          value: b.llmGatewayStatus?.budget_status ?? "—",
          sub: b.llmGatewayStatus ? `Today ${money(b.llmGatewayStatus.cost_today)}` : "/api/llm-gateway/status",
        },
        {
          label: "Most used model",
          value: b.llmCosts?.most_used_model ?? "—",
          sub: b.llmCosts?.most_expensive_agent ? `Top cost agent: ${b.llmCosts.most_expensive_agent}` : "",
        },
        {
          label: "AI ops LLM row",
          value: b.aiOpsLlmUsage?.status ?? "—",
          sub:
            b.aiOpsLlmUsage?.total_estimated_cost != null
              ? `Est. $${Number(b.aiOpsLlmUsage.total_estimated_cost).toFixed(4)}`
              : "/api/ai-ops/llm-usage",
        },
      ];
    case "data-source-intelligence": {
      const picks = pickSources(b, 6);
      if (!picks.length) {
        return [{ label: "Data sources", value: "—", sub: "No sources returned from API" }];
      }
      return picks.map((s) => ({
        label: s.name || s.key || "source",
        value: s.status.replace(/_/g, " "),
        sub: s.message?.slice(0, 100) || "",
        tone: ["connected", "configured", "installed"].includes(s.status) ? "text-emerald-300" : undefined,
      }));
    }
    case "agentops": {
      const agents = b.agentRegistry ?? [];
      const partial = agents.filter((a) => a.status === "partial" || a.status === "not_configured").length;
      const scorecards = [...(b.aiOpsAgents?.foundation_agents ?? []), ...(b.aiOpsAgents?.existing_scorecards ?? [])];
      return [
        {
          label: "Registered agents",
          value: String(agents.length),
          sub: "/api/agents/registry",
        },
        {
          label: "Needs attention",
          value: String(partial),
          sub: "partial or not_configured",
          tone: partial ? "text-amber-300" : "text-emerald-300",
        },
        {
          label: "Scorecard rows",
          value: String(scorecards.length),
          sub: b.aiOpsAgents?.data_source ? `Source ${b.aiOpsAgents.data_source}` : "/api/ai-ops/agents/status",
        },
        {
          label: "Tracing",
          value: b.tracing?.mode ?? "—",
          sub: b.settings?.platform.langsmith_tracing ? "settings: on" : "settings: off",
        },
        {
          label: "Command center agents row",
          value: String(b.commandCenter?.agents?.length ?? "—"),
          sub: "From latest command center payload",
        },
        {
          label: "Auto-run",
          value: b.autoRun?.auto_run_enabled ? "on" : "off",
          sub: b.autoRun?.status ?? "",
        },
      ];
    }
    case "model-lab": {
      const reg = b.modelRegistry;
      const groups = reg && typeof reg === "object" && "groups" in reg ? (reg.groups as unknown[]) : null;
      return [
        {
          label: "Model registry groups",
          value: groups != null ? String(groups.length) : reg ? "loaded" : "—",
          sub: "/api/model-selection/registry",
        },
        {
          label: "Backtest profiles",
          value: String(b.backtestingSummary?.profiles?.length ?? "—"),
          sub: "/api/backtesting/summary",
        },
        {
          label: "Selected scanners",
          value: String(b.modelSelection?.selected_scanner_models?.filter((m) => m.selected).length ?? "—"),
          sub: "Latest model selection",
        },
        {
          label: "Skipped models",
          value: String(b.modelSelection?.skipped_models?.length ?? "—"),
          sub: b.modelSelection?.skipped_models?.[0]?.skip_reason?.slice(0, 40) ?? "",
        },
        {
          label: "Strategy ranking status",
          value: b.strategyRanking?.status ?? "—",
          sub: b.strategyRanking?.top_strategy_key ?? "",
        },
        {
          label: "Performance drift",
          value: b.performanceDrift?.status ?? "—",
          sub: "/api/performance-drift/latest",
        },
      ];
    }
    case "risk-capital-execution":
      return [
        {
          label: "Capital plan status",
          value: b.capitalAllocation?.status ?? "—",
          sub: b.capitalAllocation?.symbol ? `Symbol ${b.capitalAllocation.symbol}` : "/api/capital-allocation/latest",
        },
        {
          label: "Allocation $",
          value: b.capitalAllocation != null ? money(b.capitalAllocation.capital_allocation_dollars) : "—",
          sub: b.capitalAllocation != null ? `R:R ${b.capitalAllocation.reward_risk_ratio}` : "",
        },
        {
          label: "Alpaca buying power",
          value: b.alpacaPaper?.account?.buying_power != null ? money(b.alpacaPaper.account.buying_power) : "—",
          sub: b.alpacaPaper?.status ?? "",
        },
        {
          label: "Open paper orders",
          value: String(b.alpacaPaper?.open_orders?.length ?? "—"),
          sub: "/api/paper-trading/alpaca",
        },
        {
          label: "Live trading",
          value: b.autoRun?.live_trading_enabled ? "on" : "off",
          sub: "/api/auto-run/status",
        },
        {
          label: "Approval required (plan)",
          value: b.capitalAllocation?.approval_required == null ? "—" : b.capitalAllocation.approval_required ? "yes" : "no",
          sub: "Latest capital allocation",
        },
      ];
    case "research-memory-journal":
      return [
        {
          label: "Journal entries",
          value: String(b.journalSummary?.total_entries ?? "—"),
          sub: `/api/journal/outcomes/summary`,
        },
        {
          label: "Win rate",
          value: b.journalSummary != null ? pct(b.journalSummary.win_rate) : "—",
          sub: "Avg R " + String(b.journalSummary?.average_realized_r ?? "—"),
        },
        {
          label: "Research tasks",
          value: String(b.researchPriority?.tasks.length ?? "—"),
          sub: b.researchPriority?.status ?? "/api/research-priority/latest",
        },
        {
          label: "Top research task",
          value: b.researchPriority?.tasks[0]?.title?.slice(0, 40) ?? "—",
          sub: b.researchPriority?.tasks[0]?.suggested_next_step?.slice(0, 40) ?? "",
        },
        {
          label: "Vector memory (AI ops)",
          value: b.aiOpsSummary?.vector_memory_status ?? "—",
          sub: "Recent count " + String(b.aiOpsSummary?.recent_memory_count ?? "—"),
        },
        {
          label: "Drift recommended actions",
          value: String(b.performanceDrift?.recommended_actions?.length ?? "—"),
          sub: b.performanceDrift?.recommended_actions?.[0]?.slice(0, 50) ?? "",
        },
      ];
    case "settings":
      return [
        {
          label: "Auto-run",
          value: b.autoRun?.auto_run_enabled ? "on" : "off",
          sub: "/api/auto-run/status",
        },
        {
          label: "Live / paper / approval",
          value: `${b.autoRun?.live_trading_enabled ? "L" : "l"}${b.autoRun?.paper_trading_enabled ? "P" : "p"}${b.autoRun?.require_human_approval ? "A" : "a"}`,
          sub: "L=live P=paper A=approval",
        },
        {
          label: "LLM daily budget",
          value: b.settings != null ? money(b.settings.llm_gateway.llm_gateway_daily_budget) : "—",
          sub: "/api/settings",
        },
        {
          label: "Paid LLM tests",
          value: b.settings?.llm_gateway.llm_gateway_enable_paid_tests ? "allowed" : "off",
          sub: "llm_gateway settings",
        },
        {
          label: "Market data provider",
          value: b.settings?.market_data.market_data_provider ?? "—",
          sub: `Alpaca MD ${b.settings?.market_data.alpaca_market_data_enabled ? "on" : "off"}`,
        },
        {
          label: "Trading: human approval",
          value: b.settings?.trading.require_human_approval ? "required" : "off",
          sub: "/api/settings trading",
        },
      ];
    default:
      return buildOwnerCards("pnl", b);
  }
}

export function buildRecommendationRows(
  mode: "ops" | "owner",
  pageKey: string,
  b: AdminDashboardBundle,
  limit = 8,
): DashboardRecRow[] {
  const rows: DashboardRecRow[] = [];
  const pr = b.platformReadiness;

  if (pageKey === "integrations" || pageKey === "data-source-intelligence") {
    const bad = b.dataSources?.sources.filter((s) => !["connected", "configured", "installed", "test_only"].includes(s.status)) ?? [];
    for (const s of bad.slice(0, 5)) {
      rows.push({
        priority: s.status.includes("error") ? "High" : "Medium",
        area: String(s.name || s.key || "source"),
        recommendation: s.message || `Status: ${s.status}`,
        benefit: "Reliable data",
        action: "/data-sources",
      });
    }
  }

  if (pageKey === "llm-cost-center" || pageKey === "settings") {
    if (b.llmCosts && b.llmCosts.budget_remaining < b.llmCosts.daily_budget * 0.1 && b.llmCosts.daily_budget > 0) {
      rows.push({
        priority: "High",
        area: "LLM",
        recommendation: "LLM budget almost exhausted for today.",
        benefit: "Avoid surprise cutoff",
        action: "/llm-gateway",
      });
    }
  }

  if (pr) {
    for (const blocker of pr.blockers.slice(0, 3)) {
      rows.push({ priority: "High", area: "Platform", recommendation: blocker, benefit: "Unblock workflows", action: "/platform-readiness" });
    }
    for (const w of pr.warnings.slice(0, 3)) {
      rows.push({ priority: "Medium", area: "Platform", recommendation: w, benefit: "Reduce risk", action: "/platform-readiness" });
    }
    for (const c of pr.checks.filter((x) => x.status !== "pass").slice(0, 4)) {
      rows.push({
        priority: c.status === "fail" ? "High" : "Medium",
        area: c.label,
        recommendation: c.message,
        benefit: c.required_for,
        action: "/platform-readiness",
      });
    }
  }

  if (mode === "owner" && (pageKey === "insights" || pageKey === "research-memory-journal")) {
    const tasks = b.researchPriority?.tasks?.filter((t) => t.status === "open") ?? [];
    for (const t of tasks.slice(0, 4)) {
      rows.push({
        priority: t.priority_rank <= 2 ? "High" : "Medium",
        area: t.task_type.replace(/_/g, " "),
        recommendation: t.title,
        benefit: t.suggested_next_step,
        action: "/research-priority",
      });
    }
  }

  if (pageKey === "workflows" && b.strategyRanking?.blockers?.length) {
    for (const bl of b.strategyRanking.blockers.slice(0, 2)) {
      rows.push({ priority: "High", area: "Ranking", recommendation: bl, benefit: "Strategy stack", action: "/strategy-lab" });
    }
  }

  if (rows.length === 0) {
    rows.push({
      priority: "Low",
      area: "Status",
      recommendation: pr ? "No blockers or failing checks in the latest platform readiness response." : "Load /api/platform-readiness to populate advisor rows.",
      benefit: "Baseline",
      action: pr ? "/platform-readiness" : "/data-sources",
    });
  }

  const dedup = new Set<string>();
  const out: DashboardRecRow[] = [];
  for (const row of rows) {
    const k = `${row.area}|${row.recommendation}`;
    if (dedup.has(k)) continue;
    dedup.add(k);
    out.push(row);
    if (out.length >= limit) break;
  }
  return out;
}

export function buildInsightTexts(
  mode: "ops" | "owner",
  pageKey: string,
  b: AdminDashboardBundle,
): { stateTitle: string; stateBody: string; forecastTitle: string; forecastBody: string; detailTitle: string; detailBody: string } {
  const pr = b.platformReadiness;
  const fr = b.dataFreshness;
  const stateTitle = pr ? `Platform: ${pr.status}` : "Platform readiness not loaded";
  const stateBody = pr
    ? `${pr.checks.length} checks | ${pr.blockers.length} blockers | ${pr.warnings.length} warnings. Generated ${new Date(pr.generated_at).toLocaleString()}.`
    : "Open Network tab and verify GET /api/platform-readiness succeeds.";

  const forecastTitle = fr ? `Data freshness: ${fr.status}` : "Data freshness";
  const forecastBody = fr
    ? `${fr.warnings.length} warnings, ${fr.blockers.length} blockers on last run (${new Date(fr.checked_at).toLocaleString()}).`
    : "No latest freshness payload — run a workflow or open /data-sources.";

  let detailTitle = mode === "ops" ? "Operations context" : "Owner context";
  let detailBody = "";
  if (pageKey === "integrations" || pageKey === "data-source-intelligence") {
    detailTitle = "Data sources";
    detailBody = b.dataSources
      ? `${b.dataSources.connected_sources}/${b.dataSources.total_sources} sources connected or test-ready (per API).`
      : "";
  } else if (pageKey === "trading") {
    detailTitle = "Command center";
    detailBody = b.commandCenter?.cost_usage_message ?? "";
  } else if (pageKey === "llm-cost-center") {
    detailTitle = "LLM gateway";
    detailBody = b.llmGatewayStatus
      ? `Status ${b.llmGatewayStatus.status}; providers configured: ${b.llmGatewayStatus.configured_providers_count}.`
      : "";
  } else {
    detailBody =
      b.runtimeCadence != null
        ? "Market phase " +
          String(b.runtimePhase?.market_phase ?? "—") +
          "; active loop " +
          b.runtimeCadence.active_loop +
          "."
        : "";
  }

  return { stateTitle, stateBody, forecastTitle, forecastBody, detailTitle, detailBody };
}
