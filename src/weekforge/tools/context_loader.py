import re
from dataclasses import dataclass
from typing import Literal

from weekforge.config.env import settings
from weekforge.config.user_profile_loader import load_user_profile
from weekforge.models.week_summary import SessionLine, WeekSummary
from weekforge.tools import notion_api_gateway as notion
from weekforge.tools import summaries_db
from weekforge.tools.plan_state import PlanState, parse_plan_state
from weekforge.tools.raw_session_collector import (
    assemble_raw_week,
    compute_checkbox_analysis,
)

_PAIN_KEYWORDS = re.compile(
    r"\b(SI|spine|flare|pain|tendon|joint)\b",
    re.IGNORECASE,
)

_HEADING_TYPES = {"heading_1", "heading_2", "heading_3"}


@dataclass(frozen=True)
class WeekDraftContext:
    template_markdown: str
    feedback_window_markdown: str
    plan_state_raw: str | None
    user_profile_markdown: str
    active_flare: bool
    is_bootstrap: bool
    plan_state_page_id: str | None


@dataclass(frozen=True)
class WeekSummarizeContext:
    raw_sessions_markdown: str
    tier0_summary: WeekSummary
    planned_plan_markdown: str | None
    user_profile_markdown: str
    plan_state_raw: str | None
    plan_state_page_id: str | None
    is_bootstrap: bool


def _format_template_pages(template_sessions: list[dict]) -> str:
    if not template_sessions:
        return ""
    lines = ["## Template Sessions\n"]
    for t in template_sessions:
        title = notion.get_page_title(t)
        lines.append(f"### {title}")
        for prop_name, prop_val in t.get("properties", {}).items():
            if prop_val.get("type") == "title":
                continue
            text = _extract_prop_text(prop_val)
            if text:
                lines.append(f"{prop_name}: {text}")
        lines.append("")
    return "\n".join(lines)


def _extract_prop_text(prop: dict) -> str:
    ptype = prop.get("type", "")
    if ptype == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if ptype == "number":
        val = prop.get("number")
        return str(val) if val is not None else ""
    if ptype == "date":
        d = prop.get("date")
        return d.get("start", "") if d else ""
    return ""


@dataclass(frozen=True)
class FeedbackRow:
    week_prefix: str
    plan_md: str | None
    summary_text: str | None


def _build_feedback_window(week_prefix: str) -> list[FeedbackRow]:
    week_num = int(week_prefix[1:])
    rows: list[FeedbackRow] = []
    for prev_week in range(week_num - 1, max(week_num - 4, 0), -1):
        prev_prefix = f"W{prev_week:02d}"
        row = summaries_db.find_summary_row(prev_prefix)
        if row is None:
            continue
        plan_md = summaries_db.read_plan_property(row)
        summary_text = summaries_db.read_summary_body(row)
        rows.append(FeedbackRow(
            week_prefix=prev_prefix,
            plan_md=plan_md,
            summary_text=summary_text,
        ))
    rows.reverse()
    return rows


def _format_feedback_window(rows: list[FeedbackRow]) -> str:
    if not rows:
        return ""
    lines = ["## Previous Weeks Feedback\n"]
    for row in rows:
        lines.append(f"### {row.week_prefix}")
        if row.plan_md:
            lines.append(f"Plan:\n{row.plan_md}")
        if row.summary_text:
            lines.append(f"Summary:\n{row.summary_text}")
        lines.append("")
    return "\n".join(lines)


def derive_active_flare(
    feedback_rows: list[FeedbackRow],
    plan_state: PlanState | None,
) -> bool:
    recent_pain = False
    if feedback_rows:
        most_recent = feedback_rows[-1]
        if most_recent.summary_text and _PAIN_KEYWORDS.search(most_recent.summary_text):
            recent_pain = True

    chronic_active_issue = False
    if plan_state and plan_state.active_issues:
        for issue in plan_state.active_issues:
            if _PAIN_KEYWORDS.search(issue):
                chronic_active_issue = True
                break

    return recent_pain or chronic_active_issue


def _format_raw_sessions(sessions: list[dict]) -> str:
    """Format raw session data (from RawSession objects) to markdown for the agent."""
    if not sessions:
        return ""
    lines = ["## Raw Session Blocks (source for exercise_log, cardio_log, climbing_log)\n"]
    for session in sessions:
        lines.append(f"### {session['name']}")
        comments = session.get("comments", [])
        lines.append(f"Comments: {', '.join(comments) if comments else 'none'}\n")
        for block in session.get("blocks", []):
            bt = block["block_type"]
            if bt in _HEADING_TYPES:
                lines.append(block["text"])
            elif bt == "to_do":
                check = "x" if block.get("checked") else " "
                lines.append(f"- [{check}] {block['text']}")
        lines.append("")
    return "\n".join(lines)


def load_week_draft_context(week_prefix: str) -> WeekDraftContext:
    all_templates = notion.query(database_id=settings.notion_db_training_templates)
    template_sessions = [
        p for p in all_templates
        if notion.get_page_title(p).startswith(week_prefix)
    ]
    if not template_sessions:
        raise RuntimeError(
            f"No template sessions found for {week_prefix}. "
            f"Check template naming in Notion (titles should start with '{week_prefix}')."
        )

    template_markdown = _format_template_pages(template_sessions)

    feedback_rows = _build_feedback_window(week_prefix)
    feedback_window_markdown = _format_feedback_window(feedback_rows)

    raw_text, page_id = summaries_db.find_plan_state_row()
    plan_state = parse_plan_state(raw_text) if raw_text else None

    profile = load_user_profile()
    active_flare = derive_active_flare(feedback_rows, plan_state)
    is_bootstrap = plan_state is None or len(feedback_rows) == 0

    return WeekDraftContext(
        template_markdown=template_markdown,
        feedback_window_markdown=feedback_window_markdown,
        plan_state_raw=raw_text,
        user_profile_markdown=profile.markdown,
        active_flare=active_flare,
        is_bootstrap=is_bootstrap,
        plan_state_page_id=page_id,
    )


def load_week_summarize_context(week_prefix: str) -> WeekSummarizeContext:
    profile = load_user_profile()

    week_num_str = str(int(week_prefix[1:]))
    all_session_pages = notion.query(database_id=settings.notion_db_training_sessions)
    session_pages = [
        p for p in all_session_pages
        if notion.get_text_prop(p, "Week") == week_num_str
    ]
    if not session_pages:
        raise RuntimeError(
            f"No session pages found for {week_prefix} in training_sessions DB."
        )

    summary_row = summaries_db.find_summary_row(week_prefix)
    planned_plan_markdown = summaries_db.read_plan_property(summary_row) if summary_row else None

    raw_week = assemble_raw_week(
        week_prefix=week_prefix,
        session_pages=session_pages,
        planned_plan_markdown=planned_plan_markdown,
    )

    implicit_fb = compute_checkbox_analysis(raw_week.sessions)

    session_lines: list[SessionLine] = []
    for s in raw_week.sessions:
        total = sum(1 for b in s.blocks if b.block_type == "to_do")
        checked = sum(1 for b in s.blocks if b.block_type == "to_do" and b.checked)
        status: Literal["done", "skip", "partial"] = (
            "done" if s.done else ("partial" if checked > 0 else "skip")
        )
        comment_text = " | ".join(s.comments) if s.comments else ""
        session_lines.append(SessionLine(
            name=s.name,
            status=status,
            exercises_done=checked,
            exercises_total=total,
            pain_status=None,
            comment=comment_text,
        ))

    done_count = sum(1 for s in raw_week.sessions if s.done)
    tier0_summary = WeekSummary(
        week_prefix=week_prefix,
        completion=f"{done_count}/{len(session_lines)}",
        sessions=session_lines,
        exercise_log=[],
        pain_status=[],
        implicit_feedback=implicit_fb,
    )

    sessions_as_dicts = [
        {
            "name": s.name,
            "page_id": s.page_id,
            "done": s.done,
            "blocks": [
                {"block_type": b.block_type, "text": b.text, "checked": b.checked}
                for b in s.blocks
            ],
            "comments": s.comments,
        }
        for s in raw_week.sessions
    ]
    raw_sessions_markdown = _format_raw_sessions(sessions_as_dicts)

    raw_text, page_id = summaries_db.find_plan_state_row()

    return WeekSummarizeContext(
        raw_sessions_markdown=raw_sessions_markdown,
        tier0_summary=tier0_summary,
        planned_plan_markdown=planned_plan_markdown,
        user_profile_markdown=profile.markdown,
        plan_state_raw=raw_text,
        plan_state_page_id=page_id,
        is_bootstrap=raw_text is None,
    )
