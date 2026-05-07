from __future__ import annotations

from datetime import datetime, timezone

from app.services.strategy_evidence.models import (
    StrategyEvidenceCreate,
    StrategyEvidenceOut,
    StrategyEvidenceStatusResponse,
    iso_utc_now,
    new_evidence_id,
)

_MEMORY: dict[str, StrategyEvidenceOut] = {}


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


def get_strategy_evidence_status() -> StrategyEvidenceStatusResponse:
    session = _db_session()
    persistence_mode = "memory"
    count = len(_MEMORY)
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import StrategyEvidenceRecord

            count = int(session.execute(select(func.count()).select_from(StrategyEvidenceRecord)).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    return StrategyEvidenceStatusResponse(updated_at=iso_utc_now(), summary={"persistence_mode": persistence_mode, "records_count": count})


def save_strategy_evidence(body: StrategyEvidenceCreate) -> StrategyEvidenceOut:
    now = iso_utc_now()
    evidence_id = body.evidence_id or new_evidence_id()
    out = StrategyEvidenceOut(
        evidence_id=evidence_id,
        strategy_key=body.strategy_key,
        strategy_group=body.strategy_group,
        asset_class=body.asset_class,
        horizon=body.horizon,
        status=body.status,
        strategy_score=body.strategy_score,
        regime_fit=body.regime_fit,
        proof_status=body.proof_status,
        selected_model_keys=list(body.selected_model_keys or []),
        scanner_needs=list(body.scanner_needs or []),
        data_needs=list(body.data_needs or []),
        metrics=dict(body.metrics or {}),
        blockers=list(body.blockers or []),
        warnings=list(body.warnings or []),
        created_at=now,
        updated_at=now,
    )

    session = _db_session()
    if session is not None:
        try:
            from app.db.models import StrategyEvidenceRecord as Row

            row = Row(
                evidence_id=out.evidence_id,
                strategy_key=out.strategy_key,
                strategy_group=out.strategy_group,
                asset_class=out.asset_class,
                horizon=out.horizon,
                status=out.status,
                strategy_score=out.strategy_score,
                regime_fit=out.regime_fit,
                proof_status=out.proof_status,
                selected_model_keys=out.selected_model_keys,
                scanner_needs=out.scanner_needs,
                data_needs=out.data_needs,
                metrics=out.metrics,
                blockers=out.blockers,
                warnings=out.warnings,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            session.merge(row)
            session.commit()
            _MEMORY[out.evidence_id] = out
            return out
        except Exception:
            try:
                session.rollback()
            except Exception:
                pass
        finally:
            session.close()

    _MEMORY[out.evidence_id] = out
    return out


def list_strategy_evidence(limit: int = 50) -> list[StrategyEvidenceOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import StrategyEvidenceRecord as Row

            rows = session.execute(select(Row).order_by(Row.updated_at.desc()).limit(limit)).scalars().all()
            out: list[StrategyEvidenceOut] = []
            for r in rows:
                out.append(
                    StrategyEvidenceOut(
                        evidence_id=r.evidence_id,
                        strategy_key=r.strategy_key,
                        strategy_group=r.strategy_group,
                        asset_class=r.asset_class,
                        horizon=r.horizon,
                        status=r.status,
                        strategy_score=r.strategy_score,
                        regime_fit=r.regime_fit,
                        proof_status=r.proof_status,
                        selected_model_keys=list(r.selected_model_keys or []),
                        scanner_needs=list(r.scanner_needs or []),
                        data_needs=list(r.data_needs or []),
                        metrics=r.metrics or {},
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


def get_latest_strategy_evidence() -> StrategyEvidenceOut | None:
    items = list_strategy_evidence(limit=1)
    return items[0] if items else None

