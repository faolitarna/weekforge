# Step 1e: Summary Format Alignment

## Goal

Align `week_summary_renderer.py` output with the canonical `<summary-format>` from `source-material/.claude/commands/summarize_week.md`. The rendered summary is an LLM-consumable artifact — primary consumers are PLAN_STATE agent, planning agent (step-2), and delta analysis. Optimize for information density, parsability, and token savings. Not human readability.

## Design Principle

Summary text is read by LLMs every workflow run. Tokens compound. Source-material format was deliberately token-optimized: pipe-delimited, colon-separated key:value, single-line sections. Renderer must match exactly.

## Current Drifts

| Section | Source Format | Current Renderer | Issue |
|---------|-------------|-----------------|-------|
| EXERCISE_LOG | `{name}:{weight}x{sets}x{reps}\|{role}\|{status}\|{feedback}` | `{name}\|{role}\|{status}\|{sets}x{reps} @ {weight}\|{feedback}` | Field order wrong, colon→pipe after name, `@` instead of `x` for weight |
| PLAN_ADHERENCE | `planned:{N}\|completed:{X}\|modified:{Y}\|skipped:{Z}` | `Total: {N} (Completed: {X}, Modified: {Y}, Skipped: {Z})` | Parenthetical format instead of pipe-delimited |
| IMPLICIT_FEEDBACK | `checkbox_completion:{checked}/{total}\|{pct}%` | `Total Checked: {checked}/{total}` (multi-line) | Multi-line labeled format instead of single-line pipe-delimited |
| IMPLICIT_FEEDBACK section_rates | `section_rates:warmup:{%}\|main:{%}\|cooldown:{%}` | Three separate labeled lines | Should be single pipe-delimited line |
| PAIN_STATUS | `si_joint:{status}\|{triggers}\|{what_helped}` | `SI Joint: {status}` | Missing `triggers` and `what_helped` fields |
| ISSUES/WINS | `{problem}:{details}` | `{text}` (flat string) | Missing colon-separated key:value structure |

## What You're Building

| File | Action | Purpose |
|------|--------|---------|
| `src/weekforge/tools/week_summary_renderer.py` | UPDATE | Align all sections to source-material pipe-delimited format |
| `src/weekforge/models/week_summary.py` | UPDATE | Add missing fields to `PainStatus` (`triggers`, `what_helped`) if not present |
| `tests/tools/test_week_summary_renderer.py` | UPDATE | Byte-level fixture tests against canonical format |

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

## Acceptance Criteria

- [ ] Renderer output matches `<summary-format>` exactly — pipe delimiters, colon key:value, single-line sections.
- [ ] EXERCISE_LOG: `{name}:{weight}x{sets}x{reps}|{role}|{status}|{feedback}` format.
- [ ] PLAN_ADHERENCE: pipe-delimited single line, not parenthetical.
- [ ] IMPLICIT_FEEDBACK: four single-line entries with pipe delimiters.
- [ ] PAIN_STATUS: includes `triggers` and `what_helped` fields.
- [ ] ISSUES/WINS: colon-separated `{key}:{details}` structure.
- [ ] Byte-level fixture test validates against canonical format sample.
- [ ] Existing tests updated to match new format.

## Out of Scope

- Changing `WeekSummary` Pydantic model structure beyond adding missing fields.
- Changing how agents produce content — only the renderer output format.
- PLAN_STATE format (separate concern, `tools/plan_state.py`).
