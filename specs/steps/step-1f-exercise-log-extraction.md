# Step 1f: Exercise Log Extraction & Context Completion

## Status
done

## Goal
- Populate `exercise_log`, `cardio_log`, `climbing_log` in the generated `WeekSummary` by passing raw session block data to `summarize_agent`.
- Load `feedback-interpretation.md` into static agent instructions so the LLM applies signal interpretation rules (explicit signals, implicit patterns, combined-signal priority).
- Read the Plan property from `training_week_summaries` in `load_context` and pass it to the agent so `plan_adherence` can be filled.
- Fix `COMPLETION` to session-based count (`done/total`) instead of checkbox percentage.
- Reorder `plan_state_check` before `agent` so the agent has PLAN_STATE progression context.
- Remove `exercise_log`, `cardio_log`, `climbing_log`, `plan_adherence` from the agent's "do not touch" restriction.

## Decisions
- Raw block data is already in `state.raw_sessions_json`. Needs wiring into deps.
- `plan_state_check` runs after `agent` today. Reorder: `plan_state_check` before `agent`. PLAN_STATE context enables progression annotations in exercise log feedback fields.
- LLM owns exercise extraction: free-text block descriptions require semantic parsing — not tier-0.
- Only inject heading + to_do blocks into agent context. Other block types not needed.
- Role classification follows source-material rules: `warmup`/`cooldown` from section heading; `focus` overrides section for 10 named focus exercises; `main`/`accessory` by exercise type within main section.
- `planned_*` from block text; `actual_*` from comments when user reports deviation; `done_modified` when checked but actuals differ.
- `cardio_log` and `climbing_log` use `raw: str` — compact summary string.
- `COMPLETION` is session-based: `done/total`. Checkbox data already in `IMPLICIT_FEEDBACK.checkbox_completion`.
- `plan_adherence`: if Plan property present in Notion row, LLM fills; if absent, leaves None.
- `feedback-interpretation.md` ships as a static prompt loaded at agent construction. Applies to all agents using `compose_static_instructions`.
- Plan property is a rich_text property named `Plan` on the `training_week_summaries` row (written by step-2).

## Open questions
- None.

## Inputs
- `state.raw_sessions_json`: per-session blocks and comments, already in `SummarizeWeekState`.
- `state.plan_state_raw`: PLAN_STATE text, fetched in `plan_state_check` (now runs before `agent`).
- `state.planned_plan_markdown`: Plan property from `training_week_summaries` row, fetched in `load_context` (new).
- `source-material/.claude/shared/feedback-interpretation.md`: copy to `src/weekforge/prompts/`.

## Outputs
- `WeekSummary.exercise_log`: non-empty `list[ExerciseLogEntry]` for all training sessions.
- `WeekSummary.cardio_log`: `list[CardioEntry]` for cardio sessions.
- `WeekSummary.climbing_log`: `list[ClimbingEntry]` for climbing sessions.
- `WeekSummary.plan_adherence`: filled when Plan property exists in Notion row; None otherwise.
- `WeekSummary.completion`: `"{done}/{total}"` session-based string.
- Agent receives feedback-interpretation ruleset at construction time.

## Files
- `src/weekforge/prompts/feedback-interpretation.md`: CREATE — copy content from `source-material/.claude/shared/feedback-interpretation.md`
- `src/weekforge/prompts/loader.py`: CHANGE — add `FEEDBACK_INTERPRETATION` to `Prompt` enum
- `src/weekforge/agents/prompt_composer.py`: CHANGE — add feedback-interpretation section to `compose_static_instructions`
- `src/weekforge/models/workflow_state.py`: CHANGE — add `planned_plan_markdown: str | None = None`
- `src/weekforge/workflows/summarize_week.py`: CHANGE — `load_context` reads Plan property; `tier0_extract` fixes COMPLETION; step order resequenced; `agent` step passes new deps
- `src/weekforge/agents/summarize_agent.py`: CHANGE — add `raw_sessions_json`, `planned_plan_markdown`, `plan_state_raw` to `SummarizeDeps`; add `_inject_raw_sessions`, `_inject_planned_sessions`, `_inject_plan_state` instructions functions; update `_BASE_TASK_INSTRUCTIONS`

## Data contracts

### SummarizeDeps additions
```
raw_sessions_json: str              # JSON array — same shape as state.raw_sessions_json
planned_plan_markdown: str | None   # Plan property from training_week_summaries; None if absent
plan_state_raw: str | None          # PLAN_STATE text; None on bootstrap week
```

### _inject_raw_sessions format
```
## Raw Session Blocks (source for exercise_log, cardio_log, climbing_log)

### {session_name}
Comments: {joined comments or "none"}

{heading_text}
- [x] {to_do_text}
- [ ] {to_do_text}
```
Heading + to_do blocks only. One blank line between sessions.

### _inject_planned_sessions format
```
## Planned Sessions (source for plan_adherence — fill if present)

{planned_plan_markdown}
```
Omit entire section if None.

### _inject_plan_state format
```
## Existing PLAN_STATE (progression context — do not modify PLAN_STATE fields)

{plan_state_raw}
```
Omit entire section if None.

### ExerciseLogEntry (model unchanged — now populated)
```
name: str
planned_weight: str | None     # from block text
planned_sets: int | None       # from block text
planned_reps: str | None       # from block text
actual_weight: str | None      # from comments when different
actual_sets: int | None        # from comments when different
actual_reps: str | None        # from comments when different
role: main|accessory|focus|warmup|cooldown
status: done|done_modified|skip
feedback: str | None           # comment excerpt + optional progression note e.g. "+2.5kg from WK1"
section: str | None            # heading text at time of exercise
```

### CardioEntry (unchanged)
```
kind: z1_run|z2_run|z3_tempo|hike|trail_run|other
raw: str    # compact: "10.5km/493m elevation|60min|avg 131 BPM"
```

### ClimbingEntry (unchanged)
```
kind: str
raw: str    # compact: "90min|6-7 pitches 6a-6c|thin holds, elbow-protective"
```

## Workflow

Plain sequence.

### A. Prompt file addition
Copy `source-material/.claude/shared/feedback-interpretation.md` → `src/weekforge/prompts/feedback-interpretation.md`. Add `FEEDBACK_INTERPRETATION` to `Prompt` enum in `loader.py`. In `compose_static_instructions`, append `"## Feedback Interpretation\n\n" + load_prompt(Prompt.FEEDBACK_INTERPRETATION)` after guardrails.

### B. State field addition (`workflow_state.py`)
Add `planned_plan_markdown: str | None = None` to `SummarizeWeekState`.

### C. load_context extension (`summarize_week.py`)
After fetching session pages: query `training_week_summaries` for the `W##` row, read `Plan` rich_text property. Store text in `state.planned_plan_markdown` (None if row not found or Plan property empty).

### D. tier0_extract COMPLETION fix (`summarize_week.py`)
Replace checkbox-based computation:
```
done_count = sum(1 for s in session_lines if s.status == "done")
total_count = len(session_lines)
completion = f"{done_count}/{total_count}"
```

### E. Step reorder (`summarize_week.py`)
Move `plan_state_check` before `agent`. New step order:
```
overwrite_check → load_context → tier0_extract → plan_state_check → agent → accept → write → plan_state_update → done
```
`plan_state_update` stays after `write` — still needs accepted summary output.

### F. Deps wiring (`summarize_week.py`, `agent` step)
Add to `SummarizeDeps` construction:
```python
raw_sessions_json=state.raw_sessions_json or "[]",
planned_plan_markdown=state.planned_plan_markdown,
plan_state_raw=state.plan_state_raw,
```

### G. New instructions functions (`summarize_agent.py`)
- `_inject_raw_sessions`: `@summarize_agent.instructions`. Deserializes `raw_sessions_json`, filters to heading + to_do blocks, formats block listing.
- `_inject_planned_sessions`: `@summarize_agent.instructions`. Returns planned sessions section or `""` if None.
- `_inject_plan_state`: `@summarize_agent.instructions`. Returns PLAN_STATE section or `""` if None.

### H. Prompt update (`summarize_agent.py`)
In `_BASE_TASK_INSTRUCTIONS`:
- Add to task list: `exercise_log`, `cardio_log`, `climbing_log`, `plan_adherence`.
- Remove these four from "do not touch" list. Keep `sessions`, `implicit_feedback` as ground truth.
- Add role classification: warmup/cooldown from section heading; focus overrides for: bar hangs, side planks, reverse/multidirectional lunges, bicep curls, elevator press, single arm OHP, carries, X-Press Lat Walk, face pulls, pull-ups; main for compound/heavy; accessory for isolation/secondary.
- Add params instruction: planned from block text; actual from comments when different; `done_modified` when checked but actuals ≠ planned.
- Add progression instruction: if PLAN_STATE present with prior data for an exercise, annotate `feedback` with delta.
- Add plan_adherence instruction: if Planned Sessions present, compare planned session names/types vs actual sessions; fill counts and patterns; if absent, leave None.

## Tier split
- Tier 0 (deterministic): checkbox counts, session status, implicit_feedback, COMPLETION (session counts), Plan property fetch
- Tier 1 (LLM): exercise_log, cardio_log, climbing_log, plan_adherence, context, issues, wins, recommendations, pain_status

## Failure modes
- `raw_sessions_json` empty → `_inject_raw_sessions` returns empty section; LLM produces empty logs; no crash
- `planned_plan_markdown` None → `_inject_planned_sessions` returns `""`; LLM sets `plan_adherence=None`; no crash
- `plan_state_raw` None → `_inject_plan_state` returns `""`; LLM omits progression annotations; no crash
- Block text has no parseable params → LLM sets `planned_weight/sets/reps` as None
- Exercise in fully-skipped session → included with `status: skip`, actual_* as None
- `_inject_raw_sessions` receives malformed JSON → catch `json.JSONDecodeError`, log warning, return empty string
- Step reorder breaks in-flight checkpoints with `step="agent"` → skips `plan_state_check` on that resume run; acceptable, clean runs work correctly

## Acceptance criteria
- [x] `feedback-interpretation.md` exists in `src/weekforge/prompts/`
- [x] `Prompt.FEEDBACK_INTERPRETATION` in `loader.py`
- [x] `compose_static_instructions` includes feedback-interpretation section
- [x] `SummarizeWeekState.planned_plan_markdown: str | None = None`
- [x] `load_context` reads Plan property from `training_week_summaries` row and stores in state
- [x] `tier0_extract` COMPLETION = `"{done}/{total}"` session-based
- [x] `plan_state_check` runs before `agent` in step sequence
- [x] `SummarizeDeps` has `raw_sessions_json`, `planned_plan_markdown`, `plan_state_raw`
- [x] `_inject_raw_sessions`, `_inject_planned_sessions`, `_inject_plan_state` all exist as `@summarize_week_agent.instructions`
- [x] `_inject_raw_sessions` emits heading + to_do blocks only
- [x] Task instructions include `exercise_log`, `cardio_log`, `climbing_log`, `plan_adherence`
- [x] `exercise_log`, `cardio_log`, `climbing_log`, `plan_adherence` removed from "do not touch"
- [x] Role classification rules (focus exercise list + section fallback) in prompt
- [x] Progression annotation instruction in prompt
- [x] plan_adherence instruction (fill when plan present, None when absent) in prompt
- [x] Manual run: `WeekSummary.exercise_log` non-empty; `COMPLETION` is session ratio
- [x] `uv run pytest tests/` passes

## Out of scope
- `STRENGTH_LOG` separate section name — canonical format uses `EXERCISE_LOG`
- Changing `ExerciseLogEntry` model shape
- Extraction verification (to_do count vs exercise_log count) — follow-up
- Overwrite-check wiring — tracked in step-1c deviations
