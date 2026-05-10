from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

from app.core.production_safety import production_database_blocker
from app.db.session import check_database_health
from app.services.agent_runtime.models import AgentRunRequest, WorkflowRunCreateRequest
from app.services.agent_runtime.service import create_agent_run, create_workflow_run
from app.services.approval_queue.models import ApprovalItemCreate
from app.services.approval_queue.service import create_item as create_approval_item
from app.services.audit_log.models import AuditEventCreate
from app.services.audit_log.service import write_event
from app.services.workflow_governance.models import WorkflowGovernanceCheckRequest
from app.services.workflow_governance.service import check_governance
from app.services.workflow_orchestrator.models import OrchestratorRunRequest, OrchestratorRunResponse, OrchestratorStatusResponse, iso_utc_now, new_orchestrator_id
from app.services.workflow_orchestrator.pipeline_carryforward import advisory_glue_next_agent_mismatch, apply_stage_carryforward
from app.services.workflow_orchestrator.safety import enforce_orchestrator_safety
from app.services.workflow_orchestrator.stage_plan import default_stage_plan, orchestrator_pipeline_agent_count
from app.services.workflow_orchestrator.state_contract import WorkflowCarryForwardState

_MEMORY: dict[str, OrchestratorRunResponse] = {}
logger = logging.getLogger(__name__)


def _recommendation_payload(
    *,
    status: str,
    symbol: str | None = None,
    reason: str | None = None,
    mock_data_used: bool = False,
    synthetic_data_used: bool = False,
) -> dict[str, Any]:
    return {
        "status": status,
        "symbol": symbol,
        "mock_data_used": bool(mock_data_used),
        "synthetic_data_used": bool(synthetic_data_used),
        "reason": reason,
    }


def _blocked_run_response(*, body: OrchestratorRunRequest, blockers: list[str], warnings: list[str] | None = None, next_action: str) -> OrchestratorRunResponse:
    wr = create_workflow_run(
        WorkflowRunCreateRequest(
            workflow_name=body.workflow_name,
            asset_class=body.asset_class,
            horizon=body.horizon,
            mode=body.mode,
            source=body.source,
            metadata=body.metadata,
        )
    )
    resp = OrchestratorRunResponse(
        orchestrator_run_id=new_orchestrator_id(),
        workflow_run_id=wr.workflow_run_id,
        status="blocked",
        current_stage=None,
        current_agent_key=None,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings or [])),
        next_action=next_action,
        approval_required=False,
        approval_id=None,
        execution_boundary_reached=False,
        governance_blockers=[],
        preview_continued_despite_governance_blockers=False,
        preview_continued_after_approval_boundary=False,
        source_mode=body.source,
        using_mock_data=False,
        recommendation=_recommendation_payload(status="data_unavailable", reason="; ".join(sorted(set(blockers)))[:500]),
        allow_submit=False,
        submitted_order=False,
        broker_called=False,
        llm_used=False,
        created_at=iso_utc_now(),
        updated_at=iso_utc_now(),
    )
    _MEMORY[resp.orchestrator_run_id] = resp
    _persist_run(resp, req=body)
    return resp


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def get_orchestrator_status() -> OrchestratorStatusResponse:
    session = _db_session()
    count = len(_MEMORY)
    persistence_mode = "memory"
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import WorkflowOrchestratorRunRecord

            count = int(session.execute(select(func.count()).select_from(WorkflowOrchestratorRunRecord)).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    return OrchestratorStatusResponse(updated_at=iso_utc_now(), summary={"persistence_mode": persistence_mode, "runs_count": count, "no_submit": True})


def _persist_run(resp: OrchestratorRunResponse, *, req: OrchestratorRunRequest) -> None:
    _MEMORY[resp.orchestrator_run_id] = resp
    session = _db_session()
    if session is None:
        return
    try:
        from app.db.models import WorkflowOrchestratorRunRecord

        session.merge(
            WorkflowOrchestratorRunRecord(
                orchestrator_run_id=resp.orchestrator_run_id,
                workflow_run_id=resp.workflow_run_id,
                status=resp.status,
                asset_class=req.asset_class,
                horizon=req.horizon,
                mode=req.mode,
                source=req.source,
                symbols=req.symbols,
                current_stage=resp.current_stage,
                current_agent_key=resp.current_agent_key,
                stage_timeline=resp.stage_timeline,
                agent_run_ids=resp.agent_run_ids,
                blockers=resp.blockers,
                warnings=resp.warnings,
                next_action=resp.next_action,
                approval_required=bool(resp.approval_required),
                execution_boundary_reached=bool(resp.execution_boundary_reached),
                submitted_order=False,
                broker_called=False,
                llm_used=False,
                metadata_json=req.metadata or {},
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        session.close()


def run_workflow(body: OrchestratorRunRequest) -> OrchestratorRunResponse:
    db_blocker = production_database_blocker()
    if db_blocker:
        db_health = check_database_health()
        return _blocked_run_response(
            body=body,
            blockers=[db_blocker],
            warnings=[str(db_health.get("message") or "database unavailable")],
            next_action="Configure a non-local production DATABASE_URL before running the autonomous workflow.",
        )

    safety = enforce_orchestrator_safety(body.model_dump())
    if safety.blockers:
        # Even blocked runs should emit a workflow_run_id so operators can trace/audit the attempt.
        return _blocked_run_response(body=body, blockers=safety.blockers, warnings=safety.warnings, next_action="Blocked by orchestrator safety policy.")

    # Governance pre-check
    gov = check_governance(
        WorkflowGovernanceCheckRequest(
            asset_class=body.asset_class,
            horizon=body.horizon,
            mode=body.mode,
            source=body.source,
            symbols=body.symbols,
            dry_run=body.dry_run,
            require_human_approval=body.require_human_approval,
            allow_submit=False,
            metadata=body.metadata,
        )
    )
    write_event(AuditEventCreate(event_type="governance_check_completed", actor="system", severity="info", message="Governance check completed", metadata=gov.model_dump()))

    if gov.decision == "blocked" and not body.dry_run:
        wr = create_workflow_run(
            WorkflowRunCreateRequest(
                workflow_name=body.workflow_name,
                asset_class=body.asset_class,
                horizon=body.horizon,
                mode=body.mode,
                source=body.source,
                metadata={**(body.metadata or {}), "governance_blocked": True},
            )
        )
        resp = OrchestratorRunResponse(
            orchestrator_run_id=new_orchestrator_id(),
            workflow_run_id=wr.workflow_run_id,
            status="blocked",
            current_stage=None,
            current_agent_key=None,
            blockers=list(gov.blockers),
            warnings=list(gov.warnings),
            next_action=gov.next_action,
            approval_required=False,
            approval_id=None,
            execution_boundary_reached=False,
            governance_blockers=list(gov.blockers),
            preview_continued_despite_governance_blockers=False,
            preview_continued_after_approval_boundary=False,
            source_mode=body.source,
            using_mock_data=body.source == "mock",
            allow_submit=False,
            submitted_order=False,
            broker_called=False,
            llm_used=False,
            created_at=iso_utc_now(),
            updated_at=iso_utc_now(),
        )
        _MEMORY[resp.orchestrator_run_id] = resp
        _persist_run(resp, req=body)
        return resp

    # Create workflow run
    wr = create_workflow_run(
        WorkflowRunCreateRequest(
            workflow_name=body.workflow_name,
            asset_class=body.asset_class,
            horizon=body.horizon,
            mode=body.mode,
            source=body.source,
            metadata=body.metadata,
        )
    )
    write_event(AuditEventCreate(workflow_run_id=wr.workflow_run_id, event_type="workflow_run_created", actor="system", severity="info", message="Workflow run created", metadata={"workflow_run_id": wr.workflow_run_id}))

    orchestrator_run_id = new_orchestrator_id()
    write_event(AuditEventCreate(workflow_run_id=wr.workflow_run_id, orchestrator_run_id=orchestrator_run_id, event_type="orchestrator_run_started", actor="system", severity="info", message="Orchestrator run started", metadata=body.model_dump()))

    plan = default_stage_plan(simulated_position=body.simulated_position, simulated_closed_trade=body.simulated_closed_trade)
    stage_cap = max(0, int(body.stop_at_stage or orchestrator_pipeline_agent_count()))
    stage_timeline: list[dict[str, Any]] = []
    agent_run_ids: list[str] = []
    blockers: list[str] = list(gov.blockers)
    warnings: list[str] = list(gov.warnings)
    current_stage: int | None = None
    current_agent: str | None = None

    state = WorkflowCarryForwardState(
        workflow_run_id=wr.workflow_run_id,
        orchestrator_run_id=orchestrator_run_id,
        asset_class=body.asset_class,
        horizon=body.horizon,
        mode=body.mode,
        source=body.source,
        symbols=list(body.symbols or []),
        workflow_request_symbols=list(body.symbols or []),
        account_equity=body.account_equity,
        max_risk_per_trade_percent=body.max_risk_per_trade_percent,
        max_daily_loss_percent=body.max_daily_loss_percent,
        max_open_positions=body.max_open_positions,
        max_trades_per_day=body.max_trades_per_day,
    )
    if body.strategy_key:
        state.strategy_key = body.strategy_key
        state.selected_strategy_key = body.strategy_key

    approval_required = bool(body.require_human_approval)
    approval_id: str | None = None
    execution_boundary_reached = False
    preview_continued_after_approval_boundary = False

    for idx, agent_key in enumerate(plan, start=1):
        current_stage = idx
        current_agent = agent_key
        write_event(AuditEventCreate(workflow_run_id=wr.workflow_run_id, orchestrator_run_id=orchestrator_run_id, event_type="agent_run_started", actor="system", severity="info", message=f"Agent started: {agent_key}", metadata={"agent_key": agent_key, "stage": idx}))

        # Stop at requested stage boundary (1-based index into plan)
        if idx > stage_cap:
            break

        try:
            agent_result = create_agent_run(
                AgentRunRequest(
                    workflow_run_id=wr.workflow_run_id,
                    agent_key=agent_key,
                    inputs=state.to_agent_inputs(),
                    context={
                        "source": "workflow_orchestrator",
                        "workflow_run_id": wr.workflow_run_id,
                        "orchestrator_run_id": orchestrator_run_id,
                    },
                    dry_run=True,
                    requested_stage=None,
                    idempotency_key=f"orc:{orchestrator_run_id}:{agent_key}",
                )
            )
        except Exception as exc:
            logger.exception("Workflow orchestrator agent stage failed", extra={"agent_key": agent_key, "orchestrator_run_id": orchestrator_run_id})
            blockers.append("operational_failure")
            warnings.append(f"{agent_key}_failed:{exc}")
            stage_timeline.append(
                {
                    "stage": idx,
                    "agent_key": agent_key,
                    "run_id": None,
                    "status": "failed",
                    "at": iso_utc_now(),
                    "pipeline_inputs_snapshot": {
                        "symbols": list(state.symbols),
                        "source_mode": state.source_mode,
                        "using_mock_data": state.using_mock_data,
                        "submitted_order": False,
                        "broker_called": False,
                        "llm_used": False,
                    },
                }
            )
            break
        agent_run_ids.append(agent_result.run_id)

        carry_warnings = apply_stage_carryforward(agent_key=agent_key, agent_result=agent_result, state=state)
        warnings.extend(carry_warnings)
        next_planned = plan[idx] if idx < len(plan) else None
        mismatch = advisory_glue_next_agent_mismatch(agent_key=agent_key, agent_result=agent_result, next_planned_agent=next_planned)
        if mismatch:
            warnings.append(mismatch)

        stage_timeline.append({
            "stage": idx,
            "agent_key": agent_key,
            "run_id": agent_result.run_id,
            "status": agent_result.status,
            "at": agent_result.created_at,
            "pipeline_inputs_snapshot": {
                k: state.model_dump().get(k)
                for k in (
                    "symbols",
                    "discovery_mode",
                    "candidate_source",
                    "raw_candidate_count",
                    "filtered_candidate_count",
                    "symbol",
                    "selected_symbol",
                    "alpha_status",
                    "alpha_selected_symbol",
                    "alpha_strategy_key",
                    "alpha_score",
                    "alpha_reason",
                    "alpha_blockers",
                    "alpha_warnings",
                    "strategy_key",
                    "selected_strategy_key",
                    "selected_model_key",
                    "proof_status",
                    "qlib_available",
                    "qlib_version",
                    "qlib_artifact_id",
                    "qlib_artifact_counts",
                    "proof_id",
                    "evidence_blockers",
                    "evidence_warnings",
                    "provider_status",
                    "source_mode",
                    "using_mock_data",
                    "usable_symbols",
                    "rejected_symbols",
                    "latest_snapshot_count",
                    "feature_row_count",
                    "persistence_status",
                    "freshness_status",
                    "kafka_status",
                    "latest_price",
                    "spread_bps",
                    "avg_dollar_volume",
                    "account_equity",
                    "max_risk_dollars",
                    "max_daily_loss_dollars",
                    "max_open_positions",
                    "max_trades_per_day",
                    "small_account_decision",
                    "feasible_symbols",
                    "small_account_rejected_symbols",
                    "small_account_blockers",
                    "small_account_warnings",
                    "submitted_order",
                    "broker_called",
                    "llm_used",
                )
            },
        })

        write_event(AuditEventCreate(workflow_run_id=wr.workflow_run_id, orchestrator_run_id=orchestrator_run_id, agent_run_id=agent_result.run_id, event_type="agent_run_completed", actor="system", severity="info", message=f"Agent completed: {agent_key}", metadata={"status": agent_result.status}))

        if agent_result.blockers:
            blockers.extend(agent_result.blockers)
        if agent_result.warnings:
            warnings.extend(agent_result.warnings)

        # Execution boundary marker (approval queue); do not stop — later agents still run in preview.
        if agent_key == "execution_approval_agent":
            execution_boundary_reached = True
            write_event(
                AuditEventCreate(
                    workflow_run_id=wr.workflow_run_id,
                    orchestrator_run_id=orchestrator_run_id,
                    event_type="execution_boundary_reached",
                    actor="system",
                    severity="info",
                    message="Execution boundary reached",
                    metadata={"agent_key": agent_key},
                )
            )
            if approval_required:
                try:
                    approval_payload = (agent_result.decision or {}).get("result") or {}
                    approval = approval_payload.get("approval") if isinstance(approval_payload, dict) else None
                    if isinstance(approval, dict) and approval.get("approval_id"):
                        approval_id = str(approval.get("approval_id"))
                except Exception:
                    approval_id = approval_id
                if body.dry_run:
                    preview_continued_after_approval_boundary = idx < min(stage_cap, len(plan))
                else:
                    break

        if agent_result.status in {"blocked", "failed"}:
            write_event(AuditEventCreate(workflow_run_id=wr.workflow_run_id, orchestrator_run_id=orchestrator_run_id, event_type="workflow_blocked", actor="system", severity="warn", message="Workflow blocked by agent", metadata={"agent_key": agent_key, "blockers": agent_result.blockers}))
            warnings.append(f"{agent_key}_reported_{agent_result.status}; preview_continued_without_submit")

    if blockers:
        status: str = "blocked"
        next_action = "Resolve blockers before continuing."
    elif approval_id:
        status = "paused_for_approval"
        next_action = "Await human approval in approval queue."
    elif execution_boundary_reached:
        status = "completed_preview"
        next_action = "Full agent pipeline preview completed (including post-approval stages). Check approval queue if execution_approval created an item."
    else:
        status = "completed_preview"
        next_action = "Preview completed."

    if state.alpha_recommendation:
        recommendation = dict(state.alpha_recommendation)
        recommendation["submitted_order"] = False
        recommendation["broker_called"] = False
        recommendation["llm_used_for_trade_decision"] = False
    elif blockers:
        if "scanner_or_provider_unavailable" in blockers:
            recommendation_status = "data_unavailable"
        elif "no_scanner_candidates_passed_filters" in blockers:
            recommendation_status = "no_qualified_setup"
        elif "no_usable_symbols" in blockers or "operational_failure" in blockers:
            recommendation_status = "data_unavailable"
        else:
            recommendation_status = "blocked"
        recommendation = _recommendation_payload(
            status=recommendation_status,
            symbol=None,
            reason="; ".join(sorted(set(blockers)))[:500],
            mock_data_used=bool(state.using_mock_data),
            synthetic_data_used=False,
        )
    elif state.selected_symbol or state.symbol:
        recommendation = _recommendation_payload(
            status="candidate_selected",
            symbol=state.selected_symbol or state.symbol,
            reason="Candidate selected by provider-backed workflow stages.",
            mock_data_used=bool(state.using_mock_data),
            synthetic_data_used=False,
        )
    else:
        recommendation = _recommendation_payload(
            status="no_qualified_setup",
            symbol=None,
            reason="No provider-backed candidate qualified.",
            mock_data_used=bool(state.using_mock_data),
            synthetic_data_used=False,
        )

    resp = OrchestratorRunResponse(
        orchestrator_run_id=orchestrator_run_id,
        workflow_run_id=wr.workflow_run_id,
        status=status,  # type: ignore[arg-type]
        current_stage=current_stage,
        current_agent_key=current_agent,
        stage_timeline=stage_timeline,
        agent_run_ids=agent_run_ids,
        blockers=sorted(set(blockers)),
        warnings=sorted(set(warnings)),
        next_action=next_action,
        approval_required=bool(approval_required and approval_id),
        approval_id=approval_id,
        execution_boundary_reached=bool(execution_boundary_reached),
        governance_blockers=list(gov.blockers),
        preview_continued_despite_governance_blockers=bool(body.dry_run and gov.blockers),
        preview_continued_after_approval_boundary=bool(preview_continued_after_approval_boundary),
        source_mode=state.source_mode or body.source,
        using_mock_data=bool(state.using_mock_data or body.source == "mock"),
        provider_status=dict(state.provider_status),
        provider_name=state.provider_name,
        usable_symbols=list(state.usable_symbols),
        rejected_symbols=list(state.rejected_symbols),
        latest_snapshot_status=state.latest_snapshot_status,
        latest_snapshot_count=state.latest_snapshot_count,
        feature_store_status=state.feature_store_status,
        feature_row_count=state.feature_row_count,
        persistence_status=state.persistence_status,
        freshness_status=state.freshness_status,
        kafka_status=state.kafka_status,
        qlib_available=state.qlib_available,
        qlib_version=state.qlib_version,
        qlib_artifact_id=state.qlib_artifact_id,
        qlib_artifact_counts=dict(state.qlib_artifact_counts),
        selected_model_key=state.selected_model_key,
        selected_model_keys=list(state.selected_model_keys),
        selected_strategy_key=state.selected_strategy_key,
        strategy_key=state.strategy_key,
        proof_status=state.proof_status,
        proof_id=state.proof_id,
        evidence_blockers=list(state.evidence_blockers),
        evidence_warnings=list(state.evidence_warnings),
        small_account_decision=state.small_account_decision,
        max_risk_dollars=state.max_risk_dollars,
        max_daily_loss_dollars=state.max_daily_loss_dollars,
        feasible_symbols=list(state.feasible_symbols),
        small_account_rejected_symbols=list(state.small_account_rejected_symbols),
        small_account_blockers=list(state.small_account_blockers),
        small_account_warnings=list(state.small_account_warnings),
        recommendation=recommendation,
        alpha_recommendation=dict(state.alpha_recommendation),
        alpha_status=state.alpha_status,
        alpha_selected_symbol=state.alpha_selected_symbol,
        alpha_strategy_key=state.alpha_strategy_key,
        alpha_score=state.alpha_score,
        alpha_reason=state.alpha_reason,
        allow_submit=False,
        submitted_order=False,
        broker_called=False,
        llm_used=False,
        created_at=iso_utc_now(),
        updated_at=iso_utc_now(),
    )
    _persist_run(resp, req=body)
    write_event(AuditEventCreate(workflow_run_id=wr.workflow_run_id, orchestrator_run_id=orchestrator_run_id, event_type="workflow_completed_preview" if status == "completed_preview" else "workflow_paused", actor="system", severity="info", message="Orchestrator finished", metadata=resp.model_dump()))
    return resp


def list_orchestrator_runs(limit: int = 20) -> list[OrchestratorRunResponse]:
    session = _db_session()
    if session is None:
        return list(_MEMORY.values())[:limit]
    try:
        from sqlalchemy import select

        from app.db.models import WorkflowOrchestratorRunRecord

        rows = session.execute(select(WorkflowOrchestratorRunRecord).order_by(WorkflowOrchestratorRunRecord.created_at.desc()).limit(limit)).scalars().all()
        out: list[OrchestratorRunResponse] = []
        for r in rows:
            out.append(
                OrchestratorRunResponse(
                    orchestrator_run_id=r.orchestrator_run_id,
                    workflow_run_id=r.workflow_run_id,
                    status=r.status,  # type: ignore[arg-type]
                    current_stage=r.current_stage,
                    current_agent_key=r.current_agent_key,
                    stage_timeline=list(r.stage_timeline or []),
                    agent_run_ids=list(r.agent_run_ids or []),
                    blockers=list(r.blockers or []),
                    warnings=list(r.warnings or []),
                    next_action=r.next_action or "",
                    approval_required=bool(r.approval_required),
                    approval_id=None,
                    execution_boundary_reached=bool(r.execution_boundary_reached),
                    submitted_order=False,
                    broker_called=False,
                    llm_used=False,
                    created_at=r.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if r.created_at else iso_utc_now(),
                    updated_at=r.updated_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if r.updated_at else iso_utc_now(),
                )
            )
        for x in out:
            _MEMORY[x.orchestrator_run_id] = x
        return out
    except Exception:
        return list(_MEMORY.values())[:limit]
    finally:
        session.close()


def get_orchestrator_run(orchestrator_run_id: str) -> OrchestratorRunResponse | None:
    if orchestrator_run_id in _MEMORY:
        return _MEMORY.get(orchestrator_run_id)
    runs = list_orchestrator_runs(limit=50)
    _ = runs
    return _MEMORY.get(orchestrator_run_id)


def get_latest_orchestrator_run() -> OrchestratorRunResponse | None:
    runs = list_orchestrator_runs(limit=1)
    return runs[0] if runs else None


def trace_workflow(workflow_run_id: str) -> dict[str, Any]:
    # Lightweight: return orchestrator runs + audit events + agent runtime latest for this workflow if available.
    session = _db_session()
    audit: list[dict[str, Any]] = []
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import WorkflowAuditEventRecord as Row

            rows = session.execute(select(Row).where(Row.workflow_run_id == workflow_run_id).order_by(Row.created_at.asc()).limit(500)).scalars().all()
            for r in rows:
                audit.append(
                    {
                        "audit_id": r.audit_id,
                        "event_type": r.event_type,
                        "actor": r.actor,
                        "severity": r.severity,
                        "message": r.message,
                        "metadata": r.metadata_json or {},
                        "created_at": r.created_at.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") if r.created_at else iso_utc_now(),
                    }
                )
        except Exception:
            audit = []
        finally:
            session.close()
    return {"status": "ok", "workflow_run_id": workflow_run_id, "audit_events": audit}


def pause_workflow(workflow_run_id: str) -> dict[str, Any]:
    write_event(AuditEventCreate(workflow_run_id=workflow_run_id, event_type="workflow_paused", actor="system", severity="info", message="Workflow paused", metadata={}))
    return {"status": "ok", "workflow_run_id": workflow_run_id, "action": "paused"}


def resume_workflow(workflow_run_id: str) -> dict[str, Any]:
    # Resume is non-submitting: does not cross execution boundary in this phase.
    write_event(AuditEventCreate(workflow_run_id=workflow_run_id, event_type="workflow_resumed", actor="system", severity="info", message="Workflow resumed", metadata={"note": "resume does not submit execution"}))
    return {"status": "ok", "workflow_run_id": workflow_run_id, "action": "resumed"}


def stop_workflow(workflow_run_id: str) -> dict[str, Any]:
    write_event(AuditEventCreate(workflow_run_id=workflow_run_id, event_type="workflow_stopped", actor="system", severity="warn", message="Workflow stopped", metadata={}))
    return {"status": "ok", "workflow_run_id": workflow_run_id, "action": "stopped"}

