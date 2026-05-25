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


# --- instruction decorator tests ---

from unittest.mock import MagicMock


def _make_draft_deps(**overrides) -> "DraftWeekDeps":
    from weekforge.agents.draft_week_agent import DraftWeekDeps, WeekFeedbackRow
    from weekforge.models.user_profile import UserProfile
    from weekforge.tools.plan_state import PlanState

    defaults = dict(
        week_prefix="W15",
        template_sessions=[],
        feedback_window=[],
        plan_state=None,
        plan_state_raw=None,
        user_profile=UserProfile(page_id="up1", markdown="# Test Profile\nGoals: get strong"),
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
        from weekforge.agents.draft_week_agent import _inject_user_profile
        deps = _make_draft_deps()
        ctx = _make_ctx(deps)
        result = _inject_user_profile(ctx)
        assert "## Active User Profile" in result
        assert "# Test Profile" in result
        assert "Goals: get strong" in result


class TestInjectTemplates:
    def test_empty_templates_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_templates
        deps = _make_draft_deps(template_sessions=[])
        ctx = _make_ctx(deps)
        assert _inject_templates(ctx) == ""

    def test_renders_template_titles(self):
        from weekforge.agents.draft_week_agent import _inject_templates
        templates = [
            {"id": "t1", "properties": {"Title": {"type": "title", "title": [{"plain_text": "W15: Push + Hinge"}]}}},
            {"id": "t2", "properties": {"Title": {"type": "title", "title": [{"plain_text": "W15: Squat Day"}]}}},
        ]
        deps = _make_draft_deps(template_sessions=templates)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert "## Template Sessions" in result
        assert "W15: Push + Hinge" in result
        assert "W15: Squat Day" in result

    def test_renders_all_non_empty_properties(self):
        from weekforge.agents.draft_week_agent import _inject_templates
        templates = [
            {
                "id": "t1",
                "properties": {
                    "Title": {"type": "title", "title": [{"plain_text": "W15: Aerobic Base"}]},
                    "WorkoutDescription": {"type": "rich_text", "rich_text": [{"plain_text": "Z2 uphill run on rolling terrain"}]},
                    "CoachComments": {"type": "rich_text", "rich_text": [{"plain_text": "Keep HR below aerobic threshold"}]},
                    "PlannedDuration": {"type": "number", "number": 1},
                    "Energy": {"type": "rich_text", "rich_text": []},
                },
            },
        ]
        deps = _make_draft_deps(template_sessions=templates)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert "WorkoutDescription: Z2 uphill run" in result
        assert "CoachComments: Keep HR below" in result
        assert "PlannedDuration: 1" in result
        assert "Energy" not in result
        assert "Title:" not in result

    def test_skips_empty_properties(self):
        from weekforge.agents.draft_week_agent import _inject_templates
        templates = [
            {
                "id": "t1",
                "properties": {
                    "Title": {"type": "title", "title": [{"plain_text": "W15: Push"}]},
                    "WorkoutDescription": {"type": "rich_text", "rich_text": []},
                    "CoachComments": {"type": "rich_text", "rich_text": []},
                    "PlannedDuration": {"type": "number", "number": None},
                },
            },
        ]
        deps = _make_draft_deps(template_sessions=templates)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert "W15: Push" in result
        assert "WorkoutDescription" not in result
        assert "CoachComments" not in result
        assert "PlannedDuration" not in result


class TestExtractPropText:
    def test_rich_text(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        prop = {"type": "rich_text", "rich_text": [{"plain_text": "hello"}, {"plain_text": " world"}]}
        assert _extract_prop_text(prop) == "hello world"

    def test_rich_text_empty(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        assert _extract_prop_text({"type": "rich_text", "rich_text": []}) == ""

    def test_number(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        assert _extract_prop_text({"type": "number", "number": 42}) == "42"

    def test_number_none(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        assert _extract_prop_text({"type": "number", "number": None}) == ""

    def test_date(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        assert _extract_prop_text({"type": "date", "date": {"start": "2024-06-03"}}) == "2024-06-03"

    def test_date_none(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        assert _extract_prop_text({"type": "date", "date": None}) == ""

    def test_unknown_type(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text
        assert _extract_prop_text({"type": "checkbox", "checkbox": True}) == ""


class TestInjectFeedbackWindow:
    def test_empty_window_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_feedback_window
        deps = _make_draft_deps(feedback_window=[])
        ctx = _make_ctx(deps)
        assert _inject_feedback_window(ctx) == ""

    def test_renders_plan_and_summary(self):
        from weekforge.agents.draft_week_agent import WeekFeedbackRow, _inject_feedback_window
        rows = [
            WeekFeedbackRow(week_prefix="W13", plan_md="Plan W13", summary_text="Summary W13"),
            WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Summary W14"),
        ]
        deps = _make_draft_deps(feedback_window=rows)
        ctx = _make_ctx(deps)
        result = _inject_feedback_window(ctx)
        assert "## Previous Weeks Feedback" in result
        assert "### W13" in result
        assert "Plan W13" in result
        assert "Summary W13" in result
        assert "### W14" in result
        assert "Summary W14" in result

    def test_skips_none_fields(self):
        from weekforge.agents.draft_week_agent import WeekFeedbackRow, _inject_feedback_window
        rows = [WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)]
        deps = _make_draft_deps(feedback_window=rows)
        ctx = _make_ctx(deps)
        result = _inject_feedback_window(ctx)
        assert "### W14" in result
        assert "Plan:" not in result
        assert "Summary:" not in result


class TestInjectPlanState:
    def test_none_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_plan_state
        deps = _make_draft_deps(plan_state_raw=None)
        ctx = _make_ctx(deps)
        assert _inject_plan_state(ctx) == ""

    def test_empty_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_plan_state
        deps = _make_draft_deps(plan_state_raw="")
        ctx = _make_ctx(deps)
        assert _inject_plan_state(ctx) == ""

    def test_present_returns_section(self):
        from weekforge.agents.draft_week_agent import _inject_plan_state
        deps = _make_draft_deps(plan_state_raw="PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk")
        ctx = _make_ctx(deps)
        result = _inject_plan_state(ctx)
        assert "## Existing PLAN_STATE" in result
        assert "MESOCYCLE:Test|12wk" in result


class TestInjectActiveFlare:
    def test_flare_yes(self):
        from weekforge.agents.draft_week_agent import _inject_active_flare
        deps = _make_draft_deps(active_flare=True)
        ctx = _make_ctx(deps)
        assert _inject_active_flare(ctx) == "ACTIVE_FLARE: YES"

    def test_flare_no(self):
        from weekforge.agents.draft_week_agent import _inject_active_flare
        deps = _make_draft_deps(active_flare=False)
        ctx = _make_ctx(deps)
        assert _inject_active_flare(ctx) == "ACTIVE_FLARE: NO"


class TestInjectBootstrapHint:
    def test_not_bootstrap_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_bootstrap_hint
        deps = _make_draft_deps(bootstrap=False)
        ctx = _make_ctx(deps)
        assert _inject_bootstrap_hint(ctx) == ""

    def test_bootstrap_returns_hint(self):
        from weekforge.agents.draft_week_agent import _inject_bootstrap_hint
        deps = _make_draft_deps(bootstrap=True)
        ctx = _make_ctx(deps)
        result = _inject_bootstrap_hint(ctx)
        assert "## Bootstrap Mode" in result
        assert "conservative" in result.lower()
