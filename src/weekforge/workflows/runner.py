from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost

S = TypeVar("S", bound=BaseModel)
StepFn = Callable[[S, RunCost], str | None]

_console = Console()


def run_workflow(
    workflow: str,
    state_cls: type[S],
    initial_state: S,
    steps: dict[str, StepFn[S]],
    thread_id: str,
    store: CheckpointStore,
) -> None:
    """Dispatch steps in sequence, saving state before each dispatch.

    Checkpoint is written BEFORE the step runs — on crash, resume re-runs the
    current step from the saved state (at-least-once, not exactly-once).

    Resume only matches `record.workflow == workflow`; no alias or fallback.
    A renamed workflow string silently starts fresh rather than corrupting an
    in-flight run from a different workflow.

    A step returns the name of the next step, or None to pause (checkpoint
    already saved above, so the run is resumable). Returns normally on "done".
    """
    record = store.load(thread_id)
    if record is not None and record.workflow == workflow:
        state = state_cls.model_validate_json(record.state_json)
    else:
        state = initial_state

    cost = RunCost()
    for c in getattr(state, "calls", []):
        cost.add(c)

    while state.step != "done":
        # Save before dispatch — crash during step leaves a resumable checkpoint.
        store.save(thread_id, workflow, state.step, state)

        step_name = state.step
        if step_name not in steps:
            raise RuntimeError(f"Unknown step: {step_name!r}")

        next_step = steps[step_name](state, cost)

        if next_step is None:
            return

        state.step = next_step

    store.delete(thread_id)
    _console.print(Panel(cost.summary(), title=f"Run complete — {workflow}", border_style="green"))
