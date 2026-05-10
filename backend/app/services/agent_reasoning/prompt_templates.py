from __future__ import annotations

import json

from app.services.agent_reasoning.agent_contracts import EvidencePack


class PromptTemplates:
    @staticmethod
    def get_system_prompt(agent_key: str) -> str:
        return f"""You are {agent_key} inside EdgeSenseAI, a real-data-only, paper-first trading platform.

You receive a strict Evidence Pack containing only real scanner output, real provider data, and real workflow state.

STRICT RULES:
- Base every claim exclusively on the Evidence Pack.
- Never invent symbols, prices, features, indicators, backtests, models, or data.
- If allowed_symbols is empty, decision must be no_qualified_setup or data_unavailable.
- Never suggest broker calls, order submission, live execution, or disabling approval.
- Never mark strategies or models active.
- Be conservative, precise, institutionally rigorous, and uncertainty-aware.
- Return valid JSON only. No markdown. No prose outside JSON.
"""

    @staticmethod
    def get_user_prompt(evidence: EvidencePack) -> str:
        contract = {
            "agent_key": evidence.agent_key,
            "reasoning_status": "completed",
            "decision": "candidate_selected | no_qualified_setup | data_unavailable | blocked | needs_more_evidence | plan_only",
            "confidence": "number between 0 and 1",
            "thesis": "short evidence-based thesis",
            "bull_case": ["evidence-backed positives only"],
            "bear_case": ["evidence-backed negatives only"],
            "missing_evidence": ["specific missing evidence"],
            "risk_notes": ["risk and uncertainty notes"],
            "recommended_next_action": "next safe workflow action",
            "hard_blockers": [],
            "soft_warnings": [],
            "data_used": {
                "provider_chain": [],
                "feature_row_id": None,
                "scanner_diagnostics": {},
                "worker_status": {},
                "symbols": [],
            },
            "llm_used": True,
            "llm_model": None,
            "prompt_hash": None,
            "output_hash": None,
        }
        return (
            "Evidence Pack:\n"
            + json.dumps(evidence.model_dump(), indent=2, ensure_ascii=False, default=str)
            + "\n\nReturn JSON matching this contract exactly:\n"
            + json.dumps(contract, indent=2)
        )
