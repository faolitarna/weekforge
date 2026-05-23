# Step 2c: Draft Week Agent + HITL Loop

## Status
ready

## Goal

Build the Tier-2 planner agent and wire it into a single accept/feedback/quit gate. Agent consumes `DraftWeekDeps` from 2b, returns a typed `WeekPlan`. HITL renders the plan, lets user approve, refine via feedback, or quit. Feedback re-runs agent with full message history. Approval transitions to 2d.

## Decisions

- **Agent file:** `src/weekforge/agents/draft_week_agent.py` (DEC-P3, DEC-P20). Pattern mirrors `summarize_week_agent.py` exactly.
- **Output type — `WeekPlan` (DEC-P13):** new model in `src/weekforge/models/week_plan.py`:
  ```python
  class PlannedSession(BaseModel):
      name: str             # "Push + Hinge"
      duration_min: int     # 85
      focus_tags: list[str] # ["push","hinge"] | ["cardio","z2","uphill"] | ...
  class WeekPlan(BaseModel):
      week_prefix: str
      sessions: list[PlannedSession]
      adjustments: list[str] = Field(default_factory=list)
  ```
- **`focus_tags` vocabulary (controlled).** Closed enumeration so Tier-0 validation in 2d is deterministic. Initial set:
  - Movement: `push`, `pull`, `squat`, `hinge`, `core`, `carry`
  - Cardio: `cardio`, `z1`, `z2`, `z3`, `uphill`, `loaded`, `run`, `hike`, `walk`
  - Skill: `climbing`, `hangboard`, `mobility`, `recovery`
  - Other: `template_restructured`
  - Free-form additions disallowed at validation time (Pydantic `Literal` set, expand list as needed).
- **Profile:** `resolve_llm_profile("reasoning")` per DEC-P4.
- **Instructions composition:** `compose_static_instructions(Prompt.DRAFT_WEEK_TASK, settings.caveman_mode)` (DEC-P5, DEC-P20). New enum entry `Prompt.DRAFT_WEEK_TASK = "draft-week-task.md"`. New file `src/weekforge/prompts/draft-week-task.md`.
- **`DraftWeekDeps` dataclass:** lives in agent file (matches `SummarizeDeps` placement). Imported by 2b.
- **Per-run instructions decorators:**
  - `_inject_user_profile` — verbatim copy of summarize_week pattern.
  - `_inject_templates` — render `template_sessions` into compact text block with name + body excerpt.
  - `_inject_feedback_window` — render last 3 weeks (Plan + Summary excerpts) per row.
  - `_inject_plan_state` — pass-through `plan_state_raw` if present.
  - `_inject_active_flare` — one-line directive `"ACTIVE_FLARE: YES"` or `"ACTIVE_FLARE: NO"`.
  - `_inject_bootstrap_hint` — only fires if `bootstrap=True`, instructs conservative defaults.
- **Workflow steps:** `agent → accept`. Both are step functions in the step registry (DEC-P25).
  - `agent` step: build prompt, call `run_with_metadata(draft_week_agent, prompt, deps=deps, message_history=prev)`. Persist `messages_json`, append `meta` to `state.calls`, save `last_output`. Return `"accept"`.
  - `accept` step: call `run_accept_gate()` (DEC-P29) with `render_fn=lambda: render_week_plan(state.last_output)` and `approved_step="validate"`. Returns `AcceptResult`. Caller reads `result.feedback` → sets `state.pending_feedback`. Returns `result.step` (`"validate"` | `"agent"` | `None`).
- **Max iterations:** `MAX_ITERATIONS = 3`. Passed to `run_accept_gate()` — shared constant.
- **Renderer:** `tools/week_plan_renderer.py` exports `render_week_plan(plan: WeekPlan) -> str`. Used by HITL panel (2c) and Notion write (2d).

## Open questions

None.

## Inputs

- `DraftWeekDeps` from 2b (rebuilt from Notion on resume)
- `state.messages_json` — prior conversation for feedback loops
- `state.pending_feedback` — user feedback text from prior accept iteration

## Outputs

- `state.last_output: WeekPlan` — validated Pydantic model
- `state.messages_json` — updated conversation history
- `state.calls` — appended `CallMetadata` per agent run
- Accept decision: `state.step` set to `"validate"` (approve), `"agent"` (feedback), or return (quit)

## Files

- `src/weekforge/agents/draft_week_agent.py`: create — agent definition, `DraftWeekDeps`, instruction decorators
- `src/weekforge/models/week_plan.py`: create — `PlannedSession`, `WeekPlan`
- `src/weekforge/prompts/draft-week-task.md`: create — task prompt (ports legacy `<week-plan>` section)
- `src/weekforge/prompts/loader.py`: edit — add `DRAFT_WEEK_TASK` enum entry
- `src/weekforge/tools/week_plan_renderer.py`: create — `render_week_plan()`
- `src/weekforge/workflows/draft_week.py`: edit — implement `agent` + `accept` steps

## Data contracts

### `WeekPlan`

```python
class PlannedSession(BaseModel):
    name: str
    duration_min: int
    focus_tags: list[str]

class WeekPlan(BaseModel):
    week_prefix: str
    sessions: list[PlannedSession]
    adjustments: list[str] = Field(default_factory=list)
```

### `DraftWeekDeps`

See 2b. Lives in `draft_week_agent.py`, imported by workflow.

### `render_week_plan()`

```python
def render_week_plan(plan: WeekPlan) -> str:
    """Render WeekPlan as legacy-compatible markdown for HITL display and Notion write."""
```

Output format:
```
Week W## Plan (N sessions):
1. W##: Push + Hinge — 85 min
2. W##: Pull + Squat — 80 min
...

Adjustments:
- adjustment_1
- adjustment_2
```

### Prompt enum addition

```python
DRAFT_WEEK_TASK = "draft-week-task.md"
```

## Workflow

1. Enter `agent` step (from `load_context` or feedback loop).
2. Rebuild `DraftWeekDeps` from Notion (Layer B — not checkpointed).
3. Deserialize `messages_json` → `message_history` (if feedback loop).
4. Build prompt: `f"Draft week plan for {state.week_prefix}."` + optional pending feedback.
5. Call `run_with_metadata(draft_week_agent, prompt, deps=deps, message_history=prev)`.
6. Store `result.output` → `state.last_output`, update `messages_json`, append `CallMetadata`.
7. Clear `state.pending_feedback`. Return `"accept"`.
8. Enter `accept` step.
9. Call `run_accept_gate(render_fn=lambda: render_week_plan(...), approved_step="validate", ...)` (DEC-P29).
10. Gate returns `AcceptResult`. If `result.feedback`: set `state.pending_feedback = result.feedback`.
11. Return `result.step`: `"validate"` | `"agent"` | `None` (quit).

## Tier split

- Tier 0: prompt assembly, message-history serialization, accept panel rendering, renderer
- Tier 1: —
- Tier 2: `draft_week_agent` (LLM synthesis via `resolve_llm_profile("reasoning")`)

## Failure modes

- Pydantic-AI output validation fails → Pydantic-AI raises; surface error and let HITL retry on user feedback or fail loudly.
- LLM ignores `focus_tags` controlled vocabulary → Pydantic `Literal` validation rejects → Pydantic-AI built-in retry handles. If still fails, surface to HITL.
- Iteration count ≥ MAX_ITERATIONS → display warning in accept panel; do NOT auto-fail. User decides.
- Empty templates (should have been caught in 2b) → agent receives no template context, produces best-effort plan.

## Acceptance criteria

- [ ] `draft_week_agent` produces structurally valid `WeekPlan` from `DraftWeekDeps`
- [ ] HITL panel renders all required fields: session list, durations, focus tags, adjustments, cost
- [ ] Approve transitions to `validate` step
- [ ] Feedback re-runs agent with accumulated message history
- [ ] Quit saves checkpoint and prints resume hint
- [ ] Message history persists across checkpoint resume
- [ ] `render_week_plan()` output matches legacy format
- [ ] Token burn warning appears at MAX_ITERATIONS
- [ ] Prompt text lives in `prompts/draft-week-task.md`, not inline

## Out of scope

- Pull:push and conditioning enforcement loop — 2d.
- Notion write — 2d.
- Multi-mesocycle reasoning — step-4.
- Fine-grained per-session content (warmup, exercises) — step-3.

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P3..P6, P10..P13, P19, P20
- [agents/summarize_week_agent.py](../../src/weekforge/agents/summarize_week_agent.py) — pattern to mirror
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — agent + accept steps pattern
- [agents/prompt_composer.py](../../src/weekforge/agents/prompt_composer.py) — `compose_static_instructions`
- [agents/agent_run_with_metadata.py](../../src/weekforge/agents/agent_run_with_metadata.py) — `run_with_metadata`
- `source-material/.claude/commands/plan_week.md` — `<week-plan>` section
