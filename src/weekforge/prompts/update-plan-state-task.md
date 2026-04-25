<update-plan-state-task>
You are updating a cumulative PLAN_STATE that tracks cross-week training trends, issue lifecycle, and progression patterns. You receive:
- The existing PLAN_STATE (with mechanical fields already updated by Python: weeks_completed, avg_completion, weight chains in main_lifts, adherence completion chain).
- This week's summary data (filtered to signal-bearing entries only).
Your job: update the **interpretive** fields listed below. Do NOT recompute mechanical fields — they are already correct.
If this is a bootstrap (all_weeks provided instead of existing PLAN_STATE + new_week): compile all weeks chronologically to establish initial state for every field.
<field-specs>

**main_lifts** — Set trend tag only. Weight chain is pre-built mechanically.
- Format: `{exercise}:{weight_chain}|peak:{max}|trend:{up|plateau|down}`
- Trend criteria:
  - `up`: 2+ consecutive weight increases in chain
  - `plateau`: volume cycling at same weight. This is EXPECTED during progression-protocol ladder (3x8→4x12 before load increase). Only flag concern if weight unchanged AND volume ceiling reached with no load increase for 3+ weeks.
  - `down`: weight decreased from prior peak (deload, regression, or pain-driven reduction)
- Do NOT modify the weight chain or peak — only the trend tag.

**push_pull_gap** — Track weekly pull:push movement ratio vs 2:1 target (from guardrails).
- Format: `{week}:{ratio}|{assessment}`
- Keep most recent 3-4 entries. Drop oldest when adding new.

**accessory_tracker** — Which accessories rotate in/out and why.
- Format: `{exercise}:{status}|{note}`
- Update on change only. Don't restate unchanged entries.

**focus_exercise_log** — Weekly frequency count vs 8+/week target (from guardrails).
- Format: `{week}:{count}/{target}|{notes}`
- One entry per week.

**hangboard** — Protocol trends. Summarize, do NOT list individual sessions.
- Format: `{week}:{protocol_summary}|{volume}|{notes}`
- Capture protocol changes, volume direction, limiting factors.

**cardio** — Weekly volume trends. Aggregate totals, do NOT copy individual sessions.
- Format: `{week}:{total_time}|{total_elevation}|{zone_split}|{notes}`
- Summarize: total weekly time, total elevation, zone distribution. One entry per week.

**climbing** — Grade and volume trends. Aggregate, do NOT list sessions.
- Format: `{week}:{summary}`
- One entry per week.

**injury_timeline** — Chronological injury/pain events.
- Format: `{week}:{joint}:{event}:{action_taken}`
- Add new events. Persist entries until issue moves to resolved.
- Reference guardrails symptom-protocol levels (mild/moderate/critical) when classifying.

**mobility_posture** — Adherence rate trends and notable changes.
- Format: `{week}:{completion_rate}|{notes}`
- One entry per week.

**adherence** — Mechanical completion chain is pre-built. You handle: barrier identification, session-type patterns, skip reasons.
- Do NOT modify the `weekly:` chain entry — it is mechanical.
- Add entries for: `barrier:{description}`, `skip_pattern:{description}`, `session_type:{type}:{observation}`

**session_preferences** — What user likes/dislikes, time patterns, format preferences.
- Format: `{preference}:{evidence}`
- Update when new signal appears. Don't repeat unchanged preferences.

**deload_history** — When and why deloads happened.
- Format: `{week}:{reason}:{scope}`
- Add only when deload occurs.

**resolved** — Issues moved from active_issues when resolved.
- Format: `{issue}:{resolved_week}:{how}`
- Move here from active_issues when evidence shows resolution (pain gone, barrier removed, performance recovered).

**active_issues** — Current unresolved problems.
- Format: `{issue}:{first_seen}:{current_status}`
- Promote from weekly issues/pain if: severity is moderate+ per guardrails symptom-protocol, OR issue persists 2+ consecutive weeks.
- Move to resolved when evidence shows resolution.
- Update current_status each week with latest data.

</field-specs>
<rules>
- Trends not lists: cardio, hangboard, climbing get one aggregated entry per week. Never copy session-level detail from the weekly summary.
- Issue lifecycle: weekly issues are ephemeral. Only promote to active_issues if severe or persisting. Active issues get resolved when evidence supports it.
- Progression-protocol awareness: plateau during volume cycling (same weight, increasing reps/sets per progression-protocol ladder) is normal training, not a stall. Flag stall only when volume ceiling reached AND no load increase for 3+ weeks.
- Compact entries: no filler words, no articles. Key:value format throughout.
- Return the complete PlanState — all fields, not just changed ones.
</rules>
</update-plan-state-task>
