"""Day Trading v1 API — thin wrappers over existing allowlisted services only."""

from __future__ import annotations

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.dependencies.ops_token import (
    ops_admin_token_configured,
    require_ops_admin_token,
)
from app.api.route_contracts.daytrading import contracts_routes_payload
from app.api.routes.platform_readiness import get_platform_readiness_status
from app.services.health_service import get_health_snapshot
from app.services.platform_readiness.final_report import build_final_readiness_status
from app.services.promotion_center.service import get_promotion_models_status, get_promotion_strategies_status
from app.services.real_scanner_diagnostics_service import build_scanner_diagnostics
from app.services.runtime_gate_config import (
    GateValidationError,
    TradingGatesSnapshot,
    TradingGatesUpdate,
    can_run_live_workflow,
    can_run_paper_workflow,
    get_trading_gates,
    update_trading_gates,
)
from app.services.worker_output_store import get_latest_worker_output_summary, save_scanner_candidates
from app.services.workflow_orchestrator.models import OrchestratorRunRequest
from app.services.workflow_orchestrator.service import get_latest_orchestrator_run, run_workflow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/daytrading", tags=["daytrading-v1"])


class DayTradingScannerRunBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    strategy_key: str = "stock_day_trading"
    symbols: list[str] = Field(default_factory=list)
    max_candidates: int = 10
    data_source: str = "auto"
    auto_run: bool = False
    trigger_type: str = "manual"
    trigger_workflow: bool = False


class DayTradingWorkflowRunBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    # Modes:
    #   plan_only - run reasoning + planning, do not place any orders.
    #   paper     - allow paper simulator submission per paper gate config.
    #   live      - allow live broker submission. Requires live gates ON,
    #               owner_authority_level=live_submit, and confirm_live=true
    #               *and* confirm_live_phrase=='LIVE' on this request.
    run_mode: Literal["plan_only", "paper", "live"] = "plan_only"
    # Legacy fields preserved for back-compat with existing tooling.
    dry_run: bool = True
    allow_submit: bool = False
    symbols: list[str] = Field(default_factory=list)
    source: str = "runtime"
    requested_by_email: str | None = None
    # Live-only confirmation. Both must be present for run_mode='live'.
    confirm_live: bool = False
    confirm_live_phrase: str | None = None


def _normalize_symbols(raw: list[str]) -> list[str]:
    out: list[str] = []
    for s in raw:
        sym = str(s or "").strip().upper()
        if sym:
            out.append(sym)
    return out


def _post_scanner_run_internal(body: DayTradingScannerRunBody) -> dict[str, Any]:
    """Shared scanner POST logic with legacy /api/scanner/run (services only)."""
    diagnostics = build_scanner_diagnostics(
        symbols=_normalize_symbols(body.symbols),
        max_candidates=body.max_candidates,
        requested_source=body.data_source,
        source="manual_request",
        candidate_source="manual_request",
    )
    save_scanner_candidates(
        worker_run_id=str(diagnostics["scanner_run_id"]),
        provider_name=diagnostics.get("provider_name"),
        candidates=list(diagnostics.get("selected_candidates") or []),
        rejected_candidates=list(diagnostics.get("rejected_candidates") or []),
        status=str(diagnostics.get("status") or "no_qualified_setup"),
        warnings=[],
        blockers=[] if diagnostics.get("selected_candidates") else [str(diagnostics.get("reason") or "no_qualified_setup")],
        run_source="manual_request",
        candidate_source="manual_request",
        diagnostics=diagnostics,
    )
    return {
        "status": diagnostics.get("status"),
        "source": "manual_request",
        "candidate_source": "manual_request",
        "scanner_diagnostics": diagnostics,
        "submitted_order": False,
        "broker_called": False,
        "llm_used": False,
    }


@router.get("/status")
def get_daytrading_status() -> dict[str, Any]:
    return {
        "status": "ok",
        "data_mode": "daytrading_v1_status_bundle",
        "health": get_health_snapshot(),
        "platform_readiness": get_platform_readiness_status(),
        "final_readiness": build_final_readiness_status(),
    }


@router.post("/scanner/run")
def post_daytrading_scanner_run(body: DayTradingScannerRunBody) -> dict[str, Any]:
    try:
        return _post_scanner_run_internal(body)
    except Exception:
        logger.exception("daytrading v1 scanner run failed")
        raise


@router.get("/scanner/latest")
def get_daytrading_scanner_latest() -> dict[str, Any]:
    summary = get_latest_worker_output_summary()
    sw = summary.get("scanner_worker") if isinstance(summary.get("scanner_worker"), dict) else {}
    dx = sw.get("scanner_diagnostics") if isinstance(sw.get("scanner_diagnostics"), dict) else {}
    return {
        "status": "ok",
        "data_mode": "daytrading_v1_scanner_latest",
        "scanner_worker": summary.get("scanner_worker"),
        "latest_scanner_diagnostics": summary.get("latest_scanner_diagnostics"),
        "candidate_count": summary.get("candidate_count"),
        "snapshot_count": summary.get("snapshot_count"),
        "feature_row_count": summary.get("feature_row_count"),
        "persistence_mode": summary.get("persistence_mode"),
        "matched_signals": dx.get("matched_signals"),
        "skipped_signals": dx.get("skipped_signals") or dx.get("rejected_candidates"),
        "symbols_scanned": dx.get("symbols_scanned") or dx.get("total_symbols_seen"),
        "scanner_run_id": dx.get("scanner_run_id") or sw.get("scanner_run_id") or sw.get("worker_run_id"),
    }


@router.get("/workers/latest")
def get_daytrading_workers_latest() -> dict[str, Any]:
    return {"status": "ok", **get_latest_worker_output_summary()}


def _validate_workflow_run_mode(body: DayTradingWorkflowRunBody) -> tuple[bool, bool]:
    """Validate gate config + per-request confirmation. Returns (dry_run, allow_submit).

    Raises HTTPException 400/403 on policy failure.
    """
    mode = body.run_mode
    if mode == "plan_only":
        return True, False

    if mode == "paper":
        allowed, reasons = can_run_paper_workflow()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "paper_run_blocked_by_gates", "reasons": reasons},
            )
        return False, True

    if mode == "live":
        allowed, reasons = can_run_live_workflow()
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "live_run_blocked_by_gates", "reasons": reasons},
            )
        if not bool(body.confirm_live):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "live_run_requires_confirm_live", "reasons": ["confirm_live=true required for live run"]},
            )
        phrase = (body.confirm_live_phrase or "").strip()
        if phrase != "LIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "live_run_requires_confirm_phrase",
                    "reasons": ["confirm_live_phrase must equal the literal string 'LIVE'"],
                },
            )
        return False, True

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"error": "unknown_run_mode", "reasons": [f"unknown run_mode={mode!r}"]},
    )


@router.post("/workflow/run", dependencies=[Depends(require_ops_admin_token)])
def post_daytrading_workflow_run(body: DayTradingWorkflowRunBody) -> dict[str, Any]:
    """Start a workflow run.

    Protected by ``OPS_ADMIN_TOKEN``. ``run_mode`` controls execution:
    ``plan_only`` (dry run), ``paper`` (paper simulator), or ``live`` (broker).
    Live mode also requires ``confirm_live=true`` and
    ``confirm_live_phrase='LIVE'`` plus live gates already enabled.
    """
    dry_run, allow_submit = _validate_workflow_run_mode(body)
    req = OrchestratorRunRequest(
        dry_run=dry_run if body.run_mode != "plan_only" or body.dry_run else True,
        allow_submit=allow_submit if body.run_mode != "plan_only" else False,
        symbols=_normalize_symbols(body.symbols),
        source=body.source,
        mode={
            "plan_only": "paper_first",
            "paper": "paper_first",
            "live": "live",
        }[body.run_mode],
    )
    try:
        run = run_workflow(req)
    except Exception:
        logger.exception("daytrading v1 workflow run failed")
        raise
    data = run.model_dump()
    return {
        "status": run.status,
        "run_mode": body.run_mode,
        "requested_by_email": (body.requested_by_email or "").strip() or None,
        "recommendation": run.recommendation,
        "submitted_order": run.submitted_order,
        "broker_called": run.broker_called,
        "llm_used": run.llm_used,
        "blockers": run.blockers,
        "warnings": run.warnings,
        "run": data,
    }


# ---------------------------------------------------------------------------
# Trading gates: settings UI + audit
# ---------------------------------------------------------------------------


class GateMutationContext(BaseModel):
    """Read-only metadata returned alongside the gate snapshot."""

    model_config = ConfigDict(extra="forbid")

    ops_admin_token_configured: bool
    paper_run_allowed: bool
    paper_run_block_reasons: list[str]
    live_run_allowed: bool
    live_run_block_reasons: list[str]


class TradingGatesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    gates: TradingGatesSnapshot
    context: GateMutationContext


def _build_gates_response() -> TradingGatesResponse:
    snapshot = get_trading_gates()
    paper_ok, paper_reasons = can_run_paper_workflow()
    live_ok, live_reasons = can_run_live_workflow()
    return TradingGatesResponse(
        gates=snapshot,
        context=GateMutationContext(
            ops_admin_token_configured=ops_admin_token_configured(),
            paper_run_allowed=paper_ok,
            paper_run_block_reasons=paper_reasons,
            live_run_allowed=live_ok,
            live_run_block_reasons=live_reasons,
        ),
    )


@router.get("/settings/gates", response_model=TradingGatesResponse)
def get_daytrading_settings_gates() -> TradingGatesResponse:
    """Read-only view of effective trading gates + run permissions."""
    return _build_gates_response()


@router.put(
    "/settings/gates",
    response_model=TradingGatesResponse,
    dependencies=[Depends(require_ops_admin_token)],
)
def put_daytrading_settings_gates(
    body: TradingGatesUpdate,
    x_ops_admin_email: str | None = Header(default=None, alias="X-Ops-Admin-Email"),
) -> TradingGatesResponse:
    """Update trading gates.

    Protected by ``OPS_ADMIN_TOKEN``. Enabling ``live_trading_enabled``
    additionally requires ``confirm_live=true`` in the request body. All
    safety invariants are enforced server-side. The audit trail captures
    ``updated_at``, ``updated_by_email``, and ``change_reason``. The Next.js
    proxy passes the NextAuth email via ``X-Ops-Admin-Email`` so the audit
    trail records the actual signed-in operator.
    """
    email = (x_ops_admin_email or "").strip() or None
    try:
        update_trading_gates(body, updated_by_email=email)
    except GateValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "gate_validation_failed", "reasons": [str(exc)]},
        ) from exc
    return _build_gates_response()


@router.get("/workflow/latest")
def get_daytrading_workflow_latest() -> dict[str, Any]:
    run = get_latest_orchestrator_run()
    return {"status": "ok", "run": run.model_dump() if run else None}


@router.get("/recommendation/latest")
def get_daytrading_recommendation_latest() -> dict[str, Any]:
    run = get_latest_orchestrator_run()
    if run is None:
        return {
            "status": "ok",
            "recommendation": None,
            "alpha_recommendation": None,
            "run": None,
        }
    data = run.model_dump()
    rec = data.get("recommendation") if isinstance(data.get("recommendation"), dict) else {}
    alpha = data.get("alpha_recommendation") if isinstance(data.get("alpha_recommendation"), dict) else {}
    return {
        "status": "ok",
        "recommendation": rec or None,
        "alpha_recommendation": alpha or None,
        "selected_symbol": data.get("alpha_selected_symbol") or data.get("selected_symbol"),
        "run": {
            "selected_symbol": data.get("selected_symbol"),
            "alpha_selected_symbol": data.get("alpha_selected_symbol"),
            "strategy_key": data.get("strategy_key"),
            "selected_strategy_key": data.get("selected_strategy_key"),
            "alpha_strategy_key": data.get("alpha_strategy_key"),
            "final_score": data.get("final_score"),
            "alpha_score": data.get("alpha_score"),
            "expected_return": data.get("expected_return"),
            "blockers": data.get("blockers"),
            "warnings": data.get("warnings"),
        },
    }


@router.get("/evidence/strategies")
def get_daytrading_evidence_strategies() -> dict[str, Any]:
    return get_promotion_strategies_status().model_dump()


@router.get("/evidence/models")
def get_daytrading_evidence_models() -> dict[str, Any]:
    return get_promotion_models_status().model_dump()


@router.get("/risk/status")
def get_daytrading_risk_status() -> dict[str, Any]:
    run = get_latest_orchestrator_run()
    if run is None:
        return {
            "status": "ok",
            "run": None,
            "recommendation": None,
            "max_risk_dollars": None,
            "position_size": None,
            "small_account_decision": None,
            "max_daily_loss_dollars": None,
            "feasible_symbols": [],
            "rejected_symbols": [],
        }
    data = run.model_dump()
    rec = data.get("recommendation") if isinstance(data.get("recommendation"), dict) else {}
    return {
        "status": "ok",
        "run": {
            "max_risk_dollars": data.get("max_risk_dollars"),
            "position_size": data.get("position_size"),
            "small_account_decision": data.get("small_account_decision"),
            "max_daily_loss_dollars": data.get("max_daily_loss_dollars"),
            "feasible_symbols": data.get("feasible_symbols"),
            "rejected_symbols": data.get("rejected_symbols") or data.get("small_account_rejected_symbols"),
            "small_account_blockers": data.get("small_account_blockers"),
        },
        "recommendation": rec,
        "max_risk_dollars": data.get("max_risk_dollars"),
        "position_size": data.get("position_size"),
        "small_account_decision": data.get("small_account_decision"),
        "max_daily_loss_dollars": data.get("max_daily_loss_dollars"),
        "feasible_symbols": data.get("feasible_symbols"),
        "rejected_symbols": data.get("rejected_symbols") or data.get("small_account_rejected_symbols"),
    }


@router.get("/execution-boundary")
def get_daytrading_execution_boundary() -> dict[str, Any]:
    platform = get_platform_readiness_status()
    systems = platform.get("systems") if isinstance(platform.get("systems"), dict) else {}
    gates = systems.get("execution_gates") if isinstance(systems.get("execution_gates"), dict) else {}
    run = get_latest_orchestrator_run()
    data = run.model_dump() if run else {}
    return {
        "status": "ok",
        "data_mode": "daytrading_v1_execution_boundary",
        "execution_gates": gates,
        "from_latest_workflow": {
            "broker_called": data.get("broker_called"),
            "submitted_order": data.get("submitted_order"),
            "allow_submit": data.get("allow_submit"),
            "approval_required": data.get("approval_required"),
            "llm_used": data.get("llm_used"),
            "using_non_real_data": data.get("using_non_real_data"),
        },
    }


@router.get("/contracts/routes")
def get_daytrading_contracts_routes() -> dict[str, Any]:
    return contracts_routes_payload()
