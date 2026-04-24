from weekforge.models.week_summary import WeekSummary


def render_week_summary(summary: WeekSummary) -> str:
    lines = []
    lines.append(f"WEEK_SUMMARY:{summary.week_prefix}")
    lines.append(f"COMPLETION:{summary.completion}")
    lines.append(f"CONTEXT:{summary.context or ''}")
    lines.append("")

    if summary.sessions:
        lines.append("SESSIONS:")
        for s in summary.sessions:
            comment = f"|\"{s.comment}\"" if s.comment else ""
            pain = f"|{s.pain_status}" if s.pain_status else "|ok"
            lines.append(f"- {s.name}|{s.status}|{s.exercises_done}/{s.exercises_total}{pain}{comment}")
        lines.append("")

    if summary.exercise_log:
        lines.append("EXERCISE_LOG:")
        for e in summary.exercise_log:
            sets_str = f"{e.planned_sets}->{e.actual_sets}" if e.actual_sets and e.actual_sets != e.planned_sets else str(e.planned_sets)
            reps_str = f"{e.planned_reps}->{e.actual_reps}" if e.actual_reps and e.actual_reps != e.planned_reps else str(e.planned_reps)
            weight_str = f"{e.planned_weight}->{e.actual_weight}" if e.actual_weight and e.actual_weight != e.planned_weight else str(e.planned_weight)
            feedback_str = f"|\"{e.feedback}\"" if e.feedback else ""
            lines.append(f"- {e.name}:{weight_str}x{sets_str}x{reps_str}|{e.role}|{e.status}{feedback_str}")
        lines.append("")

    if summary.cardio_log:
        lines.append("CARDIO_LOG:")
        for c in summary.cardio_log:
            lines.append(f"- {c.kind}|{c.raw}")
        lines.append("")

    if summary.climbing_log:
        lines.append("CLIMBING_LOG:")
        for cl in summary.climbing_log:
            lines.append(f"- {cl.kind}|{cl.raw}")
        lines.append("")

    # Section always emitted — downstream LLM consumers expect the header even when list is empty.
    lines.append("PAIN_STATUS:")
    for j in summary.pain_status:
        entry = f"- {j.name}:{j.status}"
        if j.triggers is not None:
            entry += f"|{j.triggers}"
            if j.what_helped is not None:
                entry += f"|{j.what_helped}"
        elif j.what_helped is not None:
            # what_helped without triggers — data error, render rather than drop
            entry += f"|{j.what_helped}"
        lines.append(entry)
    lines.append("")

    lines.append("ISSUES:")
    for i in summary.issues:
        lines.append(f"- {i}")
    lines.append("")

    lines.append("WINS:")
    for w in summary.wins:
        lines.append(f"- {w}")
    lines.append("")

    lines.append("RECOMMENDATIONS_NEXT:")
    for r in summary.recommendations_next:
        lines.append(f"- {r}")
    lines.append("")

    if summary.plan_adherence:
        p = summary.plan_adherence
        lines.append("PLAN_ADHERENCE:")
        lines.append(f"- planned:{p.planned_total}|completed:{p.completed}|modified:{p.modified}|skipped:{p.skipped}")
        if p.modification_patterns:
            mods = "|".join(f"{m.exercise}->{m.actual}" for m in p.modification_patterns)
            lines.append(f"- modification_patterns:{mods}")
        if p.skip_patterns:
            skips = "|".join(f"{s.exercise}:{s.reason}" for s in p.skip_patterns)
            lines.append(f"- skip_patterns:{skips}")
        lines.append("")

    fb = summary.implicit_feedback
    total = fb.total_exercises
    pct = round(fb.total_checked / total * 100) if total > 0 else 0
    sr = fb.section_rates
    lines.append("IMPLICIT_FEEDBACK:")
    lines.append(f"- checkbox_completion:{fb.total_checked}/{total}|{pct}%")
    lines.append(f"- section_rates:warmup:{sr.warmup_pct * 100:.0f}%|main:{sr.main_pct * 100:.0f}%|cooldown:{sr.cooldown_pct * 100:.0f}%")
    if fb.frequently_skipped:
        parts = "|".join(f"{fs.exercise}:{fs.skip_rate * 100:.0f}%" for fs in fb.frequently_skipped)
        lines.append(f"- frequently_skipped:{parts}")
    if fb.always_completed:
        lines.append(f"- always_completed:{'|'.join(fb.always_completed)}")

    return "\n".join(lines).strip()
