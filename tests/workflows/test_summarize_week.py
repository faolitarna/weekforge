from unittest.mock import MagicMock, patch

import pytest

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import CallMetadata
from weekforge.models.week_summary import (
    ImplicitFeedback,
    PainStatus,
    SectionRates,
    WeekSummary,
)
from weekforge.models.workflow_state import SummarizeWeekState
from weekforge.workflows.summarize_week import run_summarize


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

@patch("weekforge.tools.notion_api_gateway.query")
@patch("weekforge.config.user_profile_loader.load_user_profile")
def test_run_summarize_zero_sessions(mock_profile, mock_query, tmp_path):
    from weekforge.models.user_profile import UserProfile
    mock_profile.return_value = UserProfile.model_construct(page_id="test", markdown="test profile")
    mock_query.return_value = []
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))
    with pytest.raises(RuntimeError, match="No session pages found"):
        run_summarize("W00", "test-tid", store)

@patch("weekforge.tools.notion_api_gateway.get_title_property_name", return_value="Name")
@patch("weekforge.tools.notion_api_gateway.create")
@patch("weekforge.tools.notion_api_gateway.query")
@patch("weekforge.workflows.summarize_week.hitl_confirm")
@patch("weekforge.workflows.summarize_week.run_with_metadata")
def test_run_summarize_success(mock_run, mock_hitl, mock_query, mock_create, _mock_title, tmp_path):
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))

    state = SummarizeWeekState(week_prefix="W01", step="agent", tier0_summary=make_dummy_week_summary())
    store.save("test-tid", "summarize_week", "agent", state)

    from weekforge.tools.plan_state import PlanState
    mock_run.side_effect = [
        (MagicMock(output=make_dummy_week_summary()),
         CallMetadata(input_tokens=10, output_tokens=10, cost_eur=0.01, latency_ms=100, model_used="test"),
         []),
        (MagicMock(output=PlanState(mesocycle_name="Bootstrap", weeks_completed=1)),
         CallMetadata(input_tokens=10, output_tokens=10, cost_eur=0.01, latency_ms=100, model_used="test"),
         []),
    ]
    mock_hitl.return_value = MagicMock(approved=True, quit=False, feedback=None)
    mock_query.return_value = []
    mock_create.return_value = "new-page-id"

    run_summarize("W01", "test-tid", store)

    final_record = store.load("test-tid")
    assert final_record is None

@patch("weekforge.tools.notion_api_gateway.get_title_property_name", return_value="Name")
@patch("weekforge.tools.notion_api_gateway.create")
@patch("weekforge.tools.notion_api_gateway.query")
@patch("weekforge.workflows.summarize_week.hitl_confirm")
@patch("weekforge.workflows.summarize_week.run_with_metadata")
def test_run_summarize_feedback_loop(mock_run, mock_hitl, mock_query, mock_create, _mock_title, tmp_path):
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))

    state = SummarizeWeekState(week_prefix="W01", step="agent", tier0_summary=make_dummy_week_summary())
    store.save("test-tid", "summarize_week", "agent", state)

    meta = CallMetadata(input_tokens=10, output_tokens=10, cost_eur=0.01, latency_ms=100, model_used="test")

    from weekforge.tools.plan_state import PlanState
    summarize_result = (MagicMock(output=make_dummy_week_summary()), meta, [])
    plan_state_result = (MagicMock(output=PlanState(mesocycle_name="Bootstrap", weeks_completed=1)), meta, [])
    mock_run.side_effect = [
        summarize_result, summarize_result, summarize_result,
        plan_state_result,
    ]

    mock_hitl.side_effect = [
        MagicMock(approved=False, quit=False, feedback="redo"),
        MagicMock(approved=False, quit=False, feedback="redo2"),
        MagicMock(approved=True, quit=False, feedback=None),
    ]
    mock_query.return_value = []
    mock_create.return_value = "new-page-id"

    run_summarize("W01", "test-tid", store)

    final_record = store.load("test-tid")
    assert final_record is None
    assert mock_run.call_count == 4
