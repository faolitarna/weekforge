# Step 1d: Notion Write & PLAN_STATE

## Implementation Status

✅ **Done.** Renderer, PLAN_STATE agent, and workflow extension land in commit `0da0b93`. A follow-up commit `cdc551c` hardened Notion API integration — details in [DEC-008](../decision-log.md) and inline notes below.

**Implementation notes / deviations from draft:**
- **Notion 100-block batching.** Notion's `blocks.children.append` caps at 100 children per request. Both `write` and `plan_state_update` steps chunk the rendered block list into 100-item batches before calling `append`. Not documented in the draft — necessary for weeks with long exercise logs.
- **Dynamic title-property discovery.** The title property is not guaranteed to be named `"Title"`. `_get_title_property_name(database_id)` in `workflows/summarize_week.py` probes both the public API schema (`properties[*].type == "title"`) and the internal data-source schema (`data_sources[0].schema[*].type == "title"`) before falling back to the string `"Title"`.
- **Week filter value.** Notion stores the `Week` property as a plain numeric string (`"1"`), not `"W01"`. Workflow parses `int(state.week_prefix[1:])` and filters client-side against the rich_text `plain_text`; `filter_properties` in `data_sources.query` fails schema validation, so it was removed.
- **`RunCost` summary panel.** On `done`, the workflow prints a Rich panel with total tokens, latency, call count, and cost (aggregated across both `summarize_agent` and `plan_state_agent`). Not in the draft; added for observability.
- **PLAN_STATE page-id logging.** After a successful bootstrap write, the created page ID is logged so users can verify via the Notion UI.
- **Fixture-equality test for renderer.** Not implemented — tests use substring assertions. Preferred follow-up.

## Goal

Close the loop: render the approved `WeekSummary` back into the legacy text format, write it to the `training_week_summaries` Notion row (updating the row step-2 pre-created), and update the cumulative `PLAN_STATE` tracker (incremental merge or bootstrap). This is the only sub-step that mutates Notion persistently.

## Prerequisites

Step 1c complete (approved `WeekSummary` produced, workflow pauses at `write` step with `NotImplementedError`).

## What You're Building

| File | Action | Purpose |
|------|--------|---------|
| `src/weekforge/tools/week_summary_renderer.py` | NEW | `WeekSummary` → legacy text format (Tier-0, pure string building) |
| `src/weekforge/tools/plan_state.py` | NEW | PLAN_STATE query, incremental merge helpers, bootstrap composer |
| `src/weekforge/agents/plan_state_agent.py` | NEW | Tier-2 agent for PLAN_STATE update (merge reasoning requires LLM) |
| `src/weekforge/workflows/summarize_week.py` | UPDATE | Replace `write` step stub with real implementation; add `update_plan_state` step |
| `tests/tools/test_week_summary_renderer.py` | NEW | Round-trip tests against the legacy text format |
| `tests/tools/test_plan_state.py` | NEW | Incremental merge + bootstrap unit tests |

## Specification

### Week summary renderer (`tools/week_summary_renderer.py`)

Deterministic string builder. Target output format = `<summary-format>` block in `source-material/.claude/commands/summarize_week.md` (lines 231–301). Exact field names and delimiters preserved.

```python
def render_week_summary(summary: WeekSummary) -> str:
    """Render WeekSummary into the legacy WEEK_SUMMARY text block."""
```

Behavior:
- Emits sections in order: `WEEK_SUMMARY`, `COMPLETION`, `CONTEXT`, blank line, `SESSIONS`, `EXERCISE_LOG`, `CARDIO_LOG`, `CLIMBING_LOG`, `PAIN_STATUS`, `ISSUES`, `WINS`, `RECOMMENDATIONS_NEXT`, `PLAN_ADHERENCE` (if present), `IMPLICIT_FEEDBACK`.
- Pipe-delimited exercise lines, `planned→actual` notation for modified params, `done>{actual}` and `skip` status codes.
- Omits `PLAN_ADHERENCE` section entirely when `summary.plan_adherence is None` (matches legacy "n/a" behavior).
- Unit tests verify byte-level format compliance against fixture files under `tests/fixtures/week_summary/`.

### Notion write

Step-2 pre-creates the `training_week_summaries` row with `Week=W##`, `Plan=<markdown>`, `Summary=<empty>`. Step-1d's write path:

1. Query row: filter `Week == week_prefix`, limit 1.
2. If exists: update the row's `Summary` property (rich_text) and set the page body to the rendered text (wrapped in a code block for readability in Notion).
3. If does not exist (no step-2 run preceded, or user manually deleted): create a new row with `Week=W##`, `Summary=<text>`, `Plan=<empty>`. Log a warning — delta analysis will not be available for future re-runs.

Reuse [notion_api_gateway.py](../../src/weekforge/tools/notion_api_gateway.py) `create` and an `update` helper (add if absent — thin wrapper over `pages.update`).

### PLAN_STATE storage

Per legacy: PLAN_STATE lives in `training_week_summaries` with `Week="PLAN_STATE"`. Treat it as a singleton row in the same DB — no separate DB needed.

### PLAN_STATE incremental path (`tools/plan_state.py` + `agents/plan_state_agent.py`)

Incremental merge is partly mechanical (append new week's MAIN_LIFTS weights, update AVG_COMPLETION, etc.) and partly interpretive (move resolved ACTIVE_ISSUES → RESOLVED, detect trend direction). Split:

- **Tier-0 (`plan_state.py`):** parse existing PLAN_STATE markdown into a structured `PlanState` Pydantic model. Apply purely mechanical updates (append weight to MAIN_LIFTS chain, increment `weeks_completed`, recalculate `avg_completion`, append week to `weekly` adherence trend).
- **Tier-2 (`plan_state_agent.py`):** given `(old_plan_state: PlanState, new_week: WeekSummary)`, return `updated: PlanState` with interpretive fields reasoned:
  - Issue lifecycle (active → resolved).
  - Trend direction per lift (`up/plateau/down` over the last 3 data points).
  - Deload detection / response interpretation.
  - Persistent skip / completion pattern updates.

Separation keeps the LLM cost proportional to the reasoning that needs it.

```python
# agents/plan_state_agent.py
@dataclass
class PlanStateDeps:
    existing_plan_state: PlanState
    new_week: WeekSummary

plan_state_agent = Agent(
    model=_model,
    instructions=compose_static_instructions(settings.caveman_mode) + "\n\n" + _PLAN_STATE_TASK,
    deps_type=PlanStateDeps,
    output_type=PlanState,
)

@plan_state_agent.instructions
def _inject_current_and_new(ctx: RunContext[PlanStateDeps]) -> str:
    return (
        "## Existing PLAN_STATE\n```json\n" + ctx.deps.existing_plan_state.model_dump_json(indent=2) + "\n```\n\n"
        "## New week to merge\n```json\n" + ctx.deps.new_week.model_dump_json(indent=2) + "\n```\n"
    )
```

### PLAN_STATE bootstrap path

When PLAN_STATE row does not exist (first-ever summary, or manually deleted):

1. Query `training_week_summaries` for all rows with `Week != "PLAN_STATE"` — these are the weekly summaries.
2. If zero weekly summaries exist: create an empty PLAN_STATE skeleton with `weeks_completed=0`. Log an info message.
3. Otherwise: Tier-2 agent call with ALL weekly summaries as `deps`, reasoning across weeks to build progression chains chronologically. Same agent (`plan_state_agent`) with a different deps variant, or a dedicated `bootstrap_plan_state_agent` — pick based on whether prompt diverges significantly. Spec leaves this choice to the implementer; recommend dedicated agent for prompt clarity.

Both paths render the result to the legacy PLAN_STATE text format (defined in `summarize_week.md` lines 376–450) and write to the PLAN_STATE row via `notion.create` or `notion.update`.

### Workflow extension

Extend `ExtractionState.step` enum with:
- `write` — render + Notion write for the week summary row.
- `plan_state_check` — query for PLAN_STATE singleton; branch to incremental or bootstrap.
- `plan_state_update` — run merge / bootstrap agent, render, write.
- `done`.

Step transitions persist before each LLM call (same pattern as `agent` step in 1c). On failure mid-write, resume re-enters at the failed step.

### Failure handling

- **Notion write failure** (either the summary row or PLAN_STATE): Tenacity retry. On terminal failure, checkpoint preserves the approved `WeekSummary` so user can `weekforge resume` without re-generating.
- **PLAN_STATE row exists but malformed** (schema drift / manual edits): parse attempt raises `PlanStateParseError`. Surface to user with the option to bootstrap-regenerate (destructive) or abort. Default abort.
- **Zero weekly summaries AND no PLAN_STATE** (bootstrap edge case): emit empty skeleton, do not call the LLM (no data to reason about).

### Tests

- `test_render_week_summary_byte_for_byte` — fixture `WeekSummary` → fixture `.txt` matches.
- `test_render_omits_plan_adherence_when_none` — `plan_adherence=None` → section absent.
- `test_plan_state_incremental_mechanical_updates` — new week merged; `weeks_completed` incremented, `avg_completion` recalculated, `weekly` chain appended.
- `test_plan_state_bootstrap_skeleton_when_no_summaries` — returns an empty PlanState, no LLM call made.
- `tests/workflows/test_summarize_week_end_to_end.py` — full path from `weekforge summarize-week 7` to both Notion writes (weekly row + PLAN_STATE row), using fake Notion + fake agent.

## Acceptance Criteria

- [~] `render_week_summary` emits the exact legacy format: same section order, same delimiters, same role/status codes. Substring-level tests in place; byte-for-byte fixture-equality test is a follow-up.
- [x] `PLAN_ADHERENCE` section omitted when `summary.plan_adherence is None`.
- [x] `training_week_summaries` row for `W##` is updated (not duplicated) when step-2 pre-created it; otherwise created with a warning logged.
- [x] PLAN_STATE incremental merge: weight chain extended, `weeks_completed` incremented, LLM-reasoned fields (trend, issue lifecycle) updated.
- [x] PLAN_STATE bootstrap: compiles from all weekly summaries chronologically; empty skeleton when no summaries exist.
- [x] PLAN_STATE written to `training_week_summaries` with `Week="PLAN_STATE"`.
- [x] Workflow resumes correctly after a Notion write failure (checkpoint preserves approved `WeekSummary`).
- [x] Full end-to-end test passes: `weekforge summarize-week 7` on a seeded Notion fake produces expected summary row + expected PLAN_STATE row.
- [x] Test suite passes: `uv run pytest tests/tools/test_week_summary_renderer.py tests/tools/test_plan_state.py tests/workflows/test_summarize_week_end_to_end.py`.

## Final `weekforge summarize-week` acceptance summary (step-1 complete)

- [~] `weekforge summarize-week <week>` runs the full pipeline: ~~overwrite check~~ (pass-through — open follow-up) → load context → Tier-0 extract → agent synth → HITL accept (feedback loop) → Notion write → PLAN_STATE update.
- [x] Checkpoint persistence works across terminal sessions at every step.
- [x] Run cost surfaced at completion (sum of all `agent` + `plan_state_agent` calls).
- [x] Output matches legacy `summarize_week.md` format semantically: same schema, same section content, same PLAN_STATE behavior.
