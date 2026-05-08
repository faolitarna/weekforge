# Step 2: Planning Engine (`plan_week`) — Index

## Status
ready (sub-step index)

## Goal

Build the macro week planner. `weekforge plan <week>` loads context (templates + 3-week feedback window + PLAN_STATE + user profile), generates a high-level week plan via Tier-2 agent, runs a HITL collaborative shaping loop, and persists the approved plan onto the matching `training_week_summaries` row's `Plan` rich-text property (DEC-006). Output unlocks step-1's `plan_adherence` extraction and step-3 session generation.

Faithfully recreates `source-material/.claude/commands/plan_week.md` in the post-step-1 Weekforge architecture (Tier-0 Python for deterministic context loading + validation, Tier-2 Pydantic AI for plan synthesis).

## Prerequisites

Step 1 complete — extraction subsystem ships `WeekSummary`, `PlanState`, `summarize_week_agent`, prompt composition, `CheckpointStore`/`hitl_confirm`, `RunCost`, Notion gateway. Step 2 reuses all of it; introduces no new infrastructure.

## Sub-Step Sequence

| # | Sub-Step | Focus | Status |
|---|----------|-------|--------|
| 2a | [CLI, State, Checkpoint](./step-2a-cli-state-checkpoint.md) | `weekforge plan <week>` Typer command, `PlanWeekState`, `workflows/plan_week.py` skeleton, overwrite-confirm gate, resume support | ⬜ |
| 2b | [Context Loading](./step-2b-context-loading.md) | Tier-0: templates by prefix, 3-week feedback window, PLAN_STATE load, user profile, `active_flare` derivation | ⬜ |
| 2c | [Planning Agent + HITL](./step-2c-planning-agent-hitl.md) | `plan_week_agent`, `prompts/plan-week-task.md`, `WeekPlan` output type, accept/feedback/quit gate, message-history persistence | ⬜ |
| 2d | [Validation & Notion Write](./step-2d-validation-and-write.md) | Tier-0 pull:push + conditioning checks with 1-retry re-prompt, idempotent write to `training_week_summaries.Plan` | ⬜ |

## Decisions

Decisions captured during step-2 facilitator pass (2026-04-26).

- **DEC-P1 — Plan persistence target.** Approved plan written into the `Plan` rich-text property on the `training_week_summaries` row matching `week_prefix`. Row created if missing. Body code-block (used by step-1d for summary) stays untouched. Implements DEC-006.
- **DEC-P2 — Workflow style.** Separate file `workflows/plan_week.py`, mirrors `summarize_week.py` shape: `step` literal state machine, `CheckpointStore.save()` at every step boundary, no new orchestration abstractions.
- **DEC-P3 — Agent file naming.** `agents/plan_week_agent.py` (DEC-010 verb_noun convention). Task prompt extracted to `prompts/plan-week-task.md` (no inline LLM text per feedback_prompts_not_in_code).
- **DEC-P4 — LLM profile.** `reasoning` (gpt-5.4-medium). Plan generation is interpretive and multi-constraint; infrequent enough that reasoning cost is acceptable.
- **DEC-P5 — Shared coaching context.** Planner reuses `compose_static_instructions(Prompt.PLAN_WEEK_TASK, settings.caveman_mode)`. Persona + guardrails + feedback-interpretation + progression-protocol auto-prefixed. New enum entry `Prompt.PLAN_WEEK_TASK` added.
- **DEC-P6 — User profile injection.** Loaded via `load_user_profile()` as a markdown blob (DEC-009) and injected via `@agent.instructions` decorator, identical pattern to `summarize_week_agent._inject_user_profile`.
- **DEC-P7 — PLAN_STATE consumption.** Loaded with the same logic as `summarize_week.plan_state_check`, parsed via `parse_plan_state`. Typed `PlanState` passed into agent deps. Bootstrap (no PLAN_STATE row) → continue with warning.
- **DEC-P8 — Feedback window.** Previous 3 weeks of `training_week_summaries` rows: read both `Plan` property and body code-block summary per row. No fall-through to raw sessions — step-1 guarantees a summary for any completed week.
- **DEC-P9 — Sequential context loading (no asyncio).** Notion gateway is sync; planning loads ~5 records (1 template query, 3 summary rows, 1 PLAN_STATE row). Sequential is fine. Re-evaluate only if observed wall-time hurts.
- **DEC-P10 — HITL accept loop.** Single accept gate via `hitl_confirm`. Approve → write Plan + done. Feedback → replay into next agent run with `message_history`. Quit → checkpoint + resume hint. Mirrors step-1c/d UX.
- **DEC-P11 — Cost display.** `RunCost` accumulator. Cost summary in HITL panel header and on completion panel. Same as `summarize_week`.
- **DEC-P12 — Week prefix source.** Derived directly from CLI argument: `f"W{week:02d}"`. No separate template-week mapping. (Resolves Q1.)
- **DEC-P13 — Plan output shape.** Typed Pydantic model:
  ```python
  class PlannedSession(BaseModel):
      name: str          # "Push + Hinge"
      duration_min: int  # 85
      focus_tags: list[str]  # e.g., ["push","hinge"] or ["cardio","z2","uphill"]
  class WeekPlan(BaseModel):
      week_prefix: str   # "W15"
      sessions: list[PlannedSession]
      adjustments: list[str] = []  # human-readable reasoning bullets
  ```
  Renderer produces legacy markdown for Notion: `"N. W##: {name} — {duration_min} min"`. (Resolves Q2.)
- **DEC-P14 — Tier-0 plan validation.** After agent returns, Python counts `focus_tags`. If pull:push < 1.5:1 OR conditioning sessions < 2 → re-prompt agent once with concrete violation diff (e.g., `"got 1.2:1 pull:push, need ≥1.5:1; got 1 conditioning session, need ≥2"`). Max 1 retry. Then surface to HITL with warning. (Resolves Q3.)
- **DEC-P15 — `active_flare` source.** Union of (a) last week `WeekSummary.pain_status` containing any non-empty `JointEntry.status`, AND (b) PLAN_STATE `ACTIVE_ISSUES` section non-empty for SI / spine / joint markers. Either truthy → flag set. (Resolves Q4.)
- **DEC-P16 — Bootstrap behavior.** Missing PLAN_STATE OR empty 3-week window → CLI warning, planner proceeds with templates + user profile only. Week 1 is the canonical bootstrap. (Resolves Q5.)
- **DEC-P17 — Re-plan overwrite gate.** If `training_week_summaries[Week=W##].Plan` is non-empty → HITL confirm "Plan exists. Overwrite? [y/n]" before generating. Default: keep existing (cancel run). Symmetric with the `overwrite_check` placeholder in `summarize_week`. (Resolves Q6.)
- **DEC-P18 — No cross-command ordering enforcement.** `weekforge plan` and `weekforge summarize-week` stay independent. `summarize_week` already gracefully handles missing Plan (`planned_plan_markdown` is `None` → `plan_adherence` skipped). (Resolves Q7.)
- **DEC-P19 — Message history persistence.** `PlanWeekState.messages_json: list[dict]` mirrors `SummarizeWeekState.messages_json`. Pydantic-AI `message_history` survives quit/resume so the agent's prior plan + user's prior feedback are intact across terminal sessions. (Resolves Q9.)

## Open questions

None.

## Out of scope

- Session generation (`draft_session`) — step-3.
- Mesocycle planning (`summarize_plan`) — step-4.
- CLI polish, animations, panel restyling — step-5.
- Async Notion gateway — orthogonal infra concern; revisit only if planning latency becomes user-visible.
- New mesocycle bootstrap UI — assume PLAN_STATE either exists or absence triggers the DEC-P16 warning path.
- Editing `summarize_week` to consume a structured `WeekPlan` — keep its current markdown ingestion path.
- Backfilling `Plan` property for already-summarized weeks.

## Architectural Summary

- **Source material fidelity.** Every behavior from `source-material/.claude/commands/plan_week.md` — template load by week prefix, 3-week feedback analysis, PLAN_STATE-aware progression context, pull:push ratio enforcement, conditioning volume floor, plan format, HITL stop-point — maps to a named acceptance criterion in one of the sub-steps. Legacy `run_log` Stage transitions are dropped (DEC-006 retired the DB).
- **Tier split.** Deterministic work (Notion queries, prefix derivation, `active_flare` boolean computation, ratio counting, markdown rendering) is Tier-0 in 2a/2b/2d. Synthesis (plan composition, adjustments narrative, conflict resolution across signals) is Tier-2 in 2c.
- **HITL shape.** Two gates: (1) overwrite-confirm in 2a (only fires when row's Plan property is non-empty), (2) accept-summary loop in 2c with feedback re-prompt + message history. Validation auto-retry in 2d is pre-HITL — user never sees a structurally invalid plan unless circuit breaker trips.
- **Prompt composition.** `plan_week_agent` uses `compose_static_instructions(Prompt.PLAN_WEEK_TASK, ...)` — shared coaching prefix identical to `summarize_week_agent`. `@agent.instructions` decorators inject user profile, templates, feedback window, PLAN_STATE, `active_flare` flag at run time.
- **Reused infrastructure.** No new Tier-0 tools beyond a thin renderer for `WeekPlan → markdown`. Notion CRUD via `tools/notion_api_gateway`. PLAN_STATE parse via `tools/plan_state.parse_plan_state`. Cost via `agents/agent_run_with_metadata.run_with_metadata`.

## Data Contracts Across Sub-Steps

```
2a (CLI + state)
   └─ produces: PlanWeekState, weekforge plan CLI entry, overwrite-confirm gate
2b (Tier-0 context load)
   └─ consumes: settings, PlanWeekState.week_prefix
   └─ produces: PlanWeekDeps payload (templates, feedback_window, plan_state, user_profile, active_flare)
2c (LLM synthesis + HITL)
   └─ consumes: PlanWeekDeps
   └─ produces: WeekPlan (validated structurally by Pydantic), state.last_output, accept decision
2d (validation + persist)
   └─ consumes: WeekPlan
   └─ produces: validated WeekPlan + Notion row update on training_week_summaries
```

## Reference

- [Patterns](../reference/patterns.md) — Planning (Collaborative Shaping), Evaluator-Optimizer (used narrow in 2d)
- [State Schema](../reference/state-schema.md) — Layer A/B/C
- [Failure Modes](../reference/failure-modes.md) — Data & context failures, LLM output failures
- [Prompt Style](../reference/prompt-style.md) — Caveman-lite directive
- `source-material/.claude/commands/plan_week.md` — Legacy authoritative behavior
- `source-material/.claude/shared/session-templates.md` — Session structure conventions
- `source-material/.claude/shared/user-profile.md` — User profile seed
- [step-1-extraction.md](./step-1-extraction.md) — Upstream extraction (provides PLAN_STATE + summaries)
- [Decision Log](../decision-log.md) — DEC-006 (Plan persistence target), DEC-009 (UserProfile shape), DEC-010 (agent naming + prompt extraction)
