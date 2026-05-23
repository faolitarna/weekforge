from unittest.mock import MagicMock, patch

from weekforge.checkpoint import CheckpointStore
from weekforge.models.week_summary import (
    ImplicitFeedback,
    SectionRates,
    WeekSummary,
)
from weekforge.models.workflow_state import SummarizeWeekState


def make_dummy_week_summary():
    return WeekSummary(
        week_prefix="W01",
        completion="0/0",
        sessions=[],
        exercise_log=[],
        pain_status=[],
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

@patch("weekforge.tools.notion_api_gateway.get_title_property_name", return_value="Name")
@patch("weekforge.tools.notion_api_gateway.create")
@patch("weekforge.tools.notion_api_gateway.query")
@patch("weekforge.workflows.summarize_week.run_with_metadata")
def test_extraction_end_to_end(mock_run, mock_query, mock_create, _mock_title, tmp_path):
    from weekforge.workflows.summarize_week import run_summarize
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))
    state = SummarizeWeekState(week_prefix="W01", step="write", tier0_summary=make_dummy_week_summary(), last_output=make_dummy_week_summary(), is_bootstrap=True)
    store.save("test-tid", "summarize_week", "write", state)
    
    mock_query.side_effect = [[], []]
    mock_create.return_value = "new-page-id"
    
    # Bootstrap run returns updated plan state
    from weekforge.models.llm_call_cost import CallMetadata
    from weekforge.tools.plan_state import PlanState
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
    assert create_args[0][1]["properties"]["Week"]["rich_text"][0]["text"]["content"] == "01"
    assert "PLAN_STATE" in create_args[1][1]["properties"]["Week"]["rich_text"][0]["text"]["content"]
