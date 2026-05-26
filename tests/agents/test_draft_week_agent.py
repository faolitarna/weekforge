import pytest
from unittest.mock import MagicMock

from weekforge.agents.draft_week_agent import (
    DraftWeekDeps,
    _inject_active_flare,
    _inject_bootstrap_hint,
    _inject_feedback_window,
    _inject_plan_state,
    _inject_templates,
    _inject_user_profile,
)
from weekforge.tools.context_loader import (
    FeedbackRow,
    derive_active_flare,
)
from weekforge.tools.plan_state import PlanState


def test_draft_week_deps_construction():
    deps = DraftWeekDeps(
        week_prefix="W15",
        template_markdown="## Templates\n### W15: Push",
        feedback_window_markdown="## Previous Weeks\n### W14",
        plan_state_raw=None,
        user_profile_markdown="# Profile",
        active_flare=False,
        bootstrap=True,
    )
    assert deps.week_prefix == "W15"
    assert deps.bootstrap is True
    assert deps.active_flare is False
    assert "Push" in deps.template_markdown


def test_draft_week_deps_is_frozen():
    deps = DraftWeekDeps(
        week_prefix="W15",
        template_markdown="",
        feedback_window_markdown="",
        plan_state_raw=None,
        user_profile_markdown="# Profile",
        active_flare=False,
        bootstrap=True,
    )
    with pytest.raises(AttributeError):
        deps.week_prefix = "W16"


# --- derive_active_flare tests ---


def test_active_flare_false_when_no_data():
    assert derive_active_flare([], None) is False


def test_active_flare_false_when_no_pain_markers():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="Great week, no issues")
    assert derive_active_flare([row], PlanState()) is False


def test_active_flare_true_from_recent_summary_si_keyword():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="SI joint discomfort after squats")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_spine_keyword():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="spine stiffness noted")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_pain_keyword():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="knee pain during lunges")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_flare_keyword():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="flare up this week")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_tendon_keyword():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="tendon soreness in elbow")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_joint_keyword():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="joint stiffness in shoulder")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_only_checks_most_recent_feedback_row():
    old_row = FeedbackRow(week_prefix="W12", plan_md=None, summary_text="SI joint pain")
    recent_row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="Feeling great")
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
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="SI flare")
    ps = PlanState(active_issues=["SI joint irritation"])
    assert derive_active_flare([row], ps) is True


def test_active_flare_empty_feedback_window_no_plan_state():
    assert derive_active_flare([], None) is False


def test_active_flare_row_with_none_summary():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    assert derive_active_flare([row], PlanState()) is False


def test_active_flare_keyword_case_insensitive_pain():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="Pain in lower back")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_keyword_case_insensitive_spine():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="SPINE compression noted")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_keyword_plan_state_joint_in_active_issues():
    ps = PlanState(active_issues=["hip joint irritation"])
    assert derive_active_flare([], ps) is True


def test_active_flare_keyword_plan_state_tendon_in_active_issues():
    ps = PlanState(active_issues=["patellar tendon soreness"])
    assert derive_active_flare([], ps) is True


def test_active_flare_plan_state_empty_active_issues():
    ps = PlanState(active_issues=[])
    assert derive_active_flare([], ps) is False


def test_active_flare_only_checks_last_row_in_3_row_window():
    row1 = FeedbackRow(week_prefix="W12", plan_md=None, summary_text="Good week")
    row2 = FeedbackRow(week_prefix="W13", plan_md=None, summary_text="SI flare this week")
    row3 = FeedbackRow(week_prefix="W14", plan_md=None, summary_text="Recovered, feeling fine")
    assert derive_active_flare([row1, row2, row3], PlanState()) is False


# --- FeedbackRow tests ---


def test_feedback_row_construction():
    row = FeedbackRow(week_prefix="W14", plan_md="Push day", summary_text="Good week")
    assert row.week_prefix == "W14"
    assert row.plan_md == "Push day"
    assert row.summary_text == "Good week"


def test_feedback_row_none_fields():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    assert row.plan_md is None
    assert row.summary_text is None


def test_feedback_row_is_frozen():
    row = FeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    with pytest.raises(AttributeError):
        row.week_prefix = "W15"


# --- instruction decorator tests ---


def _make_draft_deps(**overrides) -> DraftWeekDeps:
    defaults = dict(
        week_prefix="W15",
        template_markdown="## Template Sessions\n\n### W15: Push + Hinge\n",
        feedback_window_markdown="",
        plan_state_raw=None,
        user_profile_markdown="# Test Profile\nGoals: get strong",
        active_flare=False,
        bootstrap=False,
    )
    defaults.update(overrides)
    return DraftWeekDeps(**defaults)


def _make_ctx(deps) -> MagicMock:
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


class TestInjectUserProfile:
    def test_returns_profile_markdown(self):
        deps = _make_draft_deps()
        ctx = _make_ctx(deps)
        result = _inject_user_profile(ctx)
        assert "## Active User Profile" in result
        assert "# Test Profile" in result
        assert "Goals: get strong" in result


class TestInjectTemplates:
    def test_empty_templates_returns_empty(self):
        deps = _make_draft_deps(template_markdown="")
        ctx = _make_ctx(deps)
        assert _inject_templates(ctx) == ""

    def test_returns_pre_formatted_markdown(self):
        md = "## Template Sessions\n\n### W15: Push + Hinge\nWorkoutDescription: Z2 run\n"
        deps = _make_draft_deps(template_markdown=md)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert result == md


class TestInjectFeedbackWindow:
    def test_empty_window_returns_empty(self):
        deps = _make_draft_deps(feedback_window_markdown="")
        ctx = _make_ctx(deps)
        assert _inject_feedback_window(ctx) == ""

    def test_returns_pre_formatted_markdown(self):
        md = "## Previous Weeks Feedback\n\n### W13\nPlan:\nPush day\nSummary:\nGood week\n"
        deps = _make_draft_deps(feedback_window_markdown=md)
        ctx = _make_ctx(deps)
        result = _inject_feedback_window(ctx)
        assert result == md


class TestInjectPlanState:
    def test_none_returns_empty(self):
        deps = _make_draft_deps(plan_state_raw=None)
        ctx = _make_ctx(deps)
        assert _inject_plan_state(ctx) == ""

    def test_empty_returns_empty(self):
        deps = _make_draft_deps(plan_state_raw="")
        ctx = _make_ctx(deps)
        assert _inject_plan_state(ctx) == ""

    def test_present_returns_section(self):
        deps = _make_draft_deps(plan_state_raw="PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk")
        ctx = _make_ctx(deps)
        result = _inject_plan_state(ctx)
        assert "## Existing PLAN_STATE" in result
        assert "MESOCYCLE:Test|12wk" in result


class TestInjectActiveFlare:
    def test_flare_yes(self):
        deps = _make_draft_deps(active_flare=True)
        ctx = _make_ctx(deps)
        assert _inject_active_flare(ctx) == "ACTIVE_FLARE: YES"

    def test_flare_no(self):
        deps = _make_draft_deps(active_flare=False)
        ctx = _make_ctx(deps)
        assert _inject_active_flare(ctx) == "ACTIVE_FLARE: NO"


class TestInjectBootstrapHint:
    def test_not_bootstrap_returns_empty(self):
        deps = _make_draft_deps(bootstrap=False)
        ctx = _make_ctx(deps)
        assert _inject_bootstrap_hint(ctx) == ""

    def test_bootstrap_returns_hint(self):
        deps = _make_draft_deps(bootstrap=True)
        ctx = _make_ctx(deps)
        result = _inject_bootstrap_hint(ctx)
        assert "## Bootstrap Mode" in result
        assert "conservative" in result.lower()
