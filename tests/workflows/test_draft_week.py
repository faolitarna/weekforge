from unittest.mock import MagicMock, patch

import pytest

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.week_plan import PlannedSession, WeekPlan
from weekforge.models.workflow_state import DraftWeekState


@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.notion")
def test_overwrite_check_no_existing_row(mock_notion, mock_profile, mock_run_meta, mock_gate, tmp_path):
    """No summary row → skip overwrite, load context, agent runs, hits validate stub."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        mock_db.find_plan_state_row.return_value = (None, None)
        with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
            run_draft("W15", "draft-week-W15", store)

    mock_db.find_summary_row.assert_called()


@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.notion")
def test_overwrite_check_existing_row_empty_plan(mock_notion, mock_profile, mock_run_meta, mock_gate, tmp_path):
    """Row exists but Plan empty → skip overwrite, load context, agent runs, hits validate stub."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1", "properties": {}}
        mock_db.read_plan_property.return_value = None
        mock_db.read_summary_body.return_value = None
        mock_db.find_plan_state_row.return_value = (None, None)
        with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
            run_draft("W15", "draft-week-W15", store)


@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_approve(mock_confirm, mock_notion, mock_profile, mock_run_meta, mock_gate, tmp_path):
    """Row has Plan → HITL approve → load_context → agent runs → hits validate stub."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Push day + Hinge day\nConditioning x2"
        mock_db.read_summary_body.return_value = None
        mock_db.find_plan_state_row.return_value = (None, None)
        with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
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


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.notion")
def test_overwrite_check_plan_preview_truncated(mock_notion, mock_profile, tmp_path):
    """Long plan text truncated to 10 lines in HITL context."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    long_plan = "\n".join(f"Line {i}" for i in range(20))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan

    with patch("weekforge.workflows.draft_week.hitl_confirm") as mock_confirm:
        mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
        with patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta:
            mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
            with patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate:
                mock_gate.return_value = AcceptResult(step="validate", feedback=None)
                with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
                    mock_db.find_summary_row.return_value = {"id": "page-1"}
                    mock_db.read_plan_property.return_value = long_plan
                    mock_db.read_summary_body.return_value = None
                    mock_db.find_plan_state_row.return_value = (None, None)
                    with pytest.raises(RuntimeError, match="Not yet implemented"):
                        run_draft("W15", "draft-week-W15", store)

    call_kwargs = mock_confirm.call_args
    context_text = call_kwargs.kwargs.get("context", call_kwargs[1].get("context", ""))
    assert "truncated" in context_text
    assert "Line 0" in context_text
    assert "Line 9" in context_text
    assert "Line 10" not in context_text


def test_stub_steps_raise():
    """Remaining future steps raise RuntimeError."""
    from weekforge.workflows.draft_week import (
        _step_validate,
        _step_write,
    )

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    for step_fn in [_step_validate, _step_write]:
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            step_fn(state, cost)


@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.notion")
def test_run_draft_creates_checkpoint(mock_notion, mock_profile, mock_run_meta, mock_gate, tmp_path):
    """run_draft saves checkpoint before first step dispatch."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        mock_db.find_plan_state_row.return_value = (None, None)
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None
    assert rec.workflow == "draft_week"


@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.notion")
def test_run_draft_resumes_from_checkpoint(mock_notion, mock_profile, mock_run_meta, mock_gate, tmp_path):
    """Resume dispatches to the saved step (load_context → agent runs → hits validate stub)."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(week_prefix="W15", step="load_context")
    store.save("draft-week-W15", "draft_week", "load_context", state)

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        mock_db.find_plan_state_row.return_value = (None, None)
        with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
            run_draft("W15", "draft-week-W15", store)


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_happy_path(mock_notion, mock_db, mock_profile):
    """load_context gathers all data and transitions to agent."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    # Templates: 2 matching pages
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push + Hinge"}]}}},
        {"id": "t2", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Squat Day"}]}}},
        {"id": "t3", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W14: Old Template"}]}}},
    ]

    # Feedback window: W14 exists with plan+body, W13 missing, W12 exists
    def find_row(prefix):
        if prefix == "W14":
            return {"id": "s14"}
        if prefix == "W12":
            return {"id": "s12"}
        return None

    mock_db.find_summary_row.side_effect = find_row
    mock_db.read_plan_property.side_effect = lambda page: "Plan for " + page["id"]
    mock_db.read_summary_body.return_value = "Summary body text"

    # PLAN_STATE
    mock_db.find_plan_state_row.return_value = ("PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk", "ps-page-id")

    mock_profile.return_value = UserProfile(page_id="up1", markdown="# My Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is False
    assert state.plan_state_raw is not None
    assert state.plan_state_page_id == "ps-page-id"
    # W14 + W12 present, W13 skipped → 2 calls to read_plan_property/read_summary_body
    assert mock_db.read_plan_property.call_count == 2
    assert mock_db.read_summary_body.call_count == 2


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_no_templates_raises(mock_notion, mock_db, mock_profile):
    """Empty template result for week prefix is a hard error."""
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    # No templates match W15
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W14: Old Template"}]}}},
    ]

    with pytest.raises(RuntimeError, match="No template.*W15"):
        _step_load_context(state, cost)


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_bootstrap_no_plan_state(mock_notion, mock_db, mock_profile):
    """Missing PLAN_STATE sets bootstrap=True."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)

    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True
    assert state.plan_state_raw is None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_bootstrap_empty_feedback_window(mock_notion, mock_db, mock_profile):
    """Empty feedback window (all 3 weeks missing) sets bootstrap=True."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = ("PLAN_STATE raw", "ps-id")

    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_feedback_window_ordering(mock_notion, mock_db, mock_profile):
    """Feedback rows are ordered ascending (oldest first, most recent last)."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]

    def find_row(prefix):
        if prefix in ("W14", "W13", "W12"):
            return {"id": f"s{prefix}"}
        return None

    mock_db.find_summary_row.side_effect = find_row
    mock_db.read_plan_property.return_value = "plan"
    mock_db.read_summary_body.return_value = "body"
    mock_db.find_plan_state_row.return_value = ("PS", "ps-id")

    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    _step_load_context(state, cost)

    # find_summary_row called for W14, W13, W12 (descending scan)
    calls = [c.args[0] for c in mock_db.find_summary_row.call_args_list]
    assert calls == ["W14", "W13", "W12"]


@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_end_to_end_through_workflow(mock_notion, mock_db, mock_profile, mock_run_meta, mock_gate, tmp_path):
    """load_context step runs through the full workflow, agent runs, hits validate stub."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None  # overwrite_check + feedback window
    mock_db.find_plan_state_row.return_value = (None, None)

    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(week_prefix="W15", sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])])
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
        run_draft("W15", "draft-week-W15", store)


# --- feedback window edge cases for early weeks ---


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_week_1_no_previous_weeks_scanned(mock_notion, mock_db, mock_profile):
    """W01 has no previous weeks — find_summary_row must never be called for feedback."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W01", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W01: Day 1"}]}}},
    ]
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True
    # No previous weeks to scan
    mock_db.find_summary_row.assert_not_called()


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_week_2_scans_only_one_previous_week(mock_notion, mock_db, mock_profile):
    """W02 can only look back at W01 — find_summary_row called exactly once."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W02", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W02: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    _step_load_context(state, cost)

    calls = [c.args[0] for c in mock_db.find_summary_row.call_args_list]
    assert calls == ["W01"]


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_week_3_scans_two_previous_weeks(mock_notion, mock_db, mock_profile):
    """W03 can look back at W02 and W01 (only 2 weeks available, not 3)."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W03", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W03: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    _step_load_context(state, cost)

    calls = [c.args[0] for c in mock_db.find_summary_row.call_args_list]
    assert calls == ["W02", "W01"]


# --- active_flare via plan_state active_issues in the workflow ---


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_active_flare_from_plan_state_active_issues(mock_notion, mock_db, mock_profile):
    """active_flare=True when plan_state has pain keyword in active_issues, no pain in feedback."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    # Feedback row with no pain keywords
    mock_db.find_summary_row.return_value = {"id": "s14"}
    mock_db.read_plan_property.return_value = None
    mock_db.read_summary_body.return_value = "Great week, all sessions completed."
    # PLAN_STATE with an active pain issue
    mock_db.find_plan_state_row.return_value = (
        "PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk\nACTIVE_ISSUES:\n- SI joint irritation ongoing",
        "ps-id",
    )
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is False


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_plan_state_raw_empty_string_treated_as_bootstrap(mock_notion, mock_db, mock_profile):
    """PLAN_STATE page found but empty content → raw_text='' → plan_state=None → bootstrap=True."""
    from weekforge.workflows.draft_week import _step_load_context
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    # raw_text is empty string (page exists but has no blocks)
    mock_db.find_plan_state_row.return_value = ("", "ps-id")
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True
    assert state.plan_state_raw == ""
    assert state.plan_state_page_id == "ps-id"


# --- _step_agent unit tests ---


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_step_agent_runs_and_returns_accept(mock_notion, mock_db, mock_profile):
    """Agent step builds deps, calls agent, stores output, returns 'accept'."""
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="agent")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
        adjustments=["test adjustment"],
    )

    fake_result = MagicMock()
    fake_result.output = fake_plan
    fake_meta = MagicMock(input_tokens=100, output_tokens=50, latency_ms=500, model_used="test", cost_eur=0.01)
    fake_messages = [{"role": "user", "content": "test"}]

    with patch("weekforge.workflows.draft_week.run_with_metadata", return_value=(fake_result, fake_meta, fake_messages)):
        result = _step_agent(state, cost)

    assert result == "accept"
    assert state.last_output == fake_plan
    assert len(state.calls) == 1
    assert state.pending_feedback is None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_step_agent_includes_pending_feedback_in_prompt(mock_notion, mock_db, mock_profile):
    """Pending feedback appended to prompt."""
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="agent", pending_feedback="add more conditioning")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan

    with patch("weekforge.workflows.draft_week.run_with_metadata", return_value=(fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])) as mock_run:
        _step_agent(state, cost)

    prompt_arg = mock_run.call_args[0][1]
    assert "add more conditioning" in prompt_arg
    assert state.pending_feedback is None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_step_agent_accumulates_calls(mock_notion, mock_db, mock_profile):
    """Multiple agent runs accumulate in state.calls and cost."""
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.user_profile import UserProfile
    from weekforge.models.llm_call_cost import CallMetadata

    existing_call = CallMetadata(input_tokens=50, output_tokens=25, latency_ms=200, model_used="t", cost_eur=0.005)
    state = DraftWeekState(week_prefix="W15", step="agent", calls=[existing_call])
    cost = RunCost()
    cost.add(existing_call)

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    new_meta = CallMetadata(input_tokens=100, output_tokens=50, latency_ms=500, model_used="t", cost_eur=0.01)

    with patch("weekforge.workflows.draft_week.run_with_metadata", return_value=(fake_result, new_meta, [])):
        _step_agent(state, cost)

    assert len(state.calls) == 2
    assert cost.call_count == 2


# --- step_accept integration tests ---


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_approve_transitions_to_validate(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → approve → step becomes 'validate'."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
        run_draft("W15", "draft-week-W15", store)

    mock_gate.assert_called_once()
    gate_kwargs = mock_gate.call_args
    assert gate_kwargs.kwargs.get("approved_step", gate_kwargs[1].get("approved_step")) == "validate"


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_quit_pauses_workflow(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → quit → workflow pauses with checkpoint."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    mock_gate.return_value = AcceptResult(step=None, feedback=None)

    run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_feedback_loops_to_agent(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → feedback → loops back to agent with pending_feedback set."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    mock_gate.side_effect = [
        AcceptResult(step="agent", feedback="add more conditioning"),
        AcceptResult(step=None, feedback=None),
    ]

    run_draft("W15", "draft-week-W15", store)

    assert mock_run_meta.call_count == 2
    second_prompt = mock_run_meta.call_args_list[1][0][1]
    assert "add more conditioning" in second_prompt
