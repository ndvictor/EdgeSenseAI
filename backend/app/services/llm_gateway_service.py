from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.core.settings import settings

ProviderStatus = Literal["configured", "not_configured", "placeholder", "dry_run_available", "error"]


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


class LlmGatewayCallResponse(BaseModel):
    dry_run: bool
    provider: str
    model: str
    fallback_model: str
    prompt_tokens_estimate: int
    completion_tokens_estimate: int
    estimated_cost: float
    status: str
    response_text: str
    blocked_reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    data_source: str = "placeholder"


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
    return bool(getattr(settings, _SETTING_BY_ENV.get(name, ""), ""))


_SETTING_BY_ENV = {
    "OPENAI_API_KEY": "openai_api_key",
    "ANTHROPIC_API_KEY": "anthropic_api_key",
    "AWS_REGION": "aws_region",
    "BEDROCK_MODEL_ID": "bedrock_model_id",
    "LITELLM_API_BASE": "litellm_api_base",
    "LITELLM_MASTER_KEY": "litellm_master_key",
}


def _daily_budget() -> float:
    return float(settings.llm_gateway_daily_budget)


def _cheap_model() -> str:
    return settings.llm_gateway_default_cheap_model or "gpt-4o-mini"


def _reasoning_model() -> str:
    return settings.llm_gateway_default_reasoning_model or "gpt-4o"


def _fallback_model() -> str:
    return settings.llm_gateway_default_fallback_model or "local-placeholder"


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
            status="dry_run_available",
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
    cheap = _cheap_model()
    strong = _reasoning_model()
    fallback = _fallback_model()
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
    cheap = _cheap_model()
    strong = _reasoning_model()
    fallback = _fallback_model()
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
    paid_tests_enabled = settings.llm_gateway_enable_paid_tests
    dry_run = not (request.allow_paid_call and paid_tests_enabled)
    warnings: list[str] = []
    if request.allow_paid_call and not paid_tests_enabled:
        warnings.append("allow_paid_call was true, but server-side LLM_GATEWAY_ENABLE_PAID_TESTS is false; blocked by gateway policy.")
    if dry_run:
        response_text = "Dry-run only. No provider call was made."
        status = "blocked_by_gateway_policy" if request.allow_paid_call and not paid_tests_enabled else "dry_run"
    else:
        response_text = _run_paid_test_call(request, max_tokens=20)
        status = "paid_test_completed"

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


def test_provider_connection(request: LlmGatewayTestCallRequest) -> LlmGatewayTestCallResponse:
    return test_gateway_call(request)


def _run_paid_test_call(request: LlmGatewayTestCallRequest, max_tokens: int = 20) -> str:
    try:
        import litellm

        response = litellm.completion(
            model=request.model,
            messages=[{"role": "user", "content": request.prompt[:500]}],
            max_tokens=min(max_tokens, 20),
        )
        choice = response.choices[0] if response.choices else None
        message = getattr(choice, "message", None)
        content = getattr(message, "content", None) if message else None
        return str(content or "Paid test completed with no text content.")
    except Exception as exc:
        return f"Paid test call failed safely: {exc}"


def _select_rule(task_type: str) -> LlmRoutingRule:
    for rule in get_routing_rules():
        if rule.task_type == task_type and rule.enabled:
            return rule
    return LlmRoutingRule(
        task_type=task_type,
        preferred_provider="local",
        preferred_model=_fallback_model(),
        fallback_model=_fallback_model(),
        max_cost_per_call=0.0,
        max_tokens=1000,
        enabled=True,
    )


def _provider_for_model(model: str) -> str:
    provider, _, _, _, _ = _MODEL_PRICING.get(model, ("local", "placeholder", 0.0, 0.0, None))
    return provider


def run_llm_gateway_call(
    agent_name: str,
    workflow_name: str,
    task_type: str,
    prompt: str,
    allow_paid_call: bool = False,
    metadata: dict | None = None,
) -> LlmGatewayCallResponse:
    rule = _select_rule(task_type)
    prompt_tokens = max(1, len(prompt.split()))
    completion_tokens = min(rule.max_tokens, 120)
    estimate = estimate_cost(LlmCostEstimateRequest(model=rule.preferred_model, prompt_tokens=prompt_tokens, completion_tokens=completion_tokens))
    blocked_reason = None
    dry_run = True
    status = "dry_run"
    provider = rule.preferred_provider or _provider_for_model(rule.preferred_model)
    model = rule.preferred_model

    costs = get_cost_summary()
    if costs.cost_today + estimate.estimated_cost > costs.daily_budget:
        blocked_reason = "daily_budget_would_be_exceeded"
        status = "blocked_budget"
    elif estimate.estimated_cost > rule.max_cost_per_call:
        blocked_reason = "max_cost_per_call_would_be_exceeded"
        status = "blocked_cost_limit"
    elif allow_paid_call and not settings.llm_gateway_enable_paid_tests:
        blocked_reason = "paid_calls_disabled_by_gateway_policy"
        status = "blocked_by_gateway_policy"
    elif allow_paid_call and settings.llm_gateway_enable_paid_tests:
        dry_run = False
        status = "paid_call_completed"

    if dry_run:
        response_text = "Dry-run LLM Gateway call. No provider call was made."
    else:
        response_text = _run_paid_test_call(
            LlmGatewayTestCallRequest(provider=provider, model=model, prompt=prompt, allow_paid_call=True),
            max_tokens=min(completion_tokens, 20),
        )

    record = LlmUsageRecord(
        id=f"llm-{uuid4().hex[:12]}",
        timestamp=datetime.now(timezone.utc),
        provider=provider,
        model=model,
        agent=agent_name,
        workflow=workflow_name,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=0.0 if dry_run else estimate.estimated_cost,
        latency_ms=0.0,
        status=status,
        dry_run=dry_run,
    )
    _USAGE_RECORDS.append(record)
    return LlmGatewayCallResponse(
        dry_run=dry_run,
        provider=provider,
        model=model,
        fallback_model=rule.fallback_model,
        prompt_tokens_estimate=prompt_tokens,
        completion_tokens_estimate=completion_tokens,
        estimated_cost=estimate.estimated_cost,
        status=status,
        response_text=response_text,
        blocked_reason=blocked_reason,
        metadata=metadata or {},
    )
