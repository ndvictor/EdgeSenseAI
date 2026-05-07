"""Qlib integration (Phase 3): store metadata/path refs, never require Qlib to be installed."""

from .models import (
    QlibArtifactCreate,
    QlibArtifactOut,
    QlibBacktestRecordCreate,
    QlibModelArtifactRegisterCreate,
    QlibSignalScoreCreate,
    QlibStatusResponse,
)
from .service import (
    get_latest_signal_scores,
    get_qlib_status,
    list_artifacts,
    record_backtest_artifact,
    register_model_artifact,
    save_signal_scores,
)

__all__ = [
    "QlibStatusResponse",
    "QlibSignalScoreCreate",
    "QlibBacktestRecordCreate",
    "QlibModelArtifactRegisterCreate",
    "QlibArtifactCreate",
    "QlibArtifactOut",
    "get_qlib_status",
    "list_artifacts",
    "get_latest_signal_scores",
    "save_signal_scores",
    "record_backtest_artifact",
    "register_model_artifact",
]

