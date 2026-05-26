# Remove rigid semantic analysis from workflows

Status: ready-for-agent

## Description

Replace four rigid semantic analysis points with LLM reasoning or raw data:
1. Delete `ACTIVE_FLARE` boolean flag — replace with pain-aware prompt guidance
2. Replace `_classify_section` substring matching with fast-LLM batch call
3. Replace `frequently_skipped`/`always_completed` thresholds with raw `ExerciseCheckStats`
4. Delete `_filter_week_for_plan_state` — pass full WeekSummary to plan_state agent

Principle: arithmetic stays in Python, semantic interpretation goes to the LLM.

## PRD

See [specs/remove-rigid-semantic-analysis/PRD.md](../remove-rigid-semantic-analysis/PRD.md)

## Spec

See [specs/remove-rigid-semantic-analysis/spec.md](../remove-rigid-semantic-analysis/spec.md)
