from unittest.mock import MagicMock

from weekforge.agents.summarize_week_agent import (
    SummarizeDeps,
    _inject_plan_state,
    _inject_planned_sessions,
    _inject_raw_sessions,
)
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import ImplicitFeedback, SectionRates


def _make_deps(**overrides) -> SummarizeDeps:
    defaults = dict(
        user_profile=UserProfile.model_construct(markdown="test"),
        implicit_feedback=ImplicitFeedback(
            total_checked=0, total_exercises=0, per_session=[],
            section_rates=SectionRates(warmup_pct=0.0, main_pct=0.0, cooldown_pct=0.0),
            frequently_skipped=[], always_completed=[],
        ),
        plan_adherence=None,
        tier0_summary_json="{}",
        raw_sessions_markdown="",
        planned_plan_markdown=None,
        plan_state_raw=None,
    )
    defaults.update(overrides)
    return SummarizeDeps(**defaults)


def _make_ctx(deps: SummarizeDeps) -> MagicMock:
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


class TestInjectRawSessions:
    def test_empty_returns_empty(self):
        ctx = _make_ctx(_make_deps(raw_sessions_markdown=""))
        assert _inject_raw_sessions(ctx) == ""

    def test_returns_pre_formatted_markdown(self):
        md = (
            "## Raw Session Blocks (source for exercise_log, cardio_log, climbing_log)\n\n"
            "### Upper A\n"
            "Comments: felt good\n\n"
            "Warmup\n"
            "- [x] Bar Hangs 3x30s\n"
            "- [ ] Side Planks 3x20s\n"
        )
        ctx = _make_ctx(_make_deps(raw_sessions_markdown=md))
        result = _inject_raw_sessions(ctx)
        assert "### Upper A" in result
        assert "- [x] Bar Hangs 3x30s" in result
        assert "- [ ] Side Planks 3x20s" in result
        assert "felt good" in result


class TestInjectPlannedSessions:
    def test_none_returns_empty(self):
        ctx = _make_ctx(_make_deps(planned_plan_markdown=None))
        assert _inject_planned_sessions(ctx) == ""

    def test_empty_string_returns_empty(self):
        ctx = _make_ctx(_make_deps(planned_plan_markdown=""))
        assert _inject_planned_sessions(ctx) == ""

    def test_present_returns_section(self):
        ctx = _make_ctx(_make_deps(planned_plan_markdown="Upper A, Lower B, Cardio"))
        result = _inject_planned_sessions(ctx)
        assert result.startswith("## Planned Sessions")
        assert "Upper A, Lower B, Cardio" in result


class TestInjectPlanState:
    def test_none_returns_empty(self):
        ctx = _make_ctx(_make_deps(plan_state_raw=None))
        assert _inject_plan_state(ctx) == ""

    def test_empty_string_returns_empty(self):
        ctx = _make_ctx(_make_deps(plan_state_raw=""))
        assert _inject_plan_state(ctx) == ""

    def test_present_returns_section(self):
        ctx = _make_ctx(_make_deps(plan_state_raw="GOBLET_SQUAT: 20kg 3x8"))
        result = _inject_plan_state(ctx)
        assert result.startswith("## Existing PLAN_STATE")
        assert "GOBLET_SQUAT: 20kg 3x8" in result
