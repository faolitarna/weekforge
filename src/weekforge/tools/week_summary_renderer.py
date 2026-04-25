from collections import defaultdict

from weekforge.models.week_summary import ExerciseLogEntry, WeekSummary


def _strip_week_prefix(name: str) -> str:
    if ": " in name:
        return name.split(": ", 1)[1].strip()
    return name.strip()


def _is_signal_entry(e: ExerciseLogEntry) -> bool:
    if e.planned_weight is not None or e.actual_weight is not None:
        return True
    if e.feedback is not None:
        return True
    if e.status == "done_modified":
        return True
    return False


def _build_load_string(e: ExerciseLogEntry) -> str:
    weight = e.actual_weight or e.planned_weight
    sets = e.actual_sets if e.actual_sets is not None else e.planned_sets
    reps = e.actual_reps or e.planned_reps

    parts: list[str] = []
    if weight:
        parts.append(str(weight))
    if sets is not None and reps:
        parts.append(f"{sets}x{reps}")
    elif sets is not None:
        parts.append(f"{sets}sets")
    elif reps:
        parts.append(str(reps))
    return "/".join(parts) if parts else ""


def _render_status(status: str) -> str:
    if status == "done_modified":
        return "modified"
    return status


def _render_signal_entry(e: ExerciseLogEntry) -> str:
    parts = [e.name]
    load = _build_load_string(e)
    if load:
        parts.append(load)
    parts.append(e.role)
    parts.append(_render_status(e.status))
    if e.feedback:
        parts.append(e.feedback)
    return "|".join(parts)


def render_week_summary(summary: WeekSummary) -> str:
    lines: list[str] = []
    lines.append(f"WEEK:{summary.week_prefix}")
    lines.append(f"COMPLETION:{summary.completion}")
    lines.append(f"CONTEXT:{summary.context or ''}")
    lines.append("")

    skipped_sessions: set[str] = set()
    if summary.sessions:
        lines.append("SESSIONS:")
        for s in summary.sessions:
            display_name = _strip_week_prefix(s.name)
            if s.status == "skip":
                skipped_sessions.add(display_name)
            pain = f"|{s.pain_status}" if s.pain_status else "|ok"
            comment = f"|{s.comment}" if s.comment else ""
            lines.append(
                f"{display_name}|{s.status}|{s.exercises_done}/{s.exercises_total}{pain}{comment}"
            )
        lines.append("")

    if summary.exercise_log:
        session_groups: dict[str, list[ExerciseLogEntry]] = defaultdict(list)
        for e in summary.exercise_log:
            key = e.session_name or e.section or "Other"
            session_groups[key].append(e)

        for session_name, exercises in session_groups.items():
            if session_name in skipped_sessions:
                continue

            signal = [e for e in exercises if _is_signal_entry(e)]
            compressed = [e for e in exercises if not _is_signal_entry(e)]

            lines.append(f"EXERCISES:{session_name}")
            if compressed:
                names = ",".join(e.name for e in compressed)
                lines.append(f"used:{names}")
            for e in signal:
                lines.append(_render_signal_entry(e))
            lines.append("")

    if summary.cardio_log:
        lines.append("CARDIO:")
        for c in summary.cardio_log:
            lines.append(f"{c.kind}|{c.raw}")
        lines.append("")

    if summary.climbing_log:
        lines.append("CLIMBING:")
        for cl in summary.climbing_log:
            lines.append(f"{cl.kind}|{cl.raw}")
        lines.append("")

    lines.append("PAIN:")
    for j in summary.pain_status:
        entry = f"{j.name}:{j.status}"
        if j.triggers is not None:
            entry += f"|{j.triggers}"
            if j.what_helped is not None:
                entry += f"|{j.what_helped}"
        elif j.what_helped is not None:
            entry += f"|{j.what_helped}"
        lines.append(entry)
    lines.append("")

    lines.append("ISSUES:")
    for i in summary.issues:
        lines.append(i)
    lines.append("")

    lines.append("WINS:")
    for w in summary.wins:
        lines.append(w)
    lines.append("")

    lines.append("RECS:")
    for r in summary.recommendations_next:
        lines.append(r)
    lines.append("")

    if summary.plan_adherence:
        p = summary.plan_adherence
        lines.append("PLAN_ADHERENCE:")
        lines.append(
            f"planned:{p.planned_total}|completed:{p.completed}"
            f"|modified:{p.modified}|skipped:{p.skipped}"
        )
        if p.modification_patterns:
            mods = "|".join(f"{m.exercise}->{m.actual}" for m in p.modification_patterns)
            lines.append(f"modification_patterns:{mods}")
        if p.skip_patterns:
            skips = "|".join(f"{s.exercise}:{s.reason}" for s in p.skip_patterns)
            lines.append(f"skip_patterns:{skips}")
        lines.append("")

    fb = summary.implicit_feedback
    total = fb.total_exercises
    pct = round(fb.total_checked / total * 100) if total > 0 else 0
    sr = fb.section_rates
    lines.append("CHECKBOX_STATS:")
    lines.append(f"{fb.total_checked}/{total}|{pct}%")
    lines.append(
        f"section_rates:warmup:{sr.warmup_pct * 100:.0f}%"
        f"|main:{sr.main_pct * 100:.0f}%"
        f"|cooldown:{sr.cooldown_pct * 100:.0f}%"
    )

    return "\n".join(lines).strip()
