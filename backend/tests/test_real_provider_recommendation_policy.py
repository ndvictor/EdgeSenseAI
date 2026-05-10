from __future__ import annotations

from app.services.workflow_orchestrator.models import OrchestratorRunRequest
import app.services.workflow_orchestrator.service as orchestrator_service


def test_empty_symbols_recommendation_policy_uses_discovery_not_manual_symbol_block(monkeypatch):
    import app.services.agent_runtime.wrappers.glue_agents as glue_agents

    monkeypatch.setattr(
        orchestrator_service,
        "check_governance",
        lambda _req: type(
            "Gov",
            (),
            {
                "decision": "allowed",
                "blockers": [],
                "warnings": [],
                "next_action": "allowed",
                "model_dump": lambda self: {"decision": "allowed", "blockers": [], "warnings": []},
            },
        )(),
    )

    monkeypatch.setattr(
        glue_agents,
        "build_watchlist",
        lambda **_kwargs: {
            "symbols": ["MSFT"],
            "ranked_candidates": [{"symbol": "MSFT", "source_type": "scanner", "provider": "yfinance"}],
            "selected_candidate": "MSFT",
            "candidate_source": "scanner/provider",
            "raw_candidate_count": 1,
            "filtered_candidate_count": 1,
            "blockers": [],
            "warnings": [],
            "next_action": "Proceed to strategy selection.",
        },
    )

    run = orchestrator_service.run_workflow(
        OrchestratorRunRequest(
            source="runtime",
            symbols=[],
            stop_at_stage=6,
            dry_run=True,
            allow_submit=False,
            require_human_approval=True,
        )
    )

    assert "no_symbols_selected" not in run.blockers
    assert run.recommendation["status"] == "candidate_selected"
    assert run.recommendation["symbol"] == "MSFT"
    assert run.recommendation["mock_data_used"] is False
    assert run.recommendation["synthetic_data_used"] is False
