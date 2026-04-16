import uuid

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from weekforge.checkpoint import CheckpointStore

app = typer.Typer(help="Weekforge — training week lifecycle manager.")
console = Console()

_DEFAULT_DB_PATH = ".weekforge/checkpoints.sqlite"


def _make_store() -> CheckpointStore:
    return CheckpointStore(_DEFAULT_DB_PATH)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
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
def echo(
    message: str = typer.Option("Hello from Weekforge", help="Message to echo"),
    thread_id: str | None = typer.Option(None, help="Thread ID to resume. Omit to start a new run."),
) -> None:
    """Start or resume the echo workflow."""
    from weekforge.workflows.echo import run_echo

    store = _make_store()
    tid = thread_id or str(uuid.uuid4())

    try:
        decision = run_echo(message=message, thread_id=tid, store=store)
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Paused.[/yellow] Resume with: [bold cyan]uv run weekforge echo --thread-id {tid}[/bold cyan]")
        return

    if decision.approved:
        store.delete(tid)
        console.print(Panel("Workflow complete!", style="bold green"))
    else:
        console.print(f"[yellow]Paused.[/yellow] Resume with: [bold cyan]uv run weekforge echo --thread-id {tid}[/bold cyan]")


@app.command()
def notion_test(
    database_id: str | None = typer.Option(None, help="Notion Database ID. Falls back to NOTION_TEST_DB_ID env var."),
    thread_id: str | None = typer.Option(None, help="Thread ID to resume. Omit to start a new run."),
) -> None:
    """Start or resume the Notion CRUD test workflow (step 0b)."""
    from weekforge.config.env import settings
    from weekforge.workflows.notion_test import run_notion_test

    store = _make_store()
    db_id = database_id or settings.notion_test_db_id
    if not db_id:
        console.print("[bold red]Error:[/bold red] --database-id not provided and NOTION_TEST_DB_ID is not set.")
        raise typer.Exit(code=1)

    tid = thread_id or str(uuid.uuid4())

    try:
        run_notion_test(database_id=db_id, thread_id=tid, store=store)
    except KeyboardInterrupt:
        console.print(f"\n[yellow]Paused.[/yellow] Resume with: [bold cyan]uv run weekforge notion-test --thread-id {tid}[/bold cyan]")


if __name__ == "__main__":
    app()
