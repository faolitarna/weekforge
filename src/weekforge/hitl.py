from dataclasses import dataclass, field

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from weekforge.checkpoint import CheckpointStore

_console = Console()


@dataclass
class HitlDecision:
    approved: bool
    feedback: str | None = field(default=None)


def hitl_confirm(
    context: str,
    recommendation: str,
    checkpoint: CheckpointStore,
    thread_id: str,
    workflow: str,
    step: str,
    state: BaseModel,
    options: str = "- [green]Yes[/green]: Proceed\n- [red]No[/red]: Keep paused (resume later with --thread-id)",
) -> HitlDecision:
    """Saves state, renders a Context/Options/Recommendation panel, returns user decision.

    State is saved BEFORE the prompt — crash safety. The `step` label persists to
    SQLite; renaming it breaks resume for any in-flight checkpoints.
    """
    checkpoint.save(thread_id, workflow, step, state)

    content = (
        f"[bold cyan]Context:[/bold cyan]\n{context}\n\n"
        f"[bold cyan]Options:[/bold cyan]\n{options}\n\n"
        f"[bold cyan]Recommendation:[/bold cyan]\n{recommendation}"
    )
    _console.print(Panel(content, title="Human Authorization Required", border_style="#FFA500"))

    approved = Confirm.ask("Proceed?")
    return HitlDecision(approved=approved)
