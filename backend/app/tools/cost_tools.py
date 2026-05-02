from typing import Any


_DEMO_MODEL_PRICES_PER_1K_TOKENS = {
    "gpt-4o-mini": 0.00075,
    "claude-3-5-haiku": 0.001,
    "default": 0.001,
}


def estimate_demo_llm_cost(
    model_name: str = "gpt-4o-mini",
    estimated_tokens: int = 2500,
    provider: str = "litellm",
) -> dict[str, Any]:
    price = _DEMO_MODEL_PRICES_PER_1K_TOKENS.get(model_name, _DEMO_MODEL_PRICES_PER_1K_TOKENS["default"])
    estimated_cost = round((max(estimated_tokens, 0) / 1000) * price, 6)
    return {
        "model_name": model_name,
        "estimated_tokens": estimated_tokens,
        "estimated_cost": estimated_cost,
        "provider": provider,
        "data_source": "placeholder",
        "status": "placeholder_until_litellm_usage_logs_are_wired",
    }


def estimate_llm_cost(
    model_name: str = "gpt-4o-mini",
    estimated_tokens: int = 2500,
    provider: str = "litellm",
) -> dict[str, Any]:
    return estimate_demo_llm_cost(model_name=model_name, estimated_tokens=estimated_tokens, provider=provider)
