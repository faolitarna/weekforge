import pytest
from unittest.mock import patch, MagicMock

from weekforge.checkpoint import CheckpointStore
from weekforge.workflows.extraction import run_summarize
from weekforge.models.workflow_state import ExtractionState
from weekforge.models.week_summary import WeekSummary, ImplicitFeedback, PainStatus, SectionRates
from weekforge.models.llm_call_cost import CallMetadata

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

def test_run_summarize_zero_sessions(tmp_path):
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))
    with pytest.raises(RuntimeError, match="tier0_summary missing"):
        run_summarize("W00", "test-tid", store)

@patch("weekforge.workflows.extraction.hitl_confirm")
@patch("weekforge.workflows.extraction.run_with_metadata")
def test_run_summarize_success(mock_run, mock_hitl, tmp_path):
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))
    
    state = ExtractionState(week_prefix="W01", step="agent", tier0_summary=make_dummy_week_summary())
    store.save("test-tid", "extraction", "agent", state)

    mock_run.return_value = (
        MagicMock(output=make_dummy_week_summary()),
        CallMetadata(input_tokens=10, output_tokens=10, cost_eur=0.01, latency_ms=100, model_used="test"),
        []
    )
    mock_hitl.return_value = MagicMock(approved=True, quit=False, feedback=None)

    with pytest.raises(NotImplementedError, match="step-1d"):
        run_summarize("W01", "test-tid", store)
        
    final_record = store.load("test-tid")
    assert final_record is not None
    assert final_record.step == "write"

@patch("weekforge.workflows.extraction.hitl_confirm")
@patch("weekforge.workflows.extraction.run_with_metadata")
def test_run_summarize_feedback_loop(mock_run, mock_hitl, tmp_path):
    store = CheckpointStore(str(tmp_path / "checkpoints.sqlite"))
    
    state = ExtractionState(week_prefix="W01", step="agent", tier0_summary=make_dummy_week_summary())
    store.save("test-tid", "extraction", "agent", state)

    mock_run_meta = CallMetadata(input_tokens=10, output_tokens=10, cost_eur=0.01, latency_ms=100, model_used="test")
    
    mock_run.return_value = (
        MagicMock(output=make_dummy_week_summary()), mock_run_meta, []
    )
    
    # 1. Provide feedback
    # 2. Provide feedback
    # 3. Approve
    mock_hitl.side_effect = [
        MagicMock(approved=False, quit=False, feedback="redo"),
        MagicMock(approved=False, quit=False, feedback="redo2"),
        MagicMock(approved=True, quit=False, feedback=None),
    ]

    with pytest.raises(NotImplementedError, match="step-1d"):
        run_summarize("W01", "test-tid", store)
        
    final_record = store.load("test-tid")
    assert final_record is not None
    assert final_record.step == "write"
    state = ExtractionState.model_validate_json(final_record.state_json)
    assert len(state.calls) == 3
