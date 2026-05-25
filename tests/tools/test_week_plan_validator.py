import pytest

from weekforge.models.week_plan import PlannedSession, WeekPlan


def _plan(tags_per_session: list[list[str]]) -> WeekPlan:
    """Build a WeekPlan from a list of tag-lists, one per session."""
    sessions = [
        PlannedSession(name=f"S{i}", duration_min=60, focus_tags=tags)
        for i, tags in enumerate(tags_per_session, 1)
    ]
    return WeekPlan(week_prefix="W15", sessions=sessions)


class TestPullPushRatio:
    def test_all_pull_no_push(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([["pull"], ["pull", "core"], ["pull", "hinge"]])
        passed, diff = validate_week_plan(plan)
        assert passed is True
        assert diff is None

    def test_zero_push_zero_pull_passes(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([["cardio", "z2"], ["cardio", "z2"], ["mobility"]])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_exact_threshold_1_5_passes(self):
        """3 pull, 2 push → ratio 1.5:1 — exactly at threshold."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"], ["pull"],
            ["push"], ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_below_threshold_fails(self):
        """2 pull, 2 push → ratio 1.0:1 — below 1.5."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"],
            ["push"], ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "pull:push" in diff

    def test_dual_tagged_session_counts_half(self):
        """Session tagged both pull and push → 0.5 each."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        # 2 pure pull + 1 dual + 1 pure push → pull=2.5, push=1.5 → ratio=1.67 → pass
        plan = _plan([
            ["pull"], ["pull"],
            ["pull", "push"],
            ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_dual_tagged_below_threshold(self):
        """1 pure pull + 1 dual + 2 pure push → pull=1.5, push=2.5 → ratio=0.6 → fail."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"],
            ["pull", "push"],
            ["push"], ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "pull:push" in diff


class TestConditioningFloor:
    def test_two_conditioning_passes(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["push"],
            ["cardio", "z2"], ["hike", "uphill"],
        ])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_one_conditioning_fails(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"], ["pull"],
            ["push"],
            ["cardio", "z2"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "conditioning" in diff.lower()

    def test_zero_conditioning_fails(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"], ["push"],
            ["mobility"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "conditioning" in diff.lower()

    def test_all_conditioning_tags_count(self):
        """Each conditioning tag in the set counts the session."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        for tag in ["cardio", "z1", "z2", "z3", "uphill", "loaded", "hike", "run"]:
            plan = _plan([
                ["pull"], ["pull"], ["push"],
                [tag], [tag],
            ])
            passed, _ = validate_week_plan(plan)
            assert passed is True, f"Tag '{tag}' should count as conditioning"


class TestBothViolations:
    def test_both_violations_reported(self):
        """Both ratio and conditioning fail → diff mentions both."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["push"], ["push"],
            ["mobility"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "pull:push" in diff
        assert "conditioning" in diff.lower()


class TestEmptyPlan:
    def test_empty_sessions_passes_ratio_fails_conditioning(self):
        """0 sessions → 0 push, 0 pull (ratio ok), 0 conditioning (fail)."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "conditioning" in diff.lower()
