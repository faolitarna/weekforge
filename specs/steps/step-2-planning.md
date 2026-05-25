# Step 2: Draft Week (`draft_week`) — Index

## Status
✅ Done — all sub-steps (2-prep, 2a–2d) implemented

## Goal

Build the macro week planner. `weekforge draft-week <week>` loads context (templates + 3-week feedback window + PLAN_STATE + user profile), generates a high-level week plan via Tier-2 agent, runs a HITL collaborative shaping loop, and persists the approved plan onto the matching `training_week_summaries` row's `Plan` rich-text property (DEC-006). Output unlocks step-1's `plan_adherence` extraction and step-3 session generation.

Single command: `weekforge draft-week <week>` handles both macro plan (step-2) and session generation (step-3) as one continuous workflow execution. Checkpoint/resume handles long-running sessions.

Faithfully recreates `source-material/.claude/commands/plan_week.md` in the post-step-1 Weekforge architecture (Tier-0 Python for deterministic context loading + validation, Tier-2 Pydantic AI for plan synthesis).

## Prerequisites

Step 1 complete — extraction subsystem ships `WeekSummary`, `PlanState`, `summarize_week_agent`, prompt composition, `CheckpointStore`/`hitl_confirm`, `RunCost`, Notion gateway (including `fetch_blocks` / `fetch_comments`). Step 2 reuses all of it; step-2-prep extracts shared infrastructure from step-1 code before new feature work begins.

## Sub-Step Sequence

| # | Sub-Step | Focus | Status |
|---|----------|-------|--------|
| 2-prep | [Shared Infrastructure](./step-2-prep-shared-infra.md) | Extract `run_workflow()` runner, `summaries_db` helper, `get_text_prop` to gateway, accept gate, CLI resume registry, drop legacy `"extraction"` alias | ✅ |
| 2a | [CLI, State, Checkpoint](./step-2a-cli-state-checkpoint.md) | `weekforge draft-week <week>` Typer command, `DraftWeekState`, step registry for `draft_week`, overwrite-confirm gate | ✅ |
| 2b | [Context Loading](./step-2b-context-loading.md) | Tier-0: templates by prefix, 3-week feedback window via `summaries_db`, PLAN_STATE load, user profile, `active_flare` derivation | ✅ |
| 2c | [Draft Week Agent + HITL](./step-2c-planning-agent-hitl.md) | `draft_week_agent`, `prompts/draft-week-task.md`, `WeekPlan` output type, accept gate via shared `run_accept_gate` | ✅ |
| 2d | [Validation & Notion Write](./step-2d-validation-and-write.md) | Tier-0 pull:push + conditioning checks with 1-retry re-prompt, `summaries_db.upsert_plan()`, transition to step-3 generation loop | ✅ |

## Decisions

Decisions captured during step-2 facilitator pass (2026-04-26), updated during grill session (2026-05-23).

### Original decisions (DEC-P1..P19)

- **DEC-P1 — Plan persistence target.** Approved plan written into the `Plan` rich-text property on the `training_week_summaries` row matching `week_prefix`. Row created if missing. Body code-block (used by step-1d for summary) stays untouched. Implements DEC-006.
- **DEC-P2 — Workflow style.** Separate file `workflows/draft_week.py`. Step functions registered in a dict, dispatched by shared `run_workflow()` runner (DEC-P25). Runner owns checkpoint saves and cost tracking.
- **DEC-P3 — Agent file naming.** `agents/draft_week_agent.py` (DEC-010 verb_noun convention). Task prompt extracted to `prompts/draft-week-task.md` (no inline LLM text per feedback_prompts_not_in_code).
- **DEC-P4 — LLM profile.** `resolve_llm_profile("reasoning")` per task class. Plan generation is interpretive and multi-constraint; infrequent enough that reasoning cost is acceptable.
- **DEC-P5 — Shared coaching context.** Planner reuses `compose_static_instructions(Prompt.DRAFT_WEEK_TASK, settings.caveman_mode)`. Persona + guardrails + feedback-interpretation + progression-protocol auto-prefixed. New enum entry `Prompt.DRAFT_WEEK_TASK` added.
- **DEC-P6 — User profile injection.** Loaded via `load_user_profile()` as a markdown blob (DEC-009) and injected via `@agent.instructions` decorator, identical pattern to `summarize_week_agent._inject_user_profile`.
- **DEC-P7 — PLAN_STATE consumption.** Loaded via `summaries_db.find_plan_state_row()` (DEC-P26). Typed `PlanState` parsed from raw text. Bootstrap (no PLAN_STATE row) → continue with warning.
- **DEC-P8 — Feedback window.** Previous 3 weeks of `training_week_summaries` rows: read both `Plan` property and body code-block summary per row. No fall-through to raw sessions — step-1 guarantees a summary for any completed week.
- **DEC-P9 — Sequential context loading (no asyncio).** Notion gateway is sync; planning loads ~5 records (1 template query, 3 summary rows, 1 PLAN_STATE row). Sequential is fine.
- **DEC-P10 — HITL accept loop.** Single accept gate via `run_accept_gate()` (DEC-P29). Approve → validate + write Plan. Feedback → replay into next agent run with `message_history`. Quit → checkpoint + resume hint.
- **DEC-P11 — Cost display.** `RunCost` accumulator. Cost summary in HITL panel header and on completion panel.
- **DEC-P12 — Week prefix source.** Derived directly from CLI argument: `f"W{week:02d}"`.
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
- **DEC-P14 — Tier-0 plan validation.** After agent returns, Python counts `focus_tags`. If pull:push < 1.5:1 OR conditioning sessions < 2 → re-prompt agent once with concrete violation diff. Max 1 retry. Then surface to HITL with warning.
- **DEC-P15 — `active_flare` source.** Union of (a) last week `WeekSummary.pain_status` containing any non-empty `JointEntry.status`, AND (b) PLAN_STATE `ACTIVE_ISSUES` section non-empty for SI / spine / joint markers. Either truthy → flag set.
- **DEC-P16 — Bootstrap behavior.** Missing PLAN_STATE OR empty 3-week window → CLI warning, planner proceeds with templates + user profile only.
- **DEC-P17 — Re-plan overwrite gate.** If `training_week_summaries[Week=W##].Plan` is non-empty → HITL confirm before generating. Default = quit (preserve existing).
- **DEC-P18 — No cross-command ordering enforcement.** `weekforge draft-week` and `weekforge summarize-week` stay independent. `summarize_week` already gracefully handles missing Plan.
- **DEC-P19 — Message history persistence.** `DraftWeekState.messages_json: list[dict]` mirrors `SummarizeWeekState.messages_json`.

### New decisions (2026-05-23 grill session)

- **DEC-P20 — Rename plan_week → draft_week.** All references renamed: `workflows/draft_week.py`, `DraftWeekState`, `WORKFLOW = "draft_week"`, `agents/draft_week_agent.py`, `Prompt.DRAFT_WEEK_TASK`, CLI command `weekforge draft-week`. Rationale: "draft" = high-level sketch, "plan/generate" = detailed session work.
- **DEC-P21 — Single command for macro plan + session generation.** `weekforge draft-week <week>` handles both step-2 (macro plan) and step-3 (session generation) as one continuous workflow execution. After plan approval and validation write, workflow transitions to generation loop (step-3). Checkpoint/resume handles the long-running nature.
- **DEC-P22 — Shared plan_state loader.** ~~Extract into `tools/plan_state.load_plan_state()`.~~ Superseded by DEC-P26: plan_state loading now handled by `summaries_db.find_plan_state_row()`.
- **DEC-P23 — Session generation agent naming.** `agents/generate_session_agent.py` with `Prompt.GENERATE_SESSION_TASK`. Clear hierarchy: `draft_week_agent` = macro, `generate_session_agent` = detail.
- **DEC-P24 — Gateway refactor acknowledged.** `notion_api_gateway` now exposes `fetch_blocks()` and `fetch_comments()`. Context loading in 2b uses gateway functions, not raw client. `raw_session_collector` no longer accepts `notion_client` parameter.

### Architecture review decisions (2026-05-23)

- **DEC-P25 — Deep workflow runner.** Extract `workflows/runner.py` with `run_workflow(workflow, state_cls, initial_state, steps, thread_id, store)`. Each workflow provides a step registry (`dict[str, StepFn]`). Runner owns: state restore from checkpoint, `RunCost` accumulation from `state.calls`, `while state.step != "done"` dispatch loop, checkpoint save before each step dispatch (crash safety), `store.delete()` on completion, cost panel. Steps are `Callable[[State, RunCost], str | None]` — return next step name, or `None` for quit (HITL quit). `summarize_week.py` refactored to use runner. `draft_week.py` uses runner from the start.
- **DEC-P26 — Summaries-DB helper module.** Extract `tools/summaries_db.py` with functions that hide query-all + Python-filter + property-extraction: `find_summary_row(week_prefix)`, `find_plan_state_row()`, `read_plan_property(page)`, `upsert_summary(week_prefix, content)`, `upsert_plan(week_prefix, plan_text)`. Subsumes DEC-P22 (`load_plan_state` becomes `find_plan_state_row`). Five inlined call sites across both workflows → five function calls.
- **DEC-P27 — `get_text_prop` to gateway.** Move `_get_text_prop` from `summarize_week.py` to `notion_api_gateway.get_text_prop(page, prop_name)` as a public utility. Generic Notion operation — read plain text from a rich_text property. Used by `summaries_db.py` and any future DB helpers.
- **DEC-P28 — Drop legacy "extraction" workflow alias.** Remove `"extraction"` handling from CLI resume. No in-flight checkpoints exist. Clean cut — runner handles one workflow name per workflow.
- **DEC-P29 — Accept gate helper.** Extract `run_accept_gate()` into `hitl.py`. Parameterized with `render_fn` (content callback) and `approved_step` (target step name on approve). Owns: Rich panel rendering, MAX_ITERATIONS burn warning, `hitl_confirm()` call, approve/feedback/quit branching. Returns `AcceptResult(step, feedback)` — caller sets `state.pending_feedback` from result (gate decoupled from state shape).
- **DEC-P30 — CLI resume registry.** Replace `if/elif` chain in `cli.resume()` with `dict[str, RunnerFn]` mapping workflow name → runner callable. Adding a workflow = one dict entry.
- **DEC-P31 — Shared state base class deferred.** `SummarizeWeekState` and `DraftWeekState` share ~10 fields but differ in `last_output` type (`WeekSummary` vs `WeekPlan`). Base class saves field duplication but adds Pydantic inheritance + discriminator complexity. Step-3 shares `DraftWeekState` (same workflow execution per DEC-P21), so no third state class on the horizon. Revisit if step-4 (`summarize_plan`) introduces a third state model.
- **DEC-P32 — Shared instruction injectors deferred.** `_inject_user_profile` (3 lines) and `_inject_plan_state` (5 lines) duplicated across `summarize_week_agent` and `draft_week_agent`. Sharing requires `RunContext[Any]` (loses type safety) or a Protocol (more code than the duplication). Two agents now, third (`generate_session_agent`) likely has different deps. Copy the decorators. Revisit when three agents share identical injectors.

## Open questions

None.

## Out of scope

- Mesocycle planning (`summarize_plan`) — step-4.
- CLI polish, animations, panel restyling — step-5.
- Async Notion gateway — revisit only if planning latency becomes user-visible.
- New mesocycle bootstrap UI.
- Editing `summarize_week` to consume a structured `WeekPlan`.
- Backfilling `Plan` property for already-summarized weeks.

## Architectural Summary

- **Single command.** `weekforge draft-week <week>` runs macro plan → HITL → validation → Plan write → session generation loop → HITL per session → session writes → done. One workflow file, one checkpoint thread.
- **Shared runner.** Both `summarize_week` and `draft_week` use `run_workflow()` from `workflows/runner.py` (DEC-P25). Each workflow is a step registry dict — no boilerplate loop code. Runner owns checkpoint lifecycle, cost accumulation, crash-safe dispatch.
- **Tier split.** Deterministic work (Notion queries, prefix derivation, `active_flare` boolean computation, ratio counting, markdown rendering) is Tier-0 in 2a/2b/2d. Synthesis (plan composition, adjustments narrative, conflict resolution across signals) is Tier-2 in 2c.
- **HITL shape.** Three gates using shared `run_accept_gate()` (DEC-P29): (1) overwrite-confirm in 2a (direct `hitl_confirm`), (2) accept-plan loop in 2c, (3) per-session accept loop in step-3 generation. Validation auto-retry in 2d is pre-HITL.
- **Prompt composition.** `draft_week_agent` uses `compose_static_instructions(Prompt.DRAFT_WEEK_TASK, ...)`. `@agent.instructions` decorators inject user profile, templates, feedback window, PLAN_STATE, `active_flare` flag at run time.
- **Reused infrastructure.** Notion CRUD via `tools/notion_api_gateway`. Summaries-DB access via `tools/summaries_db` (DEC-P26). Cost via `agents/agent_run_with_metadata.run_with_metadata`. CLI resume via workflow registry (DEC-P30).

## Data Contracts Across Sub-Steps

```
2a (CLI + state)
   └─ produces: DraftWeekState, weekforge draft-week CLI entry, overwrite-confirm gate
2b (Tier-0 context load)
   └─ consumes: settings, DraftWeekState.week_prefix
   └─ produces: DraftWeekDeps payload (templates, feedback_window, plan_state, user_profile, active_flare)
2c (LLM synthesis + HITL)
   └─ consumes: DraftWeekDeps
   └─ produces: WeekPlan (validated structurally by Pydantic), state.last_output, accept decision
2d (validation + persist)
   └─ consumes: WeekPlan
   └─ produces: validated WeekPlan + Notion row update on training_week_summaries
   └─ transitions to: step-3 generation loop (same workflow execution)
```

## Reference

- [Patterns](../reference/patterns.md) — Planning (Collaborative Shaping), Evaluator-Optimizer (used narrow in 2d)
- [State Schema](../reference/state-schema.md) — Layer A/B/C
- [Failure Modes](../reference/failure-modes.md) — Data & context failures, LLM output failures
- [Prompt Style](../reference/prompt-style.md) — Caveman-lite directive
- `source-material/Claude.md` — Legacy coaching persona and guardrails
- [step-1-extraction.md](./step-1-extraction.md) — Upstream extraction (provides PLAN_STATE + summaries)
- [Decision Log](../decision-log.md) — DEC-006 (Plan persistence target), DEC-009 (UserProfile shape), DEC-010 (agent naming + prompt extraction)
