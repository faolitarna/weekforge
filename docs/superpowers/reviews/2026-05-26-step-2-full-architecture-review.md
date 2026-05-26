# Step 2 Architecture Review

> Reviewed: 2026-05-26 | Range: `43edc28..HEAD` | 39 files, ~9500 lines | Result: **4/5, ready for step 3 with changes**

## Executive Summary

Well-structured implementation with clean shared infrastructure, rigorous Tier 0/2 split, and reusable patterns across both workflows. Main issues: duplicated context loading between `_step_load_context` and `_step_agent` doubling Notion API calls, `summaries_db.find_summary_row` doing a full table scan per call, and `DraftWeekDeps`/`derive_active_flare` living in the agent module instead of a domain module (blocks step 3 reuse).

## Architecture Analysis

### Module Decomposition

Clean and consistent with step 1. Each file has a single responsibility:

- `workflows/draft_week.py` — orchestration only, no domain logic
- `agents/draft_week_agent.py` — agent definition + instruction composition
- `tools/week_plan_validator.py` — pure Tier-0 validation
- `tools/week_plan_renderer.py` — formatting for HITL display and Notion write
- `tools/summaries_db.py` — shared Notion DB access layer
- `models/week_plan.py` — domain model
- `models/workflow_state.py` — workflow-scoped state

`summaries_db` extraction (step-2-prep) was the right call — both workflows share `find_summary_row`, `find_plan_state_row`, `upsert_summary`, and `upsert_plan`.

One concern: `draft_week_agent.py` holds the agent definition AND `DraftWeekDeps`/`WeekFeedbackRow` AND `derive_active_flare`. That's three concerns. When step 3 needs flare derivation, importing from the agent module to get a utility function creates coupling that should not exist.

### Step Function Pattern

`workflows/runner.py` is elegant — 63 lines, generic over state type, handles checkpoint save-before-dispatch, resume, and done cleanup. The "step returns next step name, or None to pause" design is simple and effective.

One subtle point: `state.step` is a plain string with no validation — a typo in a step return value creates a runtime error only on the next loop iteration.

### State Management (Layer A/B/C)

`DraftWeekState` partially violates Layer B's "not carried forward" principle — `plan_state_raw` and `plan_state_page_id` survive checkpoints. Pragmatic choice (avoids re-fetching from Notion on every agent retry).

More concerning: `_step_agent` reconstructs the ENTIRE context — re-queries templates, re-scans feedback window, re-parses plan state, re-loads user profile — even though `_step_load_context` already did this. Result: template queries and feedback window scans happen twice on every fresh run.

### Tier 0/2 Split

Rigorous. All deterministic work (validation, rendering, context loading, checkpoint management) is pure Python. LLM invoked exactly once per agent call. The `FocusTag` literal type makes the tag vocabulary a compile-time constraint the LLM must respect via Pydantic AI's structured output.

## Strengths

1. **Checkpoint crash safety.** `runner.py:49` saves BEFORE dispatch. `hitl.py:44` saves BEFORE rendering prompt. Any crash leaves a resumable checkpoint.
2. **`run_accept_gate` reuse.** Both `summarize_week` and `draft_week` use it identically. Clean parameterization.
3. **Validator is pure and exhaustively tested.** Zero dependencies beyond model. 252 lines of tests cover dual-tagged sessions, edge cases, multi-violation reporting.
4. **Instruction decorator pattern.** 6 decorators in `draft_week_agent.py` each return a string, composing naturally. More maintainable than monolithic instructions.
5. **Overwrite check is user-friendly.** Previews first 10 lines, defaults to quit (preserving data).
6. **State serialization round-trip tested.** `WeekPlan` with all 20 tag types survives JSON through `DraftWeekState`.
7. **Prompts externalized.** `prompts/draft-week-task.md` follows `feedback_prompts_not_in_code` convention.

## Issues

### Important (Should Fix)

**I-1. Duplicated context loading between `_step_load_context` and `_step_agent`.**

- Files: `draft_week.py:27-92` and `draft_week.py:95-155`
- Both steps query templates, scan feedback window, load plan state, load user profile
- Doubles Notion API calls on every fresh run (6-8 calls per run)
- **Fix:** Merge `_step_load_context` into `_step_agent` (recommended) or cache results on state

**I-2. `summaries_db.find_summary_row` performs full table scan every call.**

- File: `summaries_db.py:7-14`
- Called 6-8 times per run, each fetching all rows from Notion
- Will compound in step 3
- **Fix:** Batch-fetch all summaries once, or use Notion filter API server-side

**I-3. `DraftWeekDeps`, `WeekFeedbackRow`, `derive_active_flare` live in agent module.**

- File: `agents/draft_week_agent.py`
- These are Tier-0 domain logic, not agent concerns
- Step 3 will need them but shouldn't import from agents/
- **Fix:** Move to `tools/planning_context.py` or `models/planning_deps.py`

### Minor (Nice to Have)

**M-1.** `render_week_plan` omits focus tags — showing them would help users understand validation outcomes.

**M-2.** `hitl_confirm` hard-codes `choices = ["a", "f", "q"]` — overwrite gate should restrict to `["a", "q"]`.

**M-3.** Resume passes empty string for `week_prefix` (`cli.py:140`) — would produce obscure error if checkpoint missing.

**M-4.** `_extract_prop_text` in `draft_week_agent.py` duplicates Notion property reading logic that should live in the gateway.

**M-5.** `started_at` field on both state models is unused dead weight.

## Recommendations for Step 3

1. **Factor out `DraftWeekDeps`/`derive_active_flare` from agent module** — step 3 needs them
2. **Add batch-fetch helper to `summaries_db`** — step 3 generates 8-12 sessions, can't afford full-scan per call
3. **Runner is ready as-is** — generic `S` type + string dispatch scales without changes
4. **Decide: continuation of `draft_week` or separate workflow?** — spec says single command, which means new steps after "write" on `DraftWeekState`
5. **Add session count validation** — `WeekPlan` allows empty sessions, step 3 would silently produce nothing
6. **Add `duration_min > 0` validation** — before step 3 generates content based on duration

## Assessment

**Architecture quality: 4/5**

Clean design, good shared infrastructure, consistent patterns. Main deduction for duplicated context loading (I-1) which doubles API calls and will compound in step 3.

**Ready for step 3: With changes**

Fix I-1 + I-2 (eliminate duplicate loads, batch Notion queries) and I-3 (factor deps out of agent module) before step 3.
