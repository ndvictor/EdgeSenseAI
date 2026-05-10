from __future__ import annotations

from app.services.workflow_orchestrator.models import OrchestratorRunRequest
import app.services.workflow_orchestrator.service as orchestrator_service


def test_empty_symbol_production_run_keeps_mock_and_synthetic_flags_false(monkeypatch):
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
            "decision": "no_trade",
            "symbols": [],
            "ranked_candidates": [],
            "selected_candidate": None,
            "candidate_source": "none",
            "raw_candidate_count": 0,
            "filtered_candidate_count": 0,
            "blockers": ["no_scanner_candidates_passed_filters"],
            "warnings": [],
            "next_action": "No provider-backed scanner/candidate symbols are available.",
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

    assert run.using_mock_data is False
    assert run.recommendation["mock_data_used"] is False
    assert run.recommendation["synthetic_data_used"] is False
    assert run.submitted_order is False
    assert run.broker_called is False
    assert run.llm_used is False
