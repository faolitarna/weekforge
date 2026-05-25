import pytest

from weekforge.models.week_plan import PlannedSession, WeekPlan
from weekforge.models.workflow_state import DraftWeekState


def test_draft_week_state_defaults():
    state = DraftWeekState(week_prefix="W15")
    assert state.step == "overwrite_check"
    assert state.week_prefix == "W15"
    assert state.messages_json == []
    assert state.calls == []
    assert state.last_output is None
    assert state.pending_feedback is None
    assert state.validation_retry_used is False
    assert state.validation_warning is None
    assert state.written_page_id is None
    assert state.is_bootstrap is None
    assert state.plan_state_raw is None
    assert state.plan_state_page_id is None
    assert state.started_at is not None


def test_draft_week_state_roundtrip():
    state = DraftWeekState(week_prefix="W07")
    json_str = state.model_dump_json()
    restored = DraftWeekState.model_validate_json(json_str)
    assert restored.week_prefix == "W07"
    assert restored.step == "overwrite_check"
    assert restored.started_at == state.started_at


def _make_plan(week_prefix: str = "W20") -> WeekPlan:
    return WeekPlan(
        week_prefix=week_prefix,
        sessions=[
            PlannedSession(name="Push + Core", duration_min=75, focus_tags=["push", "core"]),
            PlannedSession(name="Z2 Run", duration_min=60, focus_tags=["cardio", "z2", "run"]),
        ],
        adjustments=["Reduced volume — travel week"],
    )


def test_draft_week_state_roundtrip_with_populated_last_output():
    """Checkpoint/resume: DraftWeekState carrying a real WeekPlan survives JSON round-trip."""
    plan = _make_plan()
    state = DraftWeekState(
        week_prefix="W20",
        step="awaiting_feedback",
        last_output=plan,
        pending_feedback="Looks good, ship it",
        validation_retry_used=True,
        validation_warning="session count below recommended range",
    )
    json_str = state.model_dump_json()
    restored = DraftWeekState.model_validate_json(json_str)

    assert restored.last_output is not None
    assert restored.last_output == plan
    assert restored.last_output.week_prefix == "W20"
    assert len(restored.last_output.sessions) == 2
    assert restored.last_output.sessions[0].focus_tags == ["push", "core"]
    assert restored.last_output.adjustments == ["Reduced volume — travel week"]
    assert restored.pending_feedback == "Looks good, ship it"
    assert restored.validation_retry_used is True
    assert restored.validation_warning == "session count below recommended range"
    assert restored.step == "awaiting_feedback"


def test_draft_week_state_last_output_null_roundtrip():
    """Checkpoint/resume: None last_output serializes as JSON null and restores correctly."""
    state = DraftWeekState(week_prefix="W21", last_output=None)
    json_str = state.model_dump_json()
    assert '"last_output":null' in json_str
    restored = DraftWeekState.model_validate_json(json_str)
    assert restored.last_output is None


def test_draft_week_state_last_output_week_plan_tags_preserved_after_roundtrip():
    """All FocusTag values survive JSON serialization without corruption."""
    all_tags_session = PlannedSession(
        name="Everything",
        duration_min=120,
        focus_tags=["push", "pull", "squat", "hinge", "core", "carry",
                    "cardio", "z1", "z2", "z3", "uphill", "loaded", "run", "hike", "walk",
                    "climbing", "hangboard", "mobility", "recovery", "template_restructured"],
    )
    plan = WeekPlan(week_prefix="W22", sessions=[all_tags_session])
    state = DraftWeekState(week_prefix="W22", last_output=plan)
    restored = DraftWeekState.model_validate_json(state.model_dump_json())
    assert restored.last_output.sessions[0].focus_tags == all_tags_session.focus_tags
