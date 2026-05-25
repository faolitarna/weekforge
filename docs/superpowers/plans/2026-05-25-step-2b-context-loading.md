# Step 2b: Context Loading — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the `load_context` step of `draft_week` — gather templates, 3-week feedback window, PLAN_STATE, user profile, and `active_flare` flag into a typed `DraftWeekDeps` for the agent in step 2c. Pure Tier-0 Python, no LLM.

**Architecture:** `_step_load_context` in `draft_week.py` orchestrates 5 sequential Notion/local loads (DEC-P9), computes `active_flare` via a pure predicate, and builds a frozen `DraftWeekDeps` dataclass. State carries only `is_bootstrap`, `plan_state_raw`, and `plan_state_page_id` across checkpoints — `DraftWeekDeps` is rebuilt fresh on every resume (Layer B). `DraftWeekDeps` and `WeekFeedbackRow` live in `agents/draft_week_agent.py` following the `SummarizeDeps` placement pattern.

**Tech Stack:** Python 3.13, Pydantic, dataclasses (frozen), pytest, Notion API via `notion_api_gateway`

**Baseline:** 190 tests passing on branch `step-2b/context-loading`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `src/weekforge/tools/notion_api_gateway.py` | Modify | Add `get_page_title()` — extract title text from a Notion page dict |
| `src/weekforge/agents/draft_week_agent.py` | Create | `WeekFeedbackRow`, `DraftWeekDeps` dataclasses, `derive_active_flare()` pure function |
| `src/weekforge/workflows/draft_week.py` | Modify | Replace `_step_load_context` stub with real implementation |
| `tests/tools/test_get_text_prop.py` | Modify | Add `get_page_title` tests (same file covers gateway property helpers) |
| `tests/agents/test_draft_week_agent.py` | Create | Tests for `DraftWeekDeps`, `WeekFeedbackRow`, `derive_active_flare` |
| `tests/workflows/test_draft_week.py` | Modify | Replace stub test, add `load_context` step tests |

---

### Task 1: `get_page_title` gateway helper

Notion's `get_text_prop` only handles `rich_text` properties. Template pages use a `title` property to hold names like "W15: Push + Hinge". Need a helper to extract title text from any Notion page dict.

**Files:**
- Modify: `src/weekforge/tools/notion_api_gateway.py:243-251` (add function after `get_text_prop`)
- Modify: `tests/tools/test_get_text_prop.py` (add tests)

- [ ] **Step 1: Write failing tests for `get_page_title`**

Add to `tests/tools/test_get_text_prop.py`:

```python
from weekforge.tools.notion_api_gateway import get_page_title


def test_get_page_title_extracts_title():
    page = {"properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push + Hinge"}]}}}
    assert get_page_title(page) == "W15: Push + Hinge"


def test_get_page_title_concatenates_multiple_items():
    page = {"properties": {"Name": {"type": "title", "title": [
        {"plain_text": "W15: "},
        {"plain_text": "Push + Hinge"},
    ]}}}
    assert get_page_title(page) == "W15: Push + Hinge"


def test_get_page_title_no_title_property_returns_empty():
    page = {"properties": {"Week": {"type": "rich_text", "rich_text": []}}}
    assert get_page_title(page) == ""


def test_get_page_title_empty_properties_returns_empty():
    page = {"properties": {}}
    assert get_page_title(page) == ""


def test_get_page_title_no_properties_key_returns_empty():
    page = {}
    assert get_page_title(page) == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tools/test_get_text_prop.py -v -k "get_page_title"`
Expected: FAIL — `ImportError: cannot import name 'get_page_title'`

- [ ] **Step 3: Implement `get_page_title`**

Add to `src/weekforge/tools/notion_api_gateway.py` after the `get_text_prop` function:

```python
def get_page_title(page: dict[str, Any]) -> str:
    for prop in page.get("properties", {}).values():
        if prop.get("type") == "title":
            return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    return ""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tools/test_get_text_prop.py -v`
Expected: all 10 tests PASS (5 existing + 5 new)

- [ ] **Step 5: Run full suite**

Run: `uv run pytest --tb=short -q`
Expected: 190 passed

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/tools/notion_api_gateway.py tests/tools/test_get_text_prop.py
git commit -m "feat: add get_page_title helper to notion gateway"
```

---

### Task 2: `WeekFeedbackRow`, `DraftWeekDeps`, and `derive_active_flare`

These are the typed data structures and pure predicate that `_step_load_context` builds and returns. Creating them first so the workflow step has something to construct.

**Files:**
- Create: `src/weekforge/agents/draft_week_agent.py`
- Create: `tests/agents/test_draft_week_agent.py`

- [ ] **Step 1: Write failing tests**

Create `tests/agents/test_draft_week_agent.py`:

```python
import pytest

from weekforge.agents.draft_week_agent import (
    DraftWeekDeps,
    WeekFeedbackRow,
    derive_active_flare,
)
from weekforge.models.user_profile import UserProfile
from weekforge.tools.plan_state import PlanState


def test_week_feedback_row_construction():
    row = WeekFeedbackRow(week_prefix="W14", plan_md="Push day", summary_text="Good week")
    assert row.week_prefix == "W14"
    assert row.plan_md == "Push day"
    assert row.summary_text == "Good week"


def test_week_feedback_row_none_fields():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    assert row.plan_md is None
    assert row.summary_text is None


def test_week_feedback_row_is_frozen():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    with pytest.raises(AttributeError):
        row.week_prefix = "W15"


def test_draft_week_deps_construction():
    profile = UserProfile(page_id="p1", markdown="# Profile")
    deps = DraftWeekDeps(
        week_prefix="W15",
        template_sessions=[{"id": "t1"}],
        feedback_window=[],
        plan_state=None,
        plan_state_raw=None,
        user_profile=profile,
        active_flare=False,
        bootstrap=True,
    )
    assert deps.week_prefix == "W15"
    assert deps.bootstrap is True
    assert deps.active_flare is False
    assert len(deps.template_sessions) == 1


def test_draft_week_deps_is_frozen():
    profile = UserProfile(page_id="p1", markdown="# Profile")
    deps = DraftWeekDeps(
        week_prefix="W15",
        template_sessions=[],
        feedback_window=[],
        plan_state=None,
        plan_state_raw=None,
        user_profile=profile,
        active_flare=False,
        bootstrap=True,
    )
    with pytest.raises(AttributeError):
        deps.week_prefix = "W16"


# --- derive_active_flare tests ---


def test_active_flare_false_when_no_data():
    assert derive_active_flare([], None) is False


def test_active_flare_false_when_no_pain_markers():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Great week, no issues")
    assert derive_active_flare([row], PlanState()) is False


def test_active_flare_true_from_recent_summary_si_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="SI joint discomfort after squats")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_spine_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="spine stiffness noted")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_pain_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="knee pain during lunges")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_flare_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="flare up this week")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_tendon_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="tendon soreness in elbow")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_true_from_recent_summary_joint_keyword():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="joint stiffness in shoulder")
    assert derive_active_flare([row], PlanState()) is True


def test_active_flare_only_checks_most_recent_feedback_row():
    old_row = WeekFeedbackRow(week_prefix="W12", plan_md=None, summary_text="SI joint pain")
    recent_row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Feeling great")
    # Most recent is last in the list (ordered ascending by week)
    assert derive_active_flare([old_row, recent_row], PlanState()) is False


def test_active_flare_true_from_plan_state_active_issues():
    ps = PlanState(active_issues=["SI joint irritation ongoing"])
    assert derive_active_flare([], ps) is True


def test_active_flare_true_from_plan_state_active_issues_spine():
    ps = PlanState(active_issues=["spine mobility limited"])
    assert derive_active_flare([], ps) is True


def test_active_flare_false_plan_state_active_issues_unrelated():
    ps = PlanState(active_issues=["Need more conditioning volume"])
    assert derive_active_flare([], ps) is False


def test_active_flare_true_when_both_sources_positive():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="SI flare")
    ps = PlanState(active_issues=["SI joint irritation"])
    assert derive_active_flare([row], ps) is True


def test_active_flare_empty_feedback_window_no_plan_state():
    assert derive_active_flare([], None) is False


def test_active_flare_row_with_none_summary():
    row = WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)
    assert derive_active_flare([row], PlanState()) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_draft_week_agent.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'weekforge.agents.draft_week_agent'`

- [ ] **Step 3: Implement the module**

Create `src/weekforge/agents/draft_week_agent.py`:

```python
import re
from dataclasses import dataclass

from weekforge.models.user_profile import UserProfile
from weekforge.tools.plan_state import PlanState

_PAIN_KEYWORDS = re.compile(
    r"\b(SI|spine|flare|pain|tendon|joint)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WeekFeedbackRow:
    week_prefix: str
    plan_md: str | None
    summary_text: str | None


@dataclass(frozen=True)
class DraftWeekDeps:
    week_prefix: str
    template_sessions: list[dict]
    feedback_window: list[WeekFeedbackRow]
    plan_state: PlanState | None
    plan_state_raw: str | None
    user_profile: UserProfile
    active_flare: bool
    bootstrap: bool


def derive_active_flare(
    feedback_window: list[WeekFeedbackRow],
    plan_state: PlanState | None,
) -> bool:
    recent_pain = False
    if feedback_window:
        most_recent = feedback_window[-1]
        if most_recent.summary_text and _PAIN_KEYWORDS.search(most_recent.summary_text):
            recent_pain = True

    chronic_active_issue = False
    if plan_state and plan_state.active_issues:
        for issue in plan_state.active_issues:
            if _PAIN_KEYWORDS.search(issue):
                chronic_active_issue = True
                break

    return recent_pain or chronic_active_issue
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/agents/test_draft_week_agent.py -v`
Expected: all 19 tests PASS

- [ ] **Step 5: Run full suite**

Run: `uv run pytest --tb=short -q`
Expected: 195 passed (190 baseline + 5 from Task 1)

- [ ] **Step 6: Commit**

```bash
git add src/weekforge/agents/draft_week_agent.py tests/agents/test_draft_week_agent.py
git commit -m "feat: add DraftWeekDeps, WeekFeedbackRow, derive_active_flare for step 2b"
```

---

### Task 3: Implement `_step_load_context` and update tests

Replace the stub with the real load_context step. This orchestrates 5 sequential loads and builds `DraftWeekDeps`. The deps object is passed to the agent step via return value (stored temporarily — the runner calls the next step function which receives state, and the agent step rebuilds deps from state fields + fresh Notion queries per Layer B).

Key behavior:
- Templates: query templates DB, filter by title starting with `state.week_prefix`. Error if empty.
- Feedback window: for weeks N-1, N-2, N-3 (descending), call `summaries_db.find_summary_row()`, read Plan + body. Collect into `list[WeekFeedbackRow]` ordered ascending.
- PLAN_STATE: via `summaries_db.find_plan_state_row()`. Set `state.plan_state_raw`, `state.plan_state_page_id`, `state.is_bootstrap`.
- User profile: `load_user_profile()`.
- `active_flare`: `derive_active_flare(feedback_window, plan_state)`.
- Bootstrap: `plan_state is None or len(feedback_window) == 0` → Rich warning.
- Return `"agent"`.

**Files:**
- Modify: `src/weekforge/workflows/draft_week.py:14-15` (replace `_step_load_context` stub)
- Modify: `tests/workflows/test_draft_week.py` (replace stub test, add load_context tests)

- [ ] **Step 1: Write failing tests for `_step_load_context`**

Add new tests to `tests/workflows/test_draft_week.py`. First, remove the `_step_load_context` entry from the `test_stub_steps_raise` test since it's no longer a stub:

Update `test_stub_steps_raise` in `tests/workflows/test_draft_week.py` to remove `_step_load_context`:

```python
def test_stub_steps_raise():
    """Remaining future steps raise RuntimeError."""
    from weekforge.workflows.draft_week import (
        _step_accept,
        _step_agent,
        _step_validate,
        _step_write,
    )

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    for step_fn in [_step_agent, _step_accept, _step_validate, _step_write]:
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            step_fn(state, cost)
```

Then add the following new tests to the same file:

```python
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_happy_path(mock_notion, mock_db, mock_profile, tmp_path):
    """load_context gathers all data and transitions to agent."""
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    # Templates: 2 matching pages
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push + Hinge"}]}}},
        {"id": "t2", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Squat Day"}]}}},
        {"id": "t3", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W14: Old Template"}]}}},
    ]

    # Feedback window: W14 exists with plan+body, W13 missing, W12 exists
    def find_row(prefix):
        if prefix == "W14":
            return {"id": "s14"}
        if prefix == "W12":
            return {"id": "s12"}
        return None

    mock_db.find_summary_row.side_effect = find_row
    mock_db.read_plan_property.side_effect = lambda page: "Plan for " + page["id"]
    mock_db.read_summary_body.return_value = "Summary body text"

    # PLAN_STATE
    mock_db.find_plan_state_row.return_value = ("PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk", "ps-page-id")

    # User profile
    from weekforge.models.user_profile import UserProfile
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# My Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is False
    assert state.plan_state_raw is not None
    assert state.plan_state_page_id == "ps-page-id"


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_no_templates_raises(mock_notion, mock_db, mock_profile, tmp_path):
    """Empty template result for week prefix is a hard error."""
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    # No templates match W15
    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W14: Old Template"}]}}},
    ]

    with pytest.raises(RuntimeError, match="No template.*W15"):
        _step_load_context(state, cost)


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_bootstrap_no_plan_state(mock_notion, mock_db, mock_profile, capsys):
    """Missing PLAN_STATE sets bootstrap=True and prints warning."""
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)

    from weekforge.models.user_profile import UserProfile
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True
    assert state.plan_state_raw is None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_bootstrap_empty_feedback_window(mock_notion, mock_db, mock_profile):
    """Empty feedback window (all 3 weeks missing) sets bootstrap=True."""
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = ("PLAN_STATE raw", "ps-id")

    from weekforge.models.user_profile import UserProfile
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    result = _step_load_context(state, cost)

    assert result == "agent"
    assert state.is_bootstrap is True


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_feedback_window_ordering(mock_notion, mock_db, mock_profile):
    """Feedback rows are ordered ascending (oldest first, most recent last)."""
    from weekforge.workflows.draft_week import _step_load_context

    state = DraftWeekState(week_prefix="W15", step="load_context")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]

    def find_row(prefix):
        if prefix in ("W14", "W13", "W12"):
            return {"id": f"s{prefix}"}
        return None

    mock_db.find_summary_row.side_effect = find_row
    mock_db.read_plan_property.return_value = "plan"
    mock_db.read_summary_body.return_value = "body"
    mock_db.find_plan_state_row.return_value = ("PS", "ps-id")

    from weekforge.models.user_profile import UserProfile
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    _step_load_context(state, cost)

    # find_summary_row called for W14, W13, W12 (descending scan)
    calls = [c.args[0] for c in mock_db.find_summary_row.call_args_list]
    assert calls == ["W14", "W13", "W12"]


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_load_context_end_to_end_through_workflow(mock_notion, mock_db, mock_profile, tmp_path):
    """load_context step runs through the full workflow and hits the agent stub."""
    from weekforge.workflows.draft_week import run_draft

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None  # overwrite_check + feedback window
    mock_db.find_plan_state_row.return_value = (None, None)

    from weekforge.models.user_profile import UserProfile
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    with pytest.raises(RuntimeError, match="Not yet implemented.*agent"):
        run_draft("W15", "draft-week-W15", store)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "load_context or stub_steps"`
Expected: FAIL — tests expect `_step_load_context` to work, but it still raises `RuntimeError("Not yet implemented")`

- [ ] **Step 3: Add `read_summary_body` to `summaries_db`**

The `_step_load_context` needs to read the body content (code block text) from summary rows. `summaries_db` already has `find_summary_row` and `read_plan_property` but no body reader. Add `read_summary_body`:

Add to `src/weekforge/tools/summaries_db.py`:

```python
def read_summary_body(page: dict[str, Any]) -> str | None:
    page_id = page["id"]
    fetched = notion.fetch(page_id)
    content_blocks = fetched.get("content", [])
    text = ""
    for block in content_blocks:
        if block["type"] == "code":
            text += "".join(
                t["text"]["content"] for t in block["code"]["rich_text"]
            ) + "\n"
    return text.strip() or None
```

This follows the same code-block extraction pattern used in `find_plan_state_row`.

- [ ] **Step 4: Implement `_step_load_context`**

Replace the stub in `src/weekforge/workflows/draft_week.py`. The full updated file should have these imports added at the top:

```python
from weekforge.config.user_profile_loader import load_user_profile
from weekforge.tools import notion_api_gateway as notion
from weekforge.tools.notion_api_gateway import get_page_title
from weekforge.tools.plan_state import parse_plan_state
```

And the `_step_load_context` function replaced with:

```python
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
```

Also add the `_verbose` helper at module level (same pattern as `summarize_week.py`):

```python
def _verbose(msg: str) -> None:
    from weekforge.config.env import settings
    if settings.verbose:
        _console.print(f"[dim]{msg}[/dim]")
```

- [ ] **Step 5: Run the new tests**

Run: `uv run pytest tests/workflows/test_draft_week.py -v`
Expected: all tests PASS (existing overwrite_check tests + new load_context tests)

- [ ] **Step 6: Run full suite**

Run: `uv run pytest --tb=short -q`
Expected: ~214 passed (190 + 5 gateway + 19 deps/flare + ~0 net change from stub test update)

- [ ] **Step 7: Commit**

```bash
git add src/weekforge/tools/summaries_db.py src/weekforge/workflows/draft_week.py tests/workflows/test_draft_week.py
git commit -m "feat: implement load_context step for draft_week workflow"
```

---

### Task 4: Update spec status and verify

Mark step 2b as done in the spec files.

**Files:**
- Modify: `specs/steps/step-2b-context-loading.md:3` (status: ready → done)
- Modify: `specs/steps/step-2-planning.md:24` (2b row: ⬜ → ✅)

- [ ] **Step 1: Update spec statuses**

In `specs/steps/step-2b-context-loading.md`, change line 4:
```
ready
```
to:
```
done
```

In `specs/steps/step-2-planning.md`, change the 2b row:
```
| 2b | [Context Loading](./step-2b-context-loading.md) | Tier-0: templates by prefix, 3-week feedback window via `summaries_db`, PLAN_STATE load, user profile, `active_flare` derivation | ⬜ |
```
to:
```
| 2b | [Context Loading](./step-2b-context-loading.md) | Tier-0: templates by prefix, 3-week feedback window via `summaries_db`, PLAN_STATE load, user profile, `active_flare` derivation | ✅ |
```

- [ ] **Step 2: Run full test suite one final time**

Run: `uv run pytest --tb=short -q`
Expected: all tests pass, zero failures

- [ ] **Step 3: Commit**

```bash
git add specs/steps/step-2b-context-loading.md specs/steps/step-2-planning.md
git commit -m "docs: mark step-2b context loading done"
```

---

## Self-Review

**Spec coverage:**
- ✅ `DraftWeekDeps` dataclass with all specified fields (week_prefix, template_sessions, feedback_window, plan_state, plan_state_raw, user_profile, active_flare, bootstrap)
- ✅ `WeekFeedbackRow` dataclass (week_prefix, plan_md, summary_text)
- ✅ Templates filtered by `week_prefix` title prefix from `notion_db_training_templates`
- ✅ Templates empty → fail loud (RuntimeError)
- ✅ 3-week feedback window via `summaries_db.find_summary_row()` for N-1, N-2, N-3
- ✅ PLAN_STATE via `summaries_db.find_plan_state_row()` — shared, no duplication
- ✅ User profile via `load_user_profile()`
- ✅ `active_flare` derived from pain markers + PLAN_STATE active_issues (DEC-P15)
- ✅ Bootstrap detection: `plan_state is None or feedback_window empty` → CLI warning (DEC-P16)
- ✅ State carry: `plan_state_raw`, `plan_state_page_id`, `is_bootstrap` on DraftWeekState
- ✅ Verbose mode one-line summary per load step
- ✅ No LLM calls (zero cost)
- ✅ Sequential, no async (DEC-P9)
- ✅ `read_summary_body` added to `summaries_db` for reading body code-block text

**Placeholder scan:** No TBDs, TODOs, or vague instructions. All code provided.

**Type consistency:** `WeekFeedbackRow` and `DraftWeekDeps` used consistently across Task 2 (definition), Task 3 (consumption). `derive_active_flare` signature matches spec. `get_page_title` used in Task 3 as defined in Task 1. `read_summary_body` defined in Task 3 step 3, used in step 4.
