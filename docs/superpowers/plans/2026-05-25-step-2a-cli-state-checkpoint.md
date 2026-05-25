# Step 2a: CLI, State, Checkpoint — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the bare `draft_week` workflow shell: CLI command, `DraftWeekState` model, checkpoint save/restore, overwrite-confirm gate, and resume support. No LLM calls, no Notion writes beyond the existence check.

**Architecture:** Add `DraftWeekState` to `workflow_state.py`, create `workflows/draft_week.py` with a step registry dispatched by the shared `run_workflow()` runner, replace the placeholder `plan` CLI command with `draft-week`, and register `"draft_week"` in the CLI resume registry. The `overwrite_check` step uses `summaries_db.find_summary_row()` + `read_plan_property()` to detect existing plans and gates on `hitl_confirm`. All remaining steps are stubs raising `RuntimeError`.

**Tech Stack:** Python 3.13, Pydantic, Typer, Rich, pytest, SQLite (CheckpointStore)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/weekforge/models/workflow_state.py` | Edit | Add `DraftWeekState` model |
| `src/weekforge/workflows/draft_week.py` | Create | `run_draft` entry + step registry + `overwrite_check` + stub steps |
| `src/weekforge/cli.py` | Edit | Replace `plan` placeholder with `draft-week` command, add `"draft_week"` to resume registry |
| `tests/models/test_draft_week_state.py` | Create | Unit tests for `DraftWeekState` serialization |
| `tests/workflows/test_draft_week.py` | Create | Tests for overwrite_check, stub steps, run_draft |
| `tests/test_cli.py` | Edit | Tests for `draft-week` command and resume integration |

---

### Task 1: Add `DraftWeekState` to `workflow_state.py`

**Files:**
- Modify: `src/weekforge/models/workflow_state.py`
- Create: `tests/models/test_draft_week_state.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/models/test_draft_week_state.py
from weekforge.models.workflow_state import DraftWeekState


def test_draft_week_state_defaults():
    state = DraftWeekState(week_prefix="W15")
    assert state.step == "overwrite_check"
    assert state.week_prefix == "W15"
    assert state.messages_json == []
    assert state.calls == []
    assert state.last_output is None
    assert state.pending_feedback is None
    assert state.validation_retry_used is False
    assert state.validation_warning is None
    assert state.written_page_id is None
    assert state.is_bootstrap is None
    assert state.plan_state_raw is None
    assert state.plan_state_page_id is None
    assert state.started_at is not None


def test_draft_week_state_roundtrip():
    state = DraftWeekState(week_prefix="W07")
    json_str = state.model_dump_json()
    restored = DraftWeekState.model_validate_json(json_str)
    assert restored.week_prefix == "W07"
    assert restored.step == "overwrite_check"
    assert restored.started_at == state.started_at
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/models/test_draft_week_state.py -v`
Expected: ImportError — `DraftWeekState` not in `workflow_state`

- [ ] **Step 3: Implement `DraftWeekState`**

Add to `src/weekforge/models/workflow_state.py`, after `SummarizeWeekState`:

```python
class DraftWeekState(BaseModel):
    week_prefix: str
    step: str = "overwrite_check"
    messages_json: list[dict[str, Any]] = Field(default_factory=list)
    calls: list[CallMetadata] = Field(default_factory=list)
    last_output: Any = None
    pending_feedback: str | None = None
    validation_retry_used: bool = False
    validation_warning: str | None = None
    written_page_id: str | None = None
    is_bootstrap: bool | None = None
    plan_state_raw: str | None = None
    plan_state_page_id: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

Note: `last_output` is typed `Any` for now. Step 2c will define `WeekPlan` and narrow the type.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/models/test_draft_week_state.py -v`
Expected: 2 passed

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: 175 passed

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/models/workflow_state.py tests/models/test_draft_week_state.py
git commit -m "feat: add DraftWeekState model for draft_week workflow"
```

---

### Task 2: Create `draft_week.py` with overwrite_check and stubs

**Files:**
- Create: `src/weekforge/workflows/draft_week.py`
- Create: `tests/workflows/test_draft_week.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/workflows/test_draft_week.py
from unittest.mock import MagicMock, patch

import pytest

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.workflow_state import DraftWeekState


def test_overwrite_check_no_existing_row():
    """No summary row → transition to load_context immediately."""
    from weekforge.workflows.draft_week import _step_overwrite_check

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        result = _step_overwrite_check(state, cost)

    assert result == "load_context"


def test_overwrite_check_existing_row_empty_plan():
    """Row exists but Plan property empty → transition to load_context."""
    from weekforge.workflows.draft_week import _step_overwrite_check

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1", "properties": {}}
        mock_db.read_plan_property.return_value = None
        result = _step_overwrite_check(state, cost)

    assert result == "load_context"


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_approve(mock_confirm):
    """Row has Plan → HITL confirm → approve → load_context."""
    from weekforge.workflows.draft_week import _step_overwrite_check

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Push day + Hinge day\nConditioning x2"
        result = _step_overwrite_check(state, cost)

    assert result == "load_context"


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_quit(mock_confirm):
    """Row has Plan → HITL confirm → quit → None (pause)."""
    from weekforge.workflows.draft_week import _step_overwrite_check

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()
    mock_confirm.return_value = MagicMock(approved=False, quit=True, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Existing plan text"
        result = _step_overwrite_check(state, cost)

    assert result is None


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_feedback_treated_as_quit(mock_confirm):
    """Feedback at overwrite gate = quit (nothing to refine yet)."""
    from weekforge.workflows.draft_week import _step_overwrite_check

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()
    mock_confirm.return_value = MagicMock(approved=False, quit=False, feedback="some feedback")

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Existing plan text"
        result = _step_overwrite_check(state, cost)

    assert result is None


def test_stub_steps_raise():
    """All future steps must raise RuntimeError with clear message."""
    from weekforge.workflows.draft_week import (
        _step_accept,
        _step_agent,
        _step_load_context,
        _step_validate,
        _step_write,
    )

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    for step_fn in [_step_load_context, _step_agent, _step_accept, _step_validate, _step_write]:
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            step_fn(state, cost)


def test_run_draft_creates_checkpoint(tmp_path):
    """run_draft saves checkpoint before first step dispatch."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None
    assert rec.workflow == "draft_week"


def test_run_draft_resumes_from_checkpoint(tmp_path):
    """Resume dispatches to the saved step."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(week_prefix="W15", step="load_context")
    store.save("draft-week-W15", "draft_week", "load_context", state)

    with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
        run_draft("W15", "draft-week-W15", store)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/workflows/test_draft_week.py -v`
Expected: ModuleNotFoundError — `weekforge.workflows.draft_week` does not exist

- [ ] **Step 3: Implement `draft_week.py`**

```python
# src/weekforge/workflows/draft_week.py
from rich.console import Console

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import hitl_confirm
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.workflow_state import DraftWeekState
from weekforge.tools import summaries_db
from weekforge.workflows.runner import StepFn, run_workflow

_console = Console()
WORKFLOW = "draft_week"


def _step_overwrite_check(state: DraftWeekState, cost: RunCost) -> str | None:
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
        checkpoint=CheckpointStore.__new__(CheckpointStore),
        thread_id="",
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


_STEPS: dict[str, StepFn[DraftWeekState]] = {
    "overwrite_check": _step_overwrite_check,
    "load_context": _step_load_context,
    "agent": _step_agent,
    "accept": _step_accept,
    "validate": _step_validate,
    "write": _step_write,
}


def run_draft(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    run_workflow(
        workflow=WORKFLOW,
        state_cls=DraftWeekState,
        initial_state=DraftWeekState(week_prefix=week_prefix),
        steps=_STEPS,
        thread_id=thread_id,
        store=store,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/workflows/test_draft_week.py -v`
Expected: 9 passed

- [ ] **Step 5: Fix: overwrite_check hitl_confirm needs real store/thread_id**

The `overwrite_check` step calls `hitl_confirm` which calls `checkpoint.save()`. But the step function only receives `(state, cost)` — it doesn't have `store` or `thread_id`. Same closure pattern as `summarize_week.py`'s accept step.

Move `_step_overwrite_check` into `run_draft` as a closure:

```python
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
```

Keep `_step_overwrite_check` as a module-level function too (for direct unit testing), but `run_draft` uses the closure version. Update tests to test both: module-level for logic, `run_draft` for integration.

Actually, simpler approach: keep module-level `_step_overwrite_check` for unit tests (mock `hitl_confirm` at module level). The closure in `run_draft` just delegates to it but passes `store`/`thread_id`. But `_step_overwrite_check` signature is `(state, cost)` — it can't receive store/thread_id.

Best approach: make `_step_overwrite_check` a standalone function with extra params, and the closure in `run_draft` calls it. But the spec says step functions are `Callable[[S, RunCost], str | None]`. So the closure is the correct pattern — same as `summarize_week.py`.

For unit tests, mock `hitl_confirm` at `weekforge.workflows.draft_week.hitl_confirm` and test the inner logic via `run_draft` with a real `CheckpointStore`. The tests above already do this pattern via module-level function — update them to test through `run_draft` instead.

Revised test approach — test overwrite logic through `run_draft`:

```python
# tests/workflows/test_draft_week.py
from unittest.mock import MagicMock, patch

import pytest

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost
from weekforge.models.workflow_state import DraftWeekState


def test_overwrite_check_no_existing_row(tmp_path):
    """No summary row → skip overwrite, hit load_context stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
            run_draft("W15", "draft-week-W15", store)

    mock_db.find_summary_row.assert_called_once_with("W15")


def test_overwrite_check_existing_row_empty_plan(tmp_path):
    """Row exists but Plan empty → skip overwrite, hit load_context stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1", "properties": {}}
        mock_db.read_plan_property.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
            run_draft("W15", "draft-week-W15", store)


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_approve(mock_confirm, tmp_path):
    """Row has Plan → HITL approve → load_context stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Push day + Hinge day\nConditioning x2"
        with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
            run_draft("W15", "draft-week-W15", store)

    mock_confirm.assert_called_once()


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_existing_plan_quit(mock_confirm, tmp_path):
    """Row has Plan → HITL quit → workflow pauses (no RuntimeError)."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=False, quit=True, feedback=None)

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Existing plan text"
        run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None
    assert rec.step == "overwrite_check"


@patch("weekforge.workflows.draft_week.hitl_confirm")
def test_overwrite_check_feedback_treated_as_quit(mock_confirm, tmp_path):
    """Feedback at overwrite gate = quit (nothing to refine yet)."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    mock_confirm.return_value = MagicMock(approved=False, quit=False, feedback="some feedback")

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = {"id": "page-1"}
        mock_db.read_plan_property.return_value = "Existing plan text"
        run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None


def test_overwrite_check_plan_preview_truncated(tmp_path):
    """Long plan text truncated to 10 lines in HITL context."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    long_plan = "\n".join(f"Line {i}" for i in range(20))

    with patch("weekforge.workflows.draft_week.hitl_confirm") as mock_confirm:
        mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
        with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
            mock_db.find_summary_row.return_value = {"id": "page-1"}
            mock_db.read_plan_property.return_value = long_plan
            with pytest.raises(RuntimeError, match="Not yet implemented"):
                run_draft("W15", "draft-week-W15", store)

    call_kwargs = mock_confirm.call_args
    context_text = call_kwargs.kwargs.get("context", call_kwargs[1].get("context", ""))
    assert "truncated" in context_text
    assert "Line 0" in context_text
    assert "Line 9" in context_text
    assert "Line 10" not in context_text


def test_stub_steps_raise():
    """All future steps raise RuntimeError."""
    from weekforge.workflows.draft_week import (
        _step_accept,
        _step_agent,
        _step_load_context,
        _step_validate,
        _step_write,
    )

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    for step_fn in [_step_load_context, _step_agent, _step_accept, _step_validate, _step_write]:
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            step_fn(state, cost)


def test_run_draft_creates_checkpoint(tmp_path):
    """run_draft saves checkpoint before first step dispatch."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    with patch("weekforge.workflows.draft_week.summaries_db") as mock_db:
        mock_db.find_summary_row.return_value = None
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None
    assert rec.workflow == "draft_week"


def test_run_draft_resumes_from_checkpoint(tmp_path):
    """Resume dispatches to the saved step."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(week_prefix="W15", step="load_context")
    store.save("draft-week-W15", "draft_week", "load_context", state)

    with pytest.raises(RuntimeError, match="Not yet implemented.*load_context"):
        run_draft("W15", "draft-week-W15", store)
```

- [ ] **Step 6: Revise implementation to use closure pattern**

Final `draft_week.py`:

```python
# src/weekforge/workflows/draft_week.py
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
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `uv run pytest tests/workflows/test_draft_week.py -v`
Expected: 10 passed

- [ ] **Step 8: Run full test suite**

Run: `uv run pytest -x -q`
Expected: 175 passed (new tests not yet in count)

- [ ] **Step 9: Commit**

```bash
git add src/weekforge/workflows/draft_week.py tests/workflows/test_draft_week.py
git commit -m "feat: create draft_week workflow with overwrite_check and stub steps"
```

---

### Task 3: Wire CLI `draft-week` command and resume registry

**Files:**
- Modify: `src/weekforge/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/test_cli.py`:

```python
def test_cli_draft_week_help() -> None:
    """draft-week command exists and shows help."""
    result = runner.invoke(app, ["draft-week", "--help"])
    assert result.exit_code == 0
    assert "weekly" in result.stdout.lower() or "plan" in result.stdout.lower() or "draft" in result.stdout.lower()


def test_cli_plan_placeholder_removed() -> None:
    """Old 'plan' command no longer exists."""
    result = runner.invoke(app, ["plan"])
    assert result.exit_code != 0


def test_cli_resume_dispatches_draft_week(tmp_path) -> None:
    """resume with draft_week checkpoint dispatches to run_draft."""
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    state = DraftWeekState(week_prefix="W15", step="load_context")
    store.save("draft-week-W15", "draft_week", "load_context", state)

    with patch("weekforge.cli._make_store", return_value=store):
        with patch("weekforge.workflows.draft_week.run_draft") as mock_run:
            mock_run.side_effect = RuntimeError("Not yet implemented")
            result = runner.invoke(app, ["resume", "--thread-id", "draft-week-W15"])

    # run_draft was called (RuntimeError caught by _run_or_pause isn't — it re-raises)
    # The point is that the registry dispatched correctly
    mock_run.assert_called_once()


def test_cli_register_workflows_includes_draft_week() -> None:
    """_register_workflows includes draft_week entry."""
    from weekforge.cli import _register_workflows, _WORKFLOW_RUNNERS
    _WORKFLOW_RUNNERS.clear()

    runners = _register_workflows()
    assert "draft_week" in runners
    assert "summarize_week" in runners
```

Also add these imports at the top of `tests/test_cli.py`:

```python
from weekforge.models.workflow_state import DraftWeekState
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_cli.py::test_cli_draft_week_help tests/test_cli.py::test_cli_plan_placeholder_removed tests/test_cli.py::test_cli_resume_dispatches_draft_week tests/test_cli.py::test_cli_register_workflows_includes_draft_week -v`
Expected: failures — `plan` command still exists, `draft-week` not registered

- [ ] **Step 3: Modify `cli.py`**

Replace the `plan` command (lines 86-89) with:

```python
@app.command("draft-week")
def draft_week(week: int = typer.Argument(..., help="Week number, e.g. 15")) -> None:
    """Draft a high-level weekly training plan."""
    from weekforge.tools.formatting import format_week_prefix
    from weekforge.workflows.draft_week import run_draft

    store = _make_store()
    week_prefix = format_week_prefix(week)
    tid = f"draft-week-{week_prefix}"
    _run_or_pause(tid, lambda: run_draft(week_prefix, tid, store))
```

Update `_register_workflows` to include `draft_week`:

```python
def _register_workflows() -> dict[str, Callable[[str, str, CheckpointStore], None]]:
    if not _WORKFLOW_RUNNERS:
        from weekforge.workflows.draft_week import run_draft
        from weekforge.workflows.summarize_week import run_summarize
        _WORKFLOW_RUNNERS["summarize_week"] = lambda wp, tid, store: run_summarize(wp, tid, store)
        _WORKFLOW_RUNNERS["draft_week"] = lambda wp, tid, store: run_draft(wp, tid, store)
    return _WORKFLOW_RUNNERS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all pass (existing + 4 new)

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/cli.py tests/test_cli.py
git commit -m "feat: replace plan placeholder with draft-week command, register in resume"
```

---

### Task 4: Update spec status and final verification

**Files:**
- Modify: `specs/steps/step-2a-cli-state-checkpoint.md`
- Modify: `specs/steps/step-2-planning.md`

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest -x -q`
Expected: all pass

- [ ] **Step 2: Verify acceptance criteria**

```bash
# DraftWeekState exists
grep -c "class DraftWeekState" src/weekforge/models/workflow_state.py
# Expected: 1

# draft-week CLI command exists
uv run weekforge draft-week --help 2>&1 | head -5
# Expected: shows help text

# resume registry includes draft_week
grep -c "draft_week" src/weekforge/cli.py
# Expected: >= 2

# No LLM imports in draft_week.py
grep -c "run_with_metadata\|pydantic_ai" src/weekforge/workflows/draft_week.py
# Expected: 0

# Step registry has all expected steps
grep -c "def _step_" src/weekforge/workflows/draft_week.py
# Expected: 5 (load_context, agent, accept, validate, write)

# Plan placeholder removed
grep -c "def plan()" src/weekforge/cli.py
# Expected: 0

# Uses run_workflow
grep -c "run_workflow" src/weekforge/workflows/draft_week.py
# Expected: 1

# Uses summaries_db
grep -c "summaries_db" src/weekforge/workflows/draft_week.py
# Expected: >= 2
```

- [ ] **Step 3: Mark spec status**

In `specs/steps/step-2a-cli-state-checkpoint.md`, change line 4 from `ready` to `done`.

In `specs/steps/step-2-planning.md`, update the sub-step table row for 2a from `⬜` to `✅`.

- [ ] **Step 4: Commit**

```bash
git add specs/steps/step-2a-cli-state-checkpoint.md specs/steps/step-2-planning.md
git commit -m "docs: mark step-2a done"
```

---

## Notes for Implementer

1. **Closure pattern for store/thread_id.** The `overwrite_check` step needs `store` and `thread_id` for `hitl_confirm`. These aren't in the `StepFn` signature. Solution: define `step_overwrite_check` inside `run_draft()` as a closure that captures `store` and `thread_id`. Same pattern used in `summarize_week.py` for its accept step.

2. **Feedback = quit at overwrite gate.** Per spec: "feedback is treated identically to quit since there is nothing to refine yet." The `hitl_confirm` offers approve/quit only (no feedback option). But if somehow feedback is returned, treat it as quit.

3. **`last_output: Any` for now.** The spec says `WeekPlan | None` but `WeekPlan` doesn't exist yet (created in step 2c). Using `Any` avoids a forward reference. Step 2c will narrow the type.

4. **The `plan` command removal.** The old `plan()` function at `cli.py:86-89` is a placeholder printing "Not yet implemented." Remove it entirely and replace with the real `draft_week` command.

5. **Test structure.** Tests for `overwrite_check` go through `run_draft` because the step is a closure inside `run_draft`. Mock `summaries_db` and `hitl_confirm` at the module level. The stub steps are module-level functions and can be tested directly.
