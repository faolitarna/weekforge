# Spec: Remove rigid semantic analysis from workflows

**Status**: Draft
**Date**: 2026-05-26
**Triggered by**: False positive `ACTIVE_FLARE: YES` in production — model drafted conservatively despite 3 clean weeks because regex matched stale `active_issues` entry.

## Problem

Rigid Python code performs semantic interpretation (keyword matching, substring classification, feature-based filtering) on training data, then injects results as "ground truth" into LLM prompts. When the rigid analysis is wrong, it overrides the model's correct interpretation of the same raw data.

### Concrete failure

`derive_active_flare()` scans `PLAN_STATE.active_issues` and recent summary text with regex `\b(SI|spine|flare|pain|tendon|joint)\b`. A stale or benign entry like `"SI joint:W03:resolved"` or `"SI joint: ok"` matches the regex. The resulting `ACTIVE_FLARE: YES` flag is injected into the draft agent prompt, causing conservative programming even when the model — reading the same PLAN_STATE — would correctly determine no active pain exists.

### Pattern across the codebase

| Analysis point | Type | Problem |
|---|---|---|
| `derive_active_flare` + `has_active_pain` | Regex on text | No semantic understanding. "ok" matches same as "severe pain" |
| `_classify_section` | Substring match on headings | Fails on non-standard names: "Activation", "Prep", "Finisher" |
| `frequently_skipped` threshold | Hardcoded `skip_rate > 0.5` | Rigid threshold, no context — 1/2 on a rare exercise != 1/2 on a weekly staple |
| `_filter_week_for_plan_state` | Feature-based filtering | Rigid rule decides what data reaches the plan_state agent, may drop important exercises |

### What works fine (keep as-is)

| Analysis point | Type | Why it's correct |
|---|---|---|
| Completion counting (`done/total`) | Pure arithmetic | 5/10 is always 5/10 |
| Session status (`done/partial/skip`) | Boolean + count | Deterministic from checkbox state |
| `apply_mechanical_update` | Arithmetic (averages, chain appending) | Weight chains, completion percentages |
| Pull/push ratio validator | Tag counting on LLM-generated tags | Guardrail on controlled vocabulary |
| Conditioning floor validator | Tag set check on LLM-generated tags | Same — known tag vocabulary |
| `_is_signal_entry` in renderer | UX compression | Human readability in Notion, not agent input |

## Design principle

**Arithmetic stays in Python. Semantic interpretation goes to the LLM.**

The LLM already receives the source data (PLAN_STATE, raw sessions, summaries). Pre-digesting that data with rigid code creates a fragile shortcut that collapses nuance into booleans or thresholds. When it's wrong, it actively harms output quality by overriding the model's judgment.

Exception: when classification is needed *before* the main agent call (e.g., section heading → warmup/main/cooldown mapping feeds into arithmetic that the agent receives as Tier-0 facts), use a fast/cheap LLM call with structured output.

## Changes

### 1. Delete `ACTIVE_FLARE` flag

**Remove entirely**: `derive_active_flare()`, `has_active_pain()`, `_PAIN_KEYWORDS`, `ACTIVE_FLARE: YES/NO` injection, `active_flare` field from `DraftWeekDeps`, `DraftWeekState`, `WeekDraftContext`.

**Replace with prompt guidance**: The draft agent already sees PLAN_STATE (including ACTIVE_ISSUES full text). Instead of a boolean flag, teach the model *how* to reason about pain.

**Files**: `plan_state.py`, `context_loader.py`, `draft_week_agent.py`, `workflow_state.py`, `draft_week.py`

**Prompt change in `draft-week-task.md`**:

Current line 7:
```
- ACTIVE_FLARE flag (YES/NO — triggers conservative programming).
```
Replace with:
```
- PLAN_STATE ACTIVE_ISSUES section (current injury/pain tracking — inspect before setting intensity).
```

Current rule 6 (line 18):
```
6. **ACTIVE_FLARE = YES**: apply symptom protocol. Substitute or reduce load on affected movements. Do not program through active pain.
```
Replace with:
```
6. **Pain-aware programming.** Before setting session intensity, inspect PLAN_STATE → ACTIVE_ISSUES for any active injury or pain entries. If moderate+ pain is present or persists across multiple weeks, apply symptom protocol: substitute or reduce load on affected movements. Do not program through active pain. If ACTIVE_ISSUES is empty or contains only resolved/mild items, program normally.
```

**Why this prompt is stronger than the boolean**: The model gets the reasoning framework — what to check, severity criteria, when to downshift, when to proceed normally. The boolean collapsed all of this into a bit with no severity awareness.

### 2. Replace rigid section classification with LLM call

**Current**: `_classify_section()` in `raw_session_collector.py` does substring matching (`"warmup" in lower`, `"main" in lower`, `"cooldown" in lower`), defaults to "main". Feeds into `SectionRates` (warmup_pct, main_pct, cooldown_pct) which is injected as Tier-0 ground truth.

**Problem**: Non-standard headings misclassified. When section_rates are wrong, the summarize agent builds analysis on wrong data labeled "ground truth."

**Replace with**: A single LLM call using `resolve_llm_profile("fast")` that classifies all unique headings across the week in one batch. Structured output: `dict[str, Literal["warmup", "main", "cooldown"]]`.

**New function** in `raw_session_collector.py`:
```python
def classify_sections(headings: list[str]) -> dict[str, str]:
    """Classify section headings using fast LLM. Falls back to substring matching on failure."""
```

**Prompt** (inline — micro-classification, not worth a separate prompt file):
```
Classify each training session heading into exactly one category:
- warmup: preparatory exercises, activation, warm-up, prep, mobility done before main work
- main: primary training exercises, strength work, compound movements, accessories, skill work
- cooldown: post-session stretching, cool-down, finisher, recovery exercises

Return mapping of heading text to category.
```

**Integration**: `compute_checkbox_analysis()` takes a `section_map: dict[str, str]` parameter instead of calling `_classify_section()`. Caller (`load_week_summarize_context` in `context_loader.py`) calls `classify_sections()` first.

**Fallback**: On API failure, fall back to current substring matching. Log warning.

**Files**: `raw_session_collector.py`, `context_loader.py`

### 3. Remove skip pattern thresholding

**Current**: `compute_checkbox_analysis()` counts per-exercise checked/total, then applies rigid thresholds (`skip_rate > 0.5` and `total >= 2`) to produce `frequently_skipped: list[SkippedPattern]` and `always_completed: list[str]`. These go into `ImplicitFeedback` which is labeled "Deterministic Tier-0 Facts" in the agent prompt.

**Problem**: The arithmetic (counting) is correct. The threshold is a semantic judgment — what counts as "frequently skipped" depends on context the code doesn't have. Labeling this as "ground truth" constrains the LLM's interpretation.

**Replace with**: Raw per-exercise stats. Let the summarize agent apply judgment.

**Model change in `week_summary.py`**:
```python
class ExerciseCheckStats(BaseModel):
    exercise: str
    checked: int
    total: int

class ImplicitFeedback(BaseModel):
    total_checked: int
    total_exercises: int
    per_session: list[SessionCheckCount]
    section_rates: SectionRates
    exercise_stats: list[ExerciseCheckStats]
```

Delete `SkippedPattern`, `frequently_skipped`, `always_completed`.

**Prompt addition in `summarize-week-task.md`** (after the pain_status bullet, line 31):
```
- The `implicit_feedback.exercise_stats` field contains raw per-exercise check counts (checked vs total across the week). Use these to identify patterns: exercises consistently unchecked across sessions suggest the user is skipping them; exercises always checked suggest they're well-integrated. Apply your judgment — a 1/2 skip rate on a rarely-programmed exercise is different from 1/2 on a weekly staple.
```

**Files**: `week_summary.py`, `raw_session_collector.py`, `summarize-week-task.md`

### 4. Remove signal exercise filtering from plan_state agent

**Current**: `_filter_week_for_plan_state()` in `update_plan_state_agent.py` filters exercises to only those with weight data, feedback, or "done_modified" status before passing to the plan_state update agent.

**Problem**: Rigid feature-based rule decides what training data reaches the agent. Could drop exercises the agent needs to see (e.g., a bodyweight exercise the user struggled with but has no weight data).

**Replace with**: Pass full `WeekSummary`, excluding only LLM-meta fields the agent shouldn't echo back.

**Change in `update_plan_state_agent.py`**:
```python
# Before:
filtered = json.dumps(_filter_week_for_plan_state(ctx.deps.new_week), default=str)

# After:
week_json = ctx.deps.new_week.model_dump_json(
    exclude_none=True,
    exclude={"implicit_feedback", "highlights", "trend", "recommendations_next"},
)
```

Delete `_filter_week_for_plan_state()`. Same change for bootstrap path with `all_weeks`.

**Files**: `update_plan_state_agent.py`

## CONTEXT.md updates required

After implementation, update these entries:

**"Active flare"** (line 70-71): Delete or rewrite. No longer a boolean derived by code. The concept of a flare still exists (line 66-68), but detection is now the draft agent's responsibility via PLAN_STATE → ACTIVE_ISSUES inspection.

**"Implicit feedback"** (line 42-44): Update to reflect raw stats instead of thresholded patterns:
```
Training signals derived mechanically (Tier 0) from checkbox completion data — per-session completion counts, per-exercise check rates, section completion rates (warmup/main/cooldown via LLM classification). Raw counts only — the LLM applies judgment about patterns and significance.
```

**"Tier 0 / Tier 2"** (line 76-78): Update Tier 1 status — it's now implemented for section classification:
```
Intelligence tiering. Tier 0 = pure Python, zero LLM — all deterministic work (data fetching, checkbox counting, formatting, validation). Tier 1 = fast/cheap LLM for micro-classification tasks (section heading classification). Tier 2 = heavy cognitive LLM — planning, summarization, trend synthesis.
```

## Test impact

**Delete** (~30 tests):
- All `derive_active_flare` tests in `test_draft_week_agent.py`
- `test_has_active_pain_*` in `test_plan_state.py`
- `test_load_week_draft_context_active_flare` in `test_context_loader.py`
- `test_load_context_active_flare_stored_in_state` in `test_draft_week.py`
- `test_compute_checkbox_analysis_frequently_skipped` in `test_raw_session_collector.py`
- `test_compute_checkbox_analysis_always_completed` in `test_raw_session_collector.py`

**Modify** (~22 sites):
- All `ImplicitFeedback(... frequently_skipped=[], always_completed=[])` → `ImplicitFeedback(... exercise_stats=[])`
- All `DraftWeekDeps(... active_flare=...)` → remove field
- `test_tier0_serialization_excludes_llm_fields` — update field list

**Add**:
- `test_classify_sections` — mock LLM, verify heading → category mapping
- `test_classify_sections_fallback` — verify rigid fallback on API failure
- `test_exercise_stats_raw_counts` — verify raw stats without thresholding

## Execution order

1. Delete active_flare path (plan_state → context_loader → draft_week_agent → workflow_state → draft_week)
2. Update `draft-week-task.md` prompt
3. Replace `_classify_section` with LLM call, update `context_loader.py` integration
4. Replace `frequently_skipped`/`always_completed` with raw `exercise_stats`
5. Remove `_filter_week_for_plan_state` from `update_plan_state_agent.py`
6. Update `summarize-week-task.md` prompt
7. Update CONTEXT.md
8. Update all tests
9. Run full test suite

## Verification

```bash
python -m pytest tests/ -v
```

Manual smoke test: `weekforge draft-week W07` with Notion data containing resolved pain entries in PLAN_STATE — verify no false flare triggering and that the model correctly reads ACTIVE_ISSUES to determine intensity.
