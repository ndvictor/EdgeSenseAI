from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.proof_registry.models import (
    ProofRegistryRecordCreate,
    ProofRegistryRecordOut,
    ProofRegistryStatusResponse,
    iso_utc_now,
    new_proof_id,
)

_MEMORY: dict[str, ProofRegistryRecordOut] = {}


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def evaluate_proof_status(record_or_metrics: Any) -> dict[str, Any]:
    """Normalize proof metrics into paper-first evidence status; never invent proof."""
    data = record_or_metrics.model_dump() if hasattr(record_or_metrics, "model_dump") else dict(record_or_metrics or {})
    blockers = [str(x) for x in data.get("blockers", []) if x]
    warnings = [str(x) for x in data.get("warnings", []) if x]
    existing_status = str(data.get("proof_status") or "").strip()

    if existing_status == "research_only" or data.get("evidence_type") == "research_only":
        return {"proof_status": "research_only", "blockers": blockers, "warnings": warnings, "next_action": "Research-only evidence cannot promote strategy proof."}

    sample_size = int(data.get("sample_size") or data.get("trades") or 0)
    avg_r = _float_or_none(data.get("avg_r_multiple"))
    max_dd = _float_or_none(data.get("max_drawdown_r"))
    rule_violation = _float_or_none(data.get("rule_violation_rate")) or 0.0
    slippage_fail = _float_or_none(data.get("slippage_fail_rate"))
    win_rate = _float_or_none(data.get("win_rate"))
    sharpe = _float_or_none(data.get("sharpe_ratio"))

    if rule_violation > 0:
        blockers.append("rule_violation_rate_positive")
    if max_dd is not None and max_dd <= -8:
        blockers.append("max_drawdown_too_severe")
    if blockers:
        return {
            "proof_status": "blocked",
            "sample_size": sample_size,
            "win_rate": win_rate,
            "avg_r_multiple": avg_r,
            "sharpe_ratio": sharpe,
            "max_drawdown_r": max_dd,
            "slippage_fail_rate": slippage_fail,
            "rule_violation_rate": rule_violation,
            "blockers": sorted(set(blockers)),
            "warnings": sorted(set(warnings)),
            "next_action": "Resolve proof blockers before eligibility checks.",
        }

    has_metrics = sample_size > 0 or avg_r is not None or max_dd is not None
    if not has_metrics:
        status = "backtest_required" if data.get("strategy_key") or data.get("model_key") else "proof_required"
        warnings.append("proof_metrics_missing")
    elif sample_size >= 100 and (avg_r or 0) > 0.10 and (max_dd is None or max_dd > -8) and rule_violation == 0:
        status = "proven"
    elif sample_size >= 30 and (avg_r or 0) > 0.05 and (max_dd is None or max_dd > -5) and rule_violation == 0:
        status = "paper_passed"
    else:
        status = "proof_required"
        warnings.append("proof_sample_or_quality_below_threshold")

    return {
        "proof_status": status,
        "sample_size": sample_size,
        "win_rate": win_rate,
        "avg_r_multiple": avg_r,
        "sharpe_ratio": sharpe,
        "max_drawdown_r": max_dd,
        "slippage_fail_rate": slippage_fail,
        "rule_violation_rate": rule_violation,
        "blockers": sorted(set(blockers)),
        "warnings": sorted(set(warnings)),
        "next_action": "Proceed to strategy eligibility checks." if status in {"proven", "paper_passed"} else "Record more backtest or paper evidence before proof-dependent promotion.",
    }


def _db_session():
    try:
        from app.db.init_db import init_db
        from app.db.session import open_session

        init_db()
        return open_session()
    except Exception:
        return None


def _dt_to_iso(dt: datetime | None) -> str:
    if not dt:
        return iso_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def get_proof_registry_status() -> ProofRegistryStatusResponse:
    session = _db_session()
    persistence_mode = "memory"
    count = len(_MEMORY)
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import ProofRegistryRecord

            count = int(session.execute(select(func.count()).select_from(ProofRegistryRecord)).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    latest = get_latest_proof_record()
    return ProofRegistryStatusResponse(
        updated_at=iso_utc_now(),
        summary={"persistence_mode": persistence_mode, "records_count": count, "llm_used": False, "latest_proof_status": latest.proof_status if latest else "none"},
    )


def save_proof_record(body: ProofRegistryRecordCreate) -> ProofRegistryRecordOut:
    now = iso_utc_now()
    proof_id = body.proof_id or new_proof_id()
    decision = evaluate_proof_status(body)
    out = ProofRegistryRecordOut(
        proof_id=proof_id,
        symbol=body.symbol.upper(),
        asset_class=body.asset_class,
        horizon=body.horizon,
        strategy_key=body.strategy_key,
        model_key=body.model_key,
        proof_type=body.proof_type,
        proof_status=decision["proof_status"],
        sample_size=int(body.sample_size),
        win_rate=float(body.win_rate),
        avg_r_multiple=float(body.avg_r_multiple),
        sharpe_ratio=body.sharpe_ratio,
        max_drawdown_r=body.max_drawdown_r,
        slippage_fail_rate=body.slippage_fail_rate,
        rule_violation_rate=body.rule_violation_rate,
        backtest_run_id=body.backtest_run_id,
        paper_run_id=body.paper_run_id,
        source=body.source,
        evidence=dict(body.evidence or {}),
        blockers=list(decision.get("blockers") or []),
        warnings=list(decision.get("warnings") or []),
        created_at=now,
        updated_at=now,
    )

    session = _db_session()
    if session is not None:
        try:
            from app.db.models import ProofRegistryRecord as ProofRow

            row = ProofRow(
                proof_id=out.proof_id,
                symbol=out.symbol,
                asset_class=out.asset_class,
                horizon=out.horizon,
                strategy_key=out.strategy_key,
                model_key=out.model_key,
                proof_type=out.proof_type,
                proof_status=out.proof_status,
                sample_size=out.sample_size,
                win_rate=out.win_rate,
                avg_r_multiple=out.avg_r_multiple,
                sharpe_ratio=out.sharpe_ratio,
                max_drawdown_r=out.max_drawdown_r,
                slippage_fail_rate=out.slippage_fail_rate,
                rule_violation_rate=out.rule_violation_rate,
                backtest_run_id=out.backtest_run_id,
                paper_run_id=out.paper_run_id,
                source=out.source,
                evidence=out.evidence,
                blockers=out.blockers,
                warnings=out.warnings,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.merge(row)
            session.commit()
            _MEMORY[out.proof_id] = out
            return out
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    _MEMORY[out.proof_id] = out
    return out


def list_proof_records(limit: int = 50) -> list[ProofRegistryRecordOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import ProofRegistryRecord as ProofRow

            rows = session.execute(select(ProofRow).order_by(ProofRow.updated_at.desc()).limit(limit)).scalars().all()
            out: list[ProofRegistryRecordOut] = []
            for r in rows:
                out.append(
                    ProofRegistryRecordOut(
                        proof_id=r.proof_id,
                        symbol=r.symbol,
                        asset_class=r.asset_class,
                        horizon=r.horizon,
                        strategy_key=r.strategy_key,
                        model_key=r.model_key,
                        proof_type=r.proof_type,
                        proof_status=r.proof_status,
                        sample_size=int(r.sample_size),
                        win_rate=float(r.win_rate),
                        avg_r_multiple=float(r.avg_r_multiple),
                        sharpe_ratio=r.sharpe_ratio,
                        max_drawdown_r=r.max_drawdown_r,
                        slippage_fail_rate=r.slippage_fail_rate,
                        rule_violation_rate=r.rule_violation_rate,
                        backtest_run_id=r.backtest_run_id,
                        paper_run_id=r.paper_run_id,
                        source=r.source,
                        evidence=r.evidence or {},
                        blockers=list(r.blockers or []),
                        warnings=list(r.warnings or []),
                        created_at=_dt_to_iso(getattr(r, "created_at", None)),
                        updated_at=_dt_to_iso(getattr(r, "updated_at", None)),
                    )
                )
            return out
        except Exception:
            return list(_MEMORY.values())[:limit]
        finally:
            session.close()
    return list(_MEMORY.values())[:limit]


def get_latest_proof_record() -> ProofRegistryRecordOut | None:
    items = list_proof_records(limit=1)
    return items[0] if items else None

