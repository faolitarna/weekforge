# Step 2d: Validation & Notion Write

## Status
ready

## Goal

Two responsibilities, both narrow:

1. **Tier-0 plan validation with single re-prompt.** After agent returns `WeekPlan`, count `focus_tags` to compute pull:push ratio + conditioning session count. If thresholds violated, re-prompt agent once with concrete violation text. Then accept the result regardless (HITL surfaces a warning if the second attempt also violates).
2. **Idempotent Notion write.** Persist approved plan into `training_week_summaries[Week=week_prefix].Plan` rich-text property. Create row if absent. Body code-block untouched.
3. **Transition to step-3.** After Plan write, workflow transitions to session generation loop (DEC-P21). Single `weekforge draft-week` command handles both macro plan and session generation.

## Decisions

- **Validation thresholds (DEC-P14):**
  - Pull:push ratio. Sessions tagged `pull` (not `push`) count as pull. Sessions tagged `push` (not `pull`) count as push. Sessions tagged both → 0.5 each. Threshold: `pull_count / push_count >= 1.5`. If `push_count == 0` → satisfied.
  - Conditioning floor. Sessions whose `focus_tags` contains any of `cardio`, `z1`, `z2`, `z3`, `uphill`, `loaded`, `hike`, `run`. Threshold: `>= 2`.
- **Validation lives where:** `validate` step between `accept` and `write` in `workflows/draft_week.py`.
- **Retry guard:** `state.validation_retry_used: bool = False`. Flow:
  ```
  agent → accept (approve) → validate
    pass → write
    fail (first time) → state.pending_feedback = diff; step = agent
    fail (second time) → state.validation_warning = diff; step = accept (re-render with warning, user decides)
  ```
- **Re-prompt diff format:** `f"Plan validation failed. Issues: pull:push={p2p_ratio:.1f}:1 (need >=1.5:1), conditioning_sessions={cond_count} (need >=2). Revise the plan to fix these specifically. Keep all other constraints intact."`
- **Notion write (`write` step, DEC-P1):**
  - Call `summaries_db.upsert_plan(week_prefix, rendered)` (DEC-P26). Hides: query + filter + create-or-update + title property lookup.
  - `rendered = render_week_plan(state.last_output)` (renderer from 2c).
  - Plan stored as plain text in rich-text property (not code block). Body content untouched.
- **Idempotency.** Final-state idempotent: `upsert_plan` produces same row state on re-run. Overwrite-confirm in 2a guards accidental re-writes.
- **Final transition (DEC-P21):** `write → generate_sessions` (step-3 loop, same workflow execution). Cost panel printed at write boundary, then workflow continues into session generation. `done` only reached after all sessions generated. If step-3 not yet implemented, `write → done` with cost panel + completion message.

## Open questions

None.

## Inputs

- `state.last_output: WeekPlan` — from 2c agent
- `state.validation_retry_used: bool` — retry guard
- `settings.notion_db_training_week_summaries` — DB ID

## Outputs

- `state.written_page_id: str` — Notion page ID of written/updated row
- `state.validation_warning: str | None` — warning text if validation failed twice
- Side-effect: Notion row updated with Plan rich-text property
- Side-effect: workflow transitions to step-3 generation loop (or `done` if step-3 not implemented)

## Files

- `src/weekforge/workflows/draft_week.py`: edit — add `validate` + `write` steps, transition logic
- `src/weekforge/models/workflow_state.py`: edit — `validation_retry_used`, `validation_warning` fields (already specified in 2a)

## Data contracts

### Validator function

```python
def validate_week_plan(plan: WeekPlan) -> tuple[bool, str | None]:
    """Returns (passed, violation_diff_or_none)."""
```

### Validation state fields (on `DraftWeekState`)

```python
validation_retry_used: bool = False
validation_warning: str | None = None
```

### Notion write contract

- Via `summaries_db.upsert_plan(week_prefix, rendered)` (DEC-P26)
- Hides: property targeting, key filtering, create-or-update logic
- Content: `render_week_plan(state.last_output)` as plain text

## Workflow

1. Enter `validate` step (from `accept` approval).
2. Call `validate_week_plan(state.last_output)`.
3. If passed → return `"write"`.
4. If failed, first time (`not state.validation_retry_used`):
   - `state.validation_retry_used = True`
   - `state.pending_feedback = violation_diff`
   - Return `"agent"` (re-prompt via 2c loop)
5. If failed, second time:
   - `state.validation_warning = violation_diff`
   - Return `"accept"` (re-render with warning, user decides)
6. Enter `write` step.
7. Render plan: `rendered = render_week_plan(state.last_output)`.
8. Call `summaries_db.upsert_plan(week_prefix, rendered)` (DEC-P26).
9. `state.written_page_id = page_id`.
10. Return `"done"` (or `"generate_sessions"` when step-3 implemented). Runner handles checkpoint cleanup and cost panel.

## Tier split

- Tier 0: validator (counts, ratio math), Notion query/update/create, renderer call, transition logic
- Tier 1: —
- Tier 2: — (re-prompt reuses `draft_week_agent` from 2c)

## Failure modes

- Validation passes first attempt → write directly.
- Validation fails first attempt → one re-prompt; advance regardless of second outcome.
- Validation fails twice → loop to `accept` with warning panel; user override only path forward.
- Notion 4xx on write → existing `notion_api_gateway` error mapping. Crash-safe: `validate` checkpoint precedes `write`; resume re-tries write idempotently.
- Title property missing on summaries DB → existing `get_title_property_name` fallback path.
- Plan text exceeds Notion rich-text 2000 char limit → truncate with `[truncated]` marker and log warning.

## Acceptance criteria

- [ ] Validation correctly computes pull:push ratio from `focus_tags`
- [ ] Validation correctly counts conditioning sessions
- [ ] First validation failure triggers agent re-prompt with concrete diff
- [ ] Second validation failure surfaces warning to HITL, does not auto-fail
- [ ] `validation_retry_used` guard prevents infinite loop
- [ ] Notion row created if absent, updated if present
- [ ] Plan written as plain text to `Plan` rich-text property (not code block)
- [ ] Body code-block content (from step-1d) not corrupted by Plan write
- [ ] Idempotent: re-running write produces same row state
- [ ] Cost summary panel printed at write boundary

## Out of scope

- Step-3 session generation loop (implemented in step-3 spec, invoked from `draft_week` workflow after Plan write).
- Backfilling Plan for already-summarized historical weeks.
- Tightening `focus_tags` vocabulary post-launch — defer to step-5.
- Analytics on validation failure rate.

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P1, P14, P21
- [step-2c-planning-agent-hitl.md](./step-2c-planning-agent-hitl.md) — `WeekPlan` schema, renderer
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — `write` step pattern
- [tools/notion_api_gateway.py](../../src/weekforge/tools/notion_api_gateway.py) — `query`, `update`, `create`, `get_title_property_name`
- [Decision Log](../decision-log.md) — DEC-006
