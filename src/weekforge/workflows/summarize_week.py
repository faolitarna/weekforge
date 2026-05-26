import logging

from pydantic_ai.messages import ModelMessagesTypeAdapter
from rich.console import Console

from weekforge.agents.agent_run_with_metadata import run_with_metadata
from weekforge.agents.summarize_week_agent import SummarizeDeps, summarize_week_agent
from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import run_accept_gate
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.week_summary import WeekSummary
from weekforge.models.workflow_state import SummarizeWeekState
from weekforge.tools import summaries_db
from weekforge.workflows.runner import StepFn, run_workflow

_console = Console()
_logger = logging.getLogger(__name__)
WORKFLOW = "summarize_week"
MAX_ITERATIONS = 3


def _verbose(msg: str) -> None:
    from weekforge.config.env import settings
    if settings.verbose:
        _console.print(f"[dim]{msg}[/dim]")


def _step_overwrite_check(state: SummarizeWeekState, cost: RunCost) -> str | None:
    # Placeholder for 1d
    return "load_context"


def _step_load_context(state: SummarizeWeekState, cost: RunCost) -> str | None:
    from weekforge.tools.context_loader import load_week_summarize_context

    _verbose(f"load_context: loading all context for {state.week_prefix}…")
    ctx = load_week_summarize_context(state.week_prefix)

    state.user_profile_markdown = ctx.user_profile_markdown
    state.raw_sessions_markdown = ctx.raw_sessions_markdown
    state.tier0_summary = ctx.tier0_summary
    state.planned_plan_markdown = ctx.planned_plan_markdown
    state.plan_state_raw = ctx.plan_state_raw
    state.plan_state_page_id = ctx.plan_state_page_id
    state.is_bootstrap = ctx.is_bootstrap

    _console.print(f"[green]Loaded context for {state.week_prefix}: "
                   f"{ctx.tier0_summary.completion}, "
                   f"PLAN_STATE={'incremental' if not ctx.is_bootstrap else 'bootstrap'}[/green]")
    return "agent"


def _step_agent(state: SummarizeWeekState, cost: RunCost) -> str | None:
    prev = ModelMessagesTypeAdapter.validate_python(state.messages_json) if state.messages_json else None

    from weekforge.models.user_profile import UserProfile

    profile_md = state.user_profile_markdown or "Not provided"
    profile = UserProfile.model_construct(page_id="state", markdown=profile_md)

    assert state.tier0_summary is not None
    deps = SummarizeDeps(
        user_profile=profile,
        implicit_feedback=state.tier0_summary.implicit_feedback,
        plan_adherence=state.tier0_summary.plan_adherence,
        tier0_summary_json=state.tier0_summary.model_dump_json(
            exclude_none=True,
            include={"week_prefix", "completion", "context", "sessions", "implicit_feedback"},
        ),
        raw_sessions_markdown=state.raw_sessions_markdown or "",
        planned_plan_markdown=state.planned_plan_markdown,
        plan_state_raw=state.plan_state_raw,
    )

    prompt = f"Summarize week {state.week_prefix}."
    if state.pending_feedback:
         prompt += f"\nUser feedback: {state.pending_feedback}"

    iteration = len(state.calls) + 1
    with _console.status(f"[bold]Forging week summary… (attempt {iteration})[/bold]", spinner="bouncingBar"):
        result, meta, new_messages = run_with_metadata(
            summarize_week_agent, prompt, deps=deps, message_history=prev
        )
    state.last_output = result.output
    state.messages_json = ModelMessagesTypeAdapter.dump_python(new_messages, mode="json")
    state.calls.append(meta)
    cost.add(meta)
    _verbose(f"agent: {meta.input_tokens} input / {meta.output_tokens} output tokens")
    state.pending_feedback = None
    return "accept"


def _step_write(state: SummarizeWeekState, cost: RunCost) -> str | None:
    assert state.last_output is not None
    from weekforge.tools.week_summary_renderer import render_week_summary

    _verbose("write: rendering summary…")
    rendered = render_week_summary(state.last_output)

    page_id = summaries_db.upsert_summary(state.week_prefix, rendered)
    state.written_page_id = page_id

    _console.print(f"[green]Summary written to Notion ({state.written_page_id})[/green]")
    return "plan_state_update"


def _step_plan_state_update(state: SummarizeWeekState, cost: RunCost) -> str | None:
    from weekforge.agents.update_plan_state_agent import (
        PlanStateDeps,
        update_plan_state_agent,
    )
    from weekforge.config.env import settings
    from weekforge.tools import notion_api_gateway as notion
    from weekforge.tools.plan_state import PlanState

    assert state.is_bootstrap is not None

    assert state.last_output is not None
    if not state.is_bootstrap:
        existing_ps = PlanState.from_text(state.plan_state_raw or "")
        existing_ps.apply_mechanical_update(state.last_output)
        _verbose(f"plan_state_update: mechanical fields updated, week {existing_ps.weeks_completed}")

        plan_deps = PlanStateDeps(existing_plan_state=existing_ps, new_week=state.last_output)
        prompt = "Update the plan state logically based on the new week."
        with _console.status("[bold]Updating plan state…[/bold]", spinner="bouncingBar"):
            result, meta, _ = run_with_metadata(
                update_plan_state_agent, prompt, deps=plan_deps, message_history=None
            )
        updated_ps = result.output
        cost.add(meta)
        _verbose(f"plan_state_update: {meta.input_tokens} input / {meta.output_tokens} output tokens")

        rendered_ps = updated_ps.to_text(state.week_prefix)
        code_block = f"```text\n{rendered_ps}\n```"

        assert state.plan_state_page_id is not None
        title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
        notion.update(
            page_id=state.plan_state_page_id,
            properties={title_prop: {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]}},
            content=code_block
        )
    else:
        plan_deps = PlanStateDeps(existing_plan_state=PlanState(), all_weeks=[state.last_output])
        prompt = "Bootstrap plan state from provided weeks."
        _verbose("plan_state_update: bootstrapping from scratch…")
        with _console.status("[bold]Bootstrapping plan state…[/bold]", spinner="bouncingBar"):
            result, meta, _ = run_with_metadata(
                update_plan_state_agent, prompt, deps=plan_deps, message_history=None
            )
        updated_ps = result.output
        cost.add(meta)
        _verbose(f"plan_state_update: {meta.input_tokens} input / {meta.output_tokens} output tokens")

        rendered_ps = updated_ps.to_text(state.week_prefix)
        code_block = f"```text\n{rendered_ps}\n```"

        title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
        ps_page_id = notion.create(
            database_id=settings.notion_db_training_week_summaries,
            properties={
                "Week": {"rich_text": [{"text": {"content": "PLAN_STATE"}}]},
                title_prop: {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]},
            },
            content=code_block
        )
        _verbose(f"plan_state_update: created PLAN_STATE page {ps_page_id}")

    _console.print(f"[green]PLAN_STATE updated for {state.week_prefix}[/green]")
    return "done"


def run_summarize(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    def step_accept(state: SummarizeWeekState, cost: RunCost) -> str | None:
        assert state.last_output is not None

        highlights_text = "\n".join(f"- {h}" for h in state.last_output.highlights)
        trend_text = state.last_output.trend or "N/A"

        def render_fn() -> str:
            return (
                f"[bold]Highlights:[/bold]\n{highlights_text}\n\n"
                f"[bold]Trend:[/bold] {trend_text}\n\n"
            )

        result = run_accept_gate(
            render_fn=render_fn,
            approved_step="write",
            cost=cost,
            calls=state.calls,
            max_iterations=MAX_ITERATIONS,
            store=store,
            thread_id=thread_id,
            workflow=WORKFLOW,
            step="accept",
            state=state,
        )

        if result.feedback:
            state.pending_feedback = result.feedback

        return result.step

    steps: dict[str, StepFn[SummarizeWeekState]] = {
        "overwrite_check": _step_overwrite_check,
        "load_context": _step_load_context,
        "agent": _step_agent,
        "accept": step_accept,
        "write": _step_write,
        "plan_state_update": _step_plan_state_update,
    }

    run_workflow(
        workflow=WORKFLOW,
        state_cls=SummarizeWeekState,
        initial_state=SummarizeWeekState(week_prefix=week_prefix),
        steps=steps,
        thread_id=thread_id,
        store=store,
    )
