# Step 1c: Summary Agent & Workflow

## Implementation Status

✅ **Done.** Agent, state model, workflow orchestrator, and CLI wiring land in commit `2a072b3`. Notion write + PLAN_STATE (step-1d) follow directly in the same `summarize_week.py` workflow.

**Deviations / open follow-ups:**
- `overwrite_check` step is a **pass-through placeholder** (`workflows/summarize_week.py`). The prompt described in 1a/1c Specification is not wired yet — fix before multi-week re-runs are safe.
- Workflow state model (`SummarizeWeekState`) gained extra fields owned by step-1d: `is_bootstrap`, `plan_state_raw`, `plan_state_page_id`, `written_page_id`, plus step literals `plan_state_check`, `plan_state_update`, `done`. Listed here so schema migrations stay traceable to a single source.
- Test gaps (tracked, not blocking):
  - `tests/agents/test_prompt_composer.py` covers only legacy `compose_system_prompt`, not the new `compose_static_instructions`.

## Goal

Add LLM synthesis on top of the Tier-0 extraction: define `summarize_agent` (Pydantic AI) with coaching persona + guardrails as static instructions and user profile + Tier-0 facts as dynamic instructions. Build the `extraction` workflow with a single HITL acceptance gate and feedback loop. Writes are stubbed — step-1d owns persistence.

## Prerequisites

Step 1a complete (loaders, CLI, settings).
Step 1b complete (Tier-0 extraction produces `WeekSummary` with machine-computable fields filled).

## What You're Building

| File | Action | Purpose |
|------|--------|---------|
| `src/weekforge/agents/summarize_agent.py` | NEW | Pydantic AI agent definition with `output_type=WeekSummary` |
| [src/weekforge/agents/prompt_composer.py](../../src/weekforge/agents/prompt_composer.py) | UPDATE | Add `compose_static_instructions(caveman_mode)` for multi-section composition |
| `src/weekforge/models/workflow_state.py` | UPDATE | Add `SummarizeWeekState` Pydantic model (checkpointable) |
| `src/weekforge/workflows/summarize_week.py` | NEW | `run_summarize(week_prefix, thread_id, store)` orchestrator |
| [src/weekforge/cli.py](../../src/weekforge/cli.py) | UPDATE | Replace 1a's `NotImplementedError` stub with real `run_summarize` invocation |
| `tests/agents/test_summarize_agent.py` | NEW | VCR-style test against a canned session extraction |
| `tests/workflows/test_summarize_week.py` | NEW | Workflow integration test with fake Notion + scripted HITL |

## Specification

### Prompt composition

Extend [prompt_composer.py](../../src/weekforge/agents/prompt_composer.py):

```python
def compose_static_instructions(caveman_mode: bool) -> str:
    """Concatenate coaching persona + guardrails + (optional) caveman directive.
    Passed to Agent(instructions=...) — static, known at construction time,
    eligible for prompt-cache prefix."""
    sections = [
        "## Coaching Persona\n\n" + load_prompt(Prompt.COACHING_PERSONA),
        "## Safety Guardrails\n\n" + load_prompt(Prompt.COACHING_GUARDRAILS),
    ]
    if caveman_mode:
        sections.append(CAVEMAN_LITE_DIRECTIVE)
    return "\n\n---\n\n".join(sections)
```

Keep existing `compose_system_prompt` for backward compatibility with `e2e_agent` (removal tracked as a small follow-up — DEC-006).

### Summary agent (`agents/summarize_agent.py`)

Uses Pydantic AI's `instructions=` (static) + `@agent.instructions` (dynamic) pattern — NOT `system_prompt=`. Verified against Pydantic AI docs: `instructions` are re-evaluated on every run and are NOT carried over from prior `message_history` entries, which is correct for feedback-loop workflows.

```python
from dataclasses import dataclass
from pydantic_ai import Agent, RunContext
from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_summary import WeekSummary, ImplicitFeedback, PlanAdherence

@dataclass
class SummarizeDeps:
    user_profile: UserProfile
    implicit_feedback: ImplicitFeedback
    plan_adherence: PlanAdherence | None
    tier0_summary_json: str           # WeekSummary partial, serialized as JSON for the prompt

_BASE_TASK_INSTRUCTIONS = """\
You are generating a weekly training summary. The user has already provided:
- Their coaching persona and safety guardrails (above).
- Their active user profile (conditions, HR zones, preferences).
- Deterministic facts computed from Notion: per-exercise log, completion rates, delta analysis.

Your job is to fill the narrative fields of the WeekSummary output:
- `context`: external factors mentioned in comments (illness, travel, equipment limits).
- `issues`: what didn't work or needs changing (synthesize from comments + skip patterns).
- `wins`: what worked well (synthesize from completion + positive comments).
- `recommendations_next`: concrete, coach-voiced suggestions for next week.
- `highlights`: 3–5 bullets for quick user review in the accept panel.
- `trend`: one sentence capturing week-over-week direction.

Do NOT recompute or modify deterministic fields (`sessions`, `exercise_log`, `implicit_feedback`,
`plan_adherence`, etc.). Copy them through unchanged from the input.
"""

_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

summarize_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(settings.caveman_mode) + "\n\n---\n\n" + _BASE_TASK_INSTRUCTIONS,
    deps_type=SummarizeDeps,
    output_type=WeekSummary,
)

@summarize_agent.instructions
def _inject_user_profile(ctx: RunContext[SummarizeDeps]) -> str:
    return "## Active User Profile\n\n" + ctx.deps.user_profile.markdown

@summarize_agent.instructions
def _inject_tier0_facts(ctx: RunContext[SummarizeDeps]) -> str:
    return (
        "## Deterministic Tier-0 Facts (treat as ground truth — do not regenerate)\n\n"
        f"### Tier-0 partial summary\n```json\n{ctx.deps.tier0_summary_json}\n```\n"
    )
```

Instruction order (static prefix first, then dynamic deps) matches Pydantic AI's cache-friendly ordering.

### Extraction state (`models/workflow_state.py`)

```python
from datetime import UTC, datetime
from typing import Any
from pydantic import BaseModel, Field
from weekforge.models.llm_call_cost import CallMetadata
from weekforge.models.week_summary import WeekSummary

class SummarizeWeekState(BaseModel):
    week_prefix: str
    overwrite_confirmed: bool = False
    tier0_summary: WeekSummary | None = None       # 1b output, filled in pre-agent
    last_output: WeekSummary | None = None         # latest agent output
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    pending_feedback: str | None = None
    step: str = "overwrite_check"
    written_page_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

Workflow steps (persisted literally — do not rename without a migration):
- `overwrite_check`: query training_week_summaries; if hit, prompt user to confirm overwrite.
- `load_context`: fetch user profile, planned Plan property (for delta), session pages.
- `tier0_extract`: run `assemble_tier0_summary` from step-1b.
- `agent`: call `summarize_agent` with `SummarizeDeps`, accumulate message history.
- `accept`: HITL accept panel with highlights + trend; options approve / feedback / quit.
- `write`: placeholder (raises `NotImplementedError`; 1d fills it).
- `done`.

### Workflow (`workflows/summarize_week.py`)

Modelled after [e2e.py](../../src/weekforge/workflows/e2e.py) — same shape, feedback loop, message-history persistence. Key differences:

- Fetches are trusted — no separate "verify sessions" or "verify extraction" HITL gates.
- Zero-session case hard-fails: `"No sessions found for {week_prefix} — check Notion 'Week' property spelling."`
- Single HITL gate at `accept` step:
  ```python
  decision = hitl_confirm(
      context=_render_accept_panel(state),
      recommendation="Approve writes summary to Notion. Feedback refines. Quit pauses.",
      checkpoint=store,
      thread_id=thread_id,
      workflow="extraction",
      step="accept",
      state=state,
  )
  ```
  The accept panel renders `highlights` (bulleted) and `trend` (single line) prominently, plus `completion` and session count; the full `WeekSummary` is accessible via a collapsed Rich panel or a side command (`:full` inside the HITL prompt — implementation detail, can be deferred).
- On feedback: store feedback, reset step to `agent`. Agent re-runs with `message_history` so it sees its own prior output and the critique. Re-runs MUST preserve Tier-0 fields (they don't change) — the agent's output_type lets Pydantic validate this, and the base instructions explicitly forbid regenerating them.

### CLI wiring

Replace 1a's `NotImplementedError` stub:

```python
@app.command("summarize-week")
def summarize_week(week: int = typer.Argument(...)) -> None:
    week_prefix = format_week_prefix(week)
    thread_id = f"summarize-{week_prefix}"
    store = CheckpointStore(...)
    run_summarize(week_prefix, thread_id, store)
```

Resume path: `weekforge resume --thread-id <id>` works automatically since `SummarizeWeekState` is checkpointed at every step transition (same pattern as e2e).

### Failure modes

- Notion query failure → Tenacity retry (existing behavior in [notion_api_gateway.py](../../src/weekforge/tools/notion_api_gateway.py)).
- Zero sessions for week → `RuntimeError("No sessions found for {W##}")`, CLI prints a clear recovery hint pointing at the `Week` property.
- Agent structured-output validation error → surfaces as Pydantic AI's standard validation exception; workflow checkpoints the last good state so user can re-run without losing prior messages.
- Checkpoint missing on `weekforge resume` → clear error, suggest re-running `weekforge summarize-week <week>`.

### Tests

- `tests/agents/test_summarize_agent.py` — VCR or mocked model response. Feed a canned Tier-0 `WeekSummary`, assert agent output preserves Tier-0 fields unchanged and populates narrative fields.
- `tests/workflows/test_summarize_week.py` — end-to-end with in-memory checkpoint store, fake Notion query, scripted HITL decisions (approve / feedback-then-approve / quit). Assert state persistence and message-history accumulation on feedback.
- `tests/agents/test_prompt_composer.py` — `compose_static_instructions` produces the expected concatenation with and without `caveman_mode`.

## Acceptance Criteria

- [x] `compose_static_instructions(False)` concatenates persona + guardrails. `compose_static_instructions(True)` appends the caveman directive. (No direct test — follow-up.)
- [x] `summarize_agent` is constructed with `instructions=` (NOT `system_prompt=`), `deps_type=SummarizeDeps`, `output_type=WeekSummary`.
- [x] `@summarize_agent.instructions` decorators inject user profile and Tier-0 facts from `RunContext.deps`.
- [x] `SummarizeWeekState` round-trips through JSON (checkpoint compatibility).
- [~] `run_summarize` executes overwrite_check → load_context → tier0_extract → agent → accept; each step persists before the next. (`overwrite_check` is a pass-through — see Implementation Status.)
- [x] HITL accept panel displays `highlights` + `trend` prominently; feedback loop re-invokes agent with `message_history`; quit preserves state for `weekforge resume`.
- [x] Agent output passes validation (Pydantic `WeekSummary`) and does not alter Tier-0 fields.
- [x] Zero-session input raises a `RuntimeError` with the week prefix in the message.
- [~] `write` step replaced with real implementation from step-1d (was a placeholder during 1c development).
- [~] Test suite passes: `uv run pytest tests/agents/ tests/workflows/test_summarize_week.py`. **Note:** `test_run_summarize_success` asserts the old `NotImplementedError("step-1d")` stub and will fail until updated.

## Out of Scope

- Rendering `WeekSummary` → legacy text format → step-1d
- Notion write (create or update training_week_summaries row) → step-1d
- PLAN_STATE incremental / bootstrap → step-1d
