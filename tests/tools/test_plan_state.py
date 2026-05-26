from weekforge.models.week_summary import (
    ExerciseLogEntry,
    ImplicitFeedback,
    JointEntry,
    SectionRates,
    WeekSummary,
)
from weekforge.tools.plan_state import PlanState


def _make_summary(completion="10/10", exercise_log=None, pain_status=None):
    return WeekSummary(
        week_prefix="W06",
        completion=completion,
        sessions=[],
        exercise_log=exercise_log or [],
        pain_status=pain_status or [],
        implicit_feedback=ImplicitFeedback(
            total_checked=10, total_exercises=10, per_session=[],
            section_rates=SectionRates(warmup_pct=1.0, main_pct=1.0, cooldown_pct=0.5),
            frequently_skipped=[], always_completed=[],
        ),
    )


def test_from_text_parses_metadata():
    text = """PLAN_STATE:W01-W05
MESOCYCLE:Strength|8wk
WEEKS_COMPLETED:5|AVG_COMPLETION:90.0%

MAIN_LIFTS:
- Squat:100kg->105kg|peak:105kg|trend:up

ADHERENCE:
- weekly:80%->100%|avg:90%
"""
    state = PlanState.from_text(text)
    assert state.weeks_completed == 5
    assert state.mesocycle_name == "Strength"
    assert state.total_weeks == 8
    assert state.avg_completion == 90.0
    assert len(state.main_lifts) == 1
    assert len(state.adherence) == 1


def test_from_text_bootstrap_skeleton():
    state = PlanState.from_text("")
    assert state.weeks_completed == 0
    assert state.total_weeks == 0
    assert len(state.main_lifts) == 0


def test_to_text_round_trips():
    text = """PLAN_STATE:W01-W05
MESOCYCLE:Strength|8wk
WEEKS_COMPLETED:5|AVG_COMPLETION:90.0%

MAIN_LIFTS:
- Squat:100kg->105kg|peak:105kg|trend:up

ADHERENCE:
- weekly:80%->100%|avg:90%"""
    state = PlanState.from_text(text)
    rendered = state.to_text("W05")
    reparsed = PlanState.from_text(rendered)
    assert reparsed.mesocycle_name == state.mesocycle_name
    assert reparsed.weeks_completed == state.weeks_completed
    assert reparsed.main_lifts == state.main_lifts
    assert reparsed.adherence == state.adherence


def test_apply_mechanical_update_incremental():
    text = """PLAN_STATE:W01-W05
MESOCYCLE:Strength|8wk
WEEKS_COMPLETED:5|AVG_COMPLETION:90.0%

MAIN_LIFTS:
- Squat:100kg->105kg|peak:105kg|trend:up

ADHERENCE:
- weekly:80%->100%|avg:90%
"""
    state = PlanState.from_text(text)
    summary = _make_summary(
        exercise_log=[
            ExerciseLogEntry(
                name="Squat", planned_weight="110kg", actual_weight=None,
                planned_sets=3, planned_reps="5", role="main", status="done",
            ),
        ],
        pain_status=[JointEntry(name="si_joint", status="ok")],
    )

    state.apply_mechanical_update(summary)

    assert state.weeks_completed == 6
    assert abs(state.avg_completion - 91.6666) < 0.1
    assert "Squat:100kg->105kg->110kg|peak:105kg|trend:up" in state.main_lifts[0]
    assert "weekly:80%->100%->100%|avg:91%" in state.adherence[0]


def test_apply_mechanical_update_bootstrap():
    state = PlanState()
    summary = _make_summary(completion="3/4")

    state.apply_mechanical_update(summary)

    assert state.weeks_completed == 1
    assert state.avg_completion == 75.0
    assert state.adherence[0] == "weekly:75%|avg:75%"


def test_has_active_pain_positive():
    state = PlanState(active_issues=["SI joint:W03:moderate pain"])
    assert state.has_active_pain() is True


def test_has_active_pain_negative():
    state = PlanState(active_issues=["motivation:W03:low energy"])
    assert state.has_active_pain() is False


def test_has_active_pain_empty():
    state = PlanState()
    assert state.has_active_pain() is False
