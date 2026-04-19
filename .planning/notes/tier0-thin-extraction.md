---
title: "Tier-0 should be thin — collect and count only"
date: 2026-04-19
context: "gsd-explore session — questioning step-1b tier-0 extraction design"
---

## Decision

Tier-0 extraction should be minimal. It does not attempt to parse exercise params,
classify roles, interpret comments, or perform delta analysis. All semantic work
goes to the LLM (Tier-2).

## What Tier-0 actually owns

1. **Block collection** — query Notion, fetch block children + comments per session page,
   return structured `RawWeekData` bundle
2. **Checkbox counting** — pure boolean arithmetic over `to_do.checked` fields
3. **Session identification** — which pages, session names, week prefix matching

## Why not more

- Workout blocks are LLM-written (consistent format) BUT session types vary widely:
  gym, climbing, bouldering, hiking, trail run — fundamentally different structures
- Comment parsing is inherently unstructured; user writes both quick per-exercise
  notes and longer narrative feedback depending on session type
- Regex whitelist for comment parsing is fragile and duplicates what the LLM already
  does well in the source-material summarize_week prompt
- The original source-material approach (LLM reads raw blocks directly) worked well —
  tier-0 was over-engineering a problem that doesn't exist

## Implication for step-1b

Step-1b spec needs revision. Current spec has tier-0 owning: param parsing, role
classification, reconcile_exercise (comment regex), compute_delta_analysis — all of
these should move to Tier-2 (step-1c LLM agent).

Revised step-1b scope: `raw_session_collector.py` with 2-3 functions,
`RawWeekData` dataclass, checkbox math only.

## What stays in WeekSummary

The `WeekSummary` Pydantic model shape is still valid. The path to filling it changes:
`RawWeekData bundle → LLM → WeekSummary` rather than
`regex extraction → partial WeekSummary → LLM enrichment`.
