# Step 2a: CLI, State, Checkpoint

## Status
ready (facilitator pass — contract sections to be filled by specs-developer)

## Goal

Wire the bare workflow shell for `plan_week` so an empty run can: parse a week argument, build a `PlanWeekState`, save/restore via `CheckpointStore`, prompt overwrite-confirm if the row's `Plan` property is non-empty, and resume a paused thread. No LLM, no Notion writes beyond the existence/overwrite check.

## Decisions

- **Workflow file:** `src/weekforge/workflows/plan_week.py`. Top-level entry `run_plan(week_prefix: str, thread_id: str, store: CheckpointStore) -> None` mirrors `run_summarize` shape.
- **State model:** `PlanWeekState` in `src/weekforge/models/workflow_state.py`. Fields:
  - `week_prefix: str`
  - `step: str = "overwrite_check"`
  - `messages_json: list[dict] = []` (DEC-P19, populated in 2c)
  - `calls: list[CallMetadata] = []`
  - Layer-B fields populated in 2b are stored on this model only inside the active step (cleared before checkpoint save in 2b — keep checkpointed state thin)
  - `last_output: WeekPlan | None = None` (populated in 2c)
  - `written_page_id: str | None = None` (populated in 2d)
  - `started_at: datetime` default factory
- **CLI command:** replace the placeholder `plan` command in [cli.py](../../src/weekforge/cli.py). Signature: `weekforge plan <week: int>`. Thread ID `f"plan-week-{week_prefix}"`. Identical `_run_or_pause` wrapper.
- **Resume integration:** extend `cli.resume()` to dispatch on `rec.workflow == "plan_week"` → `run_plan("", thread_id, store)`. State machine reads `week_prefix` from restored state.
- **Overwrite-confirm step (`overwrite_check`):** query `notion_db_training_week_summaries`, find row where `Week == week_prefix`. If absent or row's `Plan` property is empty → transition to `load_context` immediately. If non-empty → render HITL panel via `hitl_confirm` showing first ~10 lines of existing Plan; user picks approve (overwrite, transition to `load_context`) / quit / feedback (in this gate, "feedback" is treated identically to quit since there is nothing to refine yet). Default = quit (preserve existing plan).
- **Workflow constant:** `WORKFLOW = "plan_week"`.
- **No async, no parallel.** Sequential per DEC-P9.

## Open questions

None.

## Inputs

(specs-developer to fill)

## Outputs

(specs-developer to fill)

## Files

(specs-developer to fill — expected: workflows/plan_week.py [create], models/workflow_state.py [edit, add PlanWeekState], cli.py [edit, replace plan command + extend resume])

## Data contracts

(specs-developer to fill — `PlanWeekState` field-by-field, exact `step` literal sequence)

## Workflow

(specs-developer to fill — `overwrite_check → load_context (placeholder transition out)`, plus `done` and resume entry points)

## Tier split

- Tier 0: state model, CLI wiring, checkpoint save/load, Notion query for overwrite check, HITL prompt rendering
- Tier 1: —
- Tier 2: —

## Failure modes

- Notion 404 on summaries DB → fail loud (existing `NotionNotFoundError`).
- Stale checkpoint (workflow == legacy "extraction") → existing `cli.resume` branch handles; new `plan_week` branch added here.
- Crash mid-overwrite-confirm → `overwrite_check` step persisted, resume re-prompts user (idempotent).

## Acceptance criteria

(specs-developer to fill — minimal: command starts, state persists, resume works, overwrite-confirm fires only when Plan exists, no LLM cost)

## Out of scope

- Context loading (2b).
- Agent (2c).
- Notion Plan write (2d).
- Validation re-prompt loop (2d).

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P1..P19
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — pattern to mirror
- [hitl.py](../../src/weekforge/hitl.py) — `hitl_confirm` contract
- [checkpoint.py](../../src/weekforge/checkpoint.py) — `CheckpointStore`
