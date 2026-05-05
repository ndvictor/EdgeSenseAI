"use client";

import { useCallback, useEffect, useState } from "react";
import {
  api,
  type AccountRiskProfile,
  type AiOpsAgentStatusResponse,
  type AiOpsLlmUsageResponse,
  type AiOpsSchedulerJobsResponse,
  type AiOpsSummaryResponse,
  type AiOpsWorkflowListResponse,
  type AlpacaPaperSnapshot,
  type AutoRunControlState,
  type BacktestingResponse,
  type CapitalAllocationResponse,
  type CommandCenterResponse,
  type CoreAgentRegistryResponse,
  type DataFreshnessCheckResponse,
  type DataSourcesStatusResponse,
  type JournalOutcomeSummary,
  type LiveWatchlistResponse,
  type LLMBudgetGateResponse,
  type LlmCostSummary,
  type LlmGatewayStatusResponse,
  type MarketRegimeModelResponse,
  type MarketRegimeResponse,
  type ModelSelectionResponse,
  type PerformanceDriftResponse,
  type PlatformReadinessResponse,
  type ResearchPriorityResponse,
  type SettingsResponse,
  type StrategyRankingResponse,
  type StrategyRegistrySummary,
  type StrategyWorkflowRunResult,
  type TracingStatusResponse,
} from "@/lib/api";

function settle<T>(p: Promise<T>): Promise<{ ok: true; data: T } | { ok: false; error: string }> {
  return p
    .then((data) => ({ ok: true as const, data }))
    .catch((e: unknown) => ({
      ok: false as const,
      error: e instanceof Error ? e.message : String(e),
    }));
}

function parseStrategyRanking(raw: unknown): StrategyRankingResponse | null {
  if (!raw || typeof raw !== "object" || !("ranked_strategies" in raw)) return null;
  return raw as StrategyRankingResponse;
}

function parseModelSelection(raw: unknown): ModelSelectionResponse | null {
  if (!raw || typeof raw !== "object" || !("selected_scanner_models" in raw)) return null;
  return raw as ModelSelectionResponse;
}

function parsePerformanceDrift(raw: unknown): PerformanceDriftResponse | null {
  if (!raw || typeof raw !== "object" || !("calibration_buckets" in raw)) return null;
  return raw as PerformanceDriftResponse;
}

function parseCapitalAllocation(raw: unknown): CapitalAllocationResponse | null {
  if (!raw || typeof raw !== "object" || !("capital_allocation_dollars" in raw)) return null;
  return raw as CapitalAllocationResponse;
}

function parseResearchPriority(raw: unknown): ResearchPriorityResponse | null {
  if (!raw || typeof raw !== "object" || !("tasks" in raw)) return null;
  return raw as ResearchPriorityResponse;
}

function parseLlmBudgetGate(raw: unknown): LLMBudgetGateResponse | null {
  if (!raw || typeof raw !== "object" || !("selected_tier" in raw)) return null;
  return raw as LLMBudgetGateResponse;
}

function parseDataFreshness(raw: unknown): DataFreshnessCheckResponse | null {
  if (!raw || typeof raw !== "object" || !("results" in raw)) return null;
  return raw as DataFreshnessCheckResponse;
}

function parseMarketRegimeModel(raw: unknown): MarketRegimeModelResponse | null {
  if (!raw || typeof raw !== "object" || !("regime" in raw) || !("run_id" in raw)) return null;
  return raw as MarketRegimeModelResponse;
}

export type AdminDashboardBundle = {
  dataSources: DataSourcesStatusResponse | null;
  platformReadiness: PlatformReadinessResponse | null;
  aiOpsSummary: AiOpsSummaryResponse | null;
  aiOpsWorkflows: AiOpsWorkflowListResponse | null;
  aiOpsAgents: AiOpsAgentStatusResponse | null;
  aiOpsScheduler: AiOpsSchedulerJobsResponse | null;
  aiOpsLlmUsage: AiOpsLlmUsageResponse | null;
  settings: SettingsResponse | null;
  autoRun: AutoRunControlState | null;
  runtimePhase: {
    market_phase: string;
    current_time_et: string;
    is_trading_day: boolean;
    live_trading_allowed: boolean;
    human_approval_required: boolean;
    timestamp: string;
  } | null;
  runtimeCadence: {
    market_phase: string;
    active_loop: string;
    live_trading_allowed: boolean;
    human_approval_required: boolean;
    timestamp: string;
  } | null;
  dataFreshness: DataFreshnessCheckResponse | null;
  tracing: TracingStatusResponse | null;
  strategyRegistrySummary: StrategyRegistrySummary | null;
  strategyRanking: StrategyRankingResponse | null;
  marketRegime: MarketRegimeResponse | null;
  latestMarketRegimeModel: MarketRegimeModelResponse | null;
  accountRisk: AccountRiskProfile | null;
  llmCosts: LlmCostSummary | null;
  llmGatewayStatus: LlmGatewayStatusResponse | null;
  llmBudgetGate: LLMBudgetGateResponse | null;
  commandCenter: CommandCenterResponse | null;
  liveWatchlist: LiveWatchlistResponse | null;
  journalSummary: JournalOutcomeSummary | null;
  alpacaPaper: AlpacaPaperSnapshot | null;
  researchPriority: ResearchPriorityResponse | null;
  modelRegistry: Record<string, unknown> | null;
  performanceDrift: PerformanceDriftResponse | null;
  capitalAllocation: CapitalAllocationResponse | null;
  modelSelection: ModelSelectionResponse | null;
  backtestingSummary: BacktestingResponse | null;
  agentRegistry: CoreAgentRegistryResponse | null;
  recommendationLifecycleSummary: Record<string, unknown> | null;
  strategyWorkflowRuns: StrategyWorkflowRunResult[] | null;
};

const emptyBundle: AdminDashboardBundle = {
  dataSources: null,
  platformReadiness: null,
  aiOpsSummary: null,
  aiOpsWorkflows: null,
  aiOpsAgents: null,
  aiOpsScheduler: null,
  aiOpsLlmUsage: null,
  settings: null,
  autoRun: null,
  runtimePhase: null,
  runtimeCadence: null,
  dataFreshness: null,
  tracing: null,
  strategyRegistrySummary: null,
  strategyRanking: null,
  marketRegime: null,
  latestMarketRegimeModel: null,
  accountRisk: null,
  llmCosts: null,
  llmGatewayStatus: null,
  llmBudgetGate: null,
  commandCenter: null,
  liveWatchlist: null,
  journalSummary: null,
  alpacaPaper: null,
  researchPriority: null,
  modelRegistry: null,
  performanceDrift: null,
  capitalAllocation: null,
  modelSelection: null,
  backtestingSummary: null,
  agentRegistry: null,
  recommendationLifecycleSummary: null,
  strategyWorkflowRuns: null,
};

export function useAdminDashboardBundle() {
  const [bundle, setBundle] = useState<AdminDashboardBundle>(emptyBundle);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);

    const r = await Promise.all([
      settle(api.getDataSourcesStatus()),
      settle(api.getPlatformReadiness()),
      settle(api.getAiOpsSummary()),
      settle(api.getAiOpsWorkflows()),
      settle(api.getAiOpsAgentStatus()),
      settle(api.getAiOpsSchedulerJobs()),
      settle(api.getAiOpsLlmUsage()),
      settle(api.getSettings()),
      settle(api.getAutoRunStatus()),
      settle(api.getRuntimePhase()),
      settle(api.getRuntimeCadence()),
      settle(api.getLatestDataFreshness()),
      settle(api.getTracingStatus()),
      settle(api.getStrategyRegistrySummary()),
      settle(api.getLatestStrategyRanking()),
      settle(api.getMarketRegime()),
      settle(api.getLatestMarketRegime()),
      settle(api.getAccountRisk()),
      settle(api.getLlmGatewayCosts()),
      settle(api.getLlmGatewayStatus()),
      settle(api.getLatestLLMBudgetGate()),
      settle(api.getCommandCenter()),
      settle(api.getLiveWatchlist()),
      settle(api.getJournalSummary()),
      settle(api.getAlpacaPaperSnapshot()),
      settle(api.getLatestResearchPriority()),
      settle(api.getModelRegistry()),
      settle(api.getLatestPerformanceDrift()),
      settle(api.getLatestCapitalAllocation()),
      settle(api.getLatestModelSelection()),
      settle(api.getBacktestingSummary()),
      settle(api.getAgentRegistry()),
      settle(api.getRecommendationLifecycleSummary()),
      settle(api.getStrategyWorkflowRuns(20)),
    ]);

    const okCount = r.filter((x) => x.ok).length;
    if (okCount === 0) {
      setLoadError("Could not load any platform endpoints. Check that the backend is running and CORS is allowed.");
    }

    const get = <T,>(i: number): T | null => (r[i].ok ? (r[i] as { ok: true; data: T }).data : null);

    setBundle({
      dataSources: get(0),
      platformReadiness: get(1),
      aiOpsSummary: get(2),
      aiOpsWorkflows: get(3),
      aiOpsAgents: get(4),
      aiOpsScheduler: get(5),
      aiOpsLlmUsage: get(6),
      settings: get(7),
      autoRun: get(8),
      runtimePhase: get(9),
      runtimeCadence: get(10),
      dataFreshness: parseDataFreshness(r[11].ok ? r[11].data : null),
      tracing: get(12),
      strategyRegistrySummary: get(13),
      strategyRanking: parseStrategyRanking(r[14].ok ? r[14].data : null),
      marketRegime: get(15),
      latestMarketRegimeModel: parseMarketRegimeModel(r[16].ok ? r[16].data : null),
      accountRisk: get(17),
      llmCosts: get(18),
      llmGatewayStatus: get(19),
      llmBudgetGate: parseLlmBudgetGate(r[20].ok ? r[20].data : null),
      commandCenter: get(21),
      liveWatchlist: get(22),
      journalSummary: get(23),
      alpacaPaper: get(24),
      researchPriority: parseResearchPriority(r[25].ok ? r[25].data : null),
      modelRegistry: get(26),
      performanceDrift: parsePerformanceDrift(r[27].ok ? r[27].data : null),
      capitalAllocation: parseCapitalAllocation(r[28].ok ? r[28].data : null),
      modelSelection: parseModelSelection(r[29].ok ? r[29].data : null),
      backtestingSummary: get(30),
      agentRegistry: get(31),
      recommendationLifecycleSummary: get(32),
      strategyWorkflowRuns: get(33),
    });

    setLoading(false);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return { bundle, loading, loadError, refetch: load };
}
