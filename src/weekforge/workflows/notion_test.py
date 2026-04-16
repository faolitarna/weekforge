from typing import Any

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import hitl_confirm
from weekforge.tools import notion

_console = Console()
_WORKFLOW = "notion_test"
_STEP_REVIEWED = "reviewed"


class NotionTestState(BaseModel):
    database_id: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    created_page_id: str | None = None


def run_notion_test(database_id: str, thread_id: str, store: CheckpointStore) -> None:
    record = store.load(thread_id)
    if record is not None:
        state = NotionTestState.model_validate_json(record.state_json)
    else:
        records = notion.query(database_id=database_id)
        state = NotionTestState(database_id=database_id, records=records)

    _render_records_table(state.records)

    decision = hitl_confirm(
        context=f"Queried '{database_id}'.\nFound {len(state.records)} records (sample above).",
        options=(
            "- [green]Yes[/green]: Write a test page to this database\n"
            "- [red]No[/red]: Cancel (no write)"
        ),
        recommendation="Say Yes to validate the full CRUD cycle.",
        checkpoint=store,
        thread_id=thread_id,
        workflow=_WORKFLOW,
        step=_STEP_REVIEWED,
        state=state,
    )

    if not decision.approved:
        store.delete(thread_id)
        return

    properties = {"Title": {"title": [{"text": {"content": "Test Item"}}]}}
    content_md = "# Title\n\n- [x] Tested query\n- [x] Tested creation"

    created_id = notion.create(
        database_id=state.database_id,
        properties=properties,
        content=content_md,
    )
    notion.update(
        page_id=created_id,
        content=content_md + "\n\n- [x] Tested update (idempotent rewrite)",
    )

    state.created_page_id = created_id
    store.delete(thread_id)
    _console.print(f"[green]Done.[/green] Created page ID: {created_id}")


def _render_records_table(records: list[dict[str, Any]]) -> None:
    table = Table(title="Queried Notion Records")
    table.add_column("Record ID", style="cyan")
    table.add_column("URL", style="magenta")
    table.add_column("Created Time", style="green")
    for rec in records[:3]:
        table.add_row(
            rec.get("id", "Unknown"),
            rec.get("url", "No URL"),
            rec.get("created_time", "Unknown"),
        )
    _console.print(table)
