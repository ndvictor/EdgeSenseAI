from __future__ import annotations

from datetime import datetime, timezone

from app.services.qlib_integration.models import (
    QlibArtifactCreate,
    QlibArtifactOut,
    QlibBacktestRecordCreate,
    QlibModelArtifactRegisterCreate,
    QlibSignalScoreCreate,
    QlibStatusResponse,
    iso_utc_now,
    new_artifact_id,
)

_MEMORY: dict[str, QlibArtifactOut] = {}


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


def _probe_qlib() -> tuple[bool, str | None, list[str]]:
    """Detect Qlib availability without requiring it for startup/tests."""
    try:
        import importlib

        qlib = importlib.import_module("qlib")
        version = getattr(qlib, "__version__", None)
        return True, str(version) if version else None, []
    except Exception as exc:
        return False, None, [f"qlib_unavailable: {exc}"]


def get_qlib_status() -> QlibStatusResponse:
    available, version, blockers = _probe_qlib()
    return QlibStatusResponse(
        updated_at=iso_utc_now(),
        qlib_available=bool(available),
        qlib_version=version,
        summary={"artifacts_cached": len(_MEMORY)},
        blockers=blockers,
        warnings=[],
    )


def _save_artifact_row(out: QlibArtifactOut) -> None:
    session = _db_session()
    if session is None:
        _MEMORY[out.artifact_id] = out
        return
    try:
        from app.db.models import QlibArtifactRecord as Row

        row = Row(
            artifact_id=out.artifact_id,
            artifact_type=out.artifact_type,
            model_key=out.model_key,
            strategy_key=out.strategy_key,
            symbol=out.symbol,
            asset_class=out.asset_class,
            horizon=out.horizon,
            qlib_available=out.qlib_available,
            qlib_version=out.qlib_version,
            artifact_status=out.artifact_status,
            artifact_path=out.artifact_path,
            metrics=out.metrics,
            scores=out.scores,
            metadata_json=out.metadata,
            blockers=out.blockers,
            warnings=out.warnings,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.merge(row)
        session.commit()
        _MEMORY[out.artifact_id] = out
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
        _MEMORY[out.artifact_id] = out
    finally:
        session.close()


def record_artifact(body: QlibArtifactCreate) -> QlibArtifactOut:
    now = iso_utc_now()
    artifact_id = body.artifact_id or new_artifact_id("qa")
    out = QlibArtifactOut(
        artifact_id=artifact_id,
        artifact_type=body.artifact_type,
        model_key=body.model_key,
        strategy_key=body.strategy_key,
        symbol=body.symbol.upper() if isinstance(body.symbol, str) else None,
        asset_class=body.asset_class,
        horizon=body.horizon,
        qlib_available=bool(body.qlib_available),
        qlib_version=body.qlib_version,
        artifact_status=body.artifact_status,
        artifact_path=body.artifact_path,
        metrics=dict(body.metrics or {}),
        scores=dict(body.scores or {}),
        metadata=dict(body.metadata or {}),
        blockers=list(body.blockers or []),
        warnings=list(body.warnings or []),
        created_at=now,
        updated_at=now,
    )
    _save_artifact_row(out)
    return out


def list_artifacts(limit: int = 50) -> list[QlibArtifactOut]:
    session = _db_session()
    if session is not None:
        try:
            from sqlalchemy import select

            from app.db.models import QlibArtifactRecord as Row

            rows = session.execute(select(Row).order_by(Row.created_at.desc()).limit(limit)).scalars().all()
            out: list[QlibArtifactOut] = []
            for r in rows:
                out.append(
                    QlibArtifactOut(
                        artifact_id=r.artifact_id,
                        artifact_type=r.artifact_type,
                        model_key=r.model_key,
                        strategy_key=r.strategy_key,
                        symbol=r.symbol,
                        asset_class=r.asset_class,
                        horizon=r.horizon,
                        qlib_available=bool(r.qlib_available),
                        qlib_version=r.qlib_version,
                        artifact_status=r.artifact_status,
                        artifact_path=r.artifact_path,
                        metrics=r.metrics or {},
                        scores=r.scores or {},
                        metadata=r.metadata_json or {},
                        blockers=list(r.blockers or []),
                        warnings=list(r.warnings or []),
                        created_at=_dt_to_iso(getattr(r, "created_at", None)),
                        updated_at=_dt_to_iso(getattr(r, "updated_at", None)),
                    )
                )
            for a in out:
                _MEMORY[a.artifact_id] = a
            return out
        except Exception:
            return list(_MEMORY.values())[:limit]
        finally:
            session.close()
    return list(_MEMORY.values())[:limit]


def get_latest_signal_scores() -> QlibArtifactOut | None:
    items = [a for a in list_artifacts(limit=50) if a.artifact_type == "signal_scores"]
    return items[0] if items else None


def save_signal_scores(body: QlibSignalScoreCreate) -> QlibArtifactOut:
    available, version, blockers = _probe_qlib()
    return record_artifact(
        QlibArtifactCreate(
            artifact_id=body.artifact_id or new_artifact_id("qs"),
            artifact_type="signal_scores",
            model_key=body.model_key,
            strategy_key=body.strategy_key,
            symbol=body.symbol,
            asset_class=body.asset_class,
            horizon=body.horizon,
            qlib_available=bool(available),
            qlib_version=version,
            artifact_status="recorded",
            artifact_path=None,
            metrics=body.metrics,
            scores=body.scores,
            metadata={**(body.metadata or {}), "source": body.source},
            blockers=blockers,
            warnings=[],
        )
    )


def record_backtest_artifact(body: QlibBacktestRecordCreate) -> QlibArtifactOut:
    available, version, blockers = _probe_qlib()
    return record_artifact(
        QlibArtifactCreate(
            artifact_id=body.artifact_id or new_artifact_id("qb"),
            artifact_type="backtest",
            model_key=body.model_key,
            strategy_key=body.strategy_key,
            symbol=body.symbol,
            asset_class=body.asset_class,
            horizon=body.horizon,
            qlib_available=bool(available),
            qlib_version=version,
            artifact_status="recorded",
            artifact_path=body.artifact_path,
            metrics=body.metrics,
            scores={},
            metadata={**(body.metadata or {}), "source": body.source},
            blockers=blockers,
            warnings=[],
        )
    )


def register_model_artifact(body: QlibModelArtifactRegisterCreate) -> QlibArtifactOut:
    available, version, blockers = _probe_qlib()
    return record_artifact(
        QlibArtifactCreate(
            artifact_id=body.artifact_id or new_artifact_id("qm"),
            artifact_type="model_artifact",
            model_key=body.model_key,
            strategy_key=None,
            symbol=None,
            asset_class=body.asset_class,
            horizon=body.horizon,
            qlib_available=bool(available),
            qlib_version=version,
            artifact_status="registered",
            artifact_path=body.artifact_path,
            metrics=body.metrics,
            scores={},
            metadata={**(body.metadata or {}), "source": body.source, "model_name": body.model_name},
            blockers=blockers,
            warnings=[],
        )
    )

