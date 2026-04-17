from dataclasses import dataclass, field

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from weekforge.checkpoint import CheckpointStore

_console = Console()


@dataclass
class HitlDecision:
    approved: bool
    feedback: str | None = field(default=None)
    quit: bool = False


_DEFAULT_OPTIONS = (
    "- [green]\\[a]pprove[/green]: Accept and proceed\n"
    "- [yellow]\\[f]eedback[/yellow]: Refine with feedback (re-runs agent)\n"
    "- [red]\\[q]uit[/red]: Pause run (resume later with --thread-id)"
)


def hitl_confirm(
    context: str,
    recommendation: str,
    checkpoint: CheckpointStore,
    thread_id: str,
    workflow: str,
    step: str,
    state: BaseModel,
    options: str = _DEFAULT_OPTIONS,
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

    choices = ["a", "f", "q"]
    choice = Prompt.ask("Choose", choices=choices, default="a")

    if choice == "a":
        return HitlDecision(approved=True)
    if choice == "q":
        return HitlDecision(approved=False, quit=True)
    feedback = Prompt.ask("Feedback")
    return HitlDecision(approved=False, feedback=feedback)
