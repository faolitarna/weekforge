"""Weekforge CLI — Typer entry point for all user-facing workflow commands.

Commands are thin wrappers: construct a CheckpointStore, delegate to the workflow
function, handle KeyboardInterrupt by printing a resume hint. All rendering and
HITL logic lives in the workflow and hitl modules.
"""
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


@app.command("draft-week")
def draft_week(week: int = typer.Argument(..., help="Week number, e.g. 15")) -> None:
    """Draft a high-level weekly training plan."""
    from weekforge.tools.formatting import format_week_prefix
    from weekforge.workflows.draft_week import run_draft

    store = _make_store()
    week_prefix = format_week_prefix(week)
    tid = f"draft-week-{week_prefix}"
    _run_or_pause(tid, lambda: run_draft(week_prefix, tid, store))


@app.command("summarize-week")
def summarize_week(week: int = typer.Argument(..., help="Week number, e.g. 7")) -> None:
    """Generate a weekly summary from completed training sessions."""
    from weekforge.tools.formatting import format_week_prefix
    from weekforge.workflows.summarize_week import run_summarize

    store = _make_store()
    week_prefix = format_week_prefix(week)
    tid = f"summarize-week-{week_prefix}"
    _run_or_pause(tid, lambda: run_summarize(week_prefix, tid, store))


_WORKFLOW_RUNNERS: dict[str, Callable[[str, str, CheckpointStore], None]] = {}


def _register_workflows() -> dict[str, Callable[[str, str, CheckpointStore], None]]:
    # Deferred import — avoids circular deps at module load time.
    if not _WORKFLOW_RUNNERS:
        from weekforge.workflows.draft_week import run_draft
        from weekforge.workflows.summarize_week import run_summarize
        _WORKFLOW_RUNNERS["summarize_week"] = lambda wp, tid, store: run_summarize(wp, tid, store)
        _WORKFLOW_RUNNERS["draft_week"] = lambda wp, tid, store: run_draft(wp, tid, store)
    return _WORKFLOW_RUNNERS


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

    runners = _register_workflows()
    runner_fn = runners.get(rec.workflow)
    if runner_fn is None:
        console.print(f"[red]Unknown workflow: {rec.workflow}[/red]")
        raise typer.Exit(code=1)

    _run_or_pause(thread_id, lambda: runner_fn("", thread_id, store))


@app.command("delete-thread")
def delete_thread(
    thread_id: str = typer.Argument(..., help="Thread ID of the checkpoint to delete."),
) -> None:
    """Delete a stale checkpoint that will never be resumed."""
    store = _make_store()
    rec = store.load(thread_id)
    if rec is None:
        console.print(f"[red]No checkpoint found for thread-id {thread_id}[/red]")
        raise typer.Exit(code=1)

    store.delete(thread_id)
    console.print(f"[green]Deleted checkpoint: {thread_id} ({rec.workflow} @ {rec.step})[/green]")


if __name__ == "__main__":
    app()
