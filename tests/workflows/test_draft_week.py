from unittest.mock import MagicMock, patch

import pytest

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.workflow_state import DraftWeekState


def test_overwrite_check_no_existing_row(tmp_path):
    """No summary row → skip overwrite, hit load_context stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
            run_draft("W15", "draft-week-W15", store)

    mock_db.find_summary_row.assert_called_once_with("W15")


def test_overwrite_check_existing_row_empty_plan(tmp_path):
    """Row exists but Plan empty → skip overwrite, hit load_context stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1", "properties": {}}
        mock_db.read_plan_property.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
            run_draft("W15", "draft-week-W15", store)


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_approve(mock_confirm, tmp_path):
    """Row has Plan → HITL approve → load_context stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Push day + Hinge day\nConditioning x2"
        with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
            run_draft("W15", "draft-week-W15", store)

    mock_confirm.assert_called_once()


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_quit(mock_confirm, tmp_path):
    """Row has Plan → HITL quit → workflow pauses (no RuntimeError)."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=False, quit=True, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Existing plan text"
        run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None
    assert rec.step == "overwrite_check"


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_feedback_treated_as_quit(mock_confirm, tmp_path):
    """Feedback at overwrite gate = quit (nothing to refine yet)."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=False, quit=False, feedback="some feedback")

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Existing plan text"
        run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None


def test_overwrite_check_plan_preview_truncated(tmp_path):
    """Long plan text truncated to 10 lines in HITL context."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    long_plan = "\n".join(f"Line {i}" for i in range(20))

    with patch("weekforge.workflows.draft_week.hitl_confirm") as mock_confirm:
        mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
        with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
            mock_db.find_summary_row.return_value = {"id": "page-1"}
            mock_db.read_plan_property.return_value = long_plan
            with pytest.raises(RuntimeError, match="Not yet implemented"):
                run_draft("W15", "draft-week-W15", store)

    call_kwargs = mock_confirm.call_args
    context_text = call_kwargs.kwargs.get("context", call_kwargs[1].get("context", ""))
    assert "truncated" in context_text
    assert "Line 0" in context_text
    assert "Line 9" in context_text
    assert "Line 10" not in context_text


def test_stub_steps_raise():
    """All future steps raise RuntimeError."""
    from weekforge.workflows.draft_week import (
        _step_accept,
        _step_agent,
        _step_load_context,
        _step_validate,
        _step_write,
    )

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    for step_fn in [_step_load_context, _step_agent, _step_accept, _step_validate, _step_write]:
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            step_fn(state, cost)


def test_run_draft_creates_checkpoint(tmp_path):
    """run_draft saves checkpoint before first step dispatch."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None
    assert rec.workflow == "draft_week"


def test_run_draft_resumes_from_checkpoint(tmp_path):
    """Resume dispatches to the saved step."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(week_prefix="W15", step="load_context")
    store.save("draft-week-W15", "draft_week", "load_context", state)

    with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
        run_draft("W15", "draft-week-W15", store)
