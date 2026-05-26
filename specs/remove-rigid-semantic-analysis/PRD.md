# PRD: Remove Rigid Semantic Analysis from Workflows

**Status**: ready-for-agent
**Date**: 2026-05-26

## Problem Statement

Rigid Python code performs semantic interpretation (regex matching, substring classification, hardcoded thresholds) on training data, then injects results as "ground truth" into LLM prompts. When the rigid analysis is wrong — which happens whenever text doesn't match expected patterns — it overrides the model's correct interpretation of the same raw data.

The most visible failure: `derive_active_flare()` regex-matches against `PLAN_STATE.active_issues` and recent summary text. A stale entry like `"SI joint:W03:resolved"` triggers `ACTIVE_FLARE: YES`, causing conservative programming even when three clean weeks show no pain. The model already has the data to make this judgment correctly, but the boolean flag overrides it.

## Solution

Apply the principle: **arithmetic stays in Python, semantic interpretation goes to the LLM.**

Remove four rigid analysis points:
1. **Active flare boolean** — delete entirely. The draft agent already receives PLAN_STATE with ACTIVE_ISSUES. Replace the boolean with prompt guidance teaching the model how to reason about pain severity and recency.
2. **Section heading classification** — replace substring matching (`"warmup" in lower`) with a single fast-LLM call that classifies all unique headings in one batch. Falls back to current logic on API failure.
3. **Skip pattern thresholding** — keep the arithmetic (per-exercise checked/total counts), delete the thresholds (`skip_rate > 0.5`) and `frequently_skipped`/`always_completed` labels. Pass raw stats to the summarize agent with prompt guidance on how to interpret them.
4. **Signal exercise filtering** — delete `_filter_week_for_plan_state()` which decides what training data the plan_state agent sees. Pass the full `WeekSummary` instead (excluding only LLM-meta fields).

Deterministic analysis that works correctly is kept: completion counting, session status booleans, mechanical updates (weight chains, averages), pull/push ratio validator, conditioning floor validator, Notion rendering compression.

## User Stories

1. As a user with a resolved SI joint entry in PLAN_STATE, I want the draft agent to read ACTIVE_ISSUES and determine no active pain exists, so that my plan isn't unnecessarily conservative.
2. As a user with moderate+ active pain, I want the draft agent to detect it from PLAN_STATE context and apply symptom protocol, so that I don't train through injury.
3. As a user with non-standard session headings (e.g., "Activation", "Finisher", "Prep Work"), I want section classification to correctly categorize them, so that section completion rates are accurate.
4. As a user whose LLM API is temporarily down, I want section classification to fall back to substring matching, so that the workflow doesn't fail entirely.
5. As a user who skipped an exercise once out of two occurrences, I want the summarize agent to use its judgment on whether that's meaningful, so that one-off skips aren't flagged as patterns.
6. As a user who skipped an exercise 4 out of 5 times, I want the summarize agent to identify that as a real pattern, so that future plans can adapt.
7. As a user with bodyweight exercises that have no weight data, I want those exercises to still reach the plan_state agent, so that training context isn't silently dropped.
8. As a user reviewing a week summary, I want per-exercise raw stats (checked/total) included as data, so that the LLM can reason about skip patterns with full context.
9. As a user with an empty ACTIVE_ISSUES section, I want the draft agent to program at normal intensity, so that no false conservatism is applied.
10. As a user running the draft-week workflow, I want pain-aware programming decisions explained in the adjustments list, so that I can see why intensity was modified.
11. As a developer, I want section classification to batch all unique headings in one LLM call, so that API costs stay minimal (one fast call per workflow run, not one per heading).
12. As a developer, I want `ImplicitFeedback` to contain only raw counts, so that the model boundary between arithmetic and interpretation is clear.

## Implementation Decisions

- **Delete, don't deprecate.** `derive_active_flare()`, `has_active_pain()`, `_PAIN_KEYWORDS` (both in plan_state.py and context_loader.py), `_classify_section()`, `_SECTION_LABELS`, `SkippedPattern`, `frequently_skipped`, `always_completed`, `_filter_week_for_plan_state()` are all removed outright. No compatibility shims.
- **`active_flare` field removed from three places:** `DraftWeekDeps` dataclass, `DraftWeekState` model, `WeekDraftContext` dataclass. All callers updated.
- **Pain-aware prompt replaces boolean.** The draft-week-task prompt gets a reasoning framework: inspect PLAN_STATE → ACTIVE_ISSUES, assess severity and recency, apply symptom protocol only when moderate+ pain persists. This is stronger than the boolean because the model can distinguish "resolved" from "severe" and "1 week ago" from "ongoing."
- **Section classification uses `resolve_llm_profile("fast")`.** One batch call with structured output `dict[str, Literal["warmup", "main", "cooldown"]]`. All unique headings classified together. Falls back to substring matching on any API failure (logged as warning).
- **`classify_sections()` lives in `raw_session_collector.py`.** It's tightly coupled to `compute_checkbox_analysis()` which is its only consumer. Integration point: `load_week_summarize_context()` in `context_loader.py` calls it before passing the map to `compute_checkbox_analysis()`.
- **`ExerciseCheckStats` replaces `SkippedPattern`.** New model: `exercise: str, checked: int, total: int`. Raw data, no thresholds. `ImplicitFeedback` gets `exercise_stats: list[ExerciseCheckStats]` replacing both `frequently_skipped` and `always_completed`.
- **`_filter_week_for_plan_state()` replaced with `model_dump_json()`.** Exclude `implicit_feedback`, `highlights`, `trend`, `recommendations_next` (LLM-meta fields). Everything else reaches the plan_state agent.
- **Inline prompt for section classification.** It's a micro-classification task (3 categories, ~10 headings). Not worth a separate prompt file — goes directly in the `classify_sections()` function.
- **Tier 1 is now real.** `CONTEXT.md` needs updating: Tier 1 = fast/cheap LLM for micro-classification (previously "defined but not yet implemented").

## Testing Decisions

Tests should verify external behavior — given inputs, what outputs or side effects occur. Don't test internal implementation details (private helpers, intermediate data structures).

**Modules to test (new behavior only):**

- **`classify_sections()`** — mock the LLM call, verify heading → category mapping for standard and non-standard headings. Test fallback: mock API failure, verify substring matching produces result and logs warning.
- **`ExerciseCheckStats` population** — verify `compute_checkbox_analysis()` produces raw per-exercise `checked`/`total` counts without thresholding. Existing checkbox counting tests updated to assert on `exercise_stats` instead of `frequently_skipped`/`always_completed`.
- **Pain-aware prompt content** — verify the draft-week-task prompt contains ACTIVE_ISSUES reasoning guidance and does NOT contain ACTIVE_FLARE references.
- **Filter removal verification** — verify `update_plan_state_agent` passes full WeekSummary (minus excluded fields) rather than filtered signal exercises.

**Prior art:** `tests/tools/test_raw_session_collector.py` (checkbox analysis tests), `tests/agents/test_draft_week_agent.py` (instruction composition tests), `tests/tools/test_context_loader.py` (context building tests).

**Tests to delete:** All `derive_active_flare` tests, `has_active_pain` tests, `frequently_skipped`/`always_completed` threshold tests, active_flare context-loading tests. Pure deletions — these test behavior that no longer exists.

## Out of Scope

- **Rewriting the summarize-week agent prompt.** Only adding guidance for `exercise_stats` interpretation. The agent's core summarization logic is unchanged.
- **Changing the pull/push ratio validator or conditioning floor validator.** These operate on LLM-generated tags from a controlled vocabulary — they're legitimate Tier 0 guardrails, not semantic interpretation.
- **Changing `apply_mechanical_update` or completion counting.** Pure arithmetic stays.
- **Changing `_is_signal_entry` in the renderer.** UX compression for Notion display, not agent input.
- **Adding new LLM calls beyond section classification.** The other three changes (flare, skip patterns, filter) are pure removal — they don't need replacement LLM calls because the agents already receive the raw data.

## Further Notes

- **Execution order matters.** The active flare deletion touches the most files and has the widest blast radius — do it first. Section classification replacement is the only change that adds new code (LLM call). Skip pattern and filter removal are straightforward deletions.
- **~30 tests deleted, ~22 test sites modified, ~6 tests added.** Net test count decreases. This is correct — we're removing behavior, not adding it.
- **CONTEXT.md requires three updates:** "Active flare" entry rewritten, "Implicit feedback" updated for raw stats, "Tier 0 / Tier 2" updated for Tier 1 implementation.
- **This unblocks better flare handling later.** Once the boolean is gone, a future iteration could add nuanced flare tracking (severity levels, affected areas, recovery timeline) without fighting a binary flag.
