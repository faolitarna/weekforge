import pytest
from pydantic import ValidationError


def test_planned_session_valid():
    from weekforge.models.week_plan import PlannedSession

    s = PlannedSession(name="Push + Hinge", duration_min=85, focus_tags=["push", "hinge"])
    assert s.name == "Push + Hinge"
    assert s.duration_min == 85
    assert s.focus_tags == ["push", "hinge"]


def test_planned_session_invalid_focus_tag():
    from weekforge.models.week_plan import PlannedSession

    with pytest.raises(ValidationError, match="focus_tags"):
        PlannedSession(name="Bad", duration_min=60, focus_tags=["nonexistent_tag"])


def test_week_plan_valid():
    from weekforge.models.week_plan import PlannedSession, WeekPlan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Push + Hinge", duration_min=85, focus_tags=["push", "hinge"]),
            PlannedSession(name="Z2 Uphill", duration_min=75, focus_tags=["cardio", "z2", "uphill"]),
        ],
        adjustments=["Reduced squat volume due to SI flare"],
    )
    assert plan.week_prefix == "W15"
    assert len(plan.sessions) == 2
    assert plan.adjustments == ["Reduced squat volume due to SI flare"]


def test_week_plan_adjustments_default_empty():
    from weekforge.models.week_plan import PlannedSession, WeekPlan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="A", duration_min=60, focus_tags=["pull"])],
    )
    assert plan.adjustments == []


def test_focus_tag_all_movement_tags():
    from weekforge.models.week_plan import PlannedSession

    for tag in ["push", "pull", "squat", "hinge", "core", "carry"]:
        s = PlannedSession(name="Test", duration_min=60, focus_tags=[tag])
        assert s.focus_tags == [tag]


def test_focus_tag_all_cardio_tags():
    from weekforge.models.week_plan import PlannedSession

    for tag in ["cardio", "z1", "z2", "z3", "uphill", "loaded", "run", "hike", "walk"]:
        s = PlannedSession(name="Test", duration_min=60, focus_tags=[tag])
        assert s.focus_tags == [tag]


def test_focus_tag_all_skill_tags():
    from weekforge.models.week_plan import PlannedSession

    for tag in ["climbing", "hangboard", "mobility", "recovery"]:
        s = PlannedSession(name="Test", duration_min=60, focus_tags=[tag])
        assert s.focus_tags == [tag]


def test_focus_tag_other_tags():
    from weekforge.models.week_plan import PlannedSession

    s = PlannedSession(name="Test", duration_min=60, focus_tags=["template_restructured"])
    assert s.focus_tags == ["template_restructured"]


def test_week_plan_serialization_roundtrip():
    from weekforge.models.week_plan import PlannedSession, WeekPlan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push", "core"])],
        adjustments=["test"],
    )
    json_str = plan.model_dump_json()
    restored = WeekPlan.model_validate_json(json_str)
    assert restored == plan


def test_week_plan_empty_sessions_allowed():
    """Agent might return empty sessions on bad prompt — validation in 2d, not model."""
    from weekforge.models.week_plan import WeekPlan

    plan = WeekPlan(week_prefix="W15", sessions=[])
    assert plan.sessions == []
