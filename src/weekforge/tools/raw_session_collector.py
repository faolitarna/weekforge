import logging
from collections import defaultdict
from typing import Any

from weekforge.models.raw_week_data import RawBlock, RawSession, RawWeekData
from weekforge.models.week_summary import (
    ImplicitFeedback,
    SectionRates,
    SessionCheckCount,
    SkippedPattern,
)
from weekforge.tools import notion_api_gateway as notion

logger = logging.getLogger(__name__)

_HEADING_TYPES = {"heading_1", "heading_2", "heading_3"}


def _extract_plain_text(rich_text_array: list[Any]) -> str:
    return "".join(item.get("plain_text", "") for item in rich_text_array)


def _parse_block(block: dict[str, Any]) -> RawBlock:
    block_type = block.get("type", "unknown")
    type_data = block.get(block_type, {})
    rich_text = type_data.get("rich_text", [])
    text = _extract_plain_text(rich_text)
    checked: bool | None = None
    if block_type == "to_do":
        checked = bool(type_data.get("checked", False))
    return RawBlock(block_type=block_type, text=text, checked=checked, raw=block)


def collect_blocks(page_id: str) -> list[RawBlock]:
    raw_blocks = notion.fetch_blocks(page_id)
    return [_parse_block(b) for b in raw_blocks]


def collect_comments(page_id: str) -> list[str]:
    try:
        raw_comments = notion.fetch_comments(page_id)
        return [_extract_plain_text(c.get("rich_text", [])) for c in raw_comments]
    except Exception:
        logger.warning("Failed to fetch comments for page %s — continuing with empty list", page_id)
        return []


def collect_raw_sessions(
    session_pages: list[dict[str, Any]],
) -> list[RawSession]:
    if not session_pages:
        raise ValueError("collect_raw_sessions: session_pages is empty")
    sessions: list[RawSession] = []
    for page in session_pages:
        page_id = page.get("id", "")
        title_parts: list[Any] = next(
            (v.get("title", []) for v in page.get("properties", {}).values() if v.get("type") == "title"),
            [],
        )
        name = _extract_plain_text(title_parts) if title_parts else page_id
        done = bool(page.get("properties", {}).get("Done", {}).get("checkbox", False))
        blocks = collect_blocks(page_id)
        comments = collect_comments(page_id)
        sessions.append(RawSession(page_id=page_id, name=name, blocks=blocks, comments=comments, done=done))
    return sessions


def compute_checkbox_analysis(sessions: list[RawSession]) -> ImplicitFeedback:
    total_checked = 0
    total_exercises = 0
    per_session: list[SessionCheckCount] = []

    exercise_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"checked": 0, "total": 0})

    # section-level checkbox counts for SectionRates
    section_checked: dict[str, int] = defaultdict(int)
    section_total: dict[str, int] = defaultdict(int)

    _SECTION_LABELS = {"warmup", "main", "cooldown"}

    def _classify_section(label: str) -> str:
        lower = label.lower()
        for key in _SECTION_LABELS:
            if key in lower:
                return key
        return "main"

    for session in sessions:
        s_checked = 0
        s_total = 0
        current_section = "main"
        for block in session.blocks:
            if block.block_type in _HEADING_TYPES:
                current_section = _classify_section(block.text)
            elif block.block_type == "to_do":
                s_total += 1
                total_exercises += 1
                section_total[current_section] += 1
                exercise_stats[block.text]["total"] += 1
                if block.checked:
                    s_checked += 1
                    total_checked += 1
                    section_checked[current_section] += 1
                    exercise_stats[block.text]["checked"] += 1
        per_session.append(SessionCheckCount(session_name=session.name, checked=s_checked, total=s_total))

    def _pct(checked: int, total: int) -> float:
        return round(checked / total, 4) if total else 0.0

    section_rates = SectionRates(
        warmup_pct=_pct(section_checked["warmup"], section_total["warmup"]),
        main_pct=_pct(section_checked["main"], section_total["main"]),
        cooldown_pct=_pct(section_checked["cooldown"], section_total["cooldown"]),
    )

    frequently_skipped: list[SkippedPattern] = []
    always_completed: list[str] = []
    for exercise, stats in exercise_stats.items():
        t = stats["total"]
        c = stats["checked"]
        skip_count = t - c
        skip_rate = skip_count / t if t else 0.0
        if t >= 2 and skip_rate > 0.5:
            frequently_skipped.append(SkippedPattern(exercise=exercise, skip_rate=round(skip_rate, 4)))
        if t >= 2 and skip_count == 0:
            always_completed.append(exercise)

    return ImplicitFeedback(
        total_checked=total_checked,
        total_exercises=total_exercises,
        per_session=per_session,
        section_rates=section_rates,
        frequently_skipped=frequently_skipped,
        always_completed=always_completed,
    )


def assemble_raw_week(
    week_prefix: str,
    session_pages: list[dict[str, Any]],
    planned_plan_markdown: str | None,
) -> RawWeekData:
    if not session_pages:
        raise ValueError(f"{week_prefix}: no sessions found")
    sessions = collect_raw_sessions(session_pages)
    return RawWeekData(
        week_prefix=week_prefix,
        sessions=sessions,
        planned_plan_markdown=planned_plan_markdown,
    )
