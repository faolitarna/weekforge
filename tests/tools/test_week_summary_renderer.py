from weekforge.models.week_summary import (
    CardioEntry,
    ClimbingEntry,
    ExerciseLogEntry,
    ImplicitFeedback,
    ModificationPattern,
    PainStatus,
    PlanAdherence,
    SectionRates,
    SessionLine,
    WeekSummary,
)
from weekforge.tools.week_summary_renderer import render_week_summary


def test_render_week_summary():
    summary = WeekSummary(
        week_prefix="W07",
        completion="10/12",
        context="Full build week",
        sessions=[
            SessionLine(name="TM1_EXTENDED", status="done", exercises_done=9, exercises_total=13, pain_status="ok", comment="Partial")
        ],
        exercise_log=[
            ExerciseLogEntry(name="Goblet Squat", planned_weight="15kg", planned_sets=3, planned_reps="8", role="main", status="done", feedback="felt easy")
        ],
        cardio_log=[
            CardioEntry(kind="z2_run", raw="dist: 5km")
        ],
        climbing_log=[
            ClimbingEntry(kind="grades", raw="v4-v5")
        ],
        pain_status=PainStatus(si_joint="stiff", other=None),
        issues=["Bad sleep"],
        wins=["Felt strong"],
        recommendations_next=["Sleep more"],
        plan_adherence=PlanAdherence(planned_total=12, completed=10, modified=1, skipped=1, modification_patterns=[ModificationPattern(exercise="A", planned="B", actual="reason")], skip_patterns=[]),
        implicit_feedback=ImplicitFeedback(
            total_checked=10,
            total_exercises=12,
            per_session=[],
            section_rates=SectionRates(warmup_pct=1.0, main_pct=1.0, cooldown_pct=0.5),
            frequently_skipped=[],
            always_completed=[]
        )
    )
    rendered = render_week_summary(summary)
    assert "WEEK_SUMMARY:W07" in rendered
    assert "COMPLETION:10/12" in rendered
    assert "CONTEXT:Full build week" in rendered
    assert "- TM1_EXTENDED|done|9/13|ok|\"Partial\"" in rendered
    assert "- Goblet Squat|main|done|3x8 @ 15kg|\"felt easy\"" in rendered
    assert "- Total Checked: 10/12" in rendered
    assert "PLAN_ADHERENCE:" in rendered

def test_render_omits_plan_adherence_when_none():
    summary = WeekSummary(
        week_prefix="W07",
        completion="0/0",
        context="Full build week",
        sessions=[],
        exercise_log=[],
        cardio_log=[],
        climbing_log=[],
        pain_status=PainStatus(si_joint="stiff", other=None),
        issues=[],
        wins=[],
        recommendations_next=[],
        plan_adherence=None,
        implicit_feedback=ImplicitFeedback(
            total_checked=0,
            total_exercises=0,
            per_session=[],
            section_rates=SectionRates(warmup_pct=1.0, main_pct=1.0, cooldown_pct=0.5),
            frequently_skipped=[],
            always_completed=[]
        )
    )
    rendered = render_week_summary(summary)
    assert "PLAN_ADHERENCE:" not in rendered
