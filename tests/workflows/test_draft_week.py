from unittest.mock import MagicMock, patch

import pytest

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.week_plan import PlannedSession, WeekPlan
from weekforge.models.workflow_state import DraftWeekState


def _fake_draft_context(**overrides):
    from weekforge.tools.context_loader import WeekDraftContext
    defaults = dict(
        template_markdown="## Template Sessions\n\n### W15: Push\n",
        feedback_window_markdown="",
        plan_state_raw=None,
        user_profile_markdown="# Profile",
        active_flare=False,
        is_bootstrap=True,
        plan_state_page_id=None,
    )
    defaults.update(overrides)
    return WeekDraftContext(**defaults)


def _fake_plan(**overrides):
    defaults = dict(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    defaults.update(overrides)
    return WeekPlan(**defaults)


def _fake_run_meta_return(plan=None):
    plan = plan or _fake_plan()
    result = MagicMock()
    result.output = plan
    meta = MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0)
    return (result, meta, [])


# --- overwrite_check tests ---


@patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None))
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.notion")
@patch("weekforge.tools.context_loader.summaries_db")
def test_overwrite_check_no_existing_row(mock_cl_db, mock_cl_notion, mock_cl_profile, mock_run_meta, mock_gate, mock_validator, tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_cl_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_cl_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )
    mock_cl_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")
    mock_cl_db.find_summary_row.return_value = None
    mock_cl_db.find_plan_state_row.return_value = (None, None)

    mock_run_meta.return_value = _fake_run_meta_return()
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_wf_db:
        mock_wf_db.find_summary_row.return_value = None
        mock_wf_db.upsert_plan.return_value = "written-page-id"
        run_draft("W15", "draft-week-W15", store)

    assert store.load("draft-week-W15") is None


@patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None))
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
@patch("weekforge.tools.context_loader.load_user_profile")
@patch("weekforge.tools.context_loader.notion")
@patch("weekforge.tools.context_loader.summaries_db")
def test_overwrite_check_existing_row_empty_plan(mock_cl_db, mock_cl_notion, mock_cl_profile, mock_run_meta, mock_gate, mock_validator, tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_cl_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_cl_notion.get_page_title.side_effect = lambda p: next(
        v["title"][0]["plain_text"] for v in p["properties"].values() if v.get("type") == "title"
    )
    mock_cl_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")
    mock_cl_db.find_summary_row.return_value = None
    mock_cl_db.find_plan_state_row.return_value = (None, None)

    mock_run_meta.return_value = _fake_run_meta_return()
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_wf_db:
        mock_wf_db.find_summary_row.return_value = {"id": "page-1", "properties": {}}
        mock_wf_db.read_plan_property.return_value = None
        mock_wf_db.upsert_plan.return_value = "written-page-id"
        run_draft("W15", "draft-week-W15", store)

    assert store.load("draft-week-W15") is None


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_approve(mock_confirm, tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_wf_db, \
         patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):

        mock_wf_db.find_summary_row.return_value = {"id": "page-1"}
        mock_wf_db.read_plan_property.return_value = "Push day + Hinge day\nConditioning x2"
        mock_wf_db.upsert_plan.return_value = "written-page-id"

        mock_loader.return_value = _fake_draft_context()
        mock_run_meta.return_value = _fake_run_meta_return()
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    mock_confirm.assert_called_once()
    assert store.load("draft-week-W15") is None


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_quit(mock_confirm, tmp_path):
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
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    long_plan = "\n".join(f"Line {i}" for i in range(20))

    with patch("weekforge.workflows.draft_week.hitl_confirm") as mock_confirm, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_wf_db, \
         patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):

        mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
        mock_wf_db.find_summary_row.return_value = {"id": "page-1"}
        mock_wf_db.read_plan_property.return_value = long_plan
        mock_wf_db.upsert_plan.return_value = "written-page-id"

        mock_loader.return_value = _fake_draft_context()
        mock_run_meta.return_value = _fake_run_meta_return()
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    call_kwargs = mock_confirm.call_args
    context_text = call_kwargs.kwargs.get("context", call_kwargs[1].get("context", ""))
    assert "truncated" in context_text
    assert "Line 0" in context_text
    assert "Line 9" in context_text
    assert "Line 10" not in context_text


# --- load_context tests (mock context_loader) ---


@patch("weekforge.tools.context_loader.load_week_draft_context")
def test_load_context_happy_path(mock_loader):
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_loader.return_value = _fake_draft_context(
        plan_state_raw="PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk",
        plan_state_page_id="ps-page-id",
        is_bootstrap=False,
        feedback_window_markdown="## Previous Weeks\n### W14\nSummary: good",
    )

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is False
    assert state.plan_state_raw is not None
    assert state.plan_state_page_id == "ps-page-id"
    assert state.template_markdown is not None
    assert state.feedback_window_markdown is not None


@patch("weekforge.tools.context_loader.load_week_draft_context")
def test_load_context_no_templates_raises(mock_loader):
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_loader.side_effect = RuntimeError("No template sessions found for W15")

    with pytest.raises(RuntimeError, match="No template.*W15"):
        _step_load_context(state, cost)


@patch("weekforge.tools.context_loader.load_week_draft_context")
def test_load_context_bootstrap_no_plan_state(mock_loader):
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_loader.return_value = _fake_draft_context(
        plan_state_raw=None,
        is_bootstrap=True,
    )

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True
    assert state.plan_state_raw is None


@patch("weekforge.tools.context_loader.load_week_draft_context")
def test_load_context_bootstrap_empty_feedback_window(mock_loader):
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_loader.return_value = _fake_draft_context(
        plan_state_raw="PS raw",
        is_bootstrap=True,
        feedback_window_markdown="",
    )

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True


# --- context_loader internal tests (feedback window, week scan) are now in test_context_loader.py ---


@patch("weekforge.tools.context_loader.load_week_draft_context")
def test_load_context_active_flare_stored_in_state(mock_loader):
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_loader.return_value = _fake_draft_context(active_flare=True, is_bootstrap=False)

    _step_load_context(state, cost)

    assert state.active_flare is True


@patch("weekforge.tools.context_loader.load_week_draft_context")
def test_load_context_plan_state_raw_empty_string_treated_as_bootstrap(mock_loader):
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_loader.return_value = _fake_draft_context(
        plan_state_raw="",
        plan_state_page_id="ps-id",
        is_bootstrap=True,
    )

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True
    assert state.plan_state_raw == ""
    assert state.plan_state_page_id == "ps-id"


# --- _step_agent tests (no Notion mocks needed) ---


def test_step_agent_runs_and_returns_accept():
    from weekforge.workflows.draft_week import _step_agent

    state = DraftWeekState(
        week_prefix="W15", step="agent",
        template_markdown="## Templates\n### W15: Push\n",
        feedback_window_markdown="",
        user_profile_markdown="# Profile",
        active_flare=False,
        is_bootstrap=False,
    )
    cost = RunCost()

    fake_plan = _fake_plan(adjustments=["test adjustment"])

    with patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run:
        mock_run.return_value = _fake_run_meta_return(fake_plan)
        result = _step_agent(state, cost)

    assert result == "accept"
    assert state.last_output == fake_plan
    assert len(state.calls) == 1
    assert state.pending_feedback is None


def test_step_agent_includes_pending_feedback_in_prompt():
    from weekforge.workflows.draft_week import _step_agent

    state = DraftWeekState(
        week_prefix="W15", step="agent",
        pending_feedback="add more conditioning",
        template_markdown="## Templates\n",
        feedback_window_markdown="",
        user_profile_markdown="# Profile",
        active_flare=False,
        is_bootstrap=False,
    )
    cost = RunCost()

    with patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run:
        mock_run.return_value = _fake_run_meta_return()
        _step_agent(state, cost)

    prompt_arg = mock_run.call_args[0][1]
    assert "add more conditioning" in prompt_arg
    assert state.pending_feedback is None


def test_step_agent_accumulates_calls():
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.llm_call_cost import CallMetadata

    existing_call = CallMetadata(input_tokens=50, output_tokens=25, latency_ms=200, model_used="t", cost_eur=0.005)
    state = DraftWeekState(
        week_prefix="W15", step="agent", calls=[existing_call],
        template_markdown="## Templates\n",
        feedback_window_markdown="",
        user_profile_markdown="# Profile",
        active_flare=False,
        is_bootstrap=False,
    )
    cost = RunCost()
    cost.add(existing_call)

    new_meta = CallMetadata(input_tokens=100, output_tokens=50, latency_ms=500, model_used="t", cost_eur=0.01)

    with patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run:
        result = MagicMock()
        result.output = _fake_plan()
        mock_run.return_value = (result, new_meta, [])
        _step_agent(state, cost)

    assert len(state.calls) == 2
    assert cost.call_count == 2


# --- step_accept integration tests ---


def test_accept_approve_transitions_to_validate(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db, \
         patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_db.upsert_plan.return_value = "written-page-id"
        mock_run_meta.return_value = _fake_run_meta_return()
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    mock_gate.assert_called_once()
    assert store.load("draft-week-W15") is None


def test_accept_quit_pauses_workflow(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db:

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_run_meta.return_value = _fake_run_meta_return()
        mock_gate.return_value = AcceptResult(step=None, feedback=None)

        run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None


def test_accept_feedback_loops_to_agent(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db:

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_run_meta.return_value = _fake_run_meta_return()

        mock_gate.side_effect = [
            AcceptResult(step="agent", feedback="add more conditioning"),
            AcceptResult(step=None, feedback=None),
        ]

        run_draft("W15", "draft-week-W15", store)

    assert mock_run_meta.call_count == 2
    second_prompt = mock_run_meta.call_args_list[1][0][1]
    assert "add more conditioning" in second_prompt


# --- validate step tests ---


def test_validate_pass_transitions_to_write():
    from weekforge.workflows.draft_week import _step_validate

    plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])
    state = DraftWeekState(week_prefix="W15", step="validate", last_output=plan)
    cost = RunCost()

    with patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):
        result = _step_validate(state, cost)

    assert result == "write"
    assert state.validation_warning is None


def test_validate_fail_first_time_reprompts():
    from weekforge.workflows.draft_week import _step_validate

    plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])
    state = DraftWeekState(week_prefix="W15", step="validate", last_output=plan)
    cost = RunCost()

    with patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(False, "pull:push ratio off")):
        result = _step_validate(state, cost)

    assert result == "agent"
    assert state.validation_retry_used is True
    assert "pull:push" in state.pending_feedback


def test_validate_fail_second_time_warns_and_loops_to_accept():
    from weekforge.workflows.draft_week import _step_validate

    plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])
    state = DraftWeekState(week_prefix="W15", step="validate", last_output=plan, validation_retry_used=True)
    cost = RunCost()

    with patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(False, "pull:push ratio off")):
        result = _step_validate(state, cost)

    assert result == "accept"
    assert "pull:push" in state.validation_warning


def test_validate_pass_after_retry_clears_warning():
    from weekforge.workflows.draft_week import _step_validate

    plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])
    state = DraftWeekState(week_prefix="W15", step="validate", last_output=plan, validation_retry_used=True)
    cost = RunCost()

    with patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):
        result = _step_validate(state, cost)

    assert result == "write"
    assert state.validation_warning is None


def test_validate_override_after_warning_skips_to_write():
    from weekforge.workflows.draft_week import _step_validate

    plan = _fake_plan()
    state = DraftWeekState(
        week_prefix="W15", step="validate", last_output=plan,
        validation_retry_used=True,
        validation_warning="pull:push=1.0:2.0 (previous warning)",
    )
    cost = RunCost()

    result = _step_validate(state, cost)
    assert result == "write"


# --- write step tests ---


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_calls_upsert_and_returns_done(mock_db):
    from weekforge.workflows.draft_week import _step_write

    plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
    ], adjustments=["test adjustment"])
    state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
    cost = RunCost()

    mock_db.upsert_plan.return_value = "page-123"

    result = _step_write(state, cost)

    assert result == "done"
    assert state.written_page_id == "page-123"
    rendered = mock_db.upsert_plan.call_args[0][1]
    assert "Pull A" in rendered
    assert "test adjustment" in rendered


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_truncates_long_plan(mock_db):
    from weekforge.workflows.draft_week import _step_write

    sessions = [
        PlannedSession(name=f"Session {i} with a long name for padding purposes", duration_min=60 + i, focus_tags=["pull"])
        for i in range(1, 30)
    ]
    plan = WeekPlan(week_prefix="W15", sessions=sessions, adjustments=["a" * 500])
    state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
    cost = RunCost()

    mock_db.upsert_plan.return_value = "page-456"

    _step_write(state, cost)

    rendered = mock_db.upsert_plan.call_args[0][1]
    assert len(rendered) <= 2000
    assert "[truncated]" in rendered


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_truncated_plan_is_exactly_2000_chars(mock_db):
    from weekforge.workflows.draft_week import _step_write

    sessions = [
        PlannedSession(name=f"Session {i:03d} with extra padding text to ensure length", duration_min=60 + i, focus_tags=["pull"])
        for i in range(1, 50)
    ]
    plan = WeekPlan(week_prefix="W15", sessions=sessions, adjustments=["x" * 1000])
    state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
    cost = RunCost()

    mock_db.upsert_plan.return_value = "page-exact"

    _step_write(state, cost)

    rendered = mock_db.upsert_plan.call_args[0][1]
    assert len(rendered) == 2000
    assert rendered.endswith("[truncated]")


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_short_plan_not_truncated(mock_db):
    from weekforge.workflows.draft_week import _step_write

    plan = _fake_plan()
    state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
    cost = RunCost()

    mock_db.upsert_plan.return_value = "page-short"

    _step_write(state, cost)

    rendered = mock_db.upsert_plan.call_args[0][1]
    assert "[truncated]" not in rendered
    assert len(rendered) < 2000


# --- end-to-end integration tests ---


def test_e2e_approve_validate_pass_write(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    valid_plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db, \
         patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_db.upsert_plan.return_value = "written-page-id"
        mock_run_meta.return_value = _fake_run_meta_return(valid_plan)
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    mock_db.upsert_plan.assert_called_once()
    assert store.load("draft-week-W15") is None


def test_e2e_validate_fail_reprompt_then_pass(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    bad_plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])
    good_plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db:

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_db.upsert_plan.return_value = "written-page-id"

        bad_result = MagicMock(); bad_result.output = bad_plan
        good_result = MagicMock(); good_result.output = good_plan
        meta = MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0)

        mock_run_meta.side_effect = [
            (bad_result, meta, []),
            (good_result, meta, []),
        ]
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    assert mock_run_meta.call_count == 2
    mock_db.upsert_plan.assert_called_once()
    second_prompt = mock_run_meta.call_args_list[1][0][1]
    assert "pull:push" in second_prompt


def test_e2e_validate_fail_twice_hitl_accepts_warned_plan(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    bad_plan = _fake_plan(sessions=[
        PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
        PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
        PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
    ])

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db:

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None

        bad_result = MagicMock(); bad_result.output = bad_plan
        meta = MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0)

        mock_run_meta.side_effect = [
            (bad_result, meta, []),
            (bad_result, meta, []),
        ]
        mock_gate.side_effect = [
            AcceptResult(step="validate", feedback=None),
            AcceptResult(step="validate", feedback=None),
            AcceptResult(step=None, feedback=None),
        ]

        run_draft("W15", "draft-week-W15", store)

    assert mock_run_meta.call_count == 2
    assert mock_gate.call_count == 3
    mock_db.upsert_plan.assert_not_called()
    rec = store.load("draft-week-W15")
    assert rec is not None


# --- checkpoint tests ---


def test_run_draft_creates_checkpoint(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db, \
         patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_db.upsert_plan.return_value = "written-page-id"
        mock_run_meta.return_value = _fake_run_meta_return()
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    assert store.load("draft-week-W15") is None


def test_run_draft_resumes_from_checkpoint(tmp_path):
    from weekforge.workflows.draft_week import run_draft
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(
        week_prefix="W15", step="load_context",
    )
    store.save("draft-week-W15", "draft_week", "load_context", state)

    with patch("weekforge.tools.context_loader.load_week_draft_context") as mock_loader, \
         patch("weekforge.workflows.draft_week.run_with_metadata") as mock_run_meta, \
         patch("weekforge.workflows.draft_week.run_accept_gate") as mock_gate, \
         patch("weekforge.workflows.draft_week.summaries_db") as mock_db, \
         patch("weekforge.tools.week_plan_validator.validate_week_plan", return_value=(True, None)):

        mock_loader.return_value = _fake_draft_context()
        mock_db.find_summary_row.return_value = None
        mock_db.upsert_plan.return_value = "written-page-id"
        mock_run_meta.return_value = _fake_run_meta_return()
        mock_gate.return_value = AcceptResult(step="validate", feedback=None)

        run_draft("W15", "draft-week-W15", store)

    assert store.load("draft-week-W15") is None
