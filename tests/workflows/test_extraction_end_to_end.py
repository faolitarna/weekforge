import pytest
from unittest.mock import patch, MagicMock
from weekforge.checkpoint import CheckpointStore
from weekforge.models.workflow_state import ExtractionState
from weekforge.models.week_summary import WeekSummary
from weekforge.models.week_summary import ImplicitFeedback, PainStatus, SectionRates

def make_dummy_week_summary():
    return WeekSummary(
        week_prefix="W01",
        completion="0/0",
        sessions=[],
        exercise_log=[],
        pain_status=PainStatus(si_joint="ok", other="ok"),
        implicit_feedback=ImplicitFeedback(
            total_checked=0,
            total_exercises=0,
            per_session=[],
            section_rates=SectionRates(warmup_pct=0.0, main_pct=0.0, cooldown_pct=0.0),
            frequently_skipped=[],
            always_completed=[]
        ),
        highlights=[],
        trend=""
    )

@patch("weekforge.tools.notion_api_gateway.create")
@patch("weekforge.tools.notion_api_gateway.query")
@patch("weekforge.agents.agent_run_with_metadata.run_with_metadata")
def test_extraction_end_to_end(mock_run, mock_query, mock_create, tmp_path):
    from weekforge.workflows.extraction import run_summarize
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))
    state = ExtractionState(week_prefix="W01", step="write", tier0_summary=make_dummy_week_summary(), last_output=make_dummy_week_summary())
    store.save("test-tid", "extraction", "write", state)
    
    mock_query.side_effect = [[], []]
    mock_create.return_value = "new-page-id"
    
    # Bootstrap run returns updated plan state
    from weekforge.tools.plan_state import PlanState
    from weekforge.models.llm_call_cost import CallMetadata
    mock_run.return_value = (
        MagicMock(output=PlanState(mesocycle_name="Bootstrap", weeks_completed=1)),
        CallMetadata(input_tokens=10, output_tokens=10, cost_eur=0.01, latency_ms=100, model_used="test"),
        []
    )
    
    run_summarize("W01", "test-tid", store)
    
    # Check that state went to "done" and was deleted
    final = store.load("test-tid")
    assert final is None
    
    # Check that notion create was called twice
    assert mock_create.call_count == 2
    create_args = mock_create.call_args_list
    assert create_args[0][1]["properties"]["Week"]["rich_text"][0]["text"]["content"] == "W01"
    assert "PLAN_STATE" in create_args[1][1]["properties"]["Week"]["rich_text"][0]["text"]["content"]
