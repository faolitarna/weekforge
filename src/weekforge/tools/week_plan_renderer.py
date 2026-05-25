from weekforge.models.week_plan import WeekPlan


def render_week_plan(plan: WeekPlan) -> str:
    lines = [f"Week {plan.week_prefix} Plan ({len(plan.sessions)} sessions):"]
    for i, s in enumerate(plan.sessions, 1):
        lines.append(f"{i}. {plan.week_prefix}: {s.name} — {s.duration_min} min")
    if plan.adjustments:
        lines.append("")
        lines.append("Adjustments:")
        for adj in plan.adjustments:
            lines.append(f"- {adj}")
    return "\n".join(lines)
