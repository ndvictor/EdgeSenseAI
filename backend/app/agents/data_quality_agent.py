from typing import Any

from app.agents.base import AgentRunResult
from app.services.data_quality_service import check_market_data_quality


AGENT_NAME = "Data Quality Agent"


def run_data_quality_agent(input_payload: dict[str, Any]) -> AgentRunResult:
    report = check_market_data_quality(
        input_payload.get("symbol", input_payload.get("ticker", "UNKNOWN")),
        asset_class=input_payload.get("asset_class", "stock"),
        source=input_payload.get("source", input_payload.get("data_source", "auto")),
        snapshot=input_payload.get("snapshot"),
    )
    return AgentRunResult(
        agent_name=AGENT_NAME,
        status="completed" if report.quality_status != "fail" else "blocked",
        summary=f"Data quality {report.quality_status} for {report.ticker}.",
        confidence=0.9 if report.quality_status == "pass" else 0.65 if report.quality_status == "warn" else 0.3,
        warnings=report.warnings,
        errors=report.blockers,
        metadata={"quality_report": report.model_dump()},
        data_source=report.data_source,
    )
