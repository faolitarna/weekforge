import json
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
        raw_sessions_json="[]",
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
    def test_empty_sessions_returns_empty(self):
        ctx = _make_ctx(_make_deps(raw_sessions_json="[]"))
        assert _inject_raw_sessions(ctx) == ""

    def test_malformed_json_returns_empty(self):
        ctx = _make_ctx(_make_deps(raw_sessions_json="{bad json"))
        assert _inject_raw_sessions(ctx) == ""

    def test_filters_to_heading_and_todo_only(self):
        sessions = [
            {
                "name": "Upper A",
                "page_id": "p1",
                "blocks": [
                    {"block_type": "heading_2", "text": "Warmup", "checked": None},
                    {"block_type": "to_do", "text": "Bar Hangs 3x30s", "checked": True},
                    {"block_type": "paragraph", "text": "Some note", "checked": None},
                    {"block_type": "to_do", "text": "Side Planks 3x20s", "checked": False},
                    {"block_type": "divider", "text": "", "checked": None},
                ],
                "comments": ["felt good"],
            }
        ]
        ctx = _make_ctx(_make_deps(raw_sessions_json=json.dumps(sessions)))
        result = _inject_raw_sessions(ctx)
        assert "### Upper A" in result
        assert "Warmup" in result
        assert "- [x] Bar Hangs 3x30s" in result
        assert "- [ ] Side Planks 3x20s" in result
        assert "paragraph" not in result
        assert "divider" not in result
        assert "Some note" not in result

    def test_comments_rendered(self):
        sessions = [
            {
                "name": "Session",
                "page_id": "p1",
                "blocks": [{"block_type": "to_do", "text": "Squat", "checked": True}],
                "comments": ["knee felt stiff", "reduced weight"],
            }
        ]
        ctx = _make_ctx(_make_deps(raw_sessions_json=json.dumps(sessions)))
        result = _inject_raw_sessions(ctx)
        assert "knee felt stiff, reduced weight" in result

    def test_no_comments_shows_none(self):
        sessions = [
            {
                "name": "Session",
                "page_id": "p1",
                "blocks": [{"block_type": "to_do", "text": "Squat", "checked": True}],
                "comments": [],
            }
        ]
        ctx = _make_ctx(_make_deps(raw_sessions_json=json.dumps(sessions)))
        result = _inject_raw_sessions(ctx)
        assert "Comments: none" in result

    def test_multiple_sessions_separated(self):
        sessions = [
            {"name": "A", "page_id": "p1", "blocks": [], "comments": []},
            {"name": "B", "page_id": "p2", "blocks": [], "comments": []},
        ]
        ctx = _make_ctx(_make_deps(raw_sessions_json=json.dumps(sessions)))
        result = _inject_raw_sessions(ctx)
        assert "### A" in result
        assert "### B" in result


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
