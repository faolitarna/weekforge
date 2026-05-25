# Step 2a: CLI, State, Checkpoint

## Status
done

## Goal

Wire the bare workflow shell for `draft_week` so an empty run can: parse a week argument, build a `DraftWeekState`, save/restore via `CheckpointStore`, prompt overwrite-confirm if the row's `Plan` property is non-empty, and resume a paused thread. No LLM, no Notion writes beyond the existence/overwrite check.

## Decisions

- **Workflow file:** `src/weekforge/workflows/draft_week.py`. Top-level entry `run_draft(week_prefix: str, thread_id: str, store: CheckpointStore) -> None` calls `run_workflow()` (DEC-P25) with a step registry dict. No inline state-machine loop.
- **State model:** `DraftWeekState` in `src/weekforge/models/workflow_state.py`. Fields:
  - `week_prefix: str`
  - `step: str = "overwrite_check"`
  - `messages_json: list[dict] = []` (DEC-P19, populated in 2c)
  - `calls: list[CallMetadata] = []`
  - `last_output: WeekPlan | None = None` (populated in 2c)
  - `pending_feedback: str | None = None` (populated in 2c)
  - `validation_retry_used: bool = False` (populated in 2d)
  - `validation_warning: str | None = None` (populated in 2d)
  - `written_page_id: str | None = None` (populated in 2d)
  - `is_bootstrap: bool | None = None` (set in 2b)
  - `plan_state_raw: str | None = None` (set in 2b)
  - `plan_state_page_id: str | None = None` (set in 2b)
  - `started_at: datetime` default factory
- **CLI command:** replace the placeholder `plan` command in `cli.py`. Signature: `weekforge draft-week <week: int>`. Thread ID `f"draft-week-{week_prefix}"`. Identical `_run_or_pause` wrapper.
- **Resume integration:** add `"draft_week": run_draft` entry to CLI resume registry (DEC-P30). State machine reads `week_prefix` from restored state.
- **Overwrite-confirm step (`overwrite_check`):** call `summaries_db.find_summary_row(week_prefix)` (DEC-P26), then `summaries_db.read_plan_property(row)`. If absent or Plan empty → transition to `load_context` immediately. If non-empty → render HITL panel via `hitl_confirm` showing first ~10 lines of existing Plan; user picks approve (overwrite, transition to `load_context`) / quit / feedback (in this gate, "feedback" is treated identically to quit since there is nothing to refine yet). Default = quit (preserve existing plan).
- **Workflow constant:** `WORKFLOW = "draft_week"`.
- **No async, no parallel.** Sequential per DEC-P9.

## Open questions

None.

## Inputs

- `week: int` — CLI argument (e.g. `15`)
- `settings.notion_db_training_week_summaries` — DB ID for overwrite check
- `CheckpointStore` — SQLite checkpoint persistence

## Outputs

- `DraftWeekState` initialized with `week_prefix`, `step` set to `"load_context"` (or quit)
- Checkpoint row in SQLite for resume support
- Side-effect: HITL overwrite-confirm prompt if Plan already exists

## Files

- `src/weekforge/workflows/draft_week.py`: create — `run_draft` entry + step registry + `overwrite_check` step function
- `src/weekforge/models/workflow_state.py`: edit — add `DraftWeekState`
- `src/weekforge/cli.py`: edit — replace `plan` placeholder with `draft-week` command, add `"draft_week"` to resume registry

## Data contracts

### `DraftWeekState`

```python
class DraftWeekState(BaseModel):
    week_prefix: str
    step: str = "overwrite_check"
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    last_output: WeekPlan | None = None
    pending_feedback: str | None = None
    validation_retry_used: bool = False
    validation_warning: str | None = None
    written_page_id: str | None = None
    is_bootstrap: bool | None = None
    plan_state_raw: str | None = None
    plan_state_page_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

### Step literals

```
overwrite_check → load_context → agent → accept → validate → write → done
```

## Workflow

1. `run_draft(week_prefix, thread_id, store)` — construct `DraftWeekState(week_prefix=...)`, build step registry dict, call `run_workflow()` (DEC-P25). Runner handles checkpoint restore, cost accumulation, dispatch loop, cleanup.
2. `overwrite_check` step function:
   - Call `summaries_db.find_summary_row(week_prefix)` → page or None.
   - If None or `summaries_db.read_plan_property(page)` empty → return `"load_context"`.
   - If non-empty → HITL confirm with plan preview. Approve → return `"load_context"`. Quit/feedback → return `None`.
3. Remaining steps (`load_context`, `agent`, `accept`, `validate`, `write`) are stubs raising `RuntimeError` — filled in 2b/2c/2d.
4. Register `"draft_week": run_draft` in CLI resume registry.

## Tier split

- Tier 0: state model, CLI wiring, checkpoint save/load, Notion query for overwrite check, HITL prompt rendering
- Tier 1: —
- Tier 2: —

## Failure modes

- Notion 404 on summaries DB → fail loud (existing `NotionNotFoundError`).
- Stale checkpoint (unknown workflow name) → CLI resume registry returns "unknown workflow" (DEC-P28, P30).
- Crash mid-overwrite-confirm → `overwrite_check` step persisted, resume re-prompts user (idempotent).
- Invalid week number (≤0) → Typer argument validation, fail before workflow starts. No upper bound — training week numbers can exceed 52 for long mesocycles.

## Acceptance criteria

- [ ] `weekforge draft-week 15` starts workflow, creates checkpoint, transitions past `overwrite_check`
- [ ] State persists and restores via `CheckpointStore`
- [ ] `weekforge resume --thread-id draft-week-W15` dispatches to `run_draft`
- [ ] Overwrite-confirm fires only when Plan property non-empty on existing row
- [ ] Overwrite-confirm default = quit (preserve existing plan)
- [ ] No LLM calls in this sub-step (zero cost)
- [ ] Placeholder `plan` command removed from CLI

## Out of scope

- Context loading (2b).
- Agent (2c).
- Notion Plan write (2d).
- Validation re-prompt loop (2d).

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P1..P32
- [step-2-prep-shared-infra.md](./step-2-prep-shared-infra.md) — runner, summaries_db, accept gate (prerequisites)
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — pattern reference (post-prep refactor)
- [hitl.py](../../src/weekforge/hitl.py) — `hitl_confirm` contract
- [checkpoint.py](../../src/weekforge/checkpoint.py) — `CheckpointStore`
