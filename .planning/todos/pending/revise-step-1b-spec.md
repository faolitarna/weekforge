---
title: "Revise step-1b spec — thin Tier-0 + LLM-driven extraction"
date: 2026-04-19
priority: high
---

## Task

Rewrite `specs/steps/step-1b-tier0-extraction.md` before implementing.

## What changes

**Remove from step-1b scope:**
- `parse_to_do_block` param regex (weight/sets/reps parsing)
- `classify_role` function
- `reconcile_exercise` comment regex parsing
- `compute_delta_analysis`
- Most of the 9 unit tests (they test parsing that's moving to LLM)

**Keep in step-1b scope:**
- `RawWeekData` dataclass: session pages + block children + comments per session
- `collect_raw_sessions(notion_pages) -> list[RawSession]` — fetch blocks + comments
- `compute_checkbox_analysis(raw_sessions) -> ImplicitFeedback` — pure boolean math
- `assemble_raw_week(week_prefix, raw_sessions, planned_plan_markdown) -> RawWeekData`
- Unit tests for checkbox arithmetic only (3-4 tests max)

**Move to step-1c scope (LLM agent):**
- All semantic extraction: params, roles, comment interpretation
- Delta analysis (LLM matches planned → actual sessions)
- Filling `exercise_log`, `sessions`, `plan_adherence` in `WeekSummary`

## Context

See `.planning/notes/tier0-thin-extraction.md` for full rationale.
The imported PLAN.md at `.planning/phases/01-extraction/01-02-PLAN.md` also needs
updating to reflect the revised scope.
