from rich.console import Console

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import hitl_confirm
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.workflow_state import DraftWeekState
from weekforge.tools import summaries_db
from weekforge.workflows.runner import StepFn, run_workflow

_console = Console()
WORKFLOW = "draft_week"


def _step_load_context(state: DraftWeekState, cost: RunCost) -> str | None:
    raise RuntimeError("Not yet implemented: load_context (step 2b)")


def _step_agent(state: DraftWeekState, cost: RunCost) -> str | None:
    raise RuntimeError("Not yet implemented: agent (step 2c)")


def _step_accept(state: DraftWeekState, cost: RunCost) -> str | None:
    raise RuntimeError("Not yet implemented: accept (step 2c)")


def _step_validate(state: DraftWeekState, cost: RunCost) -> str | None:
    raise RuntimeError("Not yet implemented: validate (step 2d)")


def _step_write(state: DraftWeekState, cost: RunCost) -> str | None:
    raise RuntimeError("Not yet implemented: write (step 2d)")


def run_draft(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    def step_overwrite_check(state: DraftWeekState, cost: RunCost) -> str | None:
        row = summaries_db.find_summary_row(state.week_prefix)
        if row is None:
            return "load_context"

        plan_text = summaries_db.read_plan_property(row)
        if not plan_text:
            return "load_context"

        preview_lines = plan_text.splitlines()[:10]
        preview = "\n".join(preview_lines)
        if len(plan_text.splitlines()) > 10:
            preview += "\n[dim]… (truncated)[/dim]"

        context = (
            f"[bold]Week {state.week_prefix} already has a plan:[/bold]\n\n"
            f"{preview}\n\n"
            f"Overwrite will replace this plan with a new draft."
        )

        decision = hitl_confirm(
            context=context,
            recommendation="Quit preserves existing plan. Approve overwrites.",
            checkpoint=store,
            thread_id=thread_id,
            workflow=WORKFLOW,
            step="overwrite_check",
            state=state,
            options=(
                "- [green]\\[a]pprove[/green]: Overwrite existing plan\n"
                "- [red]\\[q]uit[/red]: Keep existing plan and exit"
            ),
        )

        if decision.approved:
            return "load_context"
        return None

    steps: dict[str, StepFn[DraftWeekState]] = {
        "overwrite_check": step_overwrite_check,
        "load_context": _step_load_context,
        "agent": _step_agent,
        "accept": _step_accept,
        "validate": _step_validate,
        "write": _step_write,
    }

    run_workflow(
        workflow=WORKFLOW,
        state_cls=DraftWeekState,
        initial_state=DraftWeekState(week_prefix=week_prefix),
        steps=steps,
        thread_id=thread_id,
        store=store,
    )
