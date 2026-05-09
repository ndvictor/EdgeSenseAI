from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime, timezone
from typing import Any

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
_JOB_MEMORY: dict[str, dict[str, Any]] = {}


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
    try:
        import importlib

        qlib = importlib.import_module("qlib")
        version = getattr(qlib, "__version__", None)
        return True, str(version) if version else None, []
    except Exception as exc:
        return False, None, ["qlib_not_installed_or_not_configured", f"qlib_unavailable: {exc}"]


def _normalize_artifact_type(value: str | None) -> str:
    raw = (value or "report").lower().strip()
    mapping = {
        "signal_scores": "signal_scores",
        "signals": "signal_scores",
        "score": "signal_scores",
        "model_artifact": "model",
        "model_artifacts": "model",
        "backtests": "backtest",
    }
    normalized = mapping.get(raw, raw)
    return normalized if normalized in {"signal", "signal_scores", "backtest", "model", "dataset", "report"} else "report"


def _normalize_artifact_status(value: str | None, *, qlib_available: bool, blockers: list[str]) -> str:
    raw = (value or "recorded").lower().strip()
    mapping = {"completed": "ready", "registered": "ready", "ok": "ready"}
    normalized = mapping.get(raw, raw)
    if normalized == "unavailable":
        return "unavailable"
    if blockers and normalized not in {"simulated", "recorded"}:
        return "failed" if qlib_available else "unavailable"
    return normalized if normalized in {"ready", "unavailable", "failed", "recorded", "simulated"} else "recorded"


def _qlib_runner_status() -> dict[str, Any]:
    available, version, blockers = _probe_qlib()
    qrun_path = shutil.which("qrun")
    config_path = os.getenv("QLIB_DEFAULT_CONFIG_PATH")
    provider_uri = os.getenv("QLIB_PROVIDER_URI")
    execution_enabled = os.getenv("QLIB_EXECUTION_ENABLED", "false").lower() in {"1", "true", "yes", "on"}

    runner_blockers = list(blockers)
    if not execution_enabled:
        runner_blockers.append("qlib_execution_disabled")
    if not qrun_path:
        runner_blockers.append("qrun_not_found")
    if not config_path:
        runner_blockers.append("qlib_default_config_path_missing")
    elif not os.path.exists(config_path):
        runner_blockers.append("qlib_default_config_path_not_found")
    if not provider_uri:
        runner_blockers.append("qlib_provider_uri_missing")

    return {
        "qlib_available": available,
        "qlib_version": version,
        "qrun_path": qrun_path,
        "default_config_path": config_path,
        "provider_uri": provider_uri,
        "execution_enabled": execution_enabled,
        "execution_ready": bool(available and qrun_path and config_path and os.path.exists(config_path) and provider_uri and execution_enabled),
        "blockers": runner_blockers,
    }


def get_qlib_status() -> QlibStatusResponse:
    runner = _qlib_runner_status()
    artifacts = list(_MEMORY.values())
    artifact_count = len(artifacts)
    latest_signal_count = len([a for a in artifacts if _normalize_artifact_type(a.artifact_type) in {"signal", "signal_scores"}])
    latest_backtest_count = len([a for a in artifacts if _normalize_artifact_type(a.artifact_type) == "backtest"])
    latest_model_count = len([a for a in artifacts if _normalize_artifact_type(a.artifact_type) == "model"])
    blockers = list(dict.fromkeys(runner["blockers"]))
    configured = bool(runner["qlib_available"] and runner["provider_uri"])
    next_action = (
        "Qlib is optional and workflow can continue unless selected strategy requires Qlib evidence."
        if not runner["qlib_available"]
        else "Review registered Qlib artifacts before using Qlib-backed evidence."
    )
    return QlibStatusResponse(
        updated_at=iso_utc_now(),
        qlib_available=bool(runner["qlib_available"]),
        qlib_version=runner["qlib_version"],
        configured=configured,
        artifact_count=artifact_count,
        latest_signal_count=latest_signal_count,
        latest_backtest_count=latest_backtest_count,
        latest_model_count=latest_model_count,
        summary={
            "artifacts_cached": artifact_count,
            "jobs_cached": len(_JOB_MEMORY),
            "execution_ready": runner["execution_ready"],
            "execution_enabled": runner["execution_enabled"],
            "qrun_path": runner["qrun_path"],
            "default_config_path": runner["default_config_path"],
            "provider_uri_configured": bool(runner["provider_uri"]),
        },
        blockers=blockers,
        warnings=[] if runner["qlib_available"] else ["qlib_optional_not_required_for_workflow"],
        next_action=next_action,
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
    artifact_type = _normalize_artifact_type(body.artifact_type)
    blockers = list(body.blockers or [])
    artifact_status = _normalize_artifact_status(body.artifact_status, qlib_available=bool(body.qlib_available), blockers=blockers)
    out = QlibArtifactOut(
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        model_key=body.model_key,
        strategy_key=body.strategy_key,
        symbol=body.symbol.upper() if isinstance(body.symbol, str) else None,
        symbols=[str(s).upper() for s in (body.symbols or ([body.symbol] if body.symbol else [])) if s],
        asset_class=body.asset_class,
        horizon=body.horizon,
        qlib_available=bool(body.qlib_available),
        qlib_version=body.qlib_version,
        artifact_status=artifact_status,
        artifact_path=body.artifact_path,
        metrics=dict(body.metrics or {}),
        scores=dict(body.scores or {}),
        metadata=dict(body.metadata or {}),
        blockers=blockers,
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
                        artifact_type=_normalize_artifact_type(r.artifact_type),
                        model_key=r.model_key,
                        strategy_key=r.strategy_key,
                        symbol=r.symbol,
                        symbols=[r.symbol] if r.symbol else [],
                        asset_class=r.asset_class,
                        horizon=r.horizon,
                        qlib_available=bool(r.qlib_available),
                        qlib_version=r.qlib_version,
                        artifact_status=_normalize_artifact_status(r.artifact_status, qlib_available=bool(r.qlib_available), blockers=list(r.blockers or [])),
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
    items = [a for a in list_artifacts(limit=50) if _normalize_artifact_type(a.artifact_type) in {"signal", "signal_scores"}]
    return items[0] if items else None


def save_signal_scores(body: QlibSignalScoreCreate) -> QlibArtifactOut:
    available, version, blockers = _probe_qlib()
    symbols = [str(s).upper() for s in (body.symbols or [body.symbol]) if s]
    scores = dict(body.scores or {})
    warnings: list[str] = []
    artifact_status = "recorded"
    artifact_blockers = list(blockers)
    if not available:
        warnings.append("qlib_unavailable_scores_are_placeholder")
        artifact_status = "simulated" if symbols else "unavailable"
        scores = scores or {symbol: {"score": 0.0, "source": "placeholder_not_trained"} for symbol in symbols}
    elif not any(_normalize_artifact_type(a.artifact_type) == "model" and a.artifact_status in {"ready", "recorded"} for a in list_artifacts(limit=100)):
        artifact_status = "unavailable"
        artifact_blockers.append("no_qlib_model_artifact_registered")
    return record_artifact(
        QlibArtifactCreate(
            artifact_id=body.artifact_id or new_artifact_id("qs"),
            artifact_type="signal_scores",
            model_key=body.model_key,
            strategy_key=body.strategy_key,
            symbol=symbols[0] if symbols else body.symbol,
            symbols=symbols,
            asset_class=body.asset_class,
            horizon=body.horizon,
            qlib_available=bool(available),
            qlib_version=version,
            artifact_status=artifact_status,
            artifact_path=None,
            metrics=body.metrics,
            scores=scores,
            metadata={**(body.metadata or {}), "source": body.source, "trained_model_backed": bool(available and artifact_status == "recorded")},
            blockers=artifact_blockers,
            warnings=warnings,
        )
    )


def _proof_status_from_metrics(metrics: dict[str, Any], blockers: list[str]) -> str:
    if blockers:
        return "blocked"
    sharpe = metrics.get("sharpe") or metrics.get("sharpe_ratio") or metrics.get("net_sharpe")
    max_dd = metrics.get("max_drawdown_r") or metrics.get("max_drawdown")
    try:
        sharpe_ok = float(sharpe) >= 0.5 if sharpe is not None else False
    except Exception:
        sharpe_ok = False
    try:
        dd_ok = abs(float(max_dd)) <= 3.0 if max_dd is not None else True
    except Exception:
        dd_ok = True
    return "passed" if sharpe_ok and dd_ok else "needs_review"


def _link_backtest_to_proof(artifact: QlibArtifactOut) -> dict[str, Any] | None:
    try:
        from app.services.proof_registry.models import ProofRegistryRecordCreate
        from app.services.proof_registry.service import save_proof_record

        metrics = artifact.metrics or {}
        proof = save_proof_record(
            ProofRegistryRecordCreate(
                symbol=artifact.symbol or "MULTI",
                asset_class=artifact.asset_class,
                horizon=artifact.horizon,
                strategy_key=artifact.strategy_key or "unknown_strategy",
                model_key=artifact.model_key,
                proof_type="qlib_backtest",
                proof_status=_proof_status_from_metrics(metrics, artifact.blockers),
                sample_size=int(metrics.get("sample_size") or metrics.get("trades") or 0),
                win_rate=float(metrics.get("win_rate") or 0.0),
                avg_r_multiple=float(metrics.get("avg_r_multiple") or 0.0),
                sharpe_ratio=metrics.get("sharpe_ratio") or metrics.get("sharpe") or metrics.get("net_sharpe"),
                max_drawdown_r=metrics.get("max_drawdown_r") or metrics.get("max_drawdown"),
                slippage_fail_rate=metrics.get("slippage_fail_rate"),
                rule_violation_rate=metrics.get("rule_violation_rate"),
                backtest_run_id=artifact.artifact_id,
                source="qlib_integration",
                evidence={"qlib_artifact_id": artifact.artifact_id, "artifact_path": artifact.artifact_path, "metadata": artifact.metadata},
                blockers=artifact.blockers,
                warnings=artifact.warnings,
            )
        )
        return proof.model_dump()
    except Exception as exc:
        return {"status": "proof_link_failed", "error": str(exc)}


def record_backtest_artifact(body: QlibBacktestRecordCreate) -> QlibArtifactOut:
    available, version, blockers = _probe_qlib()
    artifact = record_artifact(
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
            artifact_status="recorded" if available else "unavailable",
            artifact_path=body.artifact_path,
            metrics=body.metrics,
            scores={},
            metadata={**(body.metadata or {}), "source": body.source},
            blockers=blockers,
            warnings=[],
        )
    )
    proof = _link_backtest_to_proof(artifact)
    if proof:
        artifact.metadata["proof_record"] = proof
    return artifact


def register_model_artifact(body: QlibModelArtifactRegisterCreate) -> QlibArtifactOut:
    available, version, blockers = _probe_qlib()
    return record_artifact(
        QlibArtifactCreate(
            artifact_id=body.artifact_id or new_artifact_id("qm"),
                artifact_type="model",
            model_key=body.model_key,
            strategy_key=None,
            symbol=None,
            asset_class=body.asset_class,
            horizon=body.horizon,
            qlib_available=bool(available),
            qlib_version=version,
            artifact_status="ready" if available else "unavailable",
            artifact_path=body.artifact_path,
            metrics=body.metrics,
            scores={},
            metadata={**(body.metadata or {}), "source": body.source, "model_name": body.model_name},
            blockers=blockers,
            warnings=[],
        )
    )


def get_qlib_automation_status() -> dict[str, Any]:
    st = get_qlib_status()
    summary = dict(st.summary or {})
    return {
        "status": "ok",
        "qlib_available": bool(st.qlib_available),
        "qlib_version": st.qlib_version,
        "execution_mode": "ready" if summary.get("execution_ready") else "blocked",
        "execution_ready": bool(summary.get("execution_ready")),
        "execution_enabled": bool(summary.get("execution_enabled")),
        "jobs_cached": len(_JOB_MEMORY),
        "blockers": st.blockers,
        "warnings": st.warnings,
        "artifact_count": st.artifact_count,
        "latest_signal_count": st.latest_signal_count,
        "latest_backtest_count": st.latest_backtest_count,
        "latest_model_count": st.latest_model_count,
        "next_action": st.next_action,
    }


def _new_job_id(prefix: str = "qjob") -> str:
    return f"{prefix}_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{len(_JOB_MEMORY)+1}"


def list_qlib_jobs(limit: int = 50) -> list[dict[str, Any]]:
    return list(_JOB_MEMORY.values())[-limit:]


def get_qlib_job(job_id: str) -> dict[str, Any] | None:
    return _JOB_MEMORY.get(job_id)


def _blocked_job(job_type: str, payload: dict[str, Any], blockers: list[str]) -> dict[str, Any]:
    job_id = _new_job_id("qblocked")
    job = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "blocked",
        "execution_mode": "blocked",
        "payload": payload,
        "blockers": blockers,
        "warnings": [],
        "artifact": None,
        "proof_record": None,
        "created_at": iso_utc_now(),
        "completed_at": iso_utc_now(),
    }
    _JOB_MEMORY[job_id] = job
    return job


def _run_qrun_job(job_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    runner = _qlib_runner_status()
    if not runner["execution_ready"]:
        return _blocked_job(job_type, payload, list(runner["blockers"]))

    config_path = str(payload.get("config_path") or runner["default_config_path"])
    timeout_seconds = int(payload.get("timeout_seconds") or os.getenv("QLIB_JOB_TIMEOUT_SECONDS", "300"))
    job_id = _new_job_id("qrun")
    started_at = iso_utc_now()
    job = {
        "job_id": job_id,
        "job_type": job_type,
        "status": "running",
        "execution_mode": "qrun",
        "payload": payload,
        "blockers": [],
        "warnings": [],
        "artifact": None,
        "proof_record": None,
        "created_at": started_at,
        "completed_at": None,
    }
    _JOB_MEMORY[job_id] = job

    try:
        proc = subprocess.run(
            [str(runner["qrun_path"]), config_path],
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        metrics = {
            "returncode": proc.returncode,
            "stdout_tail": (proc.stdout or "")[-4000:],
            "stderr_tail": (proc.stderr or "")[-4000:],
        }
        artifact_status = "completed" if proc.returncode == 0 else "failed"
        artifact = record_artifact(
            QlibArtifactCreate(
                artifact_id=payload.get("artifact_id") or new_artifact_id("qj"),
                artifact_type="backtest" if job_type == "backtest" else "signal",
                model_key=payload.get("model_key"),
                strategy_key=payload.get("strategy_key"),
                symbol=payload.get("symbol"),
                asset_class=payload.get("asset_class") or "stock",
                horizon=payload.get("horizon") or "day_trading",
                qlib_available=True,
                qlib_version=runner["qlib_version"],
                artifact_status=artifact_status,
                artifact_path=payload.get("artifact_path"),
                metrics=metrics if job_type == "backtest" else {},
                scores=payload.get("scores") or {},
                metadata={"job_id": job_id, "config_path": config_path, "source": "qrun"},
                blockers=[] if proc.returncode == 0 else ["qrun_failed"],
                warnings=[],
            )
        )
        proof = _link_backtest_to_proof(artifact) if job_type == "backtest" else None
        job.update({"status": artifact_status, "artifact": artifact.model_dump(), "proof_record": proof, "completed_at": iso_utc_now()})
    except subprocess.TimeoutExpired:
        job.update({"status": "failed", "blockers": ["qrun_timeout"], "completed_at": iso_utc_now()})
    except Exception as exc:
        job.update({"status": "failed", "blockers": [f"qrun_error: {exc}"], "completed_at": iso_utc_now()})
    _JOB_MEMORY[job_id] = job
    return job


def automation_backtest(*, payload: dict[str, Any]) -> dict[str, Any]:
    job = _run_qrun_job("backtest", payload)
    return {"status": job["status"], "job": job, "artifact": job.get("artifact"), "proof_record": job.get("proof_record")}


def automation_score(*, payload: dict[str, Any]) -> dict[str, Any]:
    job = _run_qrun_job("score", payload)
    return {"status": job["status"], "job": job, "artifact": job.get("artifact")}
