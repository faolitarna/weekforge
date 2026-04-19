---
plan: "01-02"
phase: "01-extraction"
status: complete
---

# Summary: Plan 01-02 — Raw Session Collection (Thin Tier-0)

## What Was Built

Thin Tier-0 data collection layer — no semantic parsing, no LLM calls.

## Key Files Created

- `src/weekforge/models/week_summary.py` — Pydantic output schema (WeekSummary + all sub-models); contract for step-1c LLM
- `src/weekforge/models/raw_week_data.py` — RawBlock, RawSession, RawWeekData dataclasses
- `src/weekforge/tools/raw_session_collector.py` — collect_blocks, collect_comments, collect_raw_sessions, compute_checkbox_analysis, assemble_raw_week
- `tests/tools/test_raw_collector.py` — 8 unit tests, all passing

## Must-Haves Verified

- [x] WeekSummary round-trip: model_dump_json / model_validate_json passes
- [x] collect_raw_sessions returns one RawSession per page, all to_do + heading blocks captured
- [x] compute_checkbox_analysis: arithmetically correct per_session counts, section_rates, frequently_skipped, always_completed
- [x] assemble_raw_week raises ValueError containing week_prefix when sessions empty
- [x] All field access uses .get() — no KeyError on malformed Notion responses
- [x] uv run pytest tests/tools/test_raw_collector.py → 8 passed

## Deviations

None — implemented exactly per spec and plan.

## Self-Check: PASSED
