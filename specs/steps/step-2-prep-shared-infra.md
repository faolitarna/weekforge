# Step 2-prep: Shared Infrastructure Extraction

## Status
ready

## Goal

Extract shared patterns from `summarize_week` into reusable modules before `draft_week` implementation begins. Pure refactoring — no new features, no behavior changes. `summarize_week` must pass all existing tests after refactor.

## Decisions

- DEC-P25 (workflow runner), DEC-P26 (summaries-db helper), DEC-P27 (get_text_prop to gateway), DEC-P28 (drop legacy alias), DEC-P29 (accept gate), DEC-P30 (CLI resume registry). See [step-2-planning.md](./step-2-planning.md).

## Open questions

None.

## Inputs

- Existing `workflows/summarize_week.py` (389 lines) — source of all patterns to extract
- Existing `hitl.py` — receives accept gate helper
- Existing `notion_api_gateway.py` — receives `get_text_prop`
- Existing `cli.py` — receives resume registry

## Outputs

- `workflows/runner.py` — shared workflow runner
- `tools/summaries_db.py` — summaries-DB access helper
- `notion_api_gateway.get_text_prop()` — public text property reader
- `hitl.run_accept_gate()` — parameterized accept step
- `cli.py` resume registry — dict-based dispatch
- `summarize_week.py` refactored to use all of above
- All 136 existing tests still pass

## Files

- `src/weekforge/workflows/runner.py`: create — `run_workflow()` function
- `src/weekforge/tools/summaries_db.py`: create — `find_summary_row`, `find_plan_state_row`, `read_plan_property`, `upsert_summary`, `upsert_plan`
- `src/weekforge/tools/notion_api_gateway.py`: edit — add `get_text_prop(page, prop_name)`
- `src/weekforge/hitl.py`: edit — add `run_accept_gate()`
- `src/weekforge/cli.py`: edit — replace resume if/elif with registry dict, remove `"extraction"` alias
- `src/weekforge/workflows/summarize_week.py`: edit — refactor to use runner, summaries_db, accept gate
- `src/weekforge/models/workflow_state.py`: edit — no changes yet (base class deferred, see DEC note below)

## Data contracts

### `run_workflow()`

```python
StepFn = Callable[[S, RunCost], str | None]

def run_workflow(
    workflow: str,
    state_cls: type[S],
    initial_state: S,
    steps: dict[str, StepFn],
    thread_id: str,
    store: CheckpointStore,
) -> None:
```

- Loads checkpoint → `state_cls.model_validate_json(record.state_json)` if found, else `initial_state`
- Restores `RunCost` from `state.calls`
- Loop: `store.save(thread_id, workflow, state.step, state)` → dispatch `steps[state.step](state, cost)` → set `state.step` to return value
- `None` return from step → quit (break, don't delete checkpoint)
- `"done"` step → `store.delete(thread_id)`, print cost panel
- Unknown step → `RuntimeError`

### `summaries_db` functions

```python
def find_summary_row(week_prefix: str) -> dict | None:
    """Query training_week_summaries, filter Week == week_prefix[1:]. Returns page dict or None."""

def find_plan_state_row() -> tuple[str | None, str | None]:
    """Query training_week_summaries, filter Week == 'PLAN_STATE'.
    Returns (raw_text_from_code_blocks, page_id) or (None, None)."""

def read_plan_property(page: dict) -> str | None:
    """Read 'Plan' rich-text property from a summaries page. Returns text or None."""

def upsert_summary(week_prefix: str, content: str) -> str:
    """Find or create summary row, write content to body. Returns page_id."""

def upsert_plan(week_prefix: str, plan_text: str) -> str:
    """Find or create summary row, write plan_text to Plan property. Returns page_id."""
```

### `get_text_prop()`

```python
def get_text_prop(page: dict, prop_name: str) -> str:
    """Read plain text from a rich_text property on a Notion page. Returns empty string if missing."""
```

### `run_accept_gate()` and `AcceptResult`

```python
@dataclass
class AcceptResult:
    step: str | None    # approved_step, "agent", or None (quit)
    feedback: str | None = None  # set when user chose feedback

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
    """Render accept panel, check burn warning, call hitl_confirm, return AcceptResult.
    
    Gate is decoupled from state shape — caller reads result.feedback
    and sets state.pending_feedback themselves.
    """
```

### CLI resume registry

```python
_WORKFLOW_RUNNERS: dict[str, Callable[[str, str, CheckpointStore], None]] = {
    "summarize_week": lambda wp, tid, store: run_summarize(wp, tid, store),
    "draft_week": lambda wp, tid, store: run_draft(wp, tid, store),
}
```

## Workflow

1. Add `get_text_prop()` to `notion_api_gateway.py`.
2. Create `tools/summaries_db.py` — implement all 5 functions using gateway.
3. Create `workflows/runner.py` — implement `run_workflow()`.
4. Add `run_accept_gate()` to `hitl.py`.
5. Refactor `summarize_week.py`:
   - Convert all steps to `StepFn` functions.
   - Replace inlined summaries-DB queries with `summaries_db` calls.
   - Replace accept step body with `run_accept_gate()` call.
   - Replace `run_summarize()` body with `run_workflow()` call + step registry.
6. Refactor `cli.py`:
   - Replace resume if/elif with `_WORKFLOW_RUNNERS` dict.
   - Remove `"extraction"` alias.
7. Run all tests. Fix any breakage from refactor.

## Tier split

- Tier 0: all changes (pure Python refactoring)
- Tier 1: —
- Tier 2: —

## Failure modes

- Refactored `summarize_week` breaks existing tests → fix before proceeding. This is a pure refactor — behavior must be identical.
- `run_workflow()` checkpoint save timing differs from original → verify crash-safety: save before dispatch means resume re-runs current step (idempotent by design).
- Stale `"extraction"` checkpoint in someone's SQLite → `resume` says "unknown workflow". Acceptable — no production checkpoints exist mid-flight.

## Acceptance criteria

- [ ] All 136 existing tests pass without modification (except test imports if needed)
- [ ] `summarize_week.py` uses `run_workflow()` — no inline state-machine loop
- [ ] `summarize_week.py` uses `summaries_db` functions — no inline query+filter patterns
- [ ] `summarize_week.py` accept step uses `run_accept_gate()` — no inline panel+branch logic
- [ ] `cli.py` resume uses dict registry — no if/elif chain
- [ ] `"extraction"` alias removed from codebase
- [ ] `get_text_prop` lives in `notion_api_gateway.py`, not in workflow files
- [ ] `run_workflow()` saves checkpoint before each step dispatch
- [ ] `run_workflow()` handles `None` return (quit) without deleting checkpoint

## Out of scope

- `DraftWeekState` and `draft_week.py` — those are step-2a.
- Shared state base class — deferred (speculative, Pydantic serialization concerns).
- Shared instruction injectors — deferred (speculative, framework constraints).
- New features or behavior changes.

## Reference

- [step-2-planning.md](./step-2-planning.md) — DEC-P25..P30
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — pattern source
- [hitl.py](../../src/weekforge/hitl.py) — accept gate target
- [notion_api_gateway.py](../../src/weekforge/tools/notion_api_gateway.py) — get_text_prop target
- [cli.py](../../src/weekforge/cli.py) — resume registry target
