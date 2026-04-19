from weekforge.tools.plan_state import parse_plan_state, update_mechanical_fields, render_plan_state
from weekforge.models.week_summary import WeekSummary, ImplicitFeedback, SectionRates, PainStatus, ExerciseLogEntry

def test_plan_state_incremental_mechanical_updates():
    text = """PLAN_STATE:W01-W05
MESOCYCLE:Strength|8wk
WEEKS_COMPLETED:5|AVG_COMPLETION:90.0%

MAIN_LIFTS:
- Squat:100kg->105kg|peak:105kg|trend:up

ADHERENCE:
- weekly:80%->100%|avg:90%
"""
    state = parse_plan_state(text)
    assert state.weeks_completed == 5
    assert state.mesocycle_name == "Strength"
    
    summary = WeekSummary(
        week_prefix="W06",
        completion="10/10",
        sessions=[],
        exercise_log=[
            ExerciseLogEntry(name="Squat", planned_weight="110kg", actual_weight=None, planned_sets=3, planned_reps="5", role="main", status="done")
        ],
        pain_status=PainStatus(si_joint="ok", other=None),
        implicit_feedback=ImplicitFeedback(
            total_checked=10,
            total_exercises=10,
            per_session=[],
            section_rates=SectionRates(warmup_pct=1.0, main_pct=1.0, cooldown_pct=0.5),
            frequently_skipped=[],
            always_completed=[]
        )
    )
    
    state = update_mechanical_fields(state, summary)
    
    assert state.weeks_completed == 6
    # 5 weeks @ 90% = 4.5, + 1 week @ 100% = 5.5 / 6 = 91.6666%
    assert abs(state.avg_completion - 91.6666) < 0.1
    
    # Check chain appends
    assert "Squat:100kg->105kg->110kg|peak:105kg|trend:up" in state.main_lifts[0]
    assert "weekly:80%->100%->100%|avg:91%" in state.adherence[0]

def test_plan_state_bootstrap_skeleton_when_no_summaries():
    text = ""
    state = parse_plan_state(text)
    assert state.weeks_completed == 0
    assert state.total_weeks == 0
    assert len(state.main_lifts) == 0
