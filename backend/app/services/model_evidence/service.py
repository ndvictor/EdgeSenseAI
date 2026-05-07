from __future__ import annotations

from datetime import datetime, timezone

from app.services.model_evidence.models import (
    ModelEvidenceCreate,
    ModelEvidenceOut,
    ModelEvidenceStatusResponse,
    iso_utc_now,
    new_evidence_id,
)

_MEMORY: dict[str, ModelEvidenceOut] = {}


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


def get_model_evidence_status() -> ModelEvidenceStatusResponse:
    session = _db_session()
    persistence_mode = "memory"
    count = len(_MEMORY)
    if session is not None:
        try:
            from sqlalchemy import func, select

            from app.db.models import ModelEvidenceRecord

            count = int(session.execute(select(func.count()).select_from(ModelEvidenceRecord)).scalar() or 0)
            persistence_mode = "postgres"
        except Exception:
            persistence_mode = "memory"
        finally:
            session.close()
    return ModelEvidenceStatusResponse(updated_at=iso_utc_now(), summary={"persistence_mode": persistence_mode, "records_count": count})


def save_model_evidence(body: ModelEvidenceCreate) -> ModelEvidenceOut:
    now = iso_utc_now()
    evidence_id = body.evidence_id or new_evidence_id()
    out = ModelEvidenceOut(
        evidence_id=evidence_id,
        model_key=body.model_key,
        model_name=body.model_name,
        model_family=body.model_family,
        asset_class=body.asset_class,
        horizon=body.horizon,
        status=body.status,
        score=body.score,
        confidence=body.confidence,
        rank=body.rank,
        drift_status=body.drift_status,
        training_status=body.training_status,
        backtest_status=body.backtest_status,
        paper_status=body.paper_status,
        qlib_artifact_id=body.qlib_artifact_id,
        metrics=dict(body.metrics or {}),
        blockers=list(body.blockers or []),
        warnings=list(body.warnings or []),
        created_at=now,
        updated_at=now,
    )

    session = _db_session()
    if session is not None:
        try:
            from app.db.models import ModelEvidenceRecord as Row

            row = Row(
                evidence_id=out.evidence_id,
                model_key=out.model_key,
                model_name=out.model_name,
                model_family=out.model_family,
                asset_class=out.asset_class,
                horizon=out.horizon,
                status=out.status,
                score=out.score,
                confidence=out.confidence,
                rank=out.rank,
                drift_status=out.drift_status,
                training_status=out.training_status,
                backtest_status=out.backtest_status,
                paper_status=out.paper_status,
                qlib_artifact_id=out.qlib_artifact_id,
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


def list_model_evidence(limit: int = 50) -> list[ModelEvidenceOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import ModelEvidenceRecord as Row

            rows = session.execute(select(Row).order_by(Row.updated_at.desc()).limit(limit)).scalars().all()
            out: list[ModelEvidenceOut] = []
            for r in rows:
                out.append(
                    ModelEvidenceOut(
                        evidence_id=r.evidence_id,
                        model_key=r.model_key,
                        model_name=r.model_name,
                        model_family=r.model_family,
                        asset_class=r.asset_class,
                        horizon=r.horizon,
                        status=r.status,
                        score=r.score,
                        confidence=r.confidence,
                        rank=r.rank,
                        drift_status=r.drift_status,
                        training_status=r.training_status,
                        backtest_status=r.backtest_status,
                        paper_status=r.paper_status,
                        qlib_artifact_id=r.qlib_artifact_id,
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


def get_latest_model_evidence() -> ModelEvidenceOut | None:
    items = list_model_evidence(limit=1)
    return items[0] if items else None

