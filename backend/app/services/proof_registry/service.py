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
    return ProofRegistryStatusResponse(
        updated_at=iso_utc_now(),
        summary={"persistence_mode": persistence_mode, "records_count": count, "llm_used": False},
    )


def save_proof_record(body: ProofRegistryRecordCreate) -> ProofRegistryRecordOut:
    now = iso_utc_now()
    proof_id = body.proof_id or new_proof_id()
    out = ProofRegistryRecordOut(
        proof_id=proof_id,
        symbol=body.symbol.upper(),
        asset_class=body.asset_class,
        horizon=body.horizon,
        strategy_key=body.strategy_key,
        model_key=body.model_key,
        proof_type=body.proof_type,
        proof_status=body.proof_status,
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
        blockers=list(body.blockers or []),
        warnings=list(body.warnings or []),
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

