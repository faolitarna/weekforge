<summarize-task>
You are generating a weekly training summary. The user has already provided:
- Their coaching persona and safety guardrails (above).
- Their active user profile (conditions, HR zones, preferences).
- Deterministic facts computed from Notion: per-session checkbox counts, completion rates.
- Raw session blocks with heading + to_do items and comments.
Your job is to fill:
- `exercise_log`: list of ExerciseLogEntry for every training session exercise. Extract from Raw Session Blocks.
  - `session_name`: the training session this exercise belongs to, without week prefix (e.g. "General Strength 1", not "W01: General Strength 1"). Must match session names in the sessions list.
  - `planned_weight/sets/reps`: from block text (e.g. "Goblet Squat 3x8 @20kg" → planned_sets=3, planned_reps="8", planned_weight="20kg").
  - `actual_weight/sets/reps`: from comments when user reports deviation from plan. Leave None if no deviation.
  - `status`: `done` if checked with no deviation, `done_modified` if checked but actuals differ from planned, `skip` if unchecked.
  - `role`: classify by these rules:
    - `warmup`: exercise under a heading containing "warmup" or "warm-up"
    - `cooldown`: exercise under a heading containing "cooldown" or "cool-down"
    - `focus`: overrides section for these named exercises: bar hangs, side planks, reverse lunges, multidirectional lunges, bicep curls, elevator press, single arm OHP, carries, X-Press Lat Walk, face pulls, pull-ups
    - `main`: compound/heavy movements in main section
    - `accessory`: isolation/secondary movements in main section
  - `feedback`: comment excerpt relevant to this exercise. Do NOT include cross-week progression notes (e.g. "+2.5kg from WK1") — PLAN_STATE owns cross-week deltas.
  - `section`: heading text at time of exercise.
  - For fully-skipped sessions (status=skip in sessions list): you may omit exercise_log entries entirely. The session line already captures the skip reason.
- `cardio_log`: list of CardioEntry for cardio sessions. `kind` from session type, `raw` as compact summary string (e.g. "10.5km/493m elevation|60min|avg 131 BPM").
- `climbing_log`: list of ClimbingEntry for climbing sessions. `kind` from session type, `raw` as compact summary string.
- `plan_adherence`: if Planned Sessions section present, compare planned vs actual sessions and fill counts + patterns. If absent, set to None.
- `context`: external factors mentioned in comments (illness, travel, equipment limits).
- `issues`: what didn't work THIS WEEK. Do NOT include cross-week comparisons — PLAN_STATE tracks trends. Each item must be `"key:details"` format (e.g. `"knee_load:squats aggravated mid-session"`).
- `wins`: what worked well THIS WEEK. Report this week's numbers only, no cross-week deltas. Each item must be `"key:details"` format (e.g. `"overhead_strength:elevator press at 14kg steady"`).
- `recommendations_next`: concrete, coach-voiced suggestions for next week.
- `highlights`: 3–5 bullets for quick user review in the accept panel.
- `trend`: one sentence capturing week-over-week directional observation (e.g. "strength improving, cardio displaced by mountain days"), not numeric cross-week deltas.
- `pain_status`: list of JointEntry for each joint with a notable status. Each entry: `name` (joint identifier, e.g. `"si_joint"`), `status` (e.g. `"ok"`, `"stiff"`, `"sore"`), optional `triggers` (what provoked symptoms), optional `what_helped`. Omit entries for joints with no data.
Do NOT recompute or modify `sessions` or `implicit_feedback` — copy them through from Tier-0 unchanged.
All other fields listed above are yours to fill from Raw Session Blocks, comments, Planned Sessions, and PLAN_STATE.
</summarize-task>
