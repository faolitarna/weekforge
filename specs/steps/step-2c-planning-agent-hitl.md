# Step 2c: Planning Agent + HITL Loop

## Status
ready (facilitator pass — contract sections to be filled by specs-developer)

## Goal

Build the Tier-2 planner agent and wire it into a single accept/feedback/quit gate. Agent consumes `PlanWeekDeps` from 2b, returns a typed `WeekPlan`. HITL renders the plan, lets user approve, refine via feedback, or quit. Feedback re-runs the agent with full message history. Approval transitions to 2d.

## Decisions

- **Agent file:** `src/weekforge/agents/plan_week_agent.py`. Pattern mirrors [`summarize_week_agent.py`](../../src/weekforge/agents/summarize_week_agent.py) exactly.
- **Output type — `WeekPlan` (DEC-P13):** new model in `src/weekforge/models/week_plan.py`:
  ```python
  class PlannedSession(BaseModel):
      name: str             # "Push + Hinge"
      duration_min: int     # 85
      focus_tags: list[str] # ["push","hinge"] | ["cardio","z2","uphill"] | ...
  class WeekPlan(BaseModel):
      week_prefix: str
      sessions: list[PlannedSession]
      adjustments: list[str] = Field(default_factory=list)  # human-readable bullets
  ```
- **`focus_tags` vocabulary (controlled).** Closed enumeration so Tier-0 validation in 2d is deterministic. Initial set:
  - Movement: `push`, `pull`, `squat`, `hinge`, `core`, `carry`
  - Cardio: `cardio`, `z1`, `z2`, `z3`, `uphill`, `loaded`, `run`, `hike`, `walk`
  - Skill: `climbing`, `hangboard`, `mobility`, `recovery`
  - Other: `template_restructured` (catch-all for non-classifiable template variants)
  - Free-form additions disallowed at validation time (Pydantic `Literal` set, expand list as needed).
- **Profile:** `resolve_llm_profile("reasoning")` per DEC-P4.
- **Instructions composition:** `compose_static_instructions(Prompt.PLAN_WEEK_TASK, settings.caveman_mode)`. New enum entry `PLAN_WEEK_TASK = "plan-week-task.md"` added to `Prompt`. New file `src/weekforge/prompts/plan-week-task.md` ports the legacy `<week-plan>` section verbatim, adapted to the new structured-output contract (instructs agent to produce `WeekPlan` JSON, lists `focus_tags` vocabulary, embeds pull:push and conditioning floors as soft requirements, defers retry contract to 2d).
- **`PlanWeekDeps` dataclass:** lives in agent file (matches `SummarizeDeps` placement). Imported by 2b.
- **Per-run instructions decorators:**
  - `_inject_user_profile` — verbatim copy of summarize_week pattern.
  - `_inject_templates` — render `template_sessions` into a compact text block with name + body excerpt (mirroring legacy plan_week.md template section).
  - `_inject_feedback_window` — render last 3 weeks (Plan + Summary excerpts) per row.
  - `_inject_plan_state` — pass-through `plan_state_raw` if present (matches summarize_week pattern).
  - `_inject_active_flare` — one-line directive `"ACTIVE_FLARE: YES"` or `"ACTIVE_FLARE: NO"` so agent unambiguously sees the boolean.
  - `_inject_bootstrap_hint` — only fires if `bootstrap=True`, instructs conservative defaults.
- **Workflow steps in 2c:** `agent → accept`. Pattern matches `summarize_week.agent` step (lines 162-201) and `accept` step (lines 203-242).
  - `agent` step: build prompt from week_prefix + optional `pending_feedback`. Call `run_with_metadata(plan_week_agent, prompt, deps=deps, message_history=prev)`. Persist `messages_json`, append `meta` to `state.calls`, save `last_output`. Iteration count via `len(state.calls)`.
  - `accept` step: render Rich panel with: rendered week plan markdown (via 2d's renderer or a shared one), adjustments bullets, cost summary. Three options approve/feedback/quit via `hitl_confirm`. Approve → `state.step = "validate"` (2d). Feedback → `state.pending_feedback = decision.feedback; state.step = "agent"`. Quit → resume hint and return.
- **Max iterations:** `MAX_ITERATIONS = 3` (same as summarize_week). After threshold, the accept panel adds a "token burn warning" line — same UX.
- **`pending_feedback: str | None`** field added to `PlanWeekState`.
- **Renderer (shared with 2d):** `tools/week_plan_renderer.py` exports `render_week_plan(plan: WeekPlan) -> str` producing legacy markdown:
  ```
  Week W## Plan ({N} sessions):
  1. W##: {name} — {duration_min} min
  2. ...

  Adjustments:
  - {adjustment_1}
  - {adjustment_2}
  ```
  2c uses it for HITL panel; 2d uses it for Notion write.

## Open questions

None.

## Inputs

(specs-developer to fill — `PlanWeekDeps` from 2b, prior `messages_json`, optional `pending_feedback`)

## Outputs

(specs-developer to fill — `state.last_output: WeekPlan`, accept decision, updated message history)

## Files

(specs-developer to fill — expected: agents/plan_week_agent.py [create], models/week_plan.py [create], prompts/plan-week-task.md [create], prompts/loader.py [edit, add enum entry], tools/week_plan_renderer.py [create], workflows/plan_week.py [edit, add agent + accept steps], models/workflow_state.py [edit, add `pending_feedback` to PlanWeekState])

## Data contracts

(specs-developer to fill — `WeekPlan`, `PlannedSession`, `PlanWeekDeps`, `focus_tags` Literal/Enum)

## Workflow

(specs-developer to fill — `agent → accept (→ agent on feedback | → validate on approve | → return on quit)`)

## Tier split

- Tier 0: prompt assembly, message-history serialization, accept panel rendering, renderer
- Tier 1: —
- Tier 2: `plan_week_agent` (LLM synthesis)

## Failure modes

- Pydantic-AI output validation fails → Pydantic-AI raises; surface error and let HITL retry on user feedback or fail loudly. (No silent re-prompt at this layer — that's 2d's narrow scope.)
- LLM ignores `focus_tags` controlled vocabulary → Pydantic `Literal` validation rejects → re-prompt by Pydantic-AI's built-in retry, OR surface and let user feedback correct. Decide concretely in specs-developer pass.
- Iteration count ≥ MAX_ITERATIONS → display warning in accept panel; do NOT auto-fail. User decides.

## Acceptance criteria

(specs-developer to fill — agent produces structurally valid `WeekPlan`, HITL renders all required fields, approve/feedback/quit work, message history persists across resume)

## Out of scope

- Pull:push and conditioning enforcement loop — 2d.
- Notion write — 2d.
- Multi-mesocycle reasoning — step-4.
- Fine-grained per-session content (warmup, exercises) — step-3.

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P3..P6, P10..P13, P19
- [agents/summarize_week_agent.py](../../src/weekforge/agents/summarize_week_agent.py) — pattern to mirror
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — agent + accept steps to mirror (lines 162-242)
- [agents/prompt_composer.py](../../src/weekforge/agents/prompt_composer.py) — `compose_static_instructions`
- [agents/agent_run_with_metadata.py](../../src/weekforge/agents/agent_run_with_metadata.py) — `run_with_metadata`
- `source-material/.claude/commands/plan_week.md` — `<week-plan>` section
