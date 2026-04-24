# Step 1e: Summary Format Alignment

## Status
done

## Goal
- Align `week_summary_renderer.py` output with canonical `<summary-format>` from `source-material/.claude/commands/summarize_week.md`.
- Replace `PainStatus` model with extensible `list[JointEntry]`.
- Update `summarize_agent` prompt so LLM produces `issues`/`wins` items as `key:details` and `pain_status` as `list[JointEntry]`.
- Output is LLM-consumed artifact: optimize for information density, parsability, token savings — not human readability.

## Decisions
- Input: `WeekSummary` Pydantic model instance.
- Output: string, written to Notion, consumed by LLM in following runs.
- `PainStatus` → replace with generic `list[JointEntry]` model. `JointEntry` fields: `name`, `status`, `triggers`, `what_helped`. Extensible — adding new joint = new list entry, zero model change.
- Extraction agent update for `PainStatus` is **in scope** — model shape change requires aligned extraction. "Extraction agent" = `summarize_agent` (fills pain_status from session comments).
- `issues`/`wins` stay `list[str]`. Update `summarize_agent` prompt to instruct LLM: produce each item as `"key:details"` (e.g. `"knee_load:squats aggravated mid-session"`). Renderer passes through as-is: `- {item}`.
- `highlights`/`trend` fields exist in model but not in canonical format — renderer ignores them.
- EXERCISE_LOG weight: keep `planned->actual` notation when values differ. Deviation is meaningful signal for planning agent — `status:done_modified` alone doesn't capture which fields changed.
- `JointEntry` null fields: omit trailing nulls. `si_joint:ok`, `si_joint:stiff|deadlifts`, `si_joint:stiff|deadlifts|heat` all valid.

## Open questions
- None.

## Design Principle

Summary text is read by LLMs every workflow run. Tokens compound. Source-material format was deliberately token-optimized: pipe-delimited, colon-separated key:value, single-line sections. Renderer must match exactly.

## Inputs
- `WeekSummary` Pydantic model instance.
- Canonical format reference: `source-material/.claude/commands/summarize_week.md` lines 231–301.

## Outputs
- Rendered summary string, LLM-consumable: pipe-delimited, colon key:value, single-line sections.
- Written to Notion as a fenced code block by `summarize_week.py`.

## Files
- `src/weekforge/models/week_summary.py`: CHANGE — remove `PainStatus`, add `JointEntry`, update `WeekSummary.pain_status` type
- `src/weekforge/tools/week_summary_renderer.py`: CHANGE — fix all drifts in Current Drifts table; render `list[JointEntry]`
- `src/weekforge/workflows/summarize_week.py`: CHANGE — `tier0_extract` initializes `pain_status=[]`; remove `PainStatus` import
- `src/weekforge/agents/summarize_agent.py`: CHANGE — prompt instructs `issues`/`wins` as `key:details`; add `pain_status` field instruction
- `tests/tools/test_week_summary_renderer.py`: CHANGE — update fixtures to `list[JointEntry]`; update assertions; add byte-level canonical-format test

## Data contracts

### Removed
```python
class PainStatus(BaseModel):
    si_joint: str | None
    other: str | None
```

### Added
```python
class JointEntry(BaseModel):
    name: str           # e.g. "si_joint", "other"
    status: str         # always present
    triggers: str | None = None
    what_helped: str | None = None
```

### Changed
`WeekSummary.pain_status: PainStatus` → `WeekSummary.pain_status: list[JointEntry]`

## Workflow

Plain sequence.

### A. Model change (`week_summary.py`)
1. Remove `PainStatus` class.
2. Add `JointEntry` class per contract above.
3. Change `WeekSummary.pain_status: PainStatus` → `pain_status: list[JointEntry]`.

### B. Renderer fixes (`week_summary_renderer.py`)

**EXERCISE_LOG**
- Old: `{name}|{role}|{status}|{sets}x{reps} @ {weight}|"{feedback}"`
- New: `{name}:{weight}x{sets}x{reps}|{role}|{status}|"{feedback}"`
- Colon after name (not pipe); weight before sets/reps; `x` separator (not `@`)
- `{weight}`, `{sets}`, `{reps}` each use `planned->actual` when values differ (existing logic kept)
- Feedback quoted when present, omitted (including trailing `|`) when absent

**PLAN_ADHERENCE**
- Old: `Total: {N} (Completed: {X}, Modified: {Y}, Skipped: {Z})`
- New: `planned:{N}|completed:{X}|modified:{Y}|skipped:{Z}` (single line)
- `modification_patterns`: single line `modification_patterns:{ex}->{rep}|{ex}->{rep}`, omit line if empty
- `skip_patterns`: single line `skip_patterns:{session_type}:{reason}|{session_type}:{reason}`, omit line if empty

**IMPLICIT_FEEDBACK**
- Drop per_session lines (not in canonical format)
- `checkbox_completion:{checked}/{total}|{pct}%` — single line; compute `pct = round(checked/total * 100)`, guard against zero total
- `section_rates:warmup:{%}|main:{%}|cooldown:{%}` — single line; pct as integer (multiply by 100, round to 0 decimals)
- `frequently_skipped:{exercise}:{skip_rate}%|{exercise}:{skip_rate}%` — single line, omit line if empty
- `always_completed:{ex}|{ex}|{ex}` — single line, omit line if empty

**PAIN_STATUS**
- Render each `JointEntry`: always `{name}:{status}`; append `|{triggers}` if triggers present; append `|{what_helped}` if what_helped present (only when triggers also present)

**ISSUES/WINS**
- Renderer passes through items as-is: `- {item}`. LLM owns `key:details` format.

### C. Workflow update (`summarize_week.py`)
1. In `tier0_extract` step: replace `PainStatus(si_joint=None, other=None)` with `[]`.
2. Remove `PainStatus` from the local import on line 89; `JointEntry` import not needed (empty list requires no type reference).

### D. Agent prompt update (`summarize_agent.py`)
Add to `_BASE_TASK_INSTRUCTIONS` (under the `issues` bullet):
- `issues` and `wins`: each item must be `"key:details"` format (e.g. `"knee_load:squats aggravated mid-session"`, `"overhead_strength:elevator press at 14kg steady"`)
- `pain_status`: list of `JointEntry`; each entry needs `name` (joint identifier, e.g. `"si_joint"`), `status` (e.g. `"ok"`, `"stiff"`), optional `triggers` (what provoked it), optional `what_helped`

### E. Test updates (`tests/tools/test_week_summary_renderer.py`)
1. Replace `PainStatus` fixture with `list[JointEntry]`.
2. Update existing assertions to match new canonical format strings.
3. Add a dedicated byte-level test: construct `WeekSummary` with known values and assert exact output strings for EXERCISE_LOG, PLAN_ADHERENCE, IMPLICIT_FEEDBACK, PAIN_STATUS lines.

## Tier split
- Tier 0 (deterministic): A (model), B (renderer), C (workflow), E (tests)
- Tier 1 (LLM instruction change): D (agent prompt)

## Failure modes
- `JointEntry.triggers` None, `what_helped` None → render `{name}:{status}` only
- `JointEntry.triggers` present, `what_helped` None → render `{name}:{status}|{triggers}`
- `JointEntry.what_helped` present but `triggers` None → treat as data error; render `{name}:{status}|{what_helped}` (don't silently drop)
- `ExerciseLogEntry.planned_weight` None → render empty string, no crash
- `ImplicitFeedback.total_exercises` zero → pct renders as `0%`, no division error
- `ImplicitFeedback.frequently_skipped` empty → omit `frequently_skipped` line entirely
- `ImplicitFeedback.always_completed` empty → omit `always_completed` line entirely
- `PlanAdherence.modification_patterns` empty → omit `modification_patterns` line entirely
- `PlanAdherence.skip_patterns` empty → omit `skip_patterns` line entirely

## Acceptance criteria
- [x] `JointEntry` class in `week_summary.py`; `PainStatus` class removed; `WeekSummary.pain_status: list[JointEntry]`
- [x] `summarize_week.py` tier0_extract: `pain_status=[]`; `PainStatus` import removed
- [x] Renderer EXERCISE_LOG: `{name}:{weight}x{sets}x{reps}|{role}|{status}` with optional `|"{feedback}"`
- [x] Renderer EXERCISE_LOG: `planned->actual` notation preserved when values differ
- [x] Renderer PLAN_ADHERENCE: `planned:{N}|completed:{X}|modified:{Y}|skipped:{Z}` single pipe-delimited line
- [x] Renderer PLAN_ADHERENCE modification_patterns: single pipe-delimited line, omitted when empty
- [x] Renderer PLAN_ADHERENCE skip_patterns: single pipe-delimited line, omitted when empty
- [x] Renderer IMPLICIT_FEEDBACK: no per_session lines emitted
- [x] Renderer IMPLICIT_FEEDBACK: `checkbox_completion:{checked}/{total}|{pct}%` single line
- [x] Renderer IMPLICIT_FEEDBACK: `section_rates:warmup:{%}|main:{%}|cooldown:{%}` single line
- [x] Renderer IMPLICIT_FEEDBACK: `frequently_skipped` single pipe-delimited line, omitted when empty
- [x] Renderer IMPLICIT_FEEDBACK: `always_completed` single pipe-delimited line, omitted when empty
- [x] Renderer PAIN_STATUS: renders `list[JointEntry]` with trailing-null omission per rules above
- [x] `summarize_agent` prompt: `issues`/`wins` items as `"key:details"`; `pain_status` as list of JointEntry with field descriptions
- [x] Test fixture uses `list[JointEntry]`, not `PainStatus`
- [x] Byte-level test validates exact output strings for EXERCISE_LOG, PLAN_ADHERENCE, IMPLICIT_FEEDBACK, PAIN_STATUS

## Out of scope
- PLAN_STATE format (separate concern, `tools/plan_state.py`).
- Adding new joint types beyond what appears in existing week data.
- Changing `WeekSummary` top-level fields (`highlights`, `trend`) — renderer ignores them.
- Changing `SessionLine.comment` quoting behavior — sessions already render `|"{comment}"` correctly.

## Canonical Format Reference

Source: `source-material/.claude/commands/summarize_week.md` lines 231–301.

```text
WEEK_SUMMARY:{WEEK_PREFIX}
COMPLETION:{done_count}/{total_count}
CONTEXT:{external_factors}

SESSIONS:
- {SESSION_TYPE}|{done/skip/partial}|{exercises_done}/{exercises_total}|{pain_status}|"{comment}"

EXERCISE_LOG:
- {exercise}:{weight}x{sets}x{reps}|{role}|{status}|{feedback}

CARDIO_LOG:
- z2_run:{dist}km/{duration}min|{pace}/km|{avg_HR}bpm|cad:{spm}|"{notes}"

CLIMBING_LOG:
- {type}:{duration}|{grades}|{notes}

PAIN_STATUS:
- si_joint:{status}|{triggers}|{what_helped}
- other:{notes}

ISSUES:
- {problem}:{details}

WINS:
- {success}:{details}

RECOMMENDATIONS_NEXT:
- {recommendation}

PLAN_ADHERENCE:
- planned:{total}|completed:{X}|modified:{Y}|skipped:{Z}
- modification_patterns:{exercise}->{replacement}|{exercise}->{replacement}
- skip_patterns:{session_type}:{reason}

IMPLICIT_FEEDBACK:
- checkbox_completion:{total_checked}/{total_exercises}|{percentage}%
- section_rates:warmup:{%}|main:{%}|cooldown:{%}
- frequently_skipped:{exercise}:{skip_rate}%|{exercise}:{skip_rate}%
- always_completed:{exercise}|{exercise}|{exercise}
```
