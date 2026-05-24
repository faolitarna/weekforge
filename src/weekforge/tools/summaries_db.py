from typing import Any

from weekforge.config.env import settings
from weekforge.tools import notion_api_gateway as notion


def find_summary_row(week_prefix: str) -> dict[str, Any] | None:
    week_num = week_prefix[1:]  # "W07" -> "07"
    all_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
    for page in all_pages:
        if notion.get_text_prop(page, "Week") == week_num:
            return page
    return None


def find_plan_state_row() -> tuple[str | None, str | None]:
    all_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
    for page in all_pages:
        if notion.get_text_prop(page, "Week") == "PLAN_STATE":
            page_id = page["id"]
            fetched = notion.fetch(page_id)
            content_blocks = fetched.get("content", [])
            raw_text = ""
            for block in content_blocks:
                if block["type"] == "code":
                    raw_text += "".join(
                        t["text"]["content"] for t in block["code"]["rich_text"]
                    ) + "\n"
                elif block["type"] == "paragraph" and block.get("paragraph", {}).get("rich_text"):
                    raw_text += "".join(
                        t["text"]["content"] for t in block["paragraph"]["rich_text"]
                    ) + "\n"
            return raw_text, page_id
    return None, None


def read_plan_property(page: dict[str, Any]) -> str | None:
    text = notion.get_text_prop(page, "Plan")
    return text or None


def upsert_summary(week_prefix: str, content: str) -> str:
    week_num = week_prefix[1:]
    row = find_summary_row(week_prefix)
    code_block = f"```text\n{content}\n```"

    if row:
        page_id = row["id"]
        notion.update(page_id=page_id, content=code_block)
        return page_id

    title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
    return notion.create(
        database_id=settings.notion_db_training_week_summaries,
        properties={
            "Week": {"rich_text": [{"text": {"content": week_num}}]},
            title_prop: {"title": [{"text": {"content": f"{week_prefix} Summary"}}]},
        },
        content=code_block,
    )


def upsert_plan(week_prefix: str, plan_text: str) -> str:
    row = find_summary_row(week_prefix)
    plan_prop = {"rich_text": [{"text": {"content": plan_text}}]}

    if row:
        page_id = row["id"]
        notion.update(page_id=page_id, properties={"Plan": plan_prop})
        return page_id

    week_num = week_prefix[1:]
    title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
    return notion.create(
        database_id=settings.notion_db_training_week_summaries,
        properties={
            "Week": {"rich_text": [{"text": {"content": week_num}}]},
            "Plan": plan_prop,
            title_prop: {"title": [{"text": {"content": f"{week_prefix} Summary"}}]},
        },
        content="",
    )
