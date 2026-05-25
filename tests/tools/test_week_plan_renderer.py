from weekforge.models.week_plan import PlannedSession, WeekPlan


def test_render_basic_plan():
    from weekforge.tools.week_plan_renderer import render_week_plan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Push + Hinge", duration_min=85, focus_tags=["push", "hinge"]),
            PlannedSession(name="Squat + Pull", duration_min=80, focus_tags=["squat", "pull"]),
        ],
    )
    result = render_week_plan(plan)
    assert "Week W15 Plan (2 sessions):" in result
    assert "1. W15: Push + Hinge — 85 min" in result
    assert "2. W15: Squat + Pull — 80 min" in result
    assert "Adjustments" not in result


def test_render_with_adjustments():
    from weekforge.tools.week_plan_renderer import render_week_plan

    plan = WeekPlan(
        week_prefix="W03",
        sessions=[
            PlannedSession(name="Pull + Core", duration_min=85, focus_tags=["pull", "core"]),
        ],
        adjustments=["Reduced squat volume", "Added extra Z2 session"],
    )
    result = render_week_plan(plan)
    assert "Adjustments:" in result
    assert "- Reduced squat volume" in result
    assert "- Added extra Z2 session" in result


def test_render_empty_sessions():
    from weekforge.tools.week_plan_renderer import render_week_plan

    plan = WeekPlan(week_prefix="W01", sessions=[])
    result = render_week_plan(plan)
    assert "Week W01 Plan (0 sessions):" in result


def test_render_many_sessions():
    from weekforge.tools.week_plan_renderer import render_week_plan

    sessions = [
        PlannedSession(name=f"Session {i}", duration_min=60 + i, focus_tags=["pull"])
        for i in range(1, 13)
    ]
    plan = WeekPlan(week_prefix="W10", sessions=sessions)
    result = render_week_plan(plan)
    assert "12 sessions" in result
    assert "12. W10: Session 12 — 72 min" in result
