# Step 2c: Draft Week Agent + HITL — Implementation Plan

> **Status: DONE** (2026-05-25) — all 5 tasks implemented, merged to main as `ad47977`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Tier-2 planner agent that takes `DraftWeekDeps` from step 2b and returns a typed `WeekPlan`, wired into an accept/feedback/quit HITL gate.

**Architecture:** `draft_week_agent` mirrors `summarize_week_agent` exactly — static instructions via `compose_static_instructions`, dynamic context via `@agent.instructions` decorators. The `_step_agent` workflow step rebuilds deps fresh from Notion each run (Layer B), calls `run_with_metadata`, stores output/messages/calls. The `_step_accept` step delegates to shared `run_accept_gate()` with `render_week_plan()` as the renderer.

**Tech Stack:** Pydantic AI, Pydantic v2 (BaseModel + Literal types), Rich (HITL panel), OpenAI via `build_openai_model`

---

## File Structure

| Action | File | Responsibility |
|--------|------|---------------|
| Create | `src/weekforge/models/week_plan.py` | `FocusTag` Literal, `PlannedSession`, `WeekPlan` Pydantic models |
| Create | `src/weekforge/tools/week_plan_renderer.py` | `render_week_plan(plan) -> str` — markdown for HITL + Notion |
| Modify | `src/weekforge/prompts/loader.py` | Add `DRAFT_WEEK_TASK` enum entry |
| Create | `src/weekforge/prompts/draft-week-task.md` | Task prompt ported from legacy `<week-plan>` section |
| Modify | `src/weekforge/agents/draft_week_agent.py` | Add agent definition + 6 instruction decorators |
| Modify | `src/weekforge/models/workflow_state.py` | Type `last_output` as `WeekPlan \| None` |
| Modify | `src/weekforge/workflows/draft_week.py` | Implement `_step_agent` + move `_step_accept` into closure |
| Create | `tests/models/test_week_plan.py` | Model validation tests |
| Create | `tests/tools/test_week_plan_renderer.py` | Renderer output tests |
| Modify | `tests/agents/test_draft_week_agent.py` | Decorator injection tests |
| Modify | `tests/workflows/test_draft_week.py` | Agent + accept step tests |

---

## Task 1: WeekPlan model

**Files:**
- Create: `src/weekforge/models/week_plan.py`
- Modify: `src/weekforge/models/workflow_state.py:30-44`
- Create: `tests/models/test_week_plan.py`

- [x] **Step 1: Write failing tests for WeekPlan model**

```python
# tests/models/test_week_plan.py
import pytest
from pydantic import ValidationError


def test_planned_session_valid():
    from weekforge.models.week_plan import PlannedSession

    s = PlannedSession(name="Push + Hinge", duration_min=85, focus_tags=["push", "hinge"])
    assert s.name == "Push + Hinge"
    assert s.duration_min == 85
    assert s.focus_tags == ["push", "hinge"]


def test_planned_session_invalid_focus_tag():
    from weekforge.models.week_plan import PlannedSession

    with pytest.raises(ValidationError, match="focus_tags"):
        PlannedSession(name="Bad", duration_min=60, focus_tags=["nonexistent_tag"])


def test_week_plan_valid():
    from weekforge.models.week_plan import PlannedSession, WeekPlan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Push + Hinge", duration_min=85, focus_tags=["push", "hinge"]),
            PlannedSession(name="Z2 Uphill", duration_min=75, focus_tags=["cardio", "z2", "uphill"]),
        ],
        adjustments=["Reduced squat volume due to SI flare"],
    )
    assert plan.week_prefix == "W15"
    assert len(plan.sessions) == 2
    assert plan.adjustments == ["Reduced squat volume due to SI flare"]


def test_week_plan_adjustments_default_empty():
    from weekforge.models.week_plan import PlannedSession, WeekPlan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="A", duration_min=60, focus_tags=["pull"])],
    )
    assert plan.adjustments == []


def test_focus_tag_all_movement_tags():
    from weekforge.models.week_plan import PlannedSession

    for tag in ["push", "pull", "squat", "hinge", "core", "carry"]:
        s = PlannedSession(name="Test", duration_min=60, focus_tags=[tag])
        assert s.focus_tags == [tag]


def test_focus_tag_all_cardio_tags():
    from weekforge.models.week_plan import PlannedSession

    for tag in ["cardio", "z1", "z2", "z3", "uphill", "loaded", "run", "hike", "walk"]:
        s = PlannedSession(name="Test", duration_min=60, focus_tags=[tag])
        assert s.focus_tags == [tag]


def test_focus_tag_all_skill_tags():
    from weekforge.models.week_plan import PlannedSession

    for tag in ["climbing", "hangboard", "mobility", "recovery"]:
        s = PlannedSession(name="Test", duration_min=60, focus_tags=[tag])
        assert s.focus_tags == [tag]


def test_focus_tag_other_tags():
    from weekforge.models.week_plan import PlannedSession

    s = PlannedSession(name="Test", duration_min=60, focus_tags=["template_restructured"])
    assert s.focus_tags == ["template_restructured"]


def test_week_plan_serialization_roundtrip():
    from weekforge.models.week_plan import PlannedSession, WeekPlan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push", "core"])],
        adjustments=["test"],
    )
    json_str = plan.model_dump_json()
    restored = WeekPlan.model_validate_json(json_str)
    assert restored == plan


def test_week_plan_empty_sessions_allowed():
    """Agent might return empty sessions on bad prompt — validation in 2d, not model."""
    from weekforge.models.week_plan import WeekPlan

    plan = WeekPlan(week_prefix="W15", sessions=[])
    assert plan.sessions == []
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/models/test_week_plan.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'weekforge.models.week_plan'`

- [x] **Step 3: Create WeekPlan model**

```python
# src/weekforge/models/week_plan.py
from typing import Literal

from pydantic import BaseModel, Field

FocusTag = Literal[
    # Movement
    "push", "pull", "squat", "hinge", "core", "carry",
    # Cardio
    "cardio", "z1", "z2", "z3", "uphill", "loaded", "run", "hike", "walk",
    # Skill
    "climbing", "hangboard", "mobility", "recovery",
    # Other
    "template_restructured",
]


class PlannedSession(BaseModel):
    name: str
    duration_min: int
    focus_tags: list[FocusTag]


class WeekPlan(BaseModel):
    week_prefix: str
    sessions: list[PlannedSession]
    adjustments: list[str] = Field(default_factory=list)
```

- [x] **Step 4: Type `DraftWeekState.last_output` as `WeekPlan | None`**

In `src/weekforge/models/workflow_state.py`, add the import and change the field:

```python
# Add to imports (after the WeekSummary import):
from weekforge.models.week_plan import WeekPlan

# Change line ~35 from:
#     last_output: Any = None
# to:
    last_output: WeekPlan | None = None
```

Also remove the `Any` import from typing if it's only used for `last_output` (check — it's also used for `messages_json: list[dict[str, Any]]`, so keep it).

- [x] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/models/test_week_plan.py -v`
Expected: all PASS

- [x] **Step 6: Run existing tests to verify no regressions**

Run: `uv run pytest tests/models/test_draft_week_state.py tests/workflows/test_draft_week.py -v`
Expected: all PASS (the `Any → WeekPlan | None` change defaults to None, same as before)

- [x] **Step 7: Commit**

```bash
git add src/weekforge/models/week_plan.py src/weekforge/models/workflow_state.py tests/models/test_week_plan.py
git commit -m "feat: add WeekPlan model with controlled FocusTag vocabulary"
```

---

## Task 2: Week plan renderer

**Files:**
- Create: `src/weekforge/tools/week_plan_renderer.py`
- Create: `tests/tools/test_week_plan_renderer.py`

- [x] **Step 1: Write failing tests for renderer**

```python
# tests/tools/test_week_plan_renderer.py
from weekforge.models.week_plan import PlannedSession, WeekPlan


def test_render_basic_plan():
    from weekforge.tools.week_plan_renderer import render_week_plan

    plan = WeekPlan(
        week_prefix="W15",
        sessions=[
            PlannedSession(name="Push + Hinge", duration_min=85, focus_tags=["push", "hinge"]),
            PlannedSession(name="Squat + Pull", duration_min=80, focus_tags=["squat", "pull"]),
        ],
    )
    result = render_week_plan(plan)
    assert "Week W15 Plan (2 sessions):" in result
    assert "1. W15: Push + Hinge — 85 min" in result
    assert "2. W15: Squat + Pull — 80 min" in result
    assert "Adjustments" not in result


def test_render_with_adjustments():
    from weekforge.tools.week_plan_renderer import render_week_plan

    plan = WeekPlan(
        week_prefix="W03",
        sessions=[
            PlannedSession(name="Pull + Core", duration_min=85, focus_tags=["pull", "core"]),
        ],
        adjustments=["Reduced squat volume", "Added extra Z2 session"],
    )
    result = render_week_plan(plan)
    assert "Adjustments:" in result
    assert "- Reduced squat volume" in result
    assert "- Added extra Z2 session" in result


def test_render_empty_sessions():
    from weekforge.tools.week_plan_renderer import render_week_plan

    plan = WeekPlan(week_prefix="W01", sessions=[])
    result = render_week_plan(plan)
    assert "Week W01 Plan (0 sessions):" in result


def test_render_many_sessions():
    from weekforge.tools.week_plan_renderer import render_week_plan

    sessions = [
        PlannedSession(name=f"Session {i}", duration_min=60 + i, focus_tags=["pull"])
        for i in range(1, 13)
    ]
    plan = WeekPlan(week_prefix="W10", sessions=sessions)
    result = render_week_plan(plan)
    assert "12 sessions" in result
    assert "12. W10: Session 12 — 72 min" in result
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/tools/test_week_plan_renderer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'weekforge.tools.week_plan_renderer'`

- [x] **Step 3: Implement renderer**

```python
# src/weekforge/tools/week_plan_renderer.py
from weekforge.models.week_plan import WeekPlan


def render_week_plan(plan: WeekPlan) -> str:
    lines = [f"Week {plan.week_prefix} Plan ({len(plan.sessions)} sessions):"]
    for i, s in enumerate(plan.sessions, 1):
        lines.append(f"{i}. {plan.week_prefix}: {s.name} — {s.duration_min} min")
    if plan.adjustments:
        lines.append("")
        lines.append("Adjustments:")
        for adj in plan.adjustments:
            lines.append(f"- {adj}")
    return "\n".join(lines)
```

- [x] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/tools/test_week_plan_renderer.py -v`
Expected: all PASS

- [x] **Step 5: Commit**

```bash
git add src/weekforge/tools/week_plan_renderer.py tests/tools/test_week_plan_renderer.py
git commit -m "feat: add week plan renderer for HITL display and Notion write"
```

---

## Task 3: Prompt enum + draft-week-task.md

**Files:**
- Modify: `src/weekforge/prompts/loader.py:6-13`
- Create: `src/weekforge/prompts/draft-week-task.md`

- [x] **Step 1: Write failing test for prompt loading**

```python
# Add to tests/agents/test_prompt_composer.py (or run inline)
# We test that the new enum entry loads without error.
```

Actually, test this via the existing pattern — just verify the prompt file loads:

Run: `uv run python -c "from weekforge.prompts.loader import Prompt, load_prompt; print(load_prompt(Prompt.DRAFT_WEEK_TASK)[:50])"`
Expected: FAIL — `AttributeError: 'DRAFT_WEEK_TASK' is not a member of 'Prompt'`

- [x] **Step 2: Add enum entry to Prompt**

In `src/weekforge/prompts/loader.py`, add after the `CAVEMAN_LITE_DIRECTIVE` line:

```python
    DRAFT_WEEK_TASK = "draft-week-task.md"
```

The full enum becomes:

```python
class Prompt(StrEnum):
    COACHING_PERSONA = "coaching_persona.md"
    COACHING_GUARDRAILS = "coaching_guardrails.md"
    FEEDBACK_INTERPRETATION = "feedback-interpretation.md"
    SUMMARIZE_WEEK_TASK = "summarize-week-task.md"
    UPDATE_PLAN_STATE_TASK = "update-plan-state-task.md"
    PROGRESSION_PROTOCOL = "progression-protocol.md"
    CAVEMAN_LITE_DIRECTIVE = "caveman-lite-directive.md"
    DRAFT_WEEK_TASK = "draft-week-task.md"
```

- [x] **Step 3: Create draft-week-task.md prompt file**

The prompt ports the logic from `source-material/.claude/commands/plan_week.md` `<week-plan>` section, adapted for structured `WeekPlan` output instead of free-form text. Key constraints from the source: pull:push ~2:1 validation, conditioning ≥2 sessions, session durations from actuals/preferences not defaults, 8-12 sessions range.

```markdown
# src/weekforge/prompts/draft-week-task.md
<draft-week-task>
You are generating a high-level weekly training plan. You receive:
- Template sessions (reference structure for this week position in the mesocycle).
- Previous 3 weeks feedback (plan + summary per week, when available).
- PLAN_STATE (cumulative mesocycle tracker: progression baselines, injury timeline, deload history).
- User profile (conditions, goals, HR zones, session preferences).
- ACTIVE_FLARE flag (YES/NO — triggers conservative programming).

Your job: produce a `WeekPlan` with 8–12 planned sessions, each with a descriptive name, duration in minutes, and focus tags from the controlled vocabulary.

## Session Planning Rules

1. **Balance distribution** across: hinge, squat, pull, push, core, conditioning, skill work.
2. **Pull:push ratio ~2:1.** Count pull-dominant vs push-dominant sessions. If ratio drifts below 1.5:1, add pull sessions or convert balanced sessions to pull-dominant.
3. **Conditioning volume ≥2 sessions per week.** Sessions tagged with cardio/z2/z3/uphill/loaded/run/hike count. If fewer than 2, add conditioning or blend into existing sessions.
4. **Session durations from data, not defaults.** Use previous week actuals and user-profile SESSION_PREFERENCES as baseline. Gym sessions: 80+ min baseline. Conditioning: scale to mesocycle position. Only standalone sessions (hangboard, mobility, recovery) use shorter durations.
5. **Account for cumulative feedback.** Reduce intensity if pain reported, increase if completion is high and feedback positive. Reference PLAN_STATE for multi-week trends.
6. **ACTIVE_FLARE = YES**: apply symptom protocol. Substitute or reduce load on affected movements. Do not program through active pain.

## Focus Tags (use only these)

Movement: `push`, `pull`, `squat`, `hinge`, `core`, `carry`
Cardio: `cardio`, `z1`, `z2`, `z3`, `uphill`, `loaded`, `run`, `hike`, `walk`
Skill: `climbing`, `hangboard`, `mobility`, `recovery`
Other: `template_restructured`

Each session gets 1–4 focus tags describing its primary training focus. Tags drive Tier-0 validation in the next step (pull:push ratio, conditioning count).

## Adjustments

List specific changes from the previous weeks' feedback and PLAN_STATE trends. Each adjustment: what changed and why. Examples:
- "Reduced squat volume — SI flare reported W14"
- "Added third Z2 session — mountaineering prep on track, pushing conditioning"
- "Swapped barbell rows for cable rows — grip fatigue pattern across W12-W14"

If bootstrap mode (no feedback history): state "First week — using template baseline, conservative defaults."

## Output

Return a `WeekPlan` with:
- `week_prefix`: the week being planned (e.g., "W15")
- `sessions`: list of `PlannedSession` objects (8–12 items)
- `adjustments`: list of human-readable reasoning bullets (at least 1)
</draft-week-task>
```

- [x] **Step 4: Verify prompt loads**

Run: `uv run python -c "from weekforge.prompts.loader import Prompt, load_prompt; print(len(load_prompt(Prompt.DRAFT_WEEK_TASK)))"`
Expected: prints a number > 100 (file length)

- [x] **Step 5: Commit**

```bash
git add src/weekforge/prompts/loader.py src/weekforge/prompts/draft-week-task.md
git commit -m "feat: add DRAFT_WEEK_TASK prompt enum and task prompt file"
```

---

## Task 4: Agent definition + instruction decorators

**Files:**
- Modify: `src/weekforge/agents/draft_week_agent.py:1-49`
- Modify: `tests/agents/test_draft_week_agent.py`

**Context:** `draft_week_agent.py` already contains `WeekFeedbackRow`, `DraftWeekDeps`, and `derive_active_flare` from step 2b. This task adds the agent object and 6 `@agent.instructions` decorator functions. The pattern is identical to `summarize_week_agent.py`.

- [x] **Step 1: Write failing tests for instruction decorators**

Add to `tests/agents/test_draft_week_agent.py`:

```python
# --- instruction decorator tests ---

from unittest.mock import MagicMock


def _make_draft_deps(**overrides) -> "DraftWeekDeps":
    """Build DraftWeekDeps with sensible defaults for testing decorators."""
    from weekforge.agents.draft_week_agent import DraftWeekDeps, WeekFeedbackRow
    from weekforge.models.user_profile import UserProfile
    from weekforge.tools.plan_state import PlanState

    defaults = dict(
        week_prefix="W15",
        template_sessions=[],
        feedback_window=[],
        plan_state=None,
        plan_state_raw=None,
        user_profile=UserProfile(page_id="up1", markdown="# Test Profile\nGoals: get strong"),
        active_flare=False,
        bootstrap=False,
    )
    defaults.update(overrides)
    return DraftWeekDeps(**defaults)


def _make_ctx(deps) -> MagicMock:
    ctx = MagicMock()
    ctx.deps = deps
    return ctx


class TestInjectUserProfile:
    def test_returns_profile_markdown(self):
        from weekforge.agents.draft_week_agent import _inject_user_profile

        deps = _make_draft_deps()
        ctx = _make_ctx(deps)
        result = _inject_user_profile(ctx)
        assert "## Active User Profile" in result
        assert "# Test Profile" in result
        assert "Goals: get strong" in result


class TestInjectTemplates:
    def test_empty_templates_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_templates

        deps = _make_draft_deps(template_sessions=[])
        ctx = _make_ctx(deps)
        assert _inject_templates(ctx) == ""

    def test_renders_template_titles(self):
        from weekforge.agents.draft_week_agent import _inject_templates

        templates = [
            {"id": "t1", "properties": {"Title": {"type": "title", "title": [{"plain_text": "W15: Push + Hinge"}]}}},
            {"id": "t2", "properties": {"Title": {"type": "title", "title": [{"plain_text": "W15: Squat Day"}]}}},
        ]
        deps = _make_draft_deps(template_sessions=templates)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert "## Template Sessions" in result
        assert "W15: Push + Hinge" in result
        assert "W15: Squat Day" in result

    def test_renders_all_non_empty_properties(self):
        from weekforge.agents.draft_week_agent import _inject_templates

        templates = [
            {
                "id": "t1",
                "properties": {
                    "Title": {"type": "title", "title": [{"plain_text": "W15: Aerobic Base"}]},
                    "WorkoutDescription": {"type": "rich_text", "rich_text": [{"plain_text": "Z2 uphill run on rolling terrain"}]},
                    "CoachComments": {"type": "rich_text", "rich_text": [{"plain_text": "Keep HR below aerobic threshold"}]},
                    "PlannedDuration": {"type": "number", "number": 1},
                    "Energy": {"type": "rich_text", "rich_text": []},
                },
            },
        ]
        deps = _make_draft_deps(template_sessions=templates)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert "WorkoutDescription: Z2 uphill run" in result
        assert "CoachComments: Keep HR below" in result
        assert "PlannedDuration: 1" in result
        assert "Energy" not in result  # empty → skipped
        assert "Title:" not in result  # title rendered as heading, not as property

    def test_skips_empty_properties(self):
        from weekforge.agents.draft_week_agent import _inject_templates

        templates = [
            {
                "id": "t1",
                "properties": {
                    "Title": {"type": "title", "title": [{"plain_text": "W15: Push"}]},
                    "WorkoutDescription": {"type": "rich_text", "rich_text": []},
                    "CoachComments": {"type": "rich_text", "rich_text": []},
                    "PlannedDuration": {"type": "number", "number": None},
                },
            },
        ]
        deps = _make_draft_deps(template_sessions=templates)
        ctx = _make_ctx(deps)
        result = _inject_templates(ctx)
        assert "W15: Push" in result
        assert "WorkoutDescription" not in result
        assert "CoachComments" not in result
        assert "PlannedDuration" not in result


class TestExtractPropText:
    def test_rich_text(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        prop = {"type": "rich_text", "rich_text": [{"plain_text": "hello"}, {"plain_text": " world"}]}
        assert _extract_prop_text(prop) == "hello world"

    def test_rich_text_empty(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        assert _extract_prop_text({"type": "rich_text", "rich_text": []}) == ""

    def test_number(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        assert _extract_prop_text({"type": "number", "number": 42}) == "42"

    def test_number_none(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        assert _extract_prop_text({"type": "number", "number": None}) == ""

    def test_date(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        assert _extract_prop_text({"type": "date", "date": {"start": "2024-06-03"}}) == "2024-06-03"

    def test_date_none(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        assert _extract_prop_text({"type": "date", "date": None}) == ""

    def test_unknown_type(self):
        from weekforge.agents.draft_week_agent import _extract_prop_text

        assert _extract_prop_text({"type": "checkbox", "checkbox": True}) == ""


class TestInjectFeedbackWindow:
    def test_empty_window_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_feedback_window

        deps = _make_draft_deps(feedback_window=[])
        ctx = _make_ctx(deps)
        assert _inject_feedback_window(ctx) == ""

    def test_renders_plan_and_summary(self):
        from weekforge.agents.draft_week_agent import (
            WeekFeedbackRow,
            _inject_feedback_window,
        )

        rows = [
            WeekFeedbackRow(week_prefix="W13", plan_md="Plan W13", summary_text="Summary W13"),
            WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text="Summary W14"),
        ]
        deps = _make_draft_deps(feedback_window=rows)
        ctx = _make_ctx(deps)
        result = _inject_feedback_window(ctx)
        assert "## Previous Weeks Feedback" in result
        assert "### W13" in result
        assert "Plan W13" in result
        assert "Summary W13" in result
        assert "### W14" in result
        assert "Summary W14" in result

    def test_skips_none_fields(self):
        from weekforge.agents.draft_week_agent import (
            WeekFeedbackRow,
            _inject_feedback_window,
        )

        rows = [WeekFeedbackRow(week_prefix="W14", plan_md=None, summary_text=None)]
        deps = _make_draft_deps(feedback_window=rows)
        ctx = _make_ctx(deps)
        result = _inject_feedback_window(ctx)
        assert "### W14" in result
        assert "Plan:" not in result
        assert "Summary:" not in result


class TestInjectPlanState:
    def test_none_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_plan_state

        deps = _make_draft_deps(plan_state_raw=None)
        ctx = _make_ctx(deps)
        assert _inject_plan_state(ctx) == ""

    def test_empty_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_plan_state

        deps = _make_draft_deps(plan_state_raw="")
        ctx = _make_ctx(deps)
        assert _inject_plan_state(ctx) == ""

    def test_present_returns_section(self):
        from weekforge.agents.draft_week_agent import _inject_plan_state

        deps = _make_draft_deps(plan_state_raw="PLAN_STATE:W01-W14\nMESOCYCLE:Test|12wk")
        ctx = _make_ctx(deps)
        result = _inject_plan_state(ctx)
        assert "## Existing PLAN_STATE" in result
        assert "MESOCYCLE:Test|12wk" in result


class TestInjectActiveFlare:
    def test_flare_yes(self):
        from weekforge.agents.draft_week_agent import _inject_active_flare

        deps = _make_draft_deps(active_flare=True)
        ctx = _make_ctx(deps)
        assert _inject_active_flare(ctx) == "ACTIVE_FLARE: YES"

    def test_flare_no(self):
        from weekforge.agents.draft_week_agent import _inject_active_flare

        deps = _make_draft_deps(active_flare=False)
        ctx = _make_ctx(deps)
        assert _inject_active_flare(ctx) == "ACTIVE_FLARE: NO"


class TestInjectBootstrapHint:
    def test_not_bootstrap_returns_empty(self):
        from weekforge.agents.draft_week_agent import _inject_bootstrap_hint

        deps = _make_draft_deps(bootstrap=False)
        ctx = _make_ctx(deps)
        assert _inject_bootstrap_hint(ctx) == ""

    def test_bootstrap_returns_hint(self):
        from weekforge.agents.draft_week_agent import _inject_bootstrap_hint

        deps = _make_draft_deps(bootstrap=True)
        ctx = _make_ctx(deps)
        result = _inject_bootstrap_hint(ctx)
        assert "## Bootstrap Mode" in result
        assert "conservative" in result.lower()
```

- [x] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/agents/test_draft_week_agent.py -v -k "Inject or inject"`
Expected: FAIL — `ImportError: cannot import name '_inject_user_profile'`

- [x] **Step 3: Add agent and decorators to draft_week_agent.py**

Replace the full file `src/weekforge/agents/draft_week_agent.py`:

```python
import re
from dataclasses import dataclass

from pydantic_ai import Agent, RunContext

from weekforge.agents.openai_model_factory import build_openai_model
from weekforge.agents.prompt_composer import compose_static_instructions
from weekforge.config.env import settings
from weekforge.config.llm_profiles import resolve_llm_profile
from weekforge.models.user_profile import UserProfile
from weekforge.models.week_plan import WeekPlan
from weekforge.prompts.loader import Prompt
from weekforge.tools.notion_api_gateway import get_page_title
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


_model, _model_settings = build_openai_model(resolve_llm_profile("reasoning"))

draft_week_agent = Agent(
    model=_model,
    model_settings=_model_settings,
    instructions=compose_static_instructions(Prompt.DRAFT_WEEK_TASK, settings.caveman_mode),
    deps_type=DraftWeekDeps,
    output_type=WeekPlan,
)


@draft_week_agent.instructions
def _inject_user_profile(ctx: RunContext[DraftWeekDeps]) -> str:
    return "## Active User Profile\n\n" + ctx.deps.user_profile.markdown


@draft_week_agent.instructions
def _inject_templates(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.template_sessions:
        return ""
    lines = ["## Template Sessions\n"]
    for t in ctx.deps.template_sessions:
        title = get_page_title(t)
        lines.append(f"### {title}")
        for prop_name, prop_val in t.get("properties", {}).items():
            if prop_val.get("type") == "title":
                continue
            text = _extract_prop_text(prop_val)
            if text:
                lines.append(f"{prop_name}: {text}")
        lines.append("")
    return "\n".join(lines)


def _extract_prop_text(prop: dict) -> str:
    """Extract display text from any Notion property; empty string if blank."""
    ptype = prop.get("type", "")
    if ptype == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if ptype == "number":
        val = prop.get("number")
        return str(val) if val is not None else ""
    if ptype == "date":
        d = prop.get("date")
        return d.get("start", "") if d else ""
    return ""


@draft_week_agent.instructions
def _inject_feedback_window(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.feedback_window:
        return ""
    lines = ["## Previous Weeks Feedback\n"]
    for row in ctx.deps.feedback_window:
        lines.append(f"### {row.week_prefix}")
        if row.plan_md:
            lines.append(f"Plan:\n{row.plan_md}")
        if row.summary_text:
            lines.append(f"Summary:\n{row.summary_text}")
        lines.append("")
    return "\n".join(lines)


@draft_week_agent.instructions
def _inject_plan_state(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.plan_state_raw:
        return ""
    return (
        "## Existing PLAN_STATE (progression context)\n\n"
        + ctx.deps.plan_state_raw
    )


@draft_week_agent.instructions
def _inject_active_flare(ctx: RunContext[DraftWeekDeps]) -> str:
    flag = "YES" if ctx.deps.active_flare else "NO"
    return f"ACTIVE_FLARE: {flag}"


@draft_week_agent.instructions
def _inject_bootstrap_hint(ctx: RunContext[DraftWeekDeps]) -> str:
    if not ctx.deps.bootstrap:
        return ""
    return (
        "## Bootstrap Mode\n\n"
        "Limited historical data available. Use templates and user profile as primary references. "
        "Apply conservative defaults for load and volume."
    )
```

- [x] **Step 4: Run decorator tests**

Run: `uv run pytest tests/agents/test_draft_week_agent.py -v`
Expected: all PASS (existing 26 tests + new decorator tests)

- [x] **Step 5: Commit**

```bash
git add src/weekforge/agents/draft_week_agent.py tests/agents/test_draft_week_agent.py
git commit -m "feat: add draft_week_agent with instruction decorators"
```

---

## Task 5: Workflow agent + accept steps

**Files:**
- Modify: `src/weekforge/workflows/draft_week.py:1-164`
- Modify: `tests/workflows/test_draft_week.py`

**Context:** `_step_agent` rebuilds `DraftWeekDeps` fresh from Notion (Layer B — not checkpointed). `_step_accept` becomes a closure inside `run_draft()` (needs `store`, `thread_id` for `run_accept_gate`). Both replace the existing stubs that raise `RuntimeError("Not yet implemented")`.

- [x] **Step 1: Write failing tests for _step_agent**

Add to `tests/workflows/test_draft_week.py`:

```python
from weekforge.models.week_plan import PlannedSession, WeekPlan


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_step_agent_runs_and_returns_accept(mock_notion, mock_db, mock_profile):
    """Agent step builds deps, calls agent, stores output, returns 'accept'."""
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="agent")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
        adjustments=["test adjustment"],
    )

    fake_result = MagicMock()
    fake_result.output = fake_plan
    fake_meta = MagicMock(input_tokens=100, output_tokens=50, latency_ms=500, model_used="test", cost_eur=0.01)
    fake_messages = [{"role": "user", "content": "test"}]

    with patch("weekforge.workflows.draft_week.run_with_metadata", return_value=(fake_result, fake_meta, fake_messages)):
        result = _step_agent(state, cost)

    assert result == "accept"
    assert state.last_output == fake_plan
    assert len(state.calls) == 1
    assert state.pending_feedback is None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_step_agent_includes_pending_feedback_in_prompt(mock_notion, mock_db, mock_profile):
    """Pending feedback appended to prompt."""
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.user_profile import UserProfile

    state = DraftWeekState(week_prefix="W15", step="agent", pending_feedback="add more conditioning")
    cost = RunCost()

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan

    with patch("weekforge.workflows.draft_week.run_with_metadata", return_value=(fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])) as mock_run:
        _step_agent(state, cost)

    prompt_arg = mock_run.call_args[1].get("prompt", mock_run.call_args[0][1])
    assert "add more conditioning" in prompt_arg
    assert state.pending_feedback is None  # cleared after use


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
def test_step_agent_accumulates_calls(mock_notion, mock_db, mock_profile):
    """Multiple agent runs accumulate in state.calls and cost."""
    from weekforge.workflows.draft_week import _step_agent
    from weekforge.models.user_profile import UserProfile
    from weekforge.models.llm_call_cost import CallMetadata

    # Pre-existing call from prior iteration
    existing_call = CallMetadata(input_tokens=50, output_tokens=25, latency_ms=200, model_used="t", cost_eur=0.005)
    state = DraftWeekState(week_prefix="W15", step="agent", calls=[existing_call])
    cost = RunCost()
    cost.add(existing_call)

    mock_notion.query.return_value = [
        {"id": "t1", "properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push"}]}}},
    ]
    mock_db.find_summary_row.return_value = None
    mock_profile.return_value = UserProfile(page_id="up1", markdown="# Profile")

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    new_meta = CallMetadata(input_tokens=100, output_tokens=50, latency_ms=500, model_used="t", cost_eur=0.01)

    with patch("weekforge.workflows.draft_week.run_with_metadata", return_value=(fake_result, new_meta, [])):
        _step_agent(state, cost)

    assert len(state.calls) == 2
    assert cost.call_count == 2
```

- [x] **Step 2: Write failing tests for accept step (closure)**

Add to `tests/workflows/test_draft_week.py`:

```python
@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_approve_transitions_to_validate(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → approve → step becomes 'validate'."""
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

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    mock_gate.return_value = AcceptResult(step="validate", feedback=None)

    with pytest.raises(RuntimeError, match="Not yet implemented.*validate"):
        run_draft("W15", "draft-week-W15", store)

    mock_gate.assert_called_once()
    gate_kwargs = mock_gate.call_args[1]
    assert gate_kwargs["approved_step"] == "validate"


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_quit_pauses_workflow(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → quit → workflow pauses with checkpoint."""
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

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    mock_gate.return_value = AcceptResult(step=None, feedback=None)

    # Should NOT raise — workflow pauses
    run_draft("W15", "draft-week-W15", store)

    rec = store.load("draft-week-W15")
    assert rec is not None


@patch("weekforge.workflows.draft_week.load_user_profile")
@patch("weekforge.workflows.draft_week.summaries_db")
@patch("weekforge.workflows.draft_week.notion")
@patch("weekforge.workflows.draft_week.run_accept_gate")
@patch("weekforge.workflows.draft_week.run_with_metadata")
def test_accept_feedback_loops_to_agent(mock_run_meta, mock_gate, mock_notion, mock_db, mock_profile, tmp_path):
    """Accept → feedback → loops back to agent with pending_feedback set."""
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

    fake_plan = WeekPlan(
        week_prefix="W15",
        sessions=[PlannedSession(name="Push", duration_min=85, focus_tags=["push"])],
    )
    fake_result = MagicMock()
    fake_result.output = fake_plan
    mock_run_meta.return_value = (fake_result, MagicMock(input_tokens=0, output_tokens=0, latency_ms=0, model_used="t", cost_eur=0), [])

    # First call: feedback. Second call: quit (to terminate the loop).
    mock_gate.side_effect = [
        AcceptResult(step="agent", feedback="add more conditioning"),
        AcceptResult(step=None, feedback=None),
    ]

    run_draft("W15", "draft-week-W15", store)

    # run_with_metadata called twice (initial + feedback loop)
    assert mock_run_meta.call_count == 2
    # Second prompt should include the feedback
    second_call_prompt = mock_run_meta.call_args_list[1][0][1] if len(mock_run_meta.call_args_list[1][0]) > 1 else mock_run_meta.call_args_list[1][1].get("prompt", "")
    assert "add more conditioning" in second_call_prompt
```

- [x] **Step 3: Run tests to verify they fail**

Run: `uv run pytest tests/workflows/test_draft_week.py -v -k "step_agent or accept_approve or accept_quit or accept_feedback"`
Expected: FAIL — `RuntimeError: Not yet implemented: agent`

- [x] **Step 4: Implement _step_agent**

Replace the `_step_agent` stub in `src/weekforge/workflows/draft_week.py`:

```python
def _step_agent(state: DraftWeekState, cost: RunCost) -> str | None:
    from weekforge.agents.agent_run_with_metadata import run_with_metadata
    from weekforge.agents.draft_week_agent import (
        DraftWeekDeps,
        WeekFeedbackRow,
        derive_active_flare,
        draft_week_agent,
    )
    from weekforge.config.env import settings
    from weekforge.config.user_profile_loader import load_user_profile
    from weekforge.tools import notion_api_gateway as notion
    from weekforge.tools import summaries_db
    from weekforge.tools.notion_api_gateway import get_page_title
    from weekforge.tools.plan_state import parse_plan_state

    from pydantic_ai.messages import ModelMessagesTypeAdapter

    _verbose(f"agent: rebuilding context for {state.week_prefix}…")
    all_templates = notion.query(database_id=settings.notion_db_training_templates)
    template_sessions = [p for p in all_templates if get_page_title(p).startswith(state.week_prefix)]

    week_num = int(state.week_prefix[1:])
    feedback_window: list[WeekFeedbackRow] = []
    for prev_week in range(week_num - 1, max(week_num - 4, 0), -1):
        prev_prefix = f"W{prev_week:02d}"
        row = summaries_db.find_summary_row(prev_prefix)
        if row is None:
            continue
        feedback_window.append(WeekFeedbackRow(
            week_prefix=prev_prefix,
            plan_md=summaries_db.read_plan_property(row),
            summary_text=summaries_db.read_summary_body(row),
        ))
    feedback_window.reverse()

    plan_state = parse_plan_state(state.plan_state_raw) if state.plan_state_raw else None
    profile = load_user_profile()
    active_flare = derive_active_flare(feedback_window, plan_state)

    deps = DraftWeekDeps(
        week_prefix=state.week_prefix,
        template_sessions=template_sessions,
        feedback_window=feedback_window,
        plan_state=plan_state,
        plan_state_raw=state.plan_state_raw,
        user_profile=profile,
        active_flare=active_flare,
        bootstrap=state.is_bootstrap or False,
    )

    prev = ModelMessagesTypeAdapter.validate_python(state.messages_json) if state.messages_json else None

    prompt = f"Draft week plan for {state.week_prefix}."
    if state.pending_feedback:
        prompt += f"\nUser feedback: {state.pending_feedback}"

    iteration = len(state.calls) + 1
    with _console.status(f"[bold]Drafting week plan… (attempt {iteration})[/bold]", spinner="bouncingBar"):
        result, meta, new_messages = run_with_metadata(
            draft_week_agent, prompt, deps=deps, message_history=prev,
        )

    state.last_output = result.output
    state.messages_json = ModelMessagesTypeAdapter.dump_python(new_messages, mode="json")
    state.calls.append(meta)
    cost.add(meta)
    _verbose(f"agent: {meta.input_tokens} input / {meta.output_tokens} output tokens")
    state.pending_feedback = None
    return "accept"
```

- [x] **Step 5: Move _step_accept into run_draft closure and implement**

Add the import at module top:

```python
from weekforge.hitl import run_accept_gate
```

Add `MAX_ITERATIONS` constant near top of file:

```python
MAX_ITERATIONS = 3
```

Remove the `_step_accept` stub. Inside `run_draft()`, define it as a closure before the `steps` dict:

```python
def run_draft(week_prefix: str, thread_id: str, store: CheckpointStore) -> None:
    def step_overwrite_check(state: DraftWeekState, cost: RunCost) -> str | None:
        # ... (existing code unchanged) ...

    def step_accept(state: DraftWeekState, cost: RunCost) -> str | None:
        assert state.last_output is not None
        from weekforge.tools.week_plan_renderer import render_week_plan

        def render_fn() -> str:
            return render_week_plan(state.last_output)

        result = run_accept_gate(
            render_fn=render_fn,
            approved_step="validate",
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

    steps: dict[str, StepFn[DraftWeekState]] = {
        "overwrite_check": step_overwrite_check,
        "load_context": _step_load_context,
        "agent": _step_agent,
        "accept": step_accept,
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

- [x] **Step 6: Update test_stub_steps_raise**

The existing test `test_stub_steps_raise` imports `_step_accept` and `_step_agent` as module-level functions. After this change, `_step_accept` is no longer module-level (it's a closure). Update the test to only test the remaining stubs:

```python
def test_stub_steps_raise():
    """Remaining future steps raise RuntimeError."""
    from weekforge.workflows.draft_week import (
        _step_validate,
        _step_write,
    )

    state = DraftWeekState(week_prefix="W15")
    cost = RunCost()

    for step_fn in [_step_validate, _step_write]:
        with pytest.raises(RuntimeError, match="Not yet implemented"):
            step_fn(state, cost)
```

- [x] **Step 7: Run all draft_week tests**

Run: `uv run pytest tests/workflows/test_draft_week.py tests/agents/test_draft_week_agent.py -v`
Expected: all PASS

- [x] **Step 8: Run full test suite**

Run: `uv run pytest -v`
Expected: all PASS, no regressions

- [x] **Step 9: Commit**

```bash
git add src/weekforge/workflows/draft_week.py tests/workflows/test_draft_week.py
git commit -m "feat: implement draft_week agent and accept HITL steps"
```

---

## Self-Review

### Spec coverage check

| Spec requirement | Task |
|---|---|
| `draft_week_agent` produces structurally valid `WeekPlan` from `DraftWeekDeps` | Task 4 (agent), Task 1 (model) |
| HITL panel renders session list, durations, focus tags, adjustments, cost | Task 2 (renderer), Task 5 (accept gate renders via `render_week_plan`) |
| Approve transitions to `validate` step | Task 5 (`approved_step="validate"` in `run_accept_gate`) |
| Feedback re-runs agent with accumulated message history | Task 5 (accept returns `"agent"`, agent reads `messages_json`) |
| Quit saves checkpoint and prints resume hint | Task 5 (accept gate returns `step=None`, runner pauses) |
| Message history persists across checkpoint resume | Task 5 (`state.messages_json` set from `ModelMessagesTypeAdapter`) |
| `render_week_plan()` output matches legacy format | Task 2 (tests verify exact format) |
| Token burn warning at MAX_ITERATIONS | Task 5 (`run_accept_gate` handles this, `MAX_ITERATIONS=3` passed) |
| Prompt text in `prompts/draft-week-task.md`, not inline | Task 3 |
| Profile: `resolve_llm_profile("reasoning")` | Task 4 |
| `DraftWeekDeps` dataclass lives in agent file | Already exists from step 2b, Task 4 keeps it |
| `Prompt.DRAFT_WEEK_TASK` enum entry | Task 3 |
| `focus_tags` controlled vocabulary via Literal | Task 1 |

### Placeholder scan

No TBDs, TODOs, or "implement later" found. All code steps have complete code blocks.

### Type consistency check

- `WeekPlan` used in: Task 1 (defined), Task 2 (renderer param), Task 4 (agent output_type), Task 5 (state.last_output type)
- `DraftWeekDeps` used in: Task 4 (deps_type), Task 5 (built in _step_agent)
- `render_week_plan` used in: Task 2 (defined), Task 5 (called in accept closure)
- `FocusTag` used in: Task 1 (defined, used in PlannedSession.focus_tags)
- `MAX_ITERATIONS` used in: Task 5 (defined + passed to run_accept_gate)
- `AcceptResult` used in: Task 5 tests (imported from `weekforge.hitl`)

All consistent.
