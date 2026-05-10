from __future__ import annotations

import json
from typing import Any

from app.services.agent_reasoning.agent_contracts import AgentReasoningDecision, DataUsed


class DecisionParser:
    @staticmethod
    def parse(raw: str | dict[str, Any], *, agent_key: str, prompt_hash: str | None = None, output_hash: str | None = None, llm_model: str | None = None) -> AgentReasoningDecision:
        if isinstance(raw, str):
            text = raw.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.lower().startswith("json"):
                    text = text[4:].strip()
            payload = json.loads(text)
        else:
            payload = dict(raw)

        payload.setdefault("agent_key", agent_key)
        payload.setdefault("reasoning_status", "completed")
        payload.setdefault("decision", "needs_more_evidence")
        payload.setdefault("confidence", 0.0)
        payload.setdefault("thesis", "No thesis provided by reasoning model.")
        payload.setdefault("bull_case", [])
        payload.setdefault("bear_case", [])
        payload.setdefault("missing_evidence", [])
        payload.setdefault("risk_notes", [])
        payload.setdefault("hard_blockers", [])
        payload.setdefault("soft_warnings", [])
        payload.setdefault("data_used", {})
        if not isinstance(payload["data_used"], dict):
            payload["data_used"] = {}
        payload["data_used"] = DataUsed.model_validate(payload["data_used"]).model_dump()
        payload["llm_used"] = True
        payload["llm_model"] = payload.get("llm_model") or llm_model
        payload["prompt_hash"] = payload.get("prompt_hash") or prompt_hash
        payload["output_hash"] = payload.get("output_hash") or output_hash
        return AgentReasoningDecision.model_validate(payload)
