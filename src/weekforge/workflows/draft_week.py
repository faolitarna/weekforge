from pydantic_ai.messages import ModelMessagesTypeAdapter
from rich.console import Console

from weekforge.agents.agent_run_with_metadata import run_with_metadata
from weekforge.checkpoint import CheckpointStore
from weekforge.config.user_profile_loader import load_user_profile
from weekforge.hitl import hitl_confirm, run_accept_gate
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.workflow_state import DraftWeekState
from weekforge.tools import notion_api_gateway as notion
from weekforge.tools import summaries_db
from weekforge.tools.notion_api_gateway import get_page_title
from weekforge.tools.plan_state import parse_plan_state
from weekforge.workflows.runner import StepFn, run_workflow

_console = Console()
WORKFLOW = "draft_week"
MAX_ITERATIONS = 3


def _verbose(msg: str) -> None:
    from weekforge.config.env import settings
    if settings.verbose:
        _console.print(f"[dim]{msg}[/dim]")


def _step_load_context(state: DraftWeekState, cost: RunCost) -> str | None:
    from weekforge.agents.draft_week_agent import (
        DraftWeekDeps,
        WeekFeedbackRow,
        derive_active_flare,
    )
    from weekforge.config.env import settings

    _verbose(f"load_context: loading templates for {state.week_prefix}…")
    all_templates = notion.query(database_id=settings.notion_db_training_templates)
    template_sessions = [
        p for p in all_templates
        if get_page_title(p).startswith(state.week_prefix)
    ]
    if not template_sessions:
        raise RuntimeError(
            f"No template sessions found for {state.week_prefix}. "
            f"Check template naming in Notion (titles should start with '{state.week_prefix}')."
        )
    _verbose(f"load_context: {len(template_sessions)} templates matched")

    _verbose("load_context: loading feedback window…")
    week_num = int(state.week_prefix[1:])
    feedback_window: list[WeekFeedbackRow] = []
    # Walk backwards so missing weeks are skipped without creating gaps; then
    # reverse to give derive_active_flare() chronological (oldest-first) order.
    for prev_week in range(week_num - 1, max(week_num - 4, 0), -1):
        prev_prefix = f"W{prev_week:02d}"
        row = summaries_db.find_summary_row(prev_prefix)
        if row is None:
            continue
        plan_md = summaries_db.read_plan_property(row)
        summary_text = summaries_db.read_summary_body(row)
        feedback_window.append(WeekFeedbackRow(
            week_prefix=prev_prefix,
            plan_md=plan_md,
            summary_text=summary_text,
        ))
    feedback_window.reverse()
    _verbose(f"load_context: {len(feedback_window)} feedback rows")

    _verbose("load_context: loading PLAN_STATE…")
    raw_text, page_id = summaries_db.find_plan_state_row()
    plan_state = parse_plan_state(raw_text) if raw_text else None
    state.plan_state_raw = raw_text
    state.plan_state_page_id = page_id

    _verbose("load_context: loading user profile…")
    profile = load_user_profile()

    active_flare = derive_active_flare(feedback_window, plan_state)
    _verbose(f"load_context: active_flare={active_flare}")

    bootstrap = plan_state is None or len(feedback_window) == 0
    state.is_bootstrap = bootstrap

    if bootstrap:
        _console.print("[yellow]⚠ Bootstrap mode — PLAN_STATE or feedback history missing. "
                       "Agent will work with templates and user profile only.[/yellow]")

    _console.print(f"[green]Context loaded: {len(template_sessions)} templates, "
                   f"{len(feedback_window)} feedback weeks, "
                   f"PLAN_STATE={'yes' if plan_state else 'no'}, "
                   f"flare={'yes' if active_flare else 'no'}[/green]")

    return "agent"


def _step_agent(state: DraftWeekState, cost: RunCost) -> str | None:
    from weekforge.agents.draft_week_agent import (
        DraftWeekDeps,
        WeekFeedbackRow,
        derive_active_flare,
        draft_week_agent,
    )
    from weekforge.config.env import settings

    _verbose(f"agent: rebuilding context for {state.week_prefix}…")
    all_templates = notion.query(database_id=settings.notion_db_training_templates)
    template_sessions = [p for p in all_templates if get_page_title(p).startswith(state.week_prefix)]

    week_num = int(state.week_prefix[1:])
    feedback_window: list[WeekFeedbackRow] = []
    for prev_week in range(week_num - 1, max(week_num - 4, 0), -1):
        prev_prefix = f"W{prev_week:02d}"
        row = summaries_db.find_summary_row(prev_prefix)
        if row is None:
            continue
        feedback_window.append(WeekFeedbackRow(
            week_prefix=prev_prefix,
            plan_md=summaries_db.read_plan_property(row),
            summary_text=summaries_db.read_summary_body(row),
        ))
    feedback_window.reverse()

    plan_state = parse_plan_state(state.plan_state_raw) if state.plan_state_raw else None
    profile = load_user_profile()
    active_flare = derive_active_flare(feedback_window, plan_state)

    deps = DraftWeekDeps(
        week_prefix=state.week_prefix,
        template_sessions=template_sessions,
        feedback_window=feedback_window,
        plan_state=plan_state,
        plan_state_raw=state.plan_state_raw,
        user_profile=profile,
        active_flare=active_flare,
        bootstrap=state.is_bootstrap or False,
    )

    prev = ModelMessagesTypeAdapter.validate_python(state.messages_json) if state.messages_json else None

    prompt = f"Draft week plan for {state.week_prefix}."
    if state.pending_feedback:
        prompt += f"\nUser feedback: {state.pending_feedback}"

    iteration = len(state.calls) + 1
    with _console.status(f"[bold]Drafting week plan… (attempt {iteration})[/bold]", spinner="bouncingBar"):
        result, meta, new_messages = run_with_metadata(
            draft_week_agent, prompt, deps=deps, message_history=prev,
        )

    state.last_output = result.output
    state.messages_json = ModelMessagesTypeAdapter.dump_python(new_messages, mode="json")
    state.calls.append(meta)
    cost.add(meta)
    _verbose(f"agent: {meta.input_tokens} input / {meta.output_tokens} output tokens")
    state.pending_feedback = None
    return "accept"


def _step_validate(state: DraftWeekState, cost: RunCost) -> str | None:
    from weekforge.tools.week_plan_validator import validate_week_plan

    assert state.last_output is not None

    # User already saw the warning and approved — skip re-validation, force write.
    if state.validation_warning is not None:
        return "write"

    passed, diff = validate_week_plan(state.last_output)

    if passed:
        state.validation_warning = None
        return "write"

    if not state.validation_retry_used:
        _console.print(f"[yellow]⚠ Validation failed (first attempt): {diff}[/yellow]")
        state.validation_retry_used = True
        state.pending_feedback = diff
        return "agent"

    _console.print(f"[yellow]⚠ Validation failed again: {diff}[/yellow]")
    state.validation_warning = diff
    # Route to "accept" (not "agent") so the human sees the warning and can quit or override.
    return "accept"


# Hard Notion API limit for a single rich_text property value.
_NOTION_RICH_TEXT_LIMIT = 2000


def _step_write(state: DraftWeekState, cost: RunCost) -> str | None:
    assert state.last_output is not None
    from weekforge.tools.week_plan_renderer import render_week_plan

    rendered = render_week_plan(state.last_output)

    if len(rendered) > _NOTION_RICH_TEXT_LIMIT:
        _verbose(f"write: plan text {len(rendered)} chars, truncating to {_NOTION_RICH_TEXT_LIMIT}")
        rendered = rendered[: _NOTION_RICH_TEXT_LIMIT - len("[truncated]")] + "[truncated]"

    page_id = summaries_db.upsert_plan(state.week_prefix, rendered)
    state.written_page_id = page_id

    _console.print(f"[green]Plan written to Notion ({page_id})[/green]")
    return "done"


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

    def step_accept(state: DraftWeekState, cost: RunCost) -> str | None:
        assert state.last_output is not None
        from weekforge.tools.week_plan_renderer import render_week_plan

        def render_fn() -> str:
            return render_week_plan(state.last_output)

        result = run_accept_gate(
            render_fn=render_fn,
            approved_step="validate",
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

    steps: dict[str, StepFn[DraftWeekState]] = {
        "overwrite_check": step_overwrite_check,
        "load_context": _step_load_context,
        "agent": _step_agent,
        "accept": step_accept,
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
