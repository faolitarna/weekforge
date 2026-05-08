# Step 2d: Validation & Notion Write

## Status
ready (facilitator pass — contract sections to be filled by specs-developer)

## Goal

Two responsibilities, both narrow:

1. **Tier-0 plan validation with single re-prompt.** After agent returns `WeekPlan`, count `focus_tags` to compute pull:push ratio + conditioning session count. If thresholds violated, re-prompt agent once with concrete violation text. Then accept the result regardless (HITL surfaces a warning if the second attempt also violates).
2. **Idempotent Notion write.** Persist approved plan into `training_week_summaries[Week=week_prefix].Plan` rich-text property. Create row if absent. Body code-block (used by step-1d for summary) untouched.

## Decisions

- **Validation thresholds (DEC-P14):**
  - Pull:push ratio. Numerator = sessions where `focus_tags` contains `pull` (and not `push`). Denominator = sessions where `focus_tags` contains `push` (and not `pull`). Sessions tagged with both → counted half each (legacy "balanced" treatment, e.g., "Push + Hinge" → 0.5 push, "Pull + Squat" → 0.5 pull). Threshold: `pull_count / push_count >= 1.5`. If `push_count == 0` → ratio considered satisfied.
  - Conditioning floor. Count sessions whose `focus_tags` contains any of `cardio`, `z1`, `z2`, `z3`, `uphill`, `loaded`, `hike`, `run`. Threshold: `>= 2`.
- **Validation lives where:** new step `validate` between `accept` and `write` in `workflows/plan_week.py`. Inputs: `state.last_output: WeekPlan`. Output: passes through to `write` OR sets `state.pending_feedback = "<violation diff>"; state.step = "agent"; state.validation_retry_used = True` (one-shot guard prevents infinite loop).
- **Retry guard:** new field `validation_retry_used: bool = False` on `PlanWeekState`. After one retry the validate step accepts the result regardless and advances to `write`, but stamps a `validation_warning: str | None` field that the accept panel surfaces on the next iteration's HITL render — UX twist: if the second attempt still violates, the workflow loops back to `accept` for human override (NOT directly to `write`). Flow:
  ```
  agent → accept (approve) → validate
    pass → write
    fail (first time) → state.pending_feedback = diff; step = agent
    fail (second time) → state.validation_warning = diff; step = accept (re-render with warning, user decides)
  ```
- **Re-prompt diff format:** `f"Plan validation failed. Issues: pull:push={p2p_ratio:.1f}:1 (need >=1.5:1), conditioning_sessions={cond_count} (need >=2). Revise the plan to fix these specifically. Keep all other constraints intact."`
- **Notion write (`write` step, DEC-P1):**
  - Query `training_week_summaries`, find row where `Week == week_prefix` (Python filter — pattern from `summarize_week.write` step).
  - If row exists → `notion.update(page_id, properties={"Plan": {"rich_text": [{"text": {"content": rendered}}]}})`. Body content untouched.
  - If row absent → `notion.create(database_id=settings.notion_db_training_week_summaries, properties={"Week": ..., title_prop: ..., "Plan": ..., }, content="")`. Empty content for body — step-1d will fill it later.
  - `rendered = render_week_plan(state.last_output)` (the Tier-0 renderer from 2c).
  - Plan stored as plain text, NOT a code block (rich-text property limitation, and step-1's `_get_text_prop("Plan")` reads it as plain text).
- **Idempotency.** Final-state idempotent: re-running `weekforge plan W##` after a successful write produces the same row (overwrite-confirm in 2a guards against accidental re-writes). No staging, no conflict resolution.
- **Property name confirmation.** `Plan` rich-text property must exist on the `training_week_summaries` data source. Step-1d already reads `Plan` via `_get_text_prop`. Step-2d is the writer. Acceptance criteria assert the round-trip.
- **Final transition:** `write → done`. `cost.summary()` panel printed. `store.delete(thread_id)`.

## Open questions

None.

## Inputs

(specs-developer to fill — `state.last_output: WeekPlan`, settings)

## Outputs

(specs-developer to fill — `state.written_page_id`, side-effect: Notion row updated)

## Files

(specs-developer to fill — expected: workflows/plan_week.py [edit, add validate + write steps], models/workflow_state.py [edit, add validation_retry_used + validation_warning fields])

## Data contracts

(specs-developer to fill — validator function signature, retry/warning state fields, write step contract)

## Workflow

(specs-developer to fill — explicit `accept → validate → (agent | write | accept)` paths)

## Tier split

- Tier 0: validator (counts, ratio math), Notion query/update/create, renderer call
- Tier 1: —
- Tier 2: — (re-prompt is still the same `plan_week_agent` from 2c)

## Failure modes

- Validation passes first attempt → write directly.
- Validation fails first attempt → one re-prompt; advance regardless of second outcome.
- Validation fails twice → loop to `accept` with warning panel; user override only path forward.
- Notion 4xx on write → existing `notion_api_gateway` error mapping. Crash-safe: `validate` checkpoint precedes `write`; resume re-tries write idempotently.
- Title property missing on summaries DB → existing `get_title_property_name` fallback path.

## Acceptance criteria

(specs-developer to fill — must produce row with non-empty Plan, must respect validation retry guard, must idempotently re-run, must not corrupt body code-block from step-1d)

## Out of scope

- Step-3 generation handoff (`weekforge plan` ends at `done`; user invokes `weekforge draft` separately in step-3).
- Backfilling Plan for already-summarized historical weeks.
- Tightening `focus_tags` vocabulary post-launch — defer to step-5.
- Analytics on validation failure rate — defer.

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P1, P14
- [step-2c-planning-agent-hitl.md](./step-2c-planning-agent-hitl.md) — `WeekPlan` schema, renderer
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — `write` step pattern (lines 244-280)
- [tools/notion_api_gateway.py](../../src/weekforge/tools/notion_api_gateway.py) — `query`, `update`, `create`, `get_title_property_name`
- [Decision Log](../decision-log.md) — DEC-006
