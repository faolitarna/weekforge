"""Notion query → agent → HITL feedback loop → Notion write.

Exercises every infrastructure piece (checkpoint store, Notion tool layer,
LLM agent + metadata, HITL) in a single flow.

Lifecycle steps (persisted verbatim to SQLite — do not rename without a migration):

- "query":  fetch records from the test database
- "agent":  invoke the LLM, optionally with feedback + prior message history
- "review": HITL panel; user approves, provides feedback, or quits
- "write":  create a page in the test database with the agent output
- "done":   terminal; checkpoint deleted, run summary rendered

Feedback loop: on `[f]eedback`, the user's text is stored in `pending_feedback`
and `step` resets to `agent`. The next agent call receives the prior message
history, so the model sees its own previous output plus the new critique and
can refine iteratively. `message_history` is persisted across HITL pauses via
`ModelMessagesTypeAdapter`, so closing the terminal mid-run preserves context.
"""
import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field
from pydantic_ai.messages import ModelMessagesTypeAdapter
from rich.console import Console
from rich.panel import Panel

from weekforge.agents.agent_run_with_metadata import run_with_metadata
from weekforge.agents.e2e_agent import ProcessorResult, e2e_agent
from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import hitl_confirm
from weekforge.models.llm_call_cost import CallMetadata, RunCost
from weekforge.tools import notion_api_gateway as notion

_console = Console()
_logger = logging.getLogger(__name__)
WORKFLOW = "e2e"
_MAX_PROMPT_RECORDS = 10


class E2eState(BaseModel):
    """Full persisted state for the E2E validation run.

    `messages_json` holds the Pydantic AI message history as JSON-safe dicts
    (via ModelMessagesTypeAdapter) — enables feedback-loop resume after a
    terminal close. `calls` accumulates per-turn metadata so the final summary
    shows cost across every iteration, including ones that happened before a
    mid-run pause.
    """
    database_id: str
    records: list[dict[str, Any]] = Field(default_factory=list)
    last_output: str | None = None
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    pending_feedback: str | None = None
    step: str = "query"
    written_page_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def run_e2e(database_id: str | None, thread_id: str, store: CheckpointStore) -> None:
    """Run or resume the E2E validation workflow.

    Fresh run starts at `query`; resume jumps to whichever step is persisted.
    Agent calls are checkpointed BEFORE the network call so a crash mid-flight
    re-runs only the single interrupted turn on resume. On quit, the checkpoint
    is preserved for `weekforge resume`; on approve, it is deleted and the
    run summary panel is rendered.
    """
    record = store.load(thread_id)
    if record is not None and record.workflow == WORKFLOW:
        state = E2eState.model_validate_json(record.state_json)
    elif database_id is not None:
        state = E2eState(database_id=database_id)
    else:
        raise RuntimeError("No checkpoint found and no database_id provided.")

    while state.step != "done":
        if state.step == "query":
            state.records = notion.query(database_id=state.database_id)
            state.step = "agent"
            store.save(thread_id, WORKFLOW, state.step, state)

        elif state.step == "agent":
            store.save(thread_id, WORKFLOW, state.step, state)
            prev = ModelMessagesTypeAdapter.validate_python(state.messages_json) if state.messages_json else None
            prompt = _build_prompt(state.records, state.pending_feedback)
            result, meta, new_messages = run_with_metadata(
                e2e_agent, prompt, message_history=prev
            )
            output: ProcessorResult = result.output
            state.last_output = output.summary
            state.messages_json = ModelMessagesTypeAdapter.dump_python(new_messages, mode="json")
            state.calls.append(meta)
            state.pending_feedback = None
            state.step = "review"

        elif state.step == "review":
            cost = _rebuild_run_cost(state)
            _render_output_panel(state, cost)
            decision = hitl_confirm(
                context=(
                    f"Agent processed {len(state.records)} records.\n\n"
                    f"Output: {state.last_output}\n\n"
                    f"{cost.summary()}"
                ),
                recommendation="Approve to write to Notion, feedback to refine, quit to pause.",
                checkpoint=store,
                thread_id=thread_id,
                workflow=WORKFLOW,
                step="review",
                state=state,
            )
            if decision.approved:
                state.step = "write"
            elif decision.quit:
                _console.print(
                    f"[yellow]Paused.[/yellow] Resume: "
                    f"[bold cyan]uv run weekforge resume --thread-id {thread_id}[/bold cyan]"
                )
                return
            else:
                state.pending_feedback = decision.feedback
                state.step = "agent"

        elif state.step == "write":
            assert state.last_output is not None  # enforced by review-step precondition
            title_prop = _discover_title_property(state.records)
            state.written_page_id = notion.create(
                database_id=state.database_id,
                properties=_make_test_properties(title_prop),
                content=state.last_output,
            )
            state.step = "done"

        else:
            raise RuntimeError(f"Unknown step: {state.step!r}")

    store.delete(thread_id)
    _render_run_summary(state)


def _build_prompt(records: list[dict[str, Any]], feedback: str | None) -> str:
    truncated = records[:_MAX_PROMPT_RECORDS]
    if len(truncated) < len(records):
        _logger.warning("Truncated %d records to %d for prompt", len(records), _MAX_PROMPT_RECORDS)
    ids = [r.get("id", "unknown") for r in truncated]
    base = "Records: " + ", ".join(ids)
    if feedback:
        return f"{base}\n\nUser feedback on your previous output: {feedback}\nRefine accordingly."
    return base


def _discover_title_property(records: list[dict[str, Any]]) -> str:
    """Find the title property name from a sample record.

    Notion databases always have exactly one `type: "title"` property, but its
    name is user-defined (Name, Title, Task, etc.). We read it from the first
    queried record so the workflow works against any test database shape.
    Falls back to "Name" if no records exist.
    """
    for rec in records:
        for prop_name, prop in rec.get("properties", {}).items():
            if isinstance(prop, dict) and prop.get("type") == "title":
                return str(prop_name)
    return "Name"


def _make_test_properties(title_prop: str) -> dict[str, Any]:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%SZ")
    return {
        title_prop: {
            "title": [{"text": {"content": f"Weekforge E2E {stamp}"}}]
        }
    }


def _rebuild_run_cost(state: E2eState) -> RunCost:
    cost = RunCost()
    for c in state.calls:
        cost.add(c)
    return cost


def _render_output_panel(state: E2eState, cost: RunCost) -> None:
    body = (
        f"[bold]Output:[/bold] {state.last_output}\n\n"
        f"[bold]Iteration:[/bold] {len(state.calls)}\n"
        f"{cost.summary()}"
    )
    _console.print(Panel(body, title="Agent Output", border_style="cyan"))


def _render_run_summary(state: E2eState) -> None:
    cost = _rebuild_run_cost(state)
    wall_s = (datetime.now(UTC) - state.started_at).total_seconds()
    body = (
        f"[bold]Agent calls:[/bold]    {cost.call_count}\n"
        f"[bold]Total tokens:[/bold]   {cost.total_input_tokens} in / {cost.total_output_tokens} out\n"
        f"[bold]Cost:[/bold]           €{cost.total_cost_eur:.4f}\n"
        f"[bold]Wall time:[/bold]      {wall_s:.2f}s\n"
        f"[bold]Written pages:[/bold]  {1 if state.written_page_id else 0}"
    )
    _console.print(Panel(body, title="Run Summary", border_style="green"))
