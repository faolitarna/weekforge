from weekforge.models.week_plan import WeekPlan

_CONDITIONING_TAGS = frozenset({"cardio", "z1", "z2", "z3", "uphill", "loaded", "hike", "run"})

_PULL_PUSH_THRESHOLD = 1.5
_CONDITIONING_FLOOR = 2


def validate_week_plan(plan: WeekPlan) -> tuple[bool, str | None]:
    pull_count = 0.0
    push_count = 0.0
    conditioning_count = 0

    for s in plan.sessions:
        tags = set(s.focus_tags)
        has_pull = "pull" in tags
        has_push = "push" in tags
        if has_pull and has_push:
            pull_count += 0.5
            push_count += 0.5
        elif has_pull:
            pull_count += 1
        elif has_push:
            push_count += 1

        if tags & _CONDITIONING_TAGS:
            conditioning_count += 1

    issues: list[str] = []

    # Ratio check only meaningful once there are at least 2 push sessions to measure against.
    if push_count >= 2 and pull_count / push_count < _PULL_PUSH_THRESHOLD:
        issues.append(
            f"pull:push={pull_count:.1f}:{push_count:.1f} "
            f"(ratio {pull_count / push_count:.1f}:1, need >={_PULL_PUSH_THRESHOLD}:1)"
        )

    # Conditioning floor applies whenever strength work (push) is present, or the plan is empty
    # (a pure pull-only week is exempt — it's a deload pattern, not a mixed week).
    if (len(plan.sessions) == 0 or push_count > 0) and conditioning_count < _CONDITIONING_FLOOR:
        issues.append(
            f"conditioning_sessions={conditioning_count} (need >={_CONDITIONING_FLOOR})"
        )

    if issues:
        diff = "Plan validation failed. Issues: " + "; ".join(issues) + ". Revise the plan to fix these specifically. Keep all other constraints intact."
        return False, diff

    return True, None
