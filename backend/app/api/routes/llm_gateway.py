from fastapi import APIRouter

from app.services.llm_gateway_service import (
    LlmCostEstimateRequest,
    LlmCostEstimateResponse,
    LlmCostSummary,
    LlmGatewayStatus,
    LlmGatewayTestCallRequest,
    LlmGatewayTestCallResponse,
    LlmModelConfig,
    LlmProviderStatus,
    LlmRoutingRule,
    LlmUsageRecord,
    AgentModelMapping,
    estimate_cost,
    get_agent_model_map,
    get_cost_summary,
    get_gateway_status,
    get_model_configs,
    get_provider_statuses,
    get_routing_rules,
    get_usage_records,
    test_provider_connection,
    test_gateway_call,
)

router = APIRouter()


@router.get("/llm-gateway/status", response_model=LlmGatewayStatus)
def get_status():
    return get_gateway_status()


@router.get("/llm-gateway/providers", response_model=list[LlmProviderStatus])
def get_providers():
    return get_provider_statuses()


@router.get("/llm-gateway/models", response_model=list[LlmModelConfig])
def get_models():
    return get_model_configs()


@router.get("/llm-gateway/routing-rules", response_model=list[LlmRoutingRule])
def get_rules():
    return get_routing_rules()


@router.get("/llm-gateway/usage", response_model=list[LlmUsageRecord])
def get_usage():
    return get_usage_records()


@router.get("/llm-gateway/costs", response_model=LlmCostSummary)
def get_costs():
    return get_cost_summary()


@router.get("/llm-gateway/agent-model-map", response_model=list[AgentModelMapping])
def get_agent_map():
    return get_agent_model_map()


@router.post("/llm-gateway/estimate", response_model=LlmCostEstimateResponse)
def post_estimate(request: LlmCostEstimateRequest):
    return estimate_cost(request)


@router.post("/llm-gateway/test-call", response_model=LlmGatewayTestCallResponse)
def post_test_call(request: LlmGatewayTestCallRequest):
    return test_gateway_call(request)


@router.post("/llm-gateway/providers/test", response_model=LlmGatewayTestCallResponse)
def post_provider_test(request: LlmGatewayTestCallRequest):
    return test_provider_connection(request)
