from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.services.agent_runtime.idempotency import fingerprint
from app.services.agent_runtime.models import (
    AgentRunRequest,
    AgentRunResult,
    AgentRuntimeStatusResponse,
    WorkflowRunCreateRequest,
    WorkflowRunRecord,
    iso_utc_now,
)
from app.services.agent_runtime.registry import list_agents, require_agent
from app.services.agent_runtime.store import (
    get_agent_run as _get_agent_run,
    get_latest_agent_run_id,
    get_workflow_run as _get_workflow_run,
    index_idempotency,
    list_agent_runs,
    list_workflow_runs,
    lookup_idempotency,
    persistence_mode,
    store_agent_run,
    store_workflow_run,
)
from app.services.agent_runtime.redis_runtime import (
    acquire_agent_lock,
    get_redis_runtime_status,
    release_agent_lock,
    set_active_workflow_state,
)


def build_status() -> AgentRuntimeStatusResponse:
    updated_at = iso_utc_now()
    redis_status = get_redis_runtime_status()
    try:
        from app.core.settings import get_settings

        capability_flags = get_settings().agent_capability_flags
    except Exception:
        capability_flags = {
            "agent_reasoning_enabled": False,
            "agent_can_recommend_trades": False,
            "agent_can_create_paper_plans": False,
            "agent_can_create_approval_requests": False,
            "agent_can_submit_paper_orders": False,
            "agent_can_submit_live_orders": False,
        }
    return AgentRuntimeStatusResponse(
        updated_at=updated_at,
        summary={
            "registered_agents_count": len(list_agents()),
            "workflow_runs_count": len(list_workflow_runs()),
            "agent_runs_count": len(list_agent_runs()),
            "persistence_mode": persistence_mode(),
            "redis_mode": redis_status.redis_mode,
            "llm_required": False,
            "agent_reasoning_advisory_only": True,
            "broker_submission_enabled": False,
            "agent_capability_flags": capability_flags,
            "next_action": "Existing wrappers run deterministic gates; optional Agent Reasoning Runtime attaches audited advisory reasoning only.",
        },
        safety={
            "no_broker_calls": True,
            "no_execution_submit": True,
            "no_llm_for_trade_decision": True,
            "dry_run_default": True,
            "agent_capability_flags": capability_flags,
        },
    )


def _workflow_run_id_for_idempotency(req: AgentRunRequest) -> str:
    # Avoid coupling dedupe to auto-generated workflow_run_id.
    # If a workflow_run_id is supplied, include it; otherwise use a stable placeholder.
    return req.workflow_run_id or "auto"


def _ensure_workflow_run(req: AgentRunRequest) -> WorkflowRunRecord:
    if req.workflow_run_id:
        wr = get_workflow_run(req.workflow_run_id)
        if wr is not None:
            return wr
        return create_workflow_run(WorkflowRunCreateRequest())
    return create_workflow_run(WorkflowRunCreateRequest())


def create_workflow_run(req: WorkflowRunCreateRequest) -> WorkflowRunRecord:
    now = iso_utc_now()
    workflow_run_id = f"wr_{now.replace('-', '').replace(':', '')}"
    rec = WorkflowRunRecord(
        workflow_run_id=workflow_run_id,
        workflow_name=req.workflow_name,
        asset_class=req.asset_class,
        horizon=req.horizon,
        mode=req.mode,
        source=req.source,
        status="created",
        current_stage=None,
        current_agent_key=None,
        stage_states={},
        agent_run_ids=[],
        blockers=[],
        warnings=[],
        created_at=now,
        updated_at=now,
        metadata=req.metadata,
    )
    store_workflow_run(rec)
    return rec


def get_workflow_run(workflow_run_id: str) -> WorkflowRunRecord | None:
    return _get_workflow_run(workflow_run_id)


def get_agent_run(run_id: str) -> AgentRunResult | None:
    return _get_agent_run(run_id)


def _trace_event(event: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"event": event, "details": details or {}, "at": iso_utc_now()}


def _empty_alpha_entry_plan() -> dict[str, Any]:
    return {
        "entry": None,
        "stop": None,
        "target": None,
        "risk_per_share": None,
        "risk_dollars": None,
        "expected_r": None,
        "position_size_estimate": None,
        "plan_type": None,
        "notes": [],
    }


def _alpha_recommendation_from_reasoning(reasoning_payload: dict[str, Any], *, status: str) -> dict[str, Any]:
    entry_plan = reasoning_payload.get("entry_plan") if isinstance(reasoning_payload.get("entry_plan"), dict) else {}
    entry = {**_empty_alpha_entry_plan(), **entry_plan}
    return {
        "status": status,
        "symbol": reasoning_payload.get("symbol"),
        "strategy_key": reasoning_payload.get("strategy_key"),
        "setup_type": reasoning_payload.get("setup_type"),
        "scanner_score": reasoning_payload.get("scanner_score"),
        "model_score": reasoning_payload.get("model_score"),
        "evidence_score": reasoning_payload.get("evidence_score"),
        "small_account_score": reasoning_payload.get("small_account_score"),
        "strategy_fit_score": reasoning_payload.get("strategy_fit_score"),
        "final_score": reasoning_payload.get("final_score"),
        "confidence": reasoning_payload.get("confidence"),
        "entry_plan": entry,
        "evidence_summary": {
            "data_used": reasoning_payload.get("data_used") or {},
            "bull_case": reasoning_payload.get("bull_case") or [],
            "bear_case": reasoning_payload.get("bear_case") or [],
        },
        "risk_summary": {"risk_notes": reasoning_payload.get("risk_notes") or []},
        "blockers": list(reasoning_payload.get("hard_blockers") or []),
        "warnings": list(reasoning_payload.get("soft_warnings") or []),
        "reason": reasoning_payload.get("thesis") or "",
        "non_real_data_used": False,
        "synthetic_data_used": False,
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
        "recommendation_id": reasoning_payload.get("recommendation_id"),
        "predicted_return_pct": reasoning_payload.get("predicted_return_pct"),
        "predicted_return_r": reasoning_payload.get("predicted_return_r"),
        "predicted_win_probability": reasoning_payload.get("predicted_win_probability"),
        "predicted_expected_value_r": reasoning_payload.get("predicted_expected_value_r"),
        "prediction_horizon_minutes": reasoning_payload.get("prediction_horizon_minutes"),
        "prediction_model_key": reasoning_payload.get("prediction_model_key"),
        "prediction_reason": reasoning_payload.get("prediction_reason"),
    }


def _safe_alpha_no_qualified(reason: str, *, blockers: list[str] | None = None, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "status": "no_qualified_setup",
        "symbol": None,
        "strategy_key": None,
        "setup_type": None,
        "scanner_score": None,
        "model_score": None,
        "evidence_score": None,
        "small_account_score": None,
        "strategy_fit_score": None,
        "final_score": None,
        "confidence": None,
        "entry_plan": _empty_alpha_entry_plan(),
        "evidence_summary": {},
        "risk_summary": {},
        "blockers": sorted(set(blockers or [])),
        "warnings": sorted(set(warnings or [])),
        "reason": reason,
        "non_real_data_used": False,
        "synthetic_data_used": False,
        "submitted_order": False,
        "broker_called": False,
        "llm_used_for_trade_decision": False,
        "recommendation_id": None,
        "predicted_return_pct": None,
        "predicted_return_r": None,
        "predicted_win_probability": None,
        "predicted_expected_value_r": None,
        "prediction_horizon_minutes": None,
        "prediction_model_key": None,
        "prediction_reason": None,
    }


def _attach_advisory_reasoning(
    *,
    agent_key: str,
    workflow_run_id: str,
    inputs: dict[str, Any],
    context: dict[str, Any],
    tool_request: dict[str, Any],
    tool_response: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    """Run supported DeepAgents and let audited decisions control agent outputs.

    Behavior:
    * For ``watchlist_builder_agent`` and only when ``AGENT_REASONING_ENABLED=true``,
      a DeepAgents reasoning turn is invoked over the closed-world evidence pack.
    * If the supervisor returns ``reasoning_status="completed"`` and ``DecisionAuditor``
      accepts it, the agentic ``usable_symbols`` / ``rejected_symbols`` /
      ``candidate_rankings`` / ``candidate_source`` replace the deterministic
      values in the merged tool response. ``selected_symbol`` /
      ``selected_candidate`` remain ``None`` — Alpha selects later.
    * If the supervisor returns ``audit_rejected``, deterministic
      ``usable_symbols`` are preserved (test 8) and reasoning blockers are
      surfaced.
    * If reasoning is disabled or unavailable, the deterministic tool response
      is returned unchanged with ``reasoning_status`` attached for visibility.
    * For ``alpha_engine_agent``, an accepted audited ``candidate_selected``
      decision replaces ``alpha_recommendation`` / ``alpha_status`` /
      ``alpha_selected_symbol`` / ``alpha_strategy_key``. Rejected output does
      not overwrite the deterministic safe Alpha response.
    * Broker / submit / live-trade decision flags are always forced ``False``.
    """
    warnings: list[str] = []
    if not isinstance(tool_response, dict):
        return tool_response, None, warnings
    if agent_key not in {"watchlist_builder_agent", "alpha_engine_agent"}:
        return tool_response, None, warnings
    try:
        from app.services.deepagents_runtime import DeepAgentRunContext, DeepAgentSupervisor, EvidencePackBuilder

        workflow_state: dict[str, Any] = {
            **(inputs or {}),
            **(tool_response or {}),
            "workflow_run_id": workflow_run_id,
            "orchestrator_run_id": context.get("orchestrator_run_id"),
            "agent_key": agent_key,
            "tool_name": tool_request.get("tool_name") if isinstance(tool_request, dict) else None,
        }
        for key in ("selected_candidates", "watchlist_candidates", "scanner_candidates", "feature_rows", "watchlist"):
            if key not in workflow_state and isinstance(tool_response.get(key), list):
                workflow_state[key] = tool_response[key]
        evidence = EvidencePackBuilder.build(workflow_state, agent_key)
        reasoning = DeepAgentSupervisor().reason(
            evidence=evidence,
            context=DeepAgentRunContext(
                workflow_run_id=workflow_run_id,
                orchestrator_run_id=context.get("orchestrator_run_id"),
                trace_id=context.get("trace_id"),
                metadata={"tool_name": tool_request.get("tool_name") if isinstance(tool_request, dict) else None},
            ),
        )
        reasoning_payload = reasoning.model_dump()
        merged = dict(tool_response)
        merged["agent_reasoning"] = reasoning_payload
        merged["deepagent_reasoning"] = reasoning_payload
        ro = merged.get("reasoning_outputs") if isinstance(merged.get("reasoning_outputs"), dict) else {}
        ro[agent_key] = reasoning_payload
        merged["reasoning_outputs"] = ro
        merged["reasoning_blockers"] = list(reasoning_payload.get("hard_blockers") or [])
        merged["reasoning_warnings"] = list(reasoning_payload.get("soft_warnings") or [])
        merged["agent_reasoning_enabled"] = reasoning.reasoning_status != "disabled"
        if agent_key == "watchlist_builder_agent":
            merged["watchlist_agent_decision"] = reasoning_payload
        elif agent_key == "alpha_engine_agent":
            merged["alpha_agent_decision"] = reasoning_payload

        agentic_applied = False
        if agent_key == "watchlist_builder_agent" and reasoning.reasoning_status in {"completed", "blocked"}:
            if reasoning.decision in {"candidates_selected", "candidate_selected"}:
                allowed = {s.upper() for s in evidence.allowed_symbols}
                agentic_symbols = [
                    str(s).upper().strip()
                    for s in (reasoning.usable_symbols or [])
                    if str(s).upper().strip() in allowed
                ]
                if agentic_symbols:
                    merged["symbols"] = agentic_symbols
                    merged["usable_symbols"] = agentic_symbols
                    merged["selected_candidate"] = None
                    merged["selected_symbol"] = None
                    if reasoning.candidate_source and reasoning.candidate_source.lower() != "none":
                        merged["candidate_source"] = reasoning.candidate_source
                    merged["candidate_rankings"] = [dict(r) for r in (reasoning.candidate_rankings or [])]
                    merged["rejected_symbols"] = [dict(r) for r in (reasoning.rejected_symbols or [])]
                    merged["recommendation"] = {
                        "status": "candidate_selected",
                        "symbol": None,
                        "non_real_data_used": False,
                        "synthetic_data_used": False,
                        "reason": reasoning.thesis or "agentic_watchlist_selection",
                    }
                    merged["decision"] = "candidates_selected"
                    agentic_applied = True
            elif reasoning.decision == "no_qualified_setup":
                merged["symbols"] = []
                merged["usable_symbols"] = []
                merged["selected_candidate"] = None
                merged["selected_symbol"] = None
                merged["candidate_source"] = "none"
                merged["candidate_rankings"] = []
                merged["rejected_symbols"] = []
                merged["recommendation"] = {
                    "status": "no_qualified_setup",
                    "symbol": None,
                    "non_real_data_used": False,
                    "synthetic_data_used": False,
                    "reason": "no_real_scanner_candidates",
                }
                merged["decision"] = "no_qualified_setup"
                merged["blockers"] = sorted(set((merged.get("blockers") or []) + ["no_real_scanner_candidates"]))
                agentic_applied = True

        if agent_key == "alpha_engine_agent" and reasoning.reasoning_status in {"completed", "blocked"}:
            if reasoning.decision == "candidate_selected" and reasoning.symbol:
                alpha_payload = _alpha_recommendation_from_reasoning(reasoning_payload, status="candidate_selected")
                merged["alpha_recommendation"] = alpha_payload
                merged["recommendation"] = alpha_payload
                merged["alpha_status"] = "candidate_selected"
                merged["alpha_selected_symbol"] = str(reasoning.symbol).upper()
                merged["alpha_strategy_key"] = reasoning.strategy_key
                merged["alpha_score"] = reasoning.final_score
                merged["alpha_reason"] = reasoning.thesis
                merged["alpha_blockers"] = list(reasoning.hard_blockers or [])
                merged["alpha_warnings"] = list(reasoning.soft_warnings or [])
                merged["next_action"] = reasoning.recommended_next_action or "Proceed with audited Alpha-selected candidate."
                agentic_applied = True
            elif reasoning.decision in {"no_qualified_setup", "data_unavailable", "blocked"}:
                status = reasoning.decision
                alpha_payload = _safe_alpha_no_qualified(
                    "no_real_alpha_candidates" if status == "no_qualified_setup" else (reasoning.thesis or status),
                    blockers=list(reasoning.hard_blockers or []),
                    warnings=list(reasoning.soft_warnings or []),
                )
                if status in {"data_unavailable", "blocked"}:
                    alpha_payload["status"] = status
                merged["alpha_recommendation"] = alpha_payload
                merged["recommendation"] = alpha_payload
                merged["alpha_status"] = alpha_payload["status"]
                merged["alpha_selected_symbol"] = None
                merged["alpha_strategy_key"] = None
                merged["alpha_score"] = None
                merged["alpha_reason"] = alpha_payload["reason"]
                merged["alpha_blockers"] = list(alpha_payload["blockers"])
                merged["alpha_warnings"] = list(alpha_payload["warnings"])
                merged["next_action"] = reasoning.recommended_next_action or "No audited Alpha Engine candidate selected."
                agentic_applied = True

        merged["agentic_decision_applied"] = agentic_applied
        merged["llm_used"] = reasoning.reasoning_status == "completed" and bool(reasoning.llm_used)
        merged["submitted_order"] = False
        merged["broker_called"] = False
        merged["llm_used_for_trade_decision"] = False
        return merged, reasoning_payload, warnings
    except Exception as exc:  # Defensive: reasoning must never break deterministic agent execution.
        warnings.append(f"agent_reasoning_attach_failed:{type(exc).__name__}")
        return tool_response, None, warnings


def create_agent_run(req: AgentRunRequest) -> AgentRunResult:
    descriptor = require_agent(req.agent_key)
    if descriptor is None:
        raise ValueError(f"Unknown agent_key '{req.agent_key}'")

    # Idempotency
    fp = fingerprint(
        agent_key=req.agent_key,
        workflow_run_id=_workflow_run_id_for_idempotency(req),
        inputs=req.inputs,
        context=req.context,
        requested_stage=req.requested_stage,
        idempotency_key=req.idempotency_key,
    )
    existing_run_id = lookup_idempotency(fp)
    if existing_run_id:
        existing = get_agent_run(existing_run_id)
        if existing:
            # Return existing run with duplicate status (do not mutate persisted record).
            dup = existing.model_dump()
            dup["status"] = "duplicate"
            return AgentRunResult(**dup)

    # Create workflow run after idempotency check (so dedupe works even without workflow_run_id)
    wr = _ensure_workflow_run(req)

    now = iso_utc_now()
    run_id = f"ar_{uuid4().hex[:12]}_{now.replace('-', '').replace(':', '')}"
    trace_id = f"tr_{uuid4().hex[:10]}"

    stage_num = req.requested_stage or descriptor.stage_number

    lock_acquired = acquire_agent_lock(workflow_run_id=wr.workflow_run_id, agent_key=req.agent_key, ttl_seconds=60)

    # Phase 2 dispatch
    from app.services.agent_runtime.wrappers import WRAPPED_AGENT_KEYS, run_wrapped_agent

    reasoning_payload: dict[str, Any] | None = None
    is_wrapped = req.agent_key in WRAPPED_AGENT_KEYS and descriptor.status == "ready"
    try:
        if is_wrapped:
            wrapper_out = run_wrapped_agent(agent_key=req.agent_key, inputs=req.inputs or {}, context=req.context or {})
            tool_name = wrapper_out["tool_name"]
            tool_req = wrapper_out["tool_request"]
            tool_resp = wrapper_out["tool_response"]
            next_agent = wrapper_out.get("next_agent")
            safety = wrapper_out.get("safety")
            tool_resp, reasoning_payload, reasoning_attach_warnings = _attach_advisory_reasoning(
                agent_key=req.agent_key,
                workflow_run_id=wr.workflow_run_id,
                inputs=req.inputs or {},
                context=req.context or {},
                tool_request={"tool_name": tool_name, **(tool_req if isinstance(tool_req, dict) else {})},
                tool_response=tool_resp if isinstance(tool_resp, dict) else {"raw_tool_response": tool_resp},
            )

            decision_payload, blockers, warnings, next_action, next_agent, artifacts = wrapper_outcome_to_result(
                agent_key=req.agent_key,
                tool_name=tool_name,
                tool_request=tool_req,
                tool_response=tool_resp,
                safety=safety,
                next_agent=next_agent,
            )
            warnings = sorted(set(warnings + reasoning_attach_warnings))
            status = "completed" if not blockers and tool_resp.get("status") != "blocked" else "blocked"
            if reasoning_payload:
                artifacts["agent_reasoning"] = reasoning_payload
                artifacts["llm_used"] = bool(reasoning_payload.get("llm_used"))
                artifacts["llm_used_for_trade_decision"] = False
            decision = {
                "phase": "phase_2_wrapped",
                "agent_key": req.agent_key,
                "tool": tool_name,
                "result": decision_payload,
            }
        else:
            status = "blocked"
            blockers = ["agent_wrapper_not_implemented"]
            warnings = []
            next_agent = None
            artifacts = {"llm_used": False, "broker_called": False, "submitted_order": False, "llm_used_for_trade_decision": False}
            decision = {
                "implementation_status": "not_implemented",
                "message": "Agent is registered but wrapper is not implemented in Phase 2.",
                "agent_status": descriptor.status,
            }
            next_action = "Implement Phase 2 wrapper for this agent or mark it ready when available."
    finally:
        if lock_acquired:
            release_agent_lock(workflow_run_id=wr.workflow_run_id, agent_key=req.agent_key)

    trace = [
        _trace_event("agent_started", {"agent_key": req.agent_key, "dry_run": bool(req.dry_run)}),
        _trace_event(
            "safety_boundary_checked",
            {
                "no_broker_calls": True,
                "no_execution_submit": True,
                "no_llm_for_trade_decision": True,
                "dry_run_default": True,
            },
        ),
        _trace_event("tool_selected", {"wrapped": bool(is_wrapped)}),
        _trace_event("tool_called", {"tool": decision.get("tool") if isinstance(decision, dict) else None}),
        _trace_event("tool_result_received", {"status": status}),
        _trace_event("agent_reasoning_attached", {"attached": bool(reasoning_payload), "llm_used": bool(reasoning_payload and reasoning_payload.get("llm_used"))}),
        _trace_event("idempotency_checked", {"fingerprint": fp, "idempotency_key": req.idempotency_key}),
        _trace_event("decision_recorded", {"agent_key": req.agent_key}),
        _trace_event(
            "persisted_to_postgres_or_memory",
            {"persistence_mode": persistence_mode(), "redis_mode": get_redis_runtime_status().redis_mode},
        ),
    ]

    result = AgentRunResult(
        run_id=run_id,
        workflow_run_id=wr.workflow_run_id,
        agent_key=req.agent_key,
        status=status,  # type: ignore[arg-type]
        decision=decision,
        blockers=blockers,
        warnings=warnings,
        next_action=next_action,
        next_agent=next_agent,
        artifacts=artifacts,
        trace_id=trace_id,
        trace=trace,
        idempotency_key=req.idempotency_key or fp,
        inputs_hash=fp,
        created_at=now,
        persistence_mode=persistence_mode(),
        storage_metadata={"redis_lock_acquired": bool(lock_acquired)},
    )

    store_agent_run(result)
    index_idempotency(fp, run_id)
    set_active_workflow_state(
        workflow_run_id=wr.workflow_run_id,
        state={"workflow_run_id": wr.workflow_run_id, "current_agent_key": req.agent_key, "current_stage": stage_num, "updated_at": now},
    )

    # Update workflow run record (in-place update and persist back)
    wr.agent_run_ids.append(run_id)
    wr.current_agent_key = req.agent_key
    wr.current_stage = stage_num
    wr.stage_states[req.agent_key] = {
        "run_id": run_id,
        "status": result.status,
        "stage": stage_num,
        "created_at": now,
    }
    wr.updated_at = now
    wr.persistence_mode = persistence_mode()
    store_workflow_run(wr)

    return result


def wrapper_outcome_to_result(
    *,
    agent_key: str,
    tool_name: str,
    tool_request: dict[str, Any],
    tool_response: dict[str, Any],
    safety: Any,
    next_agent: str | None,
) -> tuple[dict[str, Any], list[str], list[str], str, str | None, dict[str, Any]]:
    from app.services.agent_runtime.wrappers.stage_wrappers import _wrap_result

    return _wrap_result(
        agent_key=agent_key,
        tool_name=tool_name,
        tool_request=tool_request,
        tool_response=tool_response,
        safety=safety,
        next_agent=next_agent,
    )


def get_latest_snapshot() -> dict[str, Any]:
    runs = list_workflow_runs()
    latest_wr = sorted(runs, key=lambda r: r.updated_at)[-1].model_dump() if runs else None

    latest_by_key: dict[str, Any] = {}
    for a in list_agents():
        rid = get_latest_agent_run_id(a.agent_key)
        latest_by_key[a.agent_key] = _get_agent_run(rid).model_dump() if rid and _get_agent_run(rid) else None

    return {
        "status": "ok",
        "data_mode": "agent_runtime_latest_v1",
        "updated_at": iso_utc_now(),
        "registered_agents_count": len(list_agents()),
        "persistence_mode": persistence_mode(),
        "redis_mode": get_redis_runtime_status().redis_mode,
        "latest_workflow_run": latest_wr,
        "latest_agent_runs_by_key": latest_by_key,
        "message": "Agent runtime latest snapshot (best-effort Postgres persistence; falls back to memory when unavailable).",
    }

