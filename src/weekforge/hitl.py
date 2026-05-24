from collections.abc import Callable
from dataclasses import dataclass, field

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import CallMetadata, RunCost

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


@dataclass
class AcceptResult:
    step: str | None
    feedback: str | None = None


def run_accept_gate(
    render_fn: Callable[[], str],
    approved_step: str,
    cost: RunCost,
    calls: list[CallMetadata],
    max_iterations: int,
    store: CheckpointStore,
    thread_id: str,
    workflow: str,
    step: str,
    state: BaseModel,
) -> AcceptResult:
    context_str = render_fn()

    if len(calls) >= max_iterations:
        context_str += "\n[red bold]Token burn warning: reached max iterations. Please accept.[/red bold]\n"

    context_str += f"\n{cost.summary()}"

    _console.print(Panel(context_str, title="Agent Output", border_style="cyan"))

    decision = hitl_confirm(
        context=context_str,
        recommendation="Approve proceeds. Feedback refines. Quit pauses.",
        checkpoint=store,
        thread_id=thread_id,
        workflow=workflow,
        step=step,
        state=state,
    )

    if decision.approved:
        return AcceptResult(step=approved_step)
    if decision.quit:
        _console.print(
            f"[yellow]Paused.[/yellow] Resume: "
            f"[bold cyan]uv run weekforge resume --thread-id {thread_id}[/bold cyan]"
        )
        return AcceptResult(step=None)
    return AcceptResult(step="agent", feedback=decision.feedback)
