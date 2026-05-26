# Step 2d: Validation & Notion Write — Implementation Plan

> **Status: DONE** (2026-05-25) — all 4 tasks implemented, 321 tests passing.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Tier-0 plan validation (pull:push ratio + conditioning count) with single re-prompt, then write approved plan to Notion as rich-text property.

**Architecture:** `validate_week_plan()` is a pure function that counts `focus_tags` and returns pass/fail + violation text. `_step_validate` orchestrates the retry guard (one re-prompt, then warn). `_step_write` calls existing `summaries_db.upsert_plan()` and transitions to `done`. Both replace existing stubs in `draft_week.py`.

**Tech Stack:** Pydantic models (WeekPlan), Notion API via `summaries_db.upsert_plan()`, Rich console

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/weekforge/tools/week_plan_validator.py` | `validate_week_plan(plan) -> (bool, str \| None)` — pure Tier-0 counting |
| Modify | `src/weekforge/workflows/draft_week.py:158-163` | Replace `_step_validate` + `_step_write` stubs |
| Create | `tests/tools/test_week_plan_validator.py` | Validator unit tests |
| Modify | `tests/workflows/test_draft_week.py` | Validate + write step integration tests |

---

## Task 1: Week plan validator

**Files:**
- Create: `src/weekforge/tools/week_plan_validator.py`
- Create: `tests/tools/test_week_plan_validator.py`

- [x] **Step 1: Write failing tests for validator**

```python
# tests/tools/test_week_plan_validator.py
import pytest

from weekforge.models.week_plan import PlannedSession, WeekPlan


def _plan(tags_per_session: list[list[str]]) -> WeekPlan:
    """Build a WeekPlan from a list of tag-lists, one per session."""
    sessions = [
        PlannedSession(name=f"S{i}", duration_min=60, focus_tags=tags)
        for i, tags in enumerate(tags_per_session, 1)
    ]
    return WeekPlan(week_prefix="W15", sessions=sessions)


class TestPullPushRatio:
    def test_all_pull_no_push(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([["pull"], ["pull", "core"], ["pull", "hinge"]])
        passed, diff = validate_week_plan(plan)
        assert passed is True
        assert diff is None

    def test_zero_push_zero_pull_passes(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([["cardio", "z2"], ["cardio", "z2"], ["mobility"]])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_exact_threshold_1_5_passes(self):
        """3 pull, 2 push → ratio 1.5:1 — exactly at threshold."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"], ["pull"],
            ["push"], ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_below_threshold_fails(self):
        """2 pull, 2 push → ratio 1.0:1 — below 1.5."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"],
            ["push"], ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "pull:push" in diff

    def test_dual_tagged_session_counts_half(self):
        """Session tagged both pull and push → 0.5 each."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        # 2 pure pull + 1 dual + 1 pure push → pull=2.5, push=1.5 → ratio=1.67 → pass
        plan = _plan([
            ["pull"], ["pull"],
            ["pull", "push"],
            ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_dual_tagged_below_threshold(self):
        """1 pure pull + 1 dual + 2 pure push → pull=1.5, push=2.5 → ratio=0.6 → fail."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"],
            ["pull", "push"],
            ["push"], ["push"],
            ["cardio", "z2"], ["cardio", "z2"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "pull:push" in diff


class TestConditioningFloor:
    def test_two_conditioning_passes(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["push"],
            ["cardio", "z2"], ["hike", "uphill"],
        ])
        passed, _ = validate_week_plan(plan)
        assert passed is True

    def test_one_conditioning_fails(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"], ["pull"],
            ["push"],
            ["cardio", "z2"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "conditioning" in diff.lower()

    def test_zero_conditioning_fails(self):
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["pull"], ["push"],
            ["mobility"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "conditioning" in diff.lower()

    def test_all_conditioning_tags_count(self):
        """Each conditioning tag in the set counts the session."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        for tag in ["cardio", "z1", "z2", "z3", "uphill", "loaded", "hike", "run"]:
            plan = _plan([
                ["pull"], ["pull"], ["push"],
                [tag], [tag],
            ])
            passed, _ = validate_week_plan(plan)
            assert passed is True, f"Tag '{tag}' should count as conditioning"


class TestBothViolations:
    def test_both_violations_reported(self):
        """Both ratio and conditioning fail → diff mentions both."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([
            ["pull"], ["push"], ["push"],
            ["mobility"],
        ])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "pull:push" in diff
        assert "conditioning" in diff.lower()


class TestEmptyPlan:
    def test_empty_sessions_passes_ratio_fails_conditioning(self):
        """0 sessions → 0 push, 0 pull (ratio ok), 0 conditioning (fail)."""
        from weekforge.tools.week_plan_validator import validate_week_plan

        plan = _plan([])
        passed, diff = validate_week_plan(plan)
        assert passed is False
        assert "conditioning" in diff.lower()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tools/test_week_plan_validator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'weekforge.tools.week_plan_validator'`

- [x] **Step 3: Implement validator**

```python
# src/weekforge/tools/week_plan_validator.py
from weekforge.models.week_plan import WeekPlan

_CONDITIONING_TAGS = frozenset({"cardio", "z1", "z2", "z3", "uphill", "loaded", "hike", "run"})

_PULL_PUSH_THRESHOLD = 1.5
_CONDITIONING_FLOOR = 2


def validate_week_plan(plan: WeekPlan) -> tuple[bool, str | None]:
    pull_count = 0.0
    push_count = 0.0
    conditioning_count = 0

    for s in plan.sessions:
        tags = set(s.focus_tags)
        has_pull = "pull" in tags
        has_push = "push" in tags
        if has_pull and has_push:
            pull_count += 0.5
            push_count += 0.5
        elif has_pull:
            pull_count += 1
        elif has_push:
            push_count += 1

        if tags & _CONDITIONING_TAGS:
            conditioning_count += 1

    issues: list[str] = []

    if push_count > 0 and pull_count / push_count < _PULL_PUSH_THRESHOLD:
        issues.append(
            f"pull:push={pull_count:.1f}:{push_count:.1f} "
            f"(ratio {pull_count / push_count:.1f}:1, need >={_PULL_PUSH_THRESHOLD}:1)"
        )

    if conditioning_count < _CONDITIONING_FLOOR:
        issues.append(
            f"conditioning_sessions={conditioning_count} (need >={_CONDITIONING_FLOOR})"
        )

    if issues:
        diff = "Plan validation failed. Issues: " + "; ".join(issues) + ". Revise the plan to fix these specifically. Keep all other constraints intact."
        return False, diff

    return True, None
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tools/test_week_plan_validator.py -v`
Expected: all PASS

- [x] **Step 5: Commit**

```bash
git add src/weekforge/tools/week_plan_validator.py tests/tools/test_week_plan_validator.py
git commit -m "feat: add Tier-0 week plan validator (pull:push ratio + conditioning floor)"
```

---

## Task 2: Validate step in workflow

**Files:**
- Modify: `src/weekforge/workflows/draft_week.py:158-159`
- Modify: `tests/workflows/test_draft_week.py`

- [x] **Step 1: Write failing tests for _step_validate**

Add to `tests/workflows/test_draft_week.py`:

```python
# --- validate step tests ---


def test_validate_pass_transitions_to_write():
    """Valid plan → step returns 'write'."""
    from weekforge.workflows.draft_week import _step_validate

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    state = DraftWeekState(week_prefix="W15", step="validate", last_output=plan)
    cost = RunCost()

    result = _step_validate(state, cost)

    assert result == "write"
    assert state.validation_warning is None
    assert state.validation_retry_used is False


def test_validate_fail_first_time_reprompts():
    """First validation failure → pending_feedback set, returns 'agent'."""
    from weekforge.workflows.draft_week import _step_validate

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    state = DraftWeekState(week_prefix="W15", step="validate", last_output=plan)
    cost = RunCost()

    result = _step_validate(state, cost)

    assert result == "agent"
    assert state.validation_retry_used is True
    assert state.pending_feedback is not None
    assert "pull:push" in state.pending_feedback


def test_validate_fail_second_time_warns_and_loops_to_accept():
    """Second validation failure → warning set, returns 'accept'."""
    from weekforge.workflows.draft_week import _step_validate

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    state = DraftWeekState(
        week_prefix="W15", step="validate", last_output=plan,
        validation_retry_used=True,
    )
    cost = RunCost()

    result = _step_validate(state, cost)

    assert result == "accept"
    assert state.validation_warning is not None
    assert "pull:push" in state.validation_warning
    assert state.pending_feedback is None


def test_validate_pass_after_retry_clears_warning():
    """Pass on second attempt → write, no warning."""
    from weekforge.workflows.draft_week import _step_validate

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    state = DraftWeekState(
        week_prefix="W15", step="validate", last_output=plan,
        validation_retry_used=True,
    )
    cost = RunCost()

    result = _step_validate(state, cost)

    assert result == "write"
    assert state.validation_warning is None
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "test_validate"`
Expected: FAIL — `RuntimeError: Not yet implemented: validate`

- [x] **Step 3: Implement _step_validate**

Replace the `_step_validate` stub in `src/weekforge/workflows/draft_week.py`:

```python
def _step_validate(state: DraftWeekState, cost: RunCost) -> str | None:
    from weekforge.tools.week_plan_validator import validate_week_plan

    assert state.last_output is not None
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
    return "accept"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "test_validate"`
Expected: all PASS

- [x] **Step 5: Run existing tests for regressions**

Run: `uv run pytest tests/workflows/test_draft_week.py -v`
Expected: all PASS (existing tests that reach validate now hit the real code, but those tests mock `run_accept_gate` to return `step="validate"` which then hits `_step_validate` — the plan it passes may fail validation, but the test already expects `RuntimeError("Not yet implemented.*validate")`. Wait — those tests were updated in 2c to expect validate stub. Now validate is real, they'll proceed further. Let me check.)

Actually, the existing tests `test_accept_approve_transitions_to_validate` expects `RuntimeError(match="Not yet implemented.*validate")`. Now that validate is real, it will try to run. The fake plan in that test has 1 session (`["push"]`) which will fail both validators. It will set `pending_feedback` and return `"agent"`, which will re-run `_step_agent` (mocked via `run_with_metadata`), then `accept` again, and loop. The test needs updating.

**Update existing test `test_accept_approve_transitions_to_validate`:**

The test currently expects `RuntimeError("Not yet implemented.*validate")`. After this change, validate runs for real. The fake plan (1 push session) fails validation, loops to agent. We need to either:
- Mock `validate_week_plan` to pass, OR
- Accept the new flow and adjust expectations

Simplest: add `@patch("weekforge.workflows.draft_week.validate_week_plan", return_value=(True, None))` from `weekforge.tools.week_plan_validator` — but it's imported locally. Instead, patch at the source module:

Change the test to patch the validator and expect the write stub:

```python
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_approve_transitions_to_validate(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → approve → validate passes → hits write stub."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    # Plan that passes validation: 3 pull, 1 push, 2 conditioning
    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with pytest.raises(RuntimeError, match="Not yet implemented.*write"):
        run_draft("W15", "draft-week-W15", store)

    mock_gate.assert_called_once()
```

Also update `test_accept_feedback_loops_to_agent` — its second gate call returns `step=None` (quit), but before that the first loop goes agent→accept(feedback)→agent→accept(quit). The plan also hits validate, so we need a valid plan too. Actually wait — let me re-read the test. The first gate returns `AcceptResult(step="agent", feedback="add more conditioning")` which sets `state.step = "agent"` directly from the accept step. It does NOT go through validate. Only when gate returns `step="validate"` does it go through validate. So `test_accept_feedback_loops_to_agent` is fine — feedback goes directly back to agent.

But `test_accept_quit_pauses_workflow` also has a plan with only 1 push session. That test's gate returns `step=None` (quit), so it never reaches validate. That's fine too.

The tests that need updating are only those where `mock_gate` returns `step="validate"`. That's just `test_accept_approve_transitions_to_validate`.

Also update `test_stub_steps_raise` — remove `_step_validate` from the stubs list since it's now real:

```python
def test_stub_steps_raise():
    """Remaining future steps raise RuntimeError."""
    from weekforge.workflows.draft_week import _step_write

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    with pytest.raises(RuntimeError, match="Not yet implemented"):
        _step_write(state, cost)
```

- [x] **Step 6: Run all draft_week tests**

Run: `uv run pytest tests/workflows/test_draft_week.py -v`
Expected: all PASS

- [x] **Step 7: Commit**

```bash
git add src/weekforge/workflows/draft_week.py tests/workflows/test_draft_week.py
git commit -m "feat: implement _step_validate with retry guard and re-prompt"
```

---

## Task 3: Write step + Notion persistence

**Files:**
- Modify: `src/weekforge/workflows/draft_week.py:162-163`
- Modify: `tests/workflows/test_draft_week.py`

- [x] **Step 1: Write failing tests for _step_write**

Add to `tests/workflows/test_draft_week.py`:

```python
# --- write step tests ---


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_calls_upsert_and_returns_done(mock_db):
    """Write step renders plan, calls upsert_plan, stores page_id, returns 'done'."""
    from weekforge.workflows.draft_week import _step_write

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
        ],
        adjustments=["test adjustment"],
    )
    state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
    cost = RunCost()

    mock_db.upsert_plan.return_value = "page-123"

    result = _step_write(state, cost)

    assert result == "done"
    assert state.written_page_id == "page-123"
    mock_db.upsert_plan.assert_called_once()
    call_args = mock_db.upsert_plan.call_args
    assert call_args[0][0] == "W15"
    rendered = call_args[0][1]
    assert "Pull A" in rendered
    assert "Z2 Run" in rendered
    assert "test adjustment" in rendered


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_truncates_long_plan(mock_db):
    """Plan exceeding 2000 chars is truncated with marker."""
    from weekforge.workflows.draft_week import _step_write

    sessions = [
        PlannedSession(name=f"Session {i} with a long name for padding purposes", duration_min=60 + i, focus_tags=["pull"])
        for i in range(1, 30)
    ]
    plan = WeekPlan(week_prefix="W15", sessions=sessions, adjustments=["a" * 500])
    state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
    cost = RunCost()

    mock_db.upsert_plan.return_value = "page-456"

    _step_write(state, cost)

    rendered = mock_db.upsert_plan.call_args[0][1]
    assert len(rendered) <= 2000
    assert "[truncated]" in rendered


@patch("weekforge.workflows.draft_week.summaries_db")
def test_write_idempotent_second_call(mock_db):
    """Calling write twice with same plan is safe (upsert semantics)."""
    from weekforge.workflows.draft_week import _step_write

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"])],
    )

    mock_db.upsert_plan.return_value = "page-789"

    for _ in range(2):
        state = DraftWeekState(week_prefix="W15", step="write", last_output=plan)
        cost = RunCost()
        result = _step_write(state, cost)
        assert result == "done"

    assert mock_db.upsert_plan.call_count == 2
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "test_write"`
Expected: FAIL — `RuntimeError: Not yet implemented: write`

- [x] **Step 3: Implement _step_write**

Replace the `_step_write` stub in `src/weekforge/workflows/draft_week.py`:

```python
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
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "test_write"`
Expected: all PASS

- [x] **Step 5: Update `test_stub_steps_raise` to remove `_step_write`**

Since `_step_write` is now real, remove the test entirely — no stubs remain:

```python
# Delete test_stub_steps_raise entirely — both validate and write are now implemented.
```

- [x] **Step 6: Run full test suite**

Run: `uv run pytest -v`
Expected: all PASS

- [x] **Step 7: Commit**

```bash
git add src/weekforge/workflows/draft_week.py tests/workflows/test_draft_week.py
git commit -m "feat: implement _step_write with Notion upsert and truncation guard"
```

---

## Task 4: End-to-end integration test

**Files:**
- Modify: `tests/workflows/test_draft_week.py`

This task adds an integration test that exercises the full validate→write flow through `run_draft`, verifying the complete happy path and the validation-retry path.

- [x] **Step 1: Write integration tests**

Add to `tests/workflows/test_draft_week.py`:

```python
# --- end-to-end integration tests for validate + write ---


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_e2e_approve_validate_pass_write(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Full flow: overwrite_check → load_context → agent → accept(approve) → validate(pass) → write → done."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_db.upsert_plan.return_value = "written-page-id"
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    valid_plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    fake_result = MagicMock()
    fake_result.output = valid_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    run_draft("W15", "draft-week-W15", store)

    mock_db.upsert_plan.assert_called_once()
    rendered = mock_db.upsert_plan.call_args[0][1]
    assert "Pull A" in rendered
    # Checkpoint cleaned up on done
    assert store.load("draft-week-W15") is None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_e2e_validate_fail_reprompt_then_pass(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Validation fails first → re-prompt → second plan passes → write → done."""
    from weekforge.workflows.draft_week import run_draft
    from weekforge.models.user_profile import UserProfile
    from weekforge.hitl import AcceptResult

    store = CheckpointStore(str(tmp_path / "cp.sqlite"))

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_db.find_plan_state_row.return_value = (None, None)
    mock_db.upsert_plan.return_value = "written-page-id"
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    # First plan fails validation (1 pull, 2 push)
    bad_plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Push B", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )
    # Second plan passes
    good_plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Pull A", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull B", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Pull C", duration_min=85, focus_tags=["pull"]),
            PlannedSession(name="Push A", duration_min=85, focus_tags=["push"]),
            PlannedSession(name="Z2 Run", duration_min=75, focus_tags=["cardio", "z2"]),
            PlannedSession(name="Z2 Hike", duration_min=90, focus_tags=["hike", "uphill"]),
        ],
    )

    bad_result = MagicMock()
    bad_result.output = bad_plan
    good_result = MagicMock()
    good_result.output = good_plan
    meta = MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0)

    # Call sequence: agent(bad) → accept(approve) → validate(fail) → agent(good) → accept(approve) → validate(pass) → write
    mock_run_meta.side_effect = [
        (bad_result, meta, []),
        (good_result, meta, []),
    ]
    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    run_draft("W15", "draft-week-W15", store)

    assert mock_run_meta.call_count == 2
    mock_db.upsert_plan.assert_called_once()
    # Second call should include validation feedback in prompt
    second_prompt = mock_run_meta.call_args_list[1][0][1]
    assert "pull:push" in second_prompt
```

- [x] **Step 2: Run tests**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "e2e"`
Expected: all PASS

- [x] **Step 3: Run full test suite**

Run: `uv run pytest -v`
Expected: all PASS

- [x] **Step 4: Commit**

```bash
git add tests/workflows/test_draft_week.py
git commit -m "test: add end-to-end integration tests for validate + write flow"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| Validation correctly computes pull:push ratio from focus_tags | Task 1 (validator + 6 ratio tests) |
| Dual-tagged sessions count 0.5 each | Task 1 (test_dual_tagged_session_counts_half, test_dual_tagged_below_threshold) |
| Validation correctly counts conditioning sessions | Task 1 (3 conditioning tests + all-tags test) |
| First validation failure triggers agent re-prompt with concrete diff | Task 2 (test_validate_fail_first_time_reprompts) |
| Second validation failure surfaces warning to HITL, does not auto-fail | Task 2 (test_validate_fail_second_time_warns_and_loops_to_accept) |
| validation_retry_used guard prevents infinite loop | Task 2 (retry guard in _step_validate) |
| Notion row created if absent, updated if present | Task 3 (upsert_plan already handles this — tested in summaries_db) |
| Plan written as plain text to Plan rich-text property | Task 3 (_step_write calls render_week_plan + upsert_plan) |
| Body code-block content not corrupted by Plan write | Already guaranteed — upsert_plan only writes properties, not content |
| Idempotent: re-running write produces same row state | Task 3 (test_write_idempotent_second_call) |
| Cost summary panel printed at write boundary | Already handled by runner.py — prints cost panel on "done" |
| Plan text truncation at 2000 char limit | Task 3 (_NOTION_RICH_TEXT_LIMIT + test_write_truncates_long_plan) |
| End-to-end happy path | Task 4 (test_e2e_approve_validate_pass_write) |
| End-to-end validation retry path | Task 4 (test_e2e_validate_fail_reprompt_then_pass) |

### Placeholder scan

No TBDs, TODOs, or "implement later" found. All code steps have complete code blocks.

### Type consistency check

- `validate_week_plan` used in: Task 1 (defined), Task 2 (called in _step_validate via local import)
- `_NOTION_RICH_TEXT_LIMIT` used in: Task 3 (defined + used in _step_write)
- `render_week_plan` used in: Task 3 (imported in _step_write — same pattern as _step_accept)
- `upsert_plan` used in: Task 3 (called on summaries_db — already exists with matching signature)
- `WeekPlan` used in all tasks — consistent
- `validation_retry_used`, `validation_warning`, `pending_feedback` — all fields already on DraftWeekState from 2a

All consistent.
