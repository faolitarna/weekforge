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
            # Format planned->actual
            sets_str = f"{e.planned_sets}->{e.actual_sets}" if e.actual_sets and e.actual_sets != e.planned_sets else str(e.planned_sets)
            reps_str = f"{e.planned_reps}->{e.actual_reps}" if e.actual_reps and e.actual_reps != e.planned_reps else str(e.planned_reps)
            weight_str = f"{e.planned_weight}->{e.actual_weight}" if e.actual_weight and e.actual_weight != e.planned_weight else str(e.planned_weight)
            
            p_str = f"{sets_str}x{reps_str} @ {weight_str}"
            feedback_str = f"|\"{e.feedback}\"" if e.feedback else ""
            lines.append(f"- {e.name}|{e.role}|{e.status}|{p_str}{feedback_str}")
        lines.append("")
        
    if summary.cardio_log:
        lines.append("CARDIO_LOG:")
        for c in summary.cardio_log:
            lines.append(f"- {c.kind}|{c.raw}")
        lines.append("")
        
    if summary.climbing_log:
        lines.append("CLIMBING_LOG:")
        for c in summary.climbing_log:
            lines.append(f"- {c.kind}|{c.raw}")
        lines.append("")
        
    lines.append("PAIN_STATUS:")
    if summary.pain_status.si_joint:
        lines.append(f"- SI Joint: {summary.pain_status.si_joint}")
    if summary.pain_status.other:
        lines.append(f"- Other: {summary.pain_status.other}")
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
        lines.append("PLAN_ADHERENCE:")
        p = summary.plan_adherence
        lines.append(f"- Total: {p.planned_total} (Completed: {p.completed}, Modified: {p.modified}, Skipped: {p.skipped})")
        if p.modification_patterns:
            lines.append("- Modifications:")
            for m0, m1, m2 in p.modification_patterns:
                lines.append(f"  - {m0}: {m1} -> {m2}")
        if p.skip_patterns:
            lines.append("- Skips:")
            for s0, s1 in p.skip_patterns:
                lines.append(f"  - {s0}: {s1}")
        lines.append("")

    lines.append("IMPLICIT_FEEDBACK:")
    lines.append(f"- Total Checked: {summary.implicit_feedback.total_checked}/{summary.implicit_feedback.total_exercises}")
    for p_name, p_done, p_tot in summary.implicit_feedback.per_session:
        lines.append(f"- Session {p_name}: {p_done}/{p_tot}")
    lines.append("- Section Completion:")
    sr = summary.implicit_feedback.section_rates
    lines.append(f"  - Warmup: {sr.warmup_pct * 100:.0f}%")
    lines.append(f"  - Main: {sr.main_pct * 100:.0f}%")
    lines.append(f"  - Cooldown: {sr.cooldown_pct * 100:.0f}%")
    if summary.implicit_feedback.frequently_skipped:
        lines.append("- Frequently Skipped:")
        for fs in summary.implicit_feedback.frequently_skipped:
            lines.append(f"  - {fs.exercise}: {fs.skip_rate * 100:.0f}%")
    if summary.implicit_feedback.always_completed:
        lines.append("- Always Completed:")
        for ac in summary.implicit_feedback.always_completed:
            lines.append(f"  - {ac}")

    # Remove trailing blank line if exists
    ret = "\n".join(lines).strip()
    return ret
