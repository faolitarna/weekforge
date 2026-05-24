# Step 2-Prep: Shared Infrastructure Extraction

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract shared patterns from `summarize_week.py` into reusable modules (`run_workflow`, `summaries_db`, `get_text_prop`, `run_accept_gate`, CLI resume registry) so `draft_week` can build on them. Pure refactoring — no behavior changes.

**Architecture:** Extract five modules from `summarize_week.py`'s inline code. Each extraction creates a focused module with a clear interface, then `summarize_week.py` is refactored to call the new module. All 136 existing tests must pass after each task.

**Tech Stack:** Python 3.13, Pydantic, Rich, Typer, pytest, SQLite (CheckpointStore)

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/weekforge/tools/notion_api_gateway.py` | Edit | Add `get_text_prop(page, prop_name)` |
| `src/weekforge/tools/summaries_db.py` | Create | DB access helpers: `find_summary_row`, `find_plan_state_row`, `read_plan_property`, `upsert_summary`, `upsert_plan` |
| `src/weekforge/workflows/runner.py` | Create | Shared `run_workflow()` dispatching step functions |
| `src/weekforge/hitl.py` | Edit | Add `run_accept_gate()` + `AcceptResult` |
| `src/weekforge/cli.py` | Edit | Replace if/elif with `_WORKFLOW_RUNNERS` dict, remove `"extraction"` alias |
| `src/weekforge/workflows/summarize_week.py` | Edit | Refactor to use runner, summaries_db, accept gate |
| `tests/tools/test_summaries_db.py` | Create | Unit tests for summaries_db |
| `tests/workflows/test_runner.py` | Create | Unit tests for workflow runner |
| `tests/test_hitl.py` | Create | Tests for `run_accept_gate` |

---

### Task 1: Add `get_text_prop` to Notion Gateway

**Files:**
- Modify: `src/weekforge/tools/notion_api_gateway.py:240` (append)
- Test: `tests/tools/test_get_text_prop.py` (create)

- [ ] **Step 1: Write the failing test**

```python
# tests/tools/test_get_text_prop.py
from weekforge.tools.notion_api_gateway import get_text_prop


def test_get_text_prop_reads_rich_text():
    page = {"properties": {"Week": {"rich_text": [{"plain_text": "W07"}]}}}
    assert get_text_prop(page, "Week") == "W07"


def test_get_text_prop_concatenates_multiple_items():
    page = {"properties": {"Plan": {"rich_text": [
        {"plain_text": "Part 1"},
        {"plain_text": " Part 2"},
    ]}}}
    assert get_text_prop(page, "Plan") == "Part 1 Part 2"


def test_get_text_prop_missing_property_returns_empty():
    page = {"properties": {}}
    assert get_text_prop(page, "Week") == ""


def test_get_text_prop_empty_rich_text_returns_empty():
    page = {"properties": {"Week": {"rich_text": []}}}
    assert get_text_prop(page, "Week") == ""


def test_get_text_prop_no_properties_key_returns_empty():
    page = {}
    assert get_text_prop(page, "Week") == ""
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/tools/test_get_text_prop.py -v`
Expected: ImportError — `get_text_prop` not in `notion_api_gateway`

- [ ] **Step 3: Implement `get_text_prop`**

Add to the bottom of `src/weekforge/tools/notion_api_gateway.py`:

```python
def get_text_prop(page: dict[str, Any], prop_name: str) -> str:
    items = page.get("properties", {}).get(prop_name, {}).get("rich_text", [])
    return "".join(item.get("plain_text", "") for item in items)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/tools/test_get_text_prop.py -v`
Expected: 5 passed

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: 136 passed

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/tools/notion_api_gateway.py tests/tools/test_get_text_prop.py
git commit -m "refactor: add get_text_prop to notion_api_gateway"
```

---

### Task 2: Create `summaries_db` Module

**Files:**
- Create: `src/weekforge/tools/summaries_db.py`
- Create: `tests/tools/test_summaries_db.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/tools/test_summaries_db.py
from unittest.mock import patch

from weekforge.tools.summaries_db import (
    find_plan_state_row,
    find_summary_row,
    read_plan_property,
    upsert_plan,
    upsert_summary,
)


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_found(mock_gtp, mock_query):
    page = {"id": "page-1", "properties": {"Week": {"rich_text": [{"plain_text": "07"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    result = find_summary_row("W07")
    assert result == page


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_not_found(mock_gtp, mock_query):
    mock_query.return_value = []
    result = find_summary_row("W99")
    assert result is None


@patch("weekforge.tools.summaries_db.notion.fetch")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_plan_state_row_found(mock_gtp, mock_query, mock_fetch):
    page = {"id": "ps-1", "properties": {"Week": {"rich_text": [{"plain_text": "PLAN_STATE"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "PLAN_STATE" if name == "Week" else ""
    mock_fetch.return_value = {
        "properties": {},
        "content": [{"type": "code", "code": {"rich_text": [{"text": {"content": "hello"}}]}}],
    }

    raw, page_id = find_plan_state_row()
    assert raw == "hello\n"
    assert page_id == "ps-1"


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_plan_state_row_not_found(mock_gtp, mock_query):
    mock_query.return_value = []
    raw, page_id = find_plan_state_row()
    assert raw is None
    assert page_id is None


def test_read_plan_property():
    page = {"properties": {"Plan": {"rich_text": [{"plain_text": "Push day focus"}]}}}
    result = read_plan_property(page)
    assert result == "Push day focus"


def test_read_plan_property_empty():
    page = {"properties": {}}
    result = read_plan_property(page)
    assert result is None


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.update")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_summary_existing(mock_gtp, mock_query, mock_update, _mock_title):
    page = {"id": "page-1", "properties": {"Week": {"rich_text": [{"plain_text": "07"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    result = upsert_summary("W07", "summary content")
    assert result == "page-1"
    mock_update.assert_called_once()


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.create")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_summary_new(mock_gtp, mock_query, mock_create, _mock_title):
    mock_query.return_value = []
    mock_create.return_value = "new-page-id"

    result = upsert_summary("W07", "summary content")
    assert result == "new-page-id"
    mock_create.assert_called_once()


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.update")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_plan_existing(mock_gtp, mock_query, mock_update, _mock_title):
    page = {"id": "page-1", "properties": {"Week": {"rich_text": [{"plain_text": "W07"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "W07" if name == "Week" else ""

    result = upsert_plan("W07", "plan text")
    assert result == "page-1"
    mock_update.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tools/test_summaries_db.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement `summaries_db.py`**

```python
# src/weekforge/tools/summaries_db.py
from typing import Any

from weekforge.config.env import settings
from weekforge.tools import notion_api_gateway as notion


def find_summary_row(week_prefix: str) -> dict[str, Any] | None:
    week_num = week_prefix[1:]  # "W07" -> "07"
    all_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
    for page in all_pages:
        if notion.get_text_prop(page, "Week") == week_num:
            return page
    return None


def find_plan_state_row() -> tuple[str | None, str | None]:
    all_pages = notion.query(database_id=settings.notion_db_training_week_summaries)
    for page in all_pages:
        if notion.get_text_prop(page, "Week") == "PLAN_STATE":
            page_id = page["id"]
            fetched = notion.fetch(page_id)
            content_blocks = fetched.get("content", [])
            raw_text = ""
            for block in content_blocks:
                if block["type"] == "code":
                    raw_text += "".join(
                        t["text"]["content"] for t in block["code"]["rich_text"]
                    ) + "\n"
                elif block["type"] == "paragraph" and block.get("paragraph", {}).get("rich_text"):
                    raw_text += "".join(
                        t["text"]["content"] for t in block["paragraph"]["rich_text"]
                    ) + "\n"
            return raw_text, page_id
    return None, None


def read_plan_property(page: dict[str, Any]) -> str | None:
    text = notion.get_text_prop(page, "Plan")
    return text or None


def upsert_summary(week_prefix: str, content: str) -> str:
    week_num = week_prefix[1:]
    row = find_summary_row(week_prefix)
    code_block = f"```text\n{content}\n```"

    if row:
        page_id = row["id"]
        notion.update(page_id=page_id, content=code_block)
        return page_id

    title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
    return notion.create(
        database_id=settings.notion_db_training_week_summaries,
        properties={
            "Week": {"rich_text": [{"text": {"content": week_num}}]},
            title_prop: {"title": [{"text": {"content": f"{week_prefix} Summary"}}]},
        },
        content=code_block,
    )


def upsert_plan(week_prefix: str, plan_text: str) -> str:
    row = find_summary_row(week_prefix)
    plan_prop = {"rich_text": [{"text": {"content": plan_text}}]}

    if row:
        page_id = row["id"]
        notion.update(page_id=page_id, properties={"Plan": plan_prop})
        return page_id

    week_num = week_prefix[1:]
    title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
    return notion.create(
        database_id=settings.notion_db_training_week_summaries,
        properties={
            "Week": {"rich_text": [{"text": {"content": week_num}}]},
            "Plan": plan_prop,
            title_prop: {"title": [{"text": {"content": f"{week_prefix} Summary"}}]},
        },
        content="",
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tools/test_summaries_db.py -v`
Expected: 9 passed

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: 136 passed (new tests don't count yet — they aren't collected in the 136)

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/tools/summaries_db.py tests/tools/test_summaries_db.py
git commit -m "refactor: create summaries_db module for shared DB access"
```

---

### Task 3: Create Workflow Runner

**Files:**
- Create: `src/weekforge/workflows/runner.py`
- Create: `tests/workflows/test_runner.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/workflows/test_runner.py
from unittest.mock import MagicMock, call, patch

import pytest
from pydantic import BaseModel, Field

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import CallMetadata, RunCost
from weekforge.workflows.runner import run_workflow


class FakeState(BaseModel):
    step: str = "step_a"
    value: int = 0
    calls: list[CallMetadata] = Field(default_factory=list)


def test_run_workflow_dispatches_steps(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    def step_a(state: FakeState, cost: RunCost) -> str:
        state.value = 1
        return "step_b"

    def step_b(state: FakeState, cost: RunCost) -> str:
        state.value = 2
        return "done"

    steps = {"step_a": step_a, "step_b": step_b}
    initial = FakeState()

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    assert store.load("tid-1") is None  # deleted on done


def test_run_workflow_resumes_from_checkpoint(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    resumed_state = FakeState(step="step_b", value=10)
    store.save("tid-1", "test_wf", "step_b", resumed_state)

    def step_b(state: FakeState, cost: RunCost) -> str:
        state.value = state.value + 1
        return "done"

    steps = {"step_b": step_b}
    initial = FakeState()  # ignored — checkpoint takes precedence

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    assert store.load("tid-1") is None


def test_run_workflow_quit_on_none(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    def step_a(state: FakeState, cost: RunCost) -> str | None:
        return None  # user quit

    steps = {"step_a": step_a}
    initial = FakeState()

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    # Checkpoint preserved (not deleted)
    record = store.load("tid-1")
    assert record is not None


def test_run_workflow_unknown_step_raises(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    def step_a(state: FakeState, cost: RunCost) -> str:
        return "nonexistent"

    steps = {"step_a": step_a}
    initial = FakeState()

    with pytest.raises(RuntimeError, match="Unknown step"):
        run_workflow(
            workflow="test_wf",
            state_cls=FakeState,
            initial_state=initial,
            steps=steps,
            thread_id="tid-1",
            store=store,
        )


def test_run_workflow_saves_before_dispatch(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    save_calls = []
    original_save = store.save

    def tracking_save(*args, **kwargs):
        save_calls.append(args)
        return original_save(*args, **kwargs)

    store.save = tracking_save

    def step_a(state: FakeState, cost: RunCost) -> str:
        return "done"

    steps = {"step_a": step_a}
    initial = FakeState()

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=initial,
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    # At least one save before the step dispatch
    assert len(save_calls) >= 1
    assert save_calls[0][2] == "step_a"  # saved with step_a before dispatching


def test_run_workflow_restores_cost_from_calls(tmp_path):
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    captured_cost = []

    meta = CallMetadata(input_tokens=100, output_tokens=50, latency_ms=500, model_used="test", cost_eur=0.01)
    resumed = FakeState(step="step_a", calls=[meta])
    store.save("tid-1", "test_wf", "step_a", resumed)

    def step_a(state: FakeState, cost: RunCost) -> str:
        captured_cost.append(cost.total_input_tokens)
        return "done"

    steps = {"step_a": step_a}

    run_workflow(
        workflow="test_wf",
        state_cls=FakeState,
        initial_state=FakeState(),
        steps=steps,
        thread_id="tid-1",
        store=store,
    )

    assert captured_cost[0] == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/workflows/test_runner.py -v`
Expected: ModuleNotFoundError

- [ ] **Step 3: Implement `runner.py`**

```python
# src/weekforge/workflows/runner.py
from collections.abc import Callable
from typing import TypeVar

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel

from weekforge.checkpoint import CheckpointStore
from weekforge.models.llm_call_cost import RunCost

S = TypeVar("S", bound=BaseModel)
StepFn = Callable[[S, RunCost], str | None]

_console = Console()


def run_workflow(
    workflow: str,
    state_cls: type[S],
    initial_state: S,
    steps: dict[str, StepFn[S]],
    thread_id: str,
    store: CheckpointStore,
) -> None:
    record = store.load(thread_id)
    if record is not None and record.workflow == workflow:
        state = state_cls.model_validate_json(record.state_json)
    else:
        state = initial_state

    cost = RunCost()
    for c in getattr(state, "calls", []):
        cost.add(c)

    while state.step != "done":
        store.save(thread_id, workflow, state.step, state)

        step_name = state.step
        if step_name not in steps:
            raise RuntimeError(f"Unknown step: {step_name!r}")

        next_step = steps[step_name](state, cost)

        if next_step is None:
            return

        state.step = next_step

    store.delete(thread_id)
    _console.print(Panel(cost.summary(), title=f"Run complete — {workflow}", border_style="green"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/workflows/test_runner.py -v`
Expected: 6 passed

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: 136 passed

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/workflows/runner.py tests/workflows/test_runner.py
git commit -m "refactor: create shared workflow runner with step dispatch"
```

---

### Task 4: Add `run_accept_gate` to `hitl.py`

**Files:**
- Modify: `src/weekforge/hitl.py`
- Create: `tests/test_hitl.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_hitl.py
from unittest.mock import MagicMock, patch

from pydantic import BaseModel

from weekforge.checkpoint import CheckpointStore
from weekforge.hitl import AcceptResult, run_accept_gate
from weekforge.models.llm_call_cost import CallMetadata, RunCost


class DummyState(BaseModel):
    step: str = "accept"


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_approve(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[],
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step == "write"
    assert result.feedback is None


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_quit(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=False, quit=True, feedback=None)
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[],
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step is None
    assert result.feedback is None


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_feedback(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=False, quit=False, feedback="more detail")
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[],
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    assert result.step == "agent"
    assert result.feedback == "more detail"


@patch("weekforge.hitl.hitl_confirm")
def test_accept_gate_burn_warning(mock_confirm, tmp_path):
    mock_confirm.return_value = MagicMock(approved=True, quit=False, feedback=None)
    store = CheckpointStore(str(tmp_path / "cp.sqlite"))
    cost = RunCost()
    meta = CallMetadata(input_tokens=10, output_tokens=10, latency_ms=100, model_used="test", cost_eur=0.01)

    result = run_accept_gate(
        render_fn=lambda: "summary text",
        approved_step="write",
        cost=cost,
        calls=[meta, meta, meta],  # at max_iterations
        max_iterations=3,
        store=store,
        thread_id="tid",
        workflow="test",
        step="accept",
        state=DummyState(),
    )

    # Burn warning shown but still approve
    assert result.step == "write"
    # Verify the context passed to hitl_confirm contained the burn warning
    call_args = mock_confirm.call_args
    assert "burn warning" in call_args.kwargs.get("context", "") or "burn warning" in call_args[1].get("context", call_args[0][0] if call_args[0] else "")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_hitl.py -v`
Expected: ImportError — `AcceptResult` and `run_accept_gate` not in `hitl`

- [ ] **Step 3: Implement `run_accept_gate` and `AcceptResult`**

Add to `src/weekforge/hitl.py` (after existing code):

```python
@dataclass
class AcceptResult:
    step: str | None
    feedback: str | None = None


def run_accept_gate(
    render_fn: Callable[[], str],
    approved_step: str,
    cost: RunCost,
    calls: list,
    max_iterations: int,
    store: CheckpointStore,
    thread_id: str,
    workflow: str,
    step: str,
    state: BaseModel,
) -> AcceptResult:
    context_str = render_fn()

    if len(calls) >= max_iterations:
        context_str += "\n[red bold]Token burn warning: reached max iterations. Please accept.[/red bold]\n"

    context_str += f"\n{cost.summary()}"

    _console.print(Panel(context_str, title="Agent Output", border_style="cyan"))

    decision = hitl_confirm(
        context=context_str,
        recommendation="Approve proceeds. Feedback refines. Quit pauses.",
        checkpoint=store,
        thread_id=thread_id,
        workflow=workflow,
        step=step,
        state=state,
    )

    if decision.approved:
        return AcceptResult(step=approved_step)
    if decision.quit:
        _console.print(
            f"[yellow]Paused.[/yellow] Resume: "
            f"[bold cyan]uv run weekforge resume --thread-id {thread_id}[/bold cyan]"
        )
        return AcceptResult(step=None)
    return AcceptResult(step="agent", feedback=decision.feedback)
```

Also add import at top of `hitl.py`:

```python
from collections.abc import Callable

from weekforge.models.llm_call_cost import RunCost
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_hitl.py -v`
Expected: 4 passed

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: 136 passed

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/hitl.py tests/test_hitl.py
git commit -m "refactor: add run_accept_gate helper to hitl module"
```

---

### Task 5: Refactor `summarize_week.py` to Use Runner, `summaries_db`, and Accept Gate

**Files:**
- Modify: `src/weekforge/workflows/summarize_week.py` (major rewrite)

This is the critical task — refactor the 389-line monolith to use the new shared modules. All existing tests must pass without modification.

- [ ] **Step 1: Run existing tests to establish baseline**

Run: `uv run pytest tests/workflows/test_summarize_week.py tests/workflows/test_summarize_week_end_to_end.py -v`
Expected: 5 passed

- [ ] **Step 2: Refactor `summarize_week.py`**

Replace the entire file with step functions + `run_workflow()` call:

```python
# src/weekforge/workflows/summarize_week.py
import json
import logging
from typing import Any, Literal

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
from weekforge.tools.notion_api_gateway import get_text_prop
from weekforge.workflows.runner import StepFn, run_workflow

_console = Console()
_logger = logging.getLogger(__name__)
WORKFLOW = "summarize_week"
MAX_ITERATIONS = 3


def _verbose(msg: str) -> None:
    from weekforge.config.env import settings
    if settings.verbose:
        _console.print(f"[dim]{msg}[/dim]")


def _step_overwrite_check(state: SummarizeWeekState, cost: RunCost) -> str:
    return "load_context"


def _step_load_context(state: SummarizeWeekState, cost: RunCost) -> str:
    from weekforge.config.env import settings
    from weekforge.config.user_profile_loader import load_user_profile
    from weekforge.tools import notion_api_gateway as notion
    from weekforge.tools.raw_session_collector import assemble_raw_week

    _verbose(f"load_context: fetching sessions for {state.week_prefix}…")

    profile = load_user_profile()
    state.user_profile_markdown = profile.markdown
    _verbose("load_context: user profile loaded")

    week_num_str = str(int(state.week_prefix[1:]))
    all_session_pages = notion.query(database_id=settings.notion_db_training_sessions)
    session_pages = [p for p in all_session_pages if get_text_prop(p, "Week") == week_num_str]
    if not session_pages:
        raise RuntimeError(
            f"No session pages found for {state.week_prefix} in training_sessions DB."
        )
    _verbose(f"load_context: found {len(session_pages)} session pages")

    # Read Plan from summaries DB
    row = summaries_db.find_summary_row(state.week_prefix)
    if row:
        plan_text = summaries_db.read_plan_property(row)
        state.planned_plan_markdown = plan_text
        _verbose(f"load_context: plan found ({len(plan_text or '')} chars)")
    else:
        state.planned_plan_markdown = None
        _verbose("load_context: no plan found")

    raw_week = assemble_raw_week(
        week_prefix=state.week_prefix,
        session_pages=session_pages,
        planned_plan_markdown=state.planned_plan_markdown,
    )
    state.raw_sessions_json = json.dumps([
        {"name": s.name, "page_id": s.page_id, "done": s.done,
         "blocks": [{"block_type": b.block_type, "text": b.text, "checked": b.checked} for b in s.blocks],
         "comments": s.comments}
        for s in raw_week.sessions
    ])

    _console.print(f"[green]Loaded {len(raw_week.sessions)} sessions for {state.week_prefix}[/green]")
    return "tier0_extract"


def _step_tier0_extract(state: SummarizeWeekState, cost: RunCost) -> str:
    from weekforge.models.raw_week_data import RawBlock, RawSession
    from weekforge.models.week_summary import SessionLine
    from weekforge.tools.raw_session_collector import compute_checkbox_analysis

    _verbose(f"tier0_extract: computing checkbox analysis for {state.week_prefix}…")

    raw_sessions_data = json.loads(state.raw_sessions_json or "[]")
    sessions = [
        RawSession(
            page_id=s["page_id"], name=s["name"],
            blocks=[RawBlock(block_type=b["block_type"], text=b["text"], checked=b["checked"], raw={}) for b in s["blocks"]],
            comments=s["comments"],
        )
        for s in raw_sessions_data
    ]

    implicit_fb = compute_checkbox_analysis(sessions)

    session_lines = []
    for s_data in raw_sessions_data:
        blocks = s_data["blocks"]
        total = sum(1 for b in blocks if b["block_type"] == "to_do")
        checked = sum(1 for b in blocks if b["block_type"] == "to_do" and b["checked"])
        session_done = s_data.get("done", False)
        status: Literal["done", "skip", "partial"] = "done" if session_done else ("partial" if checked > 0 else "skip")
        raw_comments = s_data.get("comments", [])
        comment_text = " | ".join(raw_comments) if raw_comments else ""
        session_lines.append(SessionLine(
            name=s_data["name"],
            status=status,
            exercises_done=checked,
            exercises_total=total,
            pain_status=None,
            comment=comment_text,
        ))

    done_count = sum(1 for s in raw_sessions_data if s.get("done", False))
    total_count = len(session_lines)
    state.tier0_summary = WeekSummary(
        week_prefix=state.week_prefix,
        completion=f"{done_count}/{total_count}",
        sessions=session_lines,
        exercise_log=[],
        pain_status=[],
        implicit_feedback=implicit_fb,
    )
    _verbose(f"tier0_extract: {implicit_fb.total_checked}/{implicit_fb.total_exercises} checkboxes, {len(session_lines)} sessions")
    _console.print(f"[green]Tier-0 summary: {state.tier0_summary.completion}[/green]")
    return "plan_state_check"


def _step_plan_state_check(state: SummarizeWeekState, cost: RunCost) -> str:
    _verbose("plan_state_check: querying training_week_summaries…")

    raw_text, page_id = summaries_db.find_plan_state_row()
    if raw_text is not None:
        state.plan_state_raw = raw_text
        state.plan_state_page_id = page_id
        state.is_bootstrap = False
        _verbose(f"plan_state_check: found PLAN_STATE ({len(raw_text)} chars)")
    else:
        state.is_bootstrap = True
        _verbose("plan_state_check: no PLAN_STATE found (bootstrap)")

    _console.print(f"[green]PLAN_STATE: {'incremental' if not state.is_bootstrap else 'bootstrap'}[/green]")
    return "agent"


def _step_agent(state: SummarizeWeekState, cost: RunCost) -> str:
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
        raw_sessions_json=state.raw_sessions_json or "[]",
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


def _step_accept(state: SummarizeWeekState, cost: RunCost) -> str | None:
    assert state.last_output is not None

    def render() -> str:
        highlights_text = "\n".join(f"- {h}" for h in state.last_output.highlights)
        trend_text = state.last_output.trend or "N/A"
        return (
            f"[bold]Highlights:[/bold]\n{highlights_text}\n\n"
            f"[bold]Trend:[/bold] {trend_text}"
        )

    from weekforge.checkpoint import CheckpointStore as _CS

    result = run_accept_gate(
        render_fn=render,
        approved_step="write",
        cost=cost,
        calls=state.calls,
        max_iterations=MAX_ITERATIONS,
        store=cost._store,  # injected below
        thread_id=cost._thread_id,  # injected below
        workflow=WORKFLOW,
        step="accept",
        state=state,
    )

    if result.feedback:
        state.pending_feedback = result.feedback
    return result.step


def _step_write(state: SummarizeWeekState, cost: RunCost) -> str:
    assert state.last_output is not None
    from weekforge.tools.week_summary_renderer import render_week_summary

    _verbose("write: rendering summary…")
    rendered = render_week_summary(state.last_output)
    state.written_page_id = summaries_db.upsert_summary(state.week_prefix, rendered)
    _console.print(f"[green]Summary written to Notion ({state.written_page_id})[/green]")
    return "plan_state_update"


def _step_plan_state_update(state: SummarizeWeekState, cost: RunCost) -> str:
    from weekforge.agents.update_plan_state_agent import (
        PlanStateDeps,
        update_plan_state_agent,
    )
    from weekforge.config.env import settings
    from weekforge.tools import notion_api_gateway as notion
    from weekforge.tools.plan_state import (
        PlanState,
        parse_plan_state,
        render_plan_state,
        update_mechanical_fields,
    )

    assert state.is_bootstrap is not None
    assert state.last_output is not None

    if not state.is_bootstrap:
        existing_ps = parse_plan_state(state.plan_state_raw or "")
        existing_ps = update_mechanical_fields(existing_ps, state.last_output)
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

        rendered_ps = render_plan_state(updated_ps, state.week_prefix)
        code_block = f"```text\n{rendered_ps}\n```"

        assert state.plan_state_page_id is not None
        title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
        notion.update(
            page_id=state.plan_state_page_id,
            properties={title_prop: {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]}},
            content=code_block,
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

        rendered_ps = render_plan_state(updated_ps, state.week_prefix)
        code_block = f"```text\n{rendered_ps}\n```"

        title_prop = notion.get_title_property_name(settings.notion_db_training_week_summaries)
        notion.create(
            database_id=settings.notion_db_training_week_summaries,
            properties={
                "Week": {"rich_text": [{"text": {"content": "PLAN_STATE"}}]},
                title_prop: {"title": [{"text": {"content": f"Plan State - W01-{state.week_prefix}"}}]},
            },
            content=code_block,
        )

    _console.print(f"[green]PLAN_STATE updated for {state.week_prefix}[/green]")
    return "done"


_STEPS: dict[str, StepFn[SummarizeWeekState]] = {
    "overwrite_check": _step_overwrite_check,
    "load_context": _step_load_context,
    "tier0_extract": _step_tier0_extract,
    "plan_state_check": _step_plan_state_check,
    "agent": _step_agent,
    "accept": _step_accept,
    "write": _step_write,
    "plan_state_update": _step_plan_state_update,
}


def run_summarize(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    run_workflow(
        workflow=WORKFLOW,
        state_cls=SummarizeWeekState,
        initial_state=SummarizeWeekState(week_prefix=week_prefix),
        steps=_STEPS,
        thread_id=thread_id,
        store=store,
    )
```

**Important:** The accept step needs access to `store` and `thread_id`. The runner already saves before dispatch, so the accept gate's checkpoint save is redundant but harmless. However, `run_accept_gate` needs `store`/`thread_id` which the step function doesn't naturally have. 

**Solution:** Instead of the hacky `cost._store` pattern shown above, pass `store` and `thread_id` via a closure. Rewrite `run_summarize` to create step functions that close over `store`/`thread_id`:

```python
def run_summarize(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    def step_accept(state: SummarizeWeekState, cost: RunCost) -> str | None:
        assert state.last_output is not None

        def render() -> str:
            highlights_text = "\n".join(f"- {h}" for h in state.last_output.highlights)
            trend_text = state.last_output.trend or "N/A"
            return (
                f"[bold]Highlights:[/bold]\n{highlights_text}\n\n"
                f"[bold]Trend:[/bold] {trend_text}"
            )

        result = run_accept_gate(
            render_fn=render,
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
        "tier0_extract": _step_tier0_extract,
        "plan_state_check": _step_plan_state_check,
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
```

- [ ] **Step 3: Run existing tests**

Run: `uv run pytest tests/workflows/test_summarize_week.py tests/workflows/test_summarize_week_end_to_end.py -v`
Expected: 5 passed (behavior-identical refactor)

- [ ] **Step 4: Fix any test failures**

The tests mock `weekforge.workflows.summarize_week.hitl_confirm` and `weekforge.workflows.summarize_week.run_with_metadata`. After refactor:
- `run_with_metadata` is still imported at module level → mock path unchanged
- `hitl_confirm` is now called inside `run_accept_gate` via `weekforge.hitl.hitl_confirm` → update mock path in tests to `weekforge.hitl.hitl_confirm`

If tests fail, update the mock targets. The spec says "All 136 existing tests pass without modification (except test imports if needed)" — so import changes in test files are acceptable.

- [ ] **Step 5: Run full test suite**

Run: `uv run pytest -x -q`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/workflows/summarize_week.py
git commit -m "refactor: rewrite summarize_week to use runner and shared modules"
```

---

### Task 6: Refactor CLI Resume to Dict Registry + Remove "extraction" Alias

**Files:**
- Modify: `src/weekforge/cli.py:104-122`
- Modify: `tests/test_cli.py` (if needed)

- [ ] **Step 1: Run existing CLI tests to establish baseline**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all pass

- [ ] **Step 2: Refactor `cli.py` resume command**

Replace the `resume` function body:

```python
from collections.abc import Callable

_WORKFLOW_RUNNERS: dict[str, Callable[[str, str, CheckpointStore], None]] = {}


def _register_workflows() -> dict[str, Callable[[str, str, CheckpointStore], None]]:
    if not _WORKFLOW_RUNNERS:
        from weekforge.workflows.summarize_week import run_summarize
        _WORKFLOW_RUNNERS["summarize_week"] = lambda wp, tid, store: run_summarize(wp, tid, store)
    return _WORKFLOW_RUNNERS


@app.command()
def resume(
    thread_id: str = typer.Option(..., help="Thread ID of the checkpoint to resume."),
) -> None:
    """Resume from the last checkpoint (any thread)."""
    store = _make_store()
    rec = store.load(thread_id)
    if rec is None:
        console.print(f"[red]No checkpoint found for thread-id {thread_id}[/red]")
        raise typer.Exit(code=1)

    runners = _register_workflows()
    runner_fn = runners.get(rec.workflow)
    if runner_fn is None:
        console.print(f"[red]Unknown workflow: {rec.workflow}[/red]")
        raise typer.Exit(code=1)

    _run_or_pause(thread_id, lambda: runner_fn("", thread_id, store))
```

Key changes:
- `"extraction"` alias removed
- if/elif chain replaced by dict lookup
- Adding `draft_week` later = one dict entry

- [ ] **Step 3: Run CLI tests**

Run: `uv run pytest tests/test_cli.py -v`
Expected: all pass

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -x -q`
Expected: all pass

- [ ] **Step 5: Verify "extraction" alias removed**

Run: `grep -r "extraction" src/weekforge/`
Expected: no matches (or only in comments/docs)

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/cli.py
git commit -m "refactor: replace resume if/elif with workflow registry dict, drop extraction alias"
```

---

### Task 7: Remove `_get_text_prop` from `summarize_week.py` + Final Cleanup

**Files:**
- Modify: `src/weekforge/workflows/summarize_week.py` (remove dead helper)

- [ ] **Step 1: Verify `_get_text_prop` is unused in `summarize_week.py`**

Run: `grep -n "_get_text_prop" src/weekforge/workflows/summarize_week.py`
Expected: only the function definition (if it wasn't already removed in Task 5)

- [ ] **Step 2: Remove `_get_text_prop` if still present**

Delete the `_get_text_prop` function from `summarize_week.py`. It's been replaced by `notion_api_gateway.get_text_prop`.

- [ ] **Step 3: Verify no remaining inline query+filter patterns in summarize_week.py**

Run: `grep -n "notion.query" src/weekforge/workflows/summarize_week.py`
Expected: only in `_step_load_context` for training_sessions (not summaries — those use `summaries_db`)

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest -x -q`
Expected: all pass

- [ ] **Step 5: Final acceptance check**

Run each verification:
```bash
# No inline state-machine loop in run_summarize
grep -c "while state.step" src/weekforge/workflows/summarize_week.py
# Expected: 0

# Uses run_workflow
grep -c "run_workflow" src/weekforge/workflows/summarize_week.py
# Expected: 1

# Uses summaries_db
grep -c "summaries_db" src/weekforge/workflows/summarize_week.py
# Expected: >= 2

# Uses run_accept_gate
grep -c "run_accept_gate" src/weekforge/workflows/summarize_week.py
# Expected: 1

# CLI uses dict registry
grep -c "_WORKFLOW_RUNNERS\|_register_workflows" src/weekforge/cli.py
# Expected: >= 2

# No "extraction" in source
grep -r "extraction" src/weekforge/ --include="*.py" -l
# Expected: empty
```

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/workflows/summarize_week.py
git commit -m "refactor: remove dead _get_text_prop helper, finalize step-2-prep"
```

---

## Notes for Implementer

1. **Mock paths will shift** after Task 5. The existing tests mock `weekforge.workflows.summarize_week.hitl_confirm`. After refactor, `hitl_confirm` is called inside `run_accept_gate` which lives in `weekforge.hitl`. You'll need to mock `weekforge.hitl.hitl_confirm` instead. The spec explicitly allows test import changes.

2. **The runner saves before dispatch** — this means the accept step's checkpoint save inside `hitl_confirm` is now redundant (save happens twice). This is harmless (idempotent upsert) but worth knowing. Don't remove the `hitl_confirm` save — it's still needed for workflows that don't use the runner.

3. **The `"extraction"` alias in `run_summarize` line 35** (`record.workflow in (WORKFLOW, "extraction")`) — the runner only matches `record.workflow == workflow`, so old `"extraction"` checkpoints won't resume. This is acceptable per spec (no in-flight checkpoints exist).

4. **Type annotation for `StepFn`** — use `Callable[[S, RunCost], str | None]` with the TypeVar. Python 3.13 supports this. The `dict[str, StepFn[SummarizeWeekState]]` annotation makes the step registry type-safe.
