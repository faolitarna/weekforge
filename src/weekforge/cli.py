"""Weekforge CLI — Typer entry point for all user-facing workflow commands.

Commands are thin wrappers: construct a CheckpointStore, delegate to the workflow
function, handle KeyboardInterrupt by printing a resume hint. All rendering and
HITL logic lives in the workflow and hitl modules.

Invoking `weekforge` bare shows help plus active checkpoint status — the user
never has to remember thread IDs or which workflow was in progress. The callback
validates required env vars on every invocation; a missing var yields a Rich
panel instead of a raw Pydantic stack trace.

"""
import uuid
from collections.abc import Callable

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from weekforge.checkpoint import CheckpointStore

app = typer.Typer(help="Weekforge — training week lifecycle manager.", add_completion=False)
console = Console()

# Relative to CWD — each project directory gets its own isolated checkpoint DB.
# Moving the project directory silently orphans all active checkpoints; resume will fail.
_DEFAULT_DB_PATH = ".weekforge/checkpoints.sqlite"


def _make_store() -> CheckpointStore:
    return CheckpointStore(_DEFAULT_DB_PATH)


def _validate_env_or_exit() -> None:
    """Validate required env vars on every command invocation.

    Instantiates Settings() directly rather than relying on the cached module-level
    singleton, so this check is always live regardless of prior import order.
    Pydantic's ValidationError is not user-friendly; we intercept it and render a
    Rich panel listing the missing variable names with a pointer to .env.template.
    """
    try:
        from weekforge.config.env import Settings
        Settings()  # type: ignore[call-arg]
    except ValidationError as e:
        missing = [".".join(str(p) for p in err["loc"]) for err in e.errors() if err["type"] == "missing"]
        body = (
            "[bold red]Missing required environment variables:[/bold red]\n"
            + "\n".join(f"  - {name.upper()}" for name in missing)
            + "\n\n[dim]Copy `.env.template` to `.env` and fill in values.[/dim]"
        )
        console.print(Panel(body, title="Configuration Error", border_style="red"))
        raise typer.Exit(code=1) from e


def _run_or_pause(tid: str, fn: Callable[[], None]) -> None:
    try:
        fn()
    except KeyboardInterrupt:
        console.print(
            f"\n[yellow]Paused.[/yellow] Resume: "
            f"[bold cyan]uv run weekforge resume --thread-id {tid}[/bold cyan]"
        )


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    _validate_env_or_exit()

    if ctx.invoked_subcommand is not None:
        return

    console.print(ctx.get_help())

    store = _make_store()
    active = store.list_active()
    if not active:
        console.print("\n[dim]No active checkpoints.[/dim]")
        return

    table = Table(title="Active Checkpoints", show_header=True)
    table.add_column("Thread ID", style="cyan")
    table.add_column("Workflow", style="magenta")
    table.add_column("Paused At", style="yellow")
    table.add_column("Updated", style="dim")
    for rec in active:
        table.add_row(rec.thread_id, rec.workflow, rec.step, rec.updated_at)
    console.print(table)


@app.command()
def e2e(
    database_id: str | None = typer.Option(None, help="Notion Database ID. Falls back to NOTION_TEST_DB_ID env var."),
    thread_id: str | None = typer.Option(None, help="Thread ID to resume. Omit to start a new run."),
) -> None:
    """Run the Phase-0 end-to-end validation workflow (transitional)."""
    from weekforge.config.env import settings
    from weekforge.workflows.e2e import run_e2e

    store = _make_store()
    db_id = database_id or settings.notion_test_db_id
    tid = thread_id or str(uuid.uuid4())

    _run_or_pause(tid, lambda: run_e2e(database_id=db_id, thread_id=tid, store=store))


@app.command()
def plan() -> None:
    """Start or resume the planning lifecycle (not yet implemented — step 2)."""
    console.print("[dim]Not yet implemented (step 2).[/dim]")


@app.command("summarize-week")
def summarize_week(week: int = typer.Argument(..., help="Week number, e.g. 7")) -> None:
    """Generate a weekly summary from completed training sessions."""
    from weekforge.tools.formatting import format_week_prefix
    from weekforge.workflows.extraction import run_summarize

    store = _make_store()
    week_prefix = format_week_prefix(week)
    tid = f"summarize-week-{week_prefix}"
    _run_or_pause(tid, lambda: run_summarize(week_prefix, tid, store))


@app.command()
def resume(
    thread_id: str = typer.Option(..., help="Thread ID of the checkpoint to resume."),
) -> None:
    """Resume from the last checkpoint (any thread)."""
    store = _make_store()
    rec = store.load(thread_id)
    if rec is None:
        console.print(f"[red]No checkpoint found for thread-id {thread_id}[/red]")
        raise typer.Exit(code=1)

    # Dispatch by workflow field on the checkpoint record.
    if rec.workflow == "e2e":
        from weekforge.workflows.e2e import run_e2e

        _run_or_pause(thread_id, lambda: run_e2e(database_id=None, thread_id=thread_id, store=store))
        return

    if rec.workflow == "extraction":
        from weekforge.workflows.extraction import run_summarize

        _run_or_pause(thread_id, lambda: run_summarize("", thread_id, store))
        return

    console.print(f"[red]Unknown workflow: {rec.workflow}[/red]")
    raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
