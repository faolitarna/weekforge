from weekforge.models.week_summary import (
    CardioEntry,
    ClimbingEntry,
    ExerciseLogEntry,
    ImplicitFeedback,
    JointEntry,
    ModificationPattern,
    PlanAdherence,
    SectionRates,
    SessionLine,
    SkipPattern,
    SkippedPattern,
    WeekSummary,
)
from weekforge.tools.week_summary_renderer import render_week_summary


def _make_summary(**overrides) -> WeekSummary:
    base = dict(
        week_prefix="W07",
        completion="10/12",
        context="Full build week",
        sessions=[
            SessionLine(name="TM1_EXTENDED", status="done", exercises_done=9, exercises_total=13, pain_status="ok", comment="Partial")
        ],
        exercise_log=[
            ExerciseLogEntry(name="Goblet Squat", planned_weight="15kg", planned_sets=3, planned_reps="8", role="main", status="done", feedback="felt easy")
        ],
        cardio_log=[CardioEntry(kind="z2_run", raw="dist: 5km")],
        climbing_log=[ClimbingEntry(kind="grades", raw="v4-v5")],
        pain_status=[JointEntry(name="si_joint", status="stiff")],
        issues=["Bad sleep"],
        wins=["Felt strong"],
        recommendations_next=["Sleep more"],
        plan_adherence=PlanAdherence(
            planned_total=12, completed=10, modified=1, skipped=1,
            modification_patterns=[ModificationPattern(exercise="ExA", planned="B", actual="C")],
            skip_patterns=[SkipPattern(exercise="REST", reason="fatigue")],
        ),
        implicit_feedback=ImplicitFeedback(
            total_checked=10,
            total_exercises=12,
            per_session=[],
            section_rates=SectionRates(warmup_pct=1.0, main_pct=1.0, cooldown_pct=0.5),
            frequently_skipped=[],
            always_completed=[],
        ),
    )
    base.update(overrides)
    return WeekSummary(**base)


def test_render_week_summary():
    rendered = render_week_summary(_make_summary())
    assert "WEEK_SUMMARY:W07" in rendered
    assert "COMPLETION:10/12" in rendered
    assert "CONTEXT:Full build week" in rendered
    assert "- TM1_EXTENDED|done|9/13|ok|\"Partial\"" in rendered
    assert "PLAN_ADHERENCE:" in rendered


def test_render_exercise_log_canonical_format():
    rendered = render_week_summary(_make_summary())
    assert "- Goblet Squat:15kgx3x8|main|done|\"felt easy\"" in rendered


def test_render_plan_adherence_pipe_delimited():
    rendered = render_week_summary(_make_summary())
    assert "- planned:12|completed:10|modified:1|skipped:1" in rendered
    assert "- modification_patterns:ExA->C" in rendered
    assert "- skip_patterns:REST:fatigue" in rendered


def test_render_implicit_feedback_canonical_format():
    rendered = render_week_summary(_make_summary())
    assert "- checkbox_completion:10/12|83%" in rendered
    assert "- section_rates:warmup:100%|main:100%|cooldown:50%" in rendered


def test_render_pain_status_no_trailing_nulls():
    rendered = render_week_summary(_make_summary())
    assert "- si_joint:stiff" in rendered

    with_triggers = _make_summary(pain_status=[JointEntry(name="si_joint", status="stiff", triggers="deadlifts")])
    rendered2 = render_week_summary(with_triggers)
    assert "- si_joint:stiff|deadlifts" in rendered2

    with_both = _make_summary(pain_status=[JointEntry(name="si_joint", status="stiff", triggers="deadlifts", what_helped="heat")])
    rendered3 = render_week_summary(with_both)
    assert "- si_joint:stiff|deadlifts|heat" in rendered3


def test_render_pain_status_what_helped_without_triggers():
    summary = _make_summary(pain_status=[JointEntry(name="si_joint", status="ok", what_helped="rest")])
    rendered = render_week_summary(summary)
    assert "- si_joint:ok|rest" in rendered


def test_render_omits_plan_adherence_when_none():
    rendered = render_week_summary(_make_summary(
        sessions=[],
        exercise_log=[],
        cardio_log=[],
        climbing_log=[],
        pain_status=[],
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
            always_completed=[],
        ),
    ))
    assert "PLAN_ADHERENCE:" not in rendered


def test_render_omits_modification_patterns_when_empty():
    summary = _make_summary(plan_adherence=PlanAdherence(
        planned_total=5, completed=5, modified=0, skipped=0,
        modification_patterns=[],
        skip_patterns=[],
    ))
    rendered = render_week_summary(summary)
    assert "modification_patterns" not in rendered
    assert "skip_patterns" not in rendered


def test_render_frequently_skipped_single_line():
    summary = _make_summary(implicit_feedback=ImplicitFeedback(
        total_checked=8,
        total_exercises=10,
        per_session=[],
        section_rates=SectionRates(warmup_pct=1.0, main_pct=0.8, cooldown_pct=0.5),
        frequently_skipped=[
            SkippedPattern(exercise="Foam Roller", skip_rate=0.6),
            SkippedPattern(exercise="Cat-Cow", skip_rate=0.4),
        ],
        always_completed=["Pull-ups", "Bar Hangs"],
    ))
    rendered = render_week_summary(summary)
    assert "- frequently_skipped:Foam Roller:60%|Cat-Cow:40%" in rendered
    assert "- always_completed:Pull-ups|Bar Hangs" in rendered


def test_render_implicit_feedback_zero_total():
    summary = _make_summary(implicit_feedback=ImplicitFeedback(
        total_checked=0,
        total_exercises=0,
        per_session=[],
        section_rates=SectionRates(warmup_pct=0.0, main_pct=0.0, cooldown_pct=0.0),
        frequently_skipped=[],
        always_completed=[],
    ))
    rendered = render_week_summary(summary)
    assert "- checkbox_completion:0/0|0%" in rendered


def test_render_no_per_session_lines():
    rendered = render_week_summary(_make_summary())
    assert "Session " not in rendered


def test_render_exercise_log_planned_to_actual_notation():
    summary = _make_summary(exercise_log=[
        ExerciseLogEntry(
            name="Trap Bar DL",
            planned_weight="60kg", actual_weight="62kg",
            planned_sets=4, actual_sets=4,
            planned_reps="6", actual_reps="6",
            role="main", status="done_modified",
        )
    ])
    rendered = render_week_summary(summary)
    assert "- Trap Bar DL:60kg->62kgx4x6|main|done_modified" in rendered


def test_render_pain_status_exact_line_no_extras():
    # "- si_joint:stiff" substring would also match "- si_joint:stiff|deadlifts" — test line exactly
    rendered = render_week_summary(_make_summary(
        pain_status=[JointEntry(name="si_joint", status="stiff")]
    ))
    lines = rendered.splitlines()
    assert "- si_joint:stiff" in lines
    assert not any(line.startswith("- si_joint:stiff|") for line in lines)


def test_render_multiple_joint_entries():
    summary = _make_summary(pain_status=[
        JointEntry(name="si_joint", status="stiff", triggers="deadlifts"),
        JointEntry(name="other", status="knee soreness"),
    ])
    rendered = render_week_summary(summary)
    lines = rendered.splitlines()
    assert "- si_joint:stiff|deadlifts" in lines
    assert "- other:knee soreness" in lines


def test_render_empty_pain_status_keeps_section_header():
    rendered = render_week_summary(_make_summary(pain_status=[]))
    assert "PAIN_STATUS:" in rendered


def test_render_multiple_modification_patterns_pipe_joined():
    summary = _make_summary(plan_adherence=PlanAdherence(
        planned_total=10, completed=8, modified=2, skipped=0,
        modification_patterns=[
            ModificationPattern(exercise="ExA", planned="X", actual="Y"),
            ModificationPattern(exercise="ExB", planned="P", actual="Q"),
        ],
        skip_patterns=[],
    ))
    rendered = render_week_summary(summary)
    assert "- modification_patterns:ExA->Y|ExB->Q" in rendered


def test_render_multiple_skip_patterns_pipe_joined():
    summary = _make_summary(plan_adherence=PlanAdherence(
        planned_total=10, completed=7, modified=0, skipped=3,
        modification_patterns=[],
        skip_patterns=[
            SkipPattern(exercise="REST", reason="fatigue"),
            SkipPattern(exercise="TM2", reason="travel"),
        ],
    ))
    rendered = render_week_summary(summary)
    assert "- skip_patterns:REST:fatigue|TM2:travel" in rendered
