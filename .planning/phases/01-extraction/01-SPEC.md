# Phase 01: Extraction — Specification

**Created:** 2026-04-19
**Ambiguity score:** 0.117 (gate: ≤ 0.20)
**Requirements:** 6 locked

## Goal

`weekforge summarize-week <N>` completes end-to-end: collects raw Notion session data, produces an LLM-synthesized `WeekSummary`, presents highlights in a HITL accept gate with a capped feedback loop, then writes the approved summary and updates PLAN_STATE in Notion.

## Background

Step 1a is complete: CLI stub, context loading (coaching persona, guardrails, user profile) all work. `run_summarize_week` currently raises `NotImplementedError` at `summarize_week.py:54` — no actual generation exists. Steps 1b, 1c, and 1d are all unimplemented. No `WeekSummary` model, no extraction, no Notion write-back.

Training sessions are written by LLM and have consistent `to_do` block + heading structure in Notion. User feedback arrives as free-text page comments — multiple per session, unstructured, varying by session type (gym, climbing, hiking). All semantic interpretation belongs to the LLM.

## Requirements

1. **Raw session collection**: Fetch all Notion session pages for the week into a `RawWeekData` bundle.
   - Current: No collection logic exists — `run_summarize_week` has a stub after context loading
   - Target: `assemble_raw_week(week_prefix, ...)` returns `RawWeekData` with one `RawSession` per Notion page, all `to_do` + heading blocks captured, all page comments collected, `ImplicitFeedback` checkbox arithmetic computed
   - Acceptance: For a week with N known session pages, `len(raw_week.sessions) == N` and all sessions have non-empty `blocks` lists; `ImplicitFeedback.total_exercises` equals the actual `to_do` block count

2. **LLM extraction**: `summarize_agent` fills all narrative fields of `WeekSummary` from raw session data.
   - Current: No `summarize_agent` or `WeekSummary` model exist
   - Target: Pydantic AI agent with static instructions (coaching persona + guardrails) and dynamic instructions (user profile + Tier-0 facts) fills: `context`, `issues`, `wins`, `recommendations_next`, `highlights` (3–5 bullets), `trend`, `sessions`, `exercise_log`, `cardio_log`, `climbing_log`, `pain_status`, `plan_adherence`
   - Acceptance: Agent run returns a `WeekSummary` instance that passes `model_validate(summary.model_dump())`; `highlights` has 3–5 items; no field that the agent is responsible for is left at its default empty value for a session with real data

3. **HITL accept gate with feedback loop**: User reviews highlights and accepts or provides feedback; feedback loop is capped at 3 iterations.
   - Current: No HITL gate exists in the summarize-week flow
   - Target: Terminal panel shows `highlights`; user chooses accept or types feedback; feedback triggers LLM re-run using original `RawWeekData` as ground truth (not prior LLM output); loop cap is 3 iterations; on the 3rd iteration user is warned that further iterations burn tokens and a final accept is requested
   - Acceptance: Scripted test with 2 feedback rounds then accept completes without error; scripted test that provides feedback 3 times triggers the token-burn warning on the 3rd; accepted `WeekSummary` is the one passed to the write step

4. **Notion summary write**: Approved `WeekSummary` is rendered to legacy format and written to `training_week_summaries` DB.
   - Current: No write logic exists; `training_week_summaries` rows are either pre-created by step-2 (future) or absent
   - Target: Renderer produces the legacy `WEEK_SUMMARY` text block; write path updates existing row if `Week == week_prefix` exists, creates new row if absent (logs warning on create — delta analysis unavailable); page body set to rendered text in a code block
   - Acceptance: After a run against a test week, a `training_week_summaries` row with `Week=W##` exists and its `Summary` property contains the rendered text; re-running the command offers overwrite confirmation

5. **PLAN_STATE update**: Cumulative plan tracker updated with new week's data.
   - Current: No PLAN_STATE logic exists
   - Target: `training_week_summaries` row with `Week="PLAN_STATE"` updated via incremental merge (mechanical: append weights, increment `weeks_completed`, recalculate `avg_completion`) + LLM interpretation (issue lifecycle, trend direction per lift); bootstrapped if row absent
   - Acceptance: After run, PLAN_STATE row exists with `weeks_completed` incremented by 1; `avg_completion` reflects the new week; week appears in weekly adherence trend

6. **Abort and resume**: User can interrupt at any point and resume from the last checkpoint.
   - Current: `CheckpointStore` exists and is wired to the CLI; `summarize-week` flow has no checkpoint steps
   - Target: Checkpoints written at: post-collection, post-LLM-run, post-HITL-accept, post-write; Ctrl+C at any point saves state; `weekforge resume` restores to the last completed checkpoint step
   - Acceptance: Simulated interrupt after HITL accept followed by `resume` skips re-collection and re-extraction and proceeds directly to write step; simulated interrupt during HITL followed by `resume` re-presents the accept gate with previous LLM output

## Boundaries

**In scope:**
- `RawWeekData` bundle: block + comment collection, checkbox arithmetic (`ImplicitFeedback`)
- `WeekSummary` Pydantic model (output contract for LLM)
- `summarize_agent`: Pydantic AI agent, static + dynamic instructions, `output_type=WeekSummary`
- `extraction.py` workflow: orchestrates collection → LLM → HITL → write → PLAN_STATE
- HITL accept panel with 3-iteration cap and token-burn warning
- Legacy `WEEK_SUMMARY` renderer
- Notion write: create/update `training_week_summaries` row
- PLAN_STATE: incremental merge (Tier-0) + LLM interpretation of issue lifecycle and lift trends
- Checkpoint integration: abort + resume at all major steps

**Out of scope:**
- `plan_week` command — Phase 02
- `draft_session` command — Phase 03
- `summarize_plan` mesocycle analysis — Phase 04
- Pre-creating the `training_week_summaries` row before `summarize-week` runs — that is step-2's job; step-1d handles the absent-row fallback
- Backfilling multiple weeks in a single invocation — single-week only
- Push notifications or any output beyond the terminal HITL panel

## Constraints

- HITL feedback loop: max 3 iterations; warn on 3rd that further re-runs burn tokens
- LLM re-runs use original `RawWeekData` as ground truth, not prior `WeekSummary` output — feedback is appended context, not a replacement prompt
- PLAN_STATE is a singleton row in `training_week_summaries` with `Week="PLAN_STATE"` — no separate DB
- LLM: Pydantic AI with OpenAI backend via existing `openai_model_factory.py`
- Notion: all reads/writes via existing `notion_api_gateway.py` — no direct HTTP calls
- Checkpoints via existing `CheckpointStore` (SQLite) — no new persistence mechanism

## Acceptance Criteria

- [ ] `weekforge summarize-week 7` completes end-to-end without raising `NotImplementedError`
- [ ] `len(raw_week.sessions)` equals the number of Notion session pages for the week
- [ ] `WeekSummary.highlights` has 3–5 items after LLM run
- [ ] HITL panel displays highlights; user can accept or type feedback
- [ ] Providing feedback 2× then accepting completes successfully
- [ ] Providing feedback 3× triggers token-burn warning on the 3rd round
- [ ] After accept, `training_week_summaries` row with `Week=W##` exists with rendered summary
- [ ] Re-running `summarize-week` for same week prompts overwrite confirmation
- [ ] PLAN_STATE row has `weeks_completed` incremented after run
- [ ] Interrupt after HITL accept + `resume` skips to write step without re-running LLM
- [ ] `uv run pytest tests/` passes (all existing tests continue to pass)

## Ambiguity Report

| Dimension           | Score | Min  | Status | Notes                                              |
|---------------------|-------|------|--------|----------------------------------------------------|
| Goal Clarity        | 0.92  | 0.75 | ✓      | End-to-end flow fully defined                      |
| Boundary Clarity    | 0.90  | 0.70 | ✓      | Out-of-scope phases explicit; row pre-creation excluded |
| Constraint Clarity  | 0.80  | 0.65 | ✓      | 3-iteration cap, ground truth pinned, tooling locked |
| Acceptance Criteria | 0.88  | 0.70 | ✓      | 11 pass/fail criteria covering all requirements    |
| **Ambiguity**       | 0.117 | ≤0.20| ✓      |                                                    |

## Interview Log

| Round | Perspective     | Question summary                        | Decision locked                                              |
|-------|-----------------|-----------------------------------------|--------------------------------------------------------------|
| 1     | Researcher      | What does done look like end-to-end?    | CLI → collect → LLM → HITL → write to Notion + PLAN_STATE   |
| 2     | Simplifier      | How does HITL feedback loop work?       | Feedback appended, re-run LLM with original raw data as GT   |
| 3     | Boundary Keeper | Max iterations? Abort/resume?           | Max 3 iterations, warn on 3rd; Ctrl+C + resume via checkpoint|

---

*Phase: 01-extraction*
*Spec created: 2026-04-19*
*Next step: /gsd-discuss-phase 01 — implementation decisions (how to build what's specified above)*
