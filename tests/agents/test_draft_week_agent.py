import pytest

from weekforge.agents.draft_week_agent import (
    DraftWeekDeps,
    WeekFeedbackRow,
    derive_active_flare,
)
from weekforge.models.user_profile import UserProfile
from weekforge.tools.plan_state import PlanState


def test_week_feedback_row_construction():
    row = WeekFeedbackRow(week_prefix="W14", plan_md="Push day", summary_text="Good week")
    assert row.week_prefix == "W14"
    assert row.plan_md == "Push day"
    assert row.summary_text == "Good week"


def test_week_feedback_row_none_fields():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    assert row.plan_md is None
    assert row.summary_text is None


def test_week_feedback_row_is_frozen():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    with pytest.raises(AttributeError):
        row.week_prefix = "W15"


def test_draft_week_deps_construction():
    profile = UserProfile(page_id="p1", markdown="# Profile")
    deps = DraftWeekDeps(
        week_prefix="W15",
        template_sessions=[{"id": "t1"}],
        feedback_window=[],
        plan_state=None,
        plan_state_raw=None,
        user_profile=profile,
        active_flare=False,
        bootstrap=True,
    )
    assert deps.week_prefix == "W15"
    assert deps.bootstrap is True
    assert deps.active_flare is False
    assert len(deps.template_sessions) == 1


def test_draft_week_deps_is_frozen():
    profile = UserProfile(page_id="p1", markdown="# Profile")
    deps = DraftWeekDeps(
        week_prefix="W15",
        template_sessions=[],
        feedback_window=[],
        plan_state=None,
        plan_state_raw=None,
        user_profile=profile,
        active_flare=False,
        bootstrap=True,
    )
    with pytest.raises(AttributeError):
        deps.week_prefix = "W16"


# --- derive_active_flare tests ---


def test_active_flare_false_when_no_data():
    assert derive_active_flare([], None) is False


def test_active_flare_false_when_no_pain_markers():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Great week, no issues")
    assert derive_active_flare([row], PlanState()) is False


def test_active_flare_true_from_recent_summary_si_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="SI joint discomfort after squats")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_spine_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="spine stiffness noted")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_pain_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="knee pain during lunges")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_flare_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="flare up this week")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_tendon_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="tendon soreness in elbow")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_joint_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="joint stiffness in shoulder")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_only_checks_most_recent_feedback_row():
    old_row = WeekFeedbackRow(week_prefix="W12", plan_md=None, summary_text="SI joint pain")
    recent_row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Feeling great")
    # Most recent is last in the list (ordered ascending by week)
    assert derive_active_flare([old_row, recent_row], PlanState()) is False


def test_active_flare_true_from_plan_state_active_issues():
    ps = PlanState(active_issues=["SI joint irritation ongoing"])
    assert derive_active_flare([], ps) is True


def test_active_flare_true_from_plan_state_active_issues_spine():
    ps = PlanState(active_issues=["spine mobility limited"])
    assert derive_active_flare([], ps) is True


def test_active_flare_false_plan_state_active_issues_unrelated():
    ps = PlanState(active_issues=["Need more conditioning volume"])
    assert derive_active_flare([], ps) is False


def test_active_flare_true_when_both_sources_positive():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="SI flare")
    ps = PlanState(active_issues=["SI joint irritation"])
    assert derive_active_flare([row], ps) is True


def test_active_flare_empty_feedback_window_no_plan_state():
    assert derive_active_flare([], None) is False


def test_active_flare_row_with_none_summary():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    assert derive_active_flare([row], PlanState()) is False


# --- case-insensitive keyword matching ---


def test_active_flare_keyword_case_insensitive_pain():
    """'Pain' (capital P) still triggers flare."""
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Pain in lower back")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_keyword_case_insensitive_spine():
    """'SPINE' (all caps) still triggers flare."""
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="SPINE compression noted")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_keyword_plan_state_joint_in_active_issues():
    """'joint' in plan_state.active_issues triggers flare from chronic path."""
    ps = PlanState(active_issues=["hip joint irritation"])
    assert derive_active_flare([], ps) is True


def test_active_flare_keyword_plan_state_tendon_in_active_issues():
    """'tendon' in plan_state.active_issues triggers flare."""
    ps = PlanState(active_issues=["patellar tendon soreness"])
    assert derive_active_flare([], ps) is True


def test_active_flare_plan_state_empty_active_issues():
    """plan_state with empty active_issues list → no chronic issue → False (assuming no recent pain)."""
    ps = PlanState(active_issues=[])
    assert derive_active_flare([], ps) is False


# --- most-recent-only semantics with 3-row window ---


def test_active_flare_only_checks_last_row_in_3_row_window():
    """Pain in middle row is ignored; only the last (most recent) row is checked."""
    row1 = WeekFeedbackRow(week_prefix="W12", plan_md=None, summary_text="Good week")
    row2 = WeekFeedbackRow(week_prefix="W13", plan_md=None, summary_text="SI flare this week")
    row3 = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Recovered, feeling fine")
    assert derive_active_flare([row1, row2, row3], PlanState()) is False
