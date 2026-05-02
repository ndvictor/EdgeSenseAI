import os
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


ProviderStatus = Literal["configured", "not_configured", "placeholder", "error"]


class LlmProviderStatus(BaseModel):
    provider: str
    status: ProviderStatus
    configured: bool
    required_env_vars: list[str]
    configured_env_vars: list[str]
    message: str
    data_source: str = "placeholder"


class LlmModelConfig(BaseModel):
    model_name: str
    provider: str
    role: str
    context_window: int | None = None
    pricing_source: str = "placeholder_estimate"
    input_cost_per_1k_tokens: float
    output_cost_per_1k_tokens: float
    status: str
    data_source: str = "placeholder"


class LlmRoutingRule(BaseModel):
    task_type: str
    preferred_provider: str
    preferred_model: str
    fallback_model: str
    max_cost_per_call: float
    max_tokens: int
    enabled: bool
    data_source: str = "placeholder"


class LlmUsageRecord(BaseModel):
    id: str
    timestamp: datetime
    provider: str
    model: str
    agent: str
    workflow: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    latency_ms: float | None = None
    status: str
    dry_run: bool = True
    data_source: str = "placeholder"


class LlmCostSummary(BaseModel):
    data_source: str = "placeholder"
    cost_today: float
    daily_budget: float
    budget_remaining: float
    tokens_today: int
    calls_today: int
    cost_by_provider: dict[str, float]
    cost_by_model: dict[str, float]
    cost_by_agent: dict[str, float]
    cost_by_workflow: dict[str, float]
    most_used_model: str | None = None
    most_expensive_agent: str | None = None
    pricing_source: str = "placeholder_estimate"


class AgentModelMapping(BaseModel):
    agent_name: str
    default_model: str
    fallback_model: str
    max_daily_cost: float
    max_calls_per_day: int
    current_cost_today: float = 0.0
    calls_today: int = 0
    status: str = "configured"
    data_source: str = "placeholder"


class LlmGatewayStatus(BaseModel):
    status: str
    litellm_available: bool
    litellm_api_base_configured: bool
    litellm_master_key_configured: bool
    configured_providers_count: int
    budget_status: str
    daily_budget: float
    cost_today: float
    budget_remaining: float
    data_source: str = "placeholder"


class LlmCostEstimateRequest(BaseModel):
    model: str = "gpt-4o-mini"
    prompt_tokens: int = 1000
    completion_tokens: int = 500


class LlmCostEstimateResponse(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    estimated_cost: float
    input_cost: float
    output_cost: float
    pricing_source: str = "placeholder_estimate"
    data_source: str = "placeholder"


class LlmGatewayTestCallRequest(BaseModel):
    provider: str = "local"
    model: str = "local-placeholder"
    prompt: str = "Return a safe LLM Gateway dry-run response."
    allow_paid_call: bool = False


class LlmGatewayTestCallResponse(BaseModel):
    id: str
    provider: str
    model: str
    dry_run: bool
    paid_call_attempted: bool = False
    status: str
    response_text: str
    estimated_cost: float
    data_source: str = "placeholder"
    warnings: list[str] = Field(default_factory=list)


_MODEL_PRICING: dict[str, tuple[str, str, float, float, int | None]] = {
    "gpt-4o-mini": ("openai", "cheap_fast_model", 0.00015, 0.0006, 128000),
    "gpt-4o": ("openai", "strong_reasoning_model", 0.005, 0.015, 128000),
    "claude-3-haiku": ("anthropic", "cheap_fast_model", 0.00025, 0.00125, 200000),
    "claude-3-sonnet": ("anthropic", "strong_reasoning_model", 0.003, 0.015, 200000),
    "bedrock-claude-haiku": ("bedrock", "cheap_fast_model", 0.00025, 0.00125, 200000),
    "local-placeholder": ("local", "placeholder", 0.0, 0.0, None),
}

_USAGE_RECORDS: list[LlmUsageRecord] = []


def _env_present(name: str) -> bool:
    return bool(os.getenv(name))


def _daily_budget() -> float:
    try:
        return float(os.getenv("LLM_GATEWAY_DAILY_BUDGET", "25"))
    except ValueError:
        return 25.0


def _litellm_available() -> bool:
    try:
        import litellm  # noqa: F401

        return True
    except Exception:
        return False


def get_provider_statuses() -> list[LlmProviderStatus]:
    providers = [
        ("openai", ["OPENAI_API_KEY"], "OpenAI API key"),
        ("anthropic", ["ANTHROPIC_API_KEY"], "Anthropic API key"),
        ("bedrock", ["AWS_REGION", "BEDROCK_MODEL_ID"], "AWS Bedrock region and model"),
        ("litellm_proxy", ["LITELLM_API_BASE", "LITELLM_MASTER_KEY"], "LiteLLM proxy endpoint"),
    ]
    rows: list[LlmProviderStatus] = []
    for provider, env_vars, label in providers:
        configured = [name for name in env_vars if _env_present(name)]
        is_ready = len(configured) == len(env_vars)
        rows.append(
            LlmProviderStatus(
                provider=provider,
                status="configured" if is_ready else "not_configured",
                configured=is_ready,
                required_env_vars=env_vars,
                configured_env_vars=configured,
                message=f"{label} {'configured' if is_ready else 'not fully configured'}.",
            )
        )
    rows.append(
        LlmProviderStatus(
            provider="local",
            status="placeholder",
            configured=True,
            required_env_vars=[],
            configured_env_vars=[],
            message="Local placeholder provider is always available for dry-run tests.",
        )
    )
    return rows


def get_model_configs() -> list[LlmModelConfig]:
    provider_status = {row.provider: row.status for row in get_provider_statuses()}
    return [
        LlmModelConfig(
            model_name=model_name,
            provider=provider,
            role=role,
            context_window=context_window,
            input_cost_per_1k_tokens=input_cost,
            output_cost_per_1k_tokens=output_cost,
            status="available" if provider == "local" or provider_status.get(provider) == "configured" else "provider_not_configured",
        )
        for model_name, (provider, role, input_cost, output_cost, context_window) in _MODEL_PRICING.items()
    ]


def get_routing_rules() -> list[LlmRoutingRule]:
    cheap = "gpt-4o-mini"
    strong = "gpt-4o"
    fallback = "local-placeholder"
    cheap_tasks = ["ticker_extraction", "news_classification", "data_quality_summary", "edge_signal_explanation"]
    strong_tasks = ["portfolio_manager_decision", "options_strategy_review", "macro_conflict_analysis", "final_recommendation_summary"]
    return [
        LlmRoutingRule(task_type=task, preferred_provider="openai", preferred_model=cheap, fallback_model=fallback, max_cost_per_call=0.02, max_tokens=2000, enabled=True)
        for task in cheap_tasks
    ] + [
        LlmRoutingRule(task_type=task, preferred_provider="openai", preferred_model=strong, fallback_model="gpt-4o-mini", max_cost_per_call=0.25, max_tokens=5000, enabled=True)
        for task in strong_tasks
    ]


def get_agent_model_map() -> list[AgentModelMapping]:
    cheap = "gpt-4o-mini"
    strong = "gpt-4o"
    fallback = "local-placeholder"
    mappings = [
        ("Market Regime Agent", cheap, fallback, 2.0, 100),
        ("Edge Signal Scanner Agent", cheap, fallback, 3.0, 150),
        ("Data Quality Agent", cheap, fallback, 1.0, 200),
        ("Model Orchestrator Agent", strong, cheap, 5.0, 80),
        ("Risk Manager Agent", cheap, fallback, 2.0, 100),
        ("Portfolio Manager Agent", strong, cheap, 5.0, 80),
        ("Cost Controller Agent", "local-placeholder", fallback, 0.25, 500),
        ("Recommendation Agent", strong, cheap, 5.0, 80),
        ("Journal Agent", cheap, fallback, 1.0, 100),
    ]
    cost_by_agent = get_cost_summary().cost_by_agent
    calls_by_agent: dict[str, int] = {}
    for record in _USAGE_RECORDS:
        calls_by_agent[record.agent] = calls_by_agent.get(record.agent, 0) + 1
    return [
        AgentModelMapping(
            agent_name=agent,
            default_model=default,
            fallback_model=fallback_model,
            max_daily_cost=max_cost,
            max_calls_per_day=max_calls,
            current_cost_today=round(cost_by_agent.get(agent, 0.0), 6),
            calls_today=calls_by_agent.get(agent, 0),
            status="configured",
        )
        for agent, default, fallback_model, max_cost, max_calls in mappings
    ]


def estimate_cost(request: LlmCostEstimateRequest) -> LlmCostEstimateResponse:
    _, _, input_rate, output_rate, _ = _MODEL_PRICING.get(request.model, _MODEL_PRICING["local-placeholder"])
    prompt_tokens = max(0, request.prompt_tokens)
    completion_tokens = max(0, request.completion_tokens)
    input_cost = (prompt_tokens / 1000) * input_rate
    output_cost = (completion_tokens / 1000) * output_rate
    return LlmCostEstimateResponse(
        model=request.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        input_cost=round(input_cost, 6),
        output_cost=round(output_cost, 6),
        estimated_cost=round(input_cost + output_cost, 6),
    )


def get_usage_records() -> list[LlmUsageRecord]:
    return sorted(_USAGE_RECORDS, key=lambda record: record.timestamp, reverse=True)


def get_cost_summary() -> LlmCostSummary:
    cost_by_provider: dict[str, float] = {}
    cost_by_model: dict[str, float] = {}
    cost_by_agent: dict[str, float] = {}
    cost_by_workflow: dict[str, float] = {}
    tokens_today = 0
    for record in _USAGE_RECORDS:
        cost_by_provider[record.provider] = cost_by_provider.get(record.provider, 0.0) + record.estimated_cost
        cost_by_model[record.model] = cost_by_model.get(record.model, 0.0) + record.estimated_cost
        cost_by_agent[record.agent] = cost_by_agent.get(record.agent, 0.0) + record.estimated_cost
        cost_by_workflow[record.workflow] = cost_by_workflow.get(record.workflow, 0.0) + record.estimated_cost
        tokens_today += record.prompt_tokens + record.completion_tokens
    cost_today = round(sum(cost_by_provider.values()), 6)
    daily_budget = _daily_budget()
    model_counts: dict[str, int] = {}
    for record in _USAGE_RECORDS:
        model_counts[record.model] = model_counts.get(record.model, 0) + 1
    return LlmCostSummary(
        cost_today=cost_today,
        daily_budget=daily_budget,
        budget_remaining=round(max(daily_budget - cost_today, 0), 6),
        tokens_today=tokens_today,
        calls_today=len(_USAGE_RECORDS),
        cost_by_provider={key: round(value, 6) for key, value in cost_by_provider.items()},
        cost_by_model={key: round(value, 6) for key, value in cost_by_model.items()},
        cost_by_agent={key: round(value, 6) for key, value in cost_by_agent.items()},
        cost_by_workflow={key: round(value, 6) for key, value in cost_by_workflow.items()},
        most_used_model=max(model_counts, key=model_counts.get) if model_counts else None,
        most_expensive_agent=max(cost_by_agent, key=cost_by_agent.get) if cost_by_agent else None,
    )


def get_gateway_status() -> LlmGatewayStatus:
    providers = get_provider_statuses()
    configured_count = len([provider for provider in providers if provider.configured and provider.provider != "local"])
    costs = get_cost_summary()
    budget_status = "ok" if costs.cost_today < costs.daily_budget else "exceeded"
    return LlmGatewayStatus(
        status="configured" if _litellm_available() else "litellm_not_installed",
        litellm_available=_litellm_available(),
        litellm_api_base_configured=_env_present("LITELLM_API_BASE"),
        litellm_master_key_configured=_env_present("LITELLM_MASTER_KEY"),
        configured_providers_count=configured_count,
        budget_status=budget_status,
        daily_budget=costs.daily_budget,
        cost_today=costs.cost_today,
        budget_remaining=costs.budget_remaining,
    )


def get_gateway_summary() -> dict[str, Any]:
    status = get_gateway_status()
    costs = get_cost_summary()
    return {
        "gateway_status": status.status,
        "configured_providers_count": status.configured_providers_count,
        "llm_cost_today": costs.cost_today,
        "daily_budget": costs.daily_budget,
        "budget_remaining": costs.budget_remaining,
        "most_used_model": costs.most_used_model or "none",
        "most_expensive_agent": costs.most_expensive_agent or "none",
        "data_source": "placeholder",
    }


def test_gateway_call(request: LlmGatewayTestCallRequest) -> LlmGatewayTestCallResponse:
    estimate = estimate_cost(
        LlmCostEstimateRequest(
            model=request.model,
            prompt_tokens=max(1, len(request.prompt.split())),
            completion_tokens=40,
        )
    )
    paid_tests_enabled = os.getenv("LLM_GATEWAY_ENABLE_PAID_TESTS", "false").lower() == "true"
    dry_run = not (request.allow_paid_call and paid_tests_enabled)
    warnings: list[str] = []
    if request.allow_paid_call and not paid_tests_enabled:
        warnings.append("allow_paid_call was true, but server-side LLM_GATEWAY_ENABLE_PAID_TESTS is not true; returning dry run.")
    if dry_run:
        response_text = "Dry-run only. No provider call was made."
        status = "dry_run"
    else:
        response_text = "Paid test calls are gated; wire a reviewed LiteLLM call path before enabling production use."
        status = "paid_test_not_implemented"
        dry_run = True
        warnings.append("Paid call path is intentionally not implemented in this foundation pass.")

    record = LlmUsageRecord(
        id=f"llm-{uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc),
        provider=request.provider,
        model=request.model,
        agent="LLM Gateway Test Panel",
        workflow="llm_gateway_test",
        prompt_tokens=estimate.prompt_tokens,
        completion_tokens=estimate.completion_tokens,
        estimated_cost=0.0 if dry_run else estimate.estimated_cost,
        latency_ms=0.0,
        status=status,
        dry_run=dry_run,
    )
    _USAGE_RECORDS.append(record)
    return LlmGatewayTestCallResponse(
        id=record.id,
        provider=request.provider,
        model=request.model,
        dry_run=dry_run,
        paid_call_attempted=not dry_run,
        status=status,
        response_text=response_text,
        estimated_cost=record.estimated_cost,
        warnings=warnings,
    )
