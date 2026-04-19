# Step 1: Extraction Subsystem (`summarize_week`) — Index

## Goal

Build post-execution extraction. Summarize a completed training week, generate feedback, and manage PLAN_STATE. Faithfully recreates `source-material/.claude/commands/summarize_week.md` in the Weekforge architecture (Tier-0 Python for deterministic work, Tier-2 Pydantic AI for synthesis).

## Prerequisites

Step 0d complete (all infrastructure validated end-to-end).

## Sub-Step Sequence

Step 1 is split into four sub-steps so each can be implemented independently by a weaker model. Each sub-step has its own input contract (the artifacts produced by the previous sub-step) and acceptance criteria.

| # | Sub-Step | Focus | Status |
|---|----------|-------|--------|
| 1a | [Context & CLI](./step-1a-context-and-cli.md) | Prompts dir (persona, guardrails), `.env` DB IDs, user-profile Notion DB + loader, `weekforge summarize <week>` CLI | ⬜ |
| 1b | [Tier-0 Extraction](./step-1b-tier0-extraction.md) | Pure-Python parsing of sessions, role classification, checkbox analysis, delta analysis. Pydantic `WeekSummary` models. | ⬜ |
| 1c | [Summary Agent & Workflow](./step-1c-summary-agent.md) | `summarize_agent` (Pydantic AI), `extraction.py` workflow, single HITL acceptance gate with feedback loop | ⬜ |
| 1d | [Notion Write & PLAN_STATE](./step-1d-notion-write-and-plan-state.md) | `WeekSummary` → legacy text renderer, Notion write, PLAN_STATE incremental/bootstrap | ⬜ |

## Architectural Summary

- **Source material fidelity.** Every behavior from `summarize_week.md` — week-prefix parse, existing-summary overwrite check, exercise role classification, checkbox analysis, delta analysis, summary format, PLAN_STATE update — maps to a named acceptance criterion in one of the sub-steps.
- **Tier split.** Deterministic work (parsing, arithmetic, format rendering) is Tier-0 Python in `tools/extraction.py`. Synthesis (interpretation, wins/issues, recommendations, highlights/trend) is Tier-2 in `summarize_agent`.
- **HITL shape.** One gate only: *accept summary*. Fetch validation removed — Notion API fetch is trusted; a genuinely empty result is a hard fail with a clear message. The accept gate renders `highlights` + `trend` for quick review, with the full `WeekSummary` available as a collapsed panel; feedback re-runs the agent with message history (same pattern as [e2e.py](../../src/weekforge/workflows/e2e.py)).
- **Prompt composition.** `summarize_agent` uses Pydantic AI `instructions=` (static, for persona + guardrails, cacheable prefix) plus `@agent.instructions` decorators (dynamic, for per-run user profile and Tier-0 facts via `RunContext`). See sub-step 1c for the composition.
- **Config storage split.** Persona and guardrails ship as local markdown in `src/weekforge/prompts/` (internal, stable). User profile lives in a single Notion page loaded as markdown (user-changeable, no typed properties — see DEC-007).
- **`run_log` retired.** Legacy `run_log` DB is dropped. In-flight workflow state lives in SQLite checkpoint. The approved week plan is persisted by step-2 as a `Plan` property on the `training_week_summaries` row (see [step-2 spec update](#step-2-spec-update-delta-analysis-source)) and read back by step-1 for delta analysis.

## Data Contracts Across Sub-Steps

```
1a (prompts loaded, CLI, DB IDs)
   └─ produces: settings, prompts.loader, UserProfile loader, CLI entry
1b (pure Python)
   └─ consumes: session payloads (Notion query results), run_log-equivalent (Plan property)
   └─ produces: WeekSummary Pydantic models (with ImplicitFeedback + PlanAdherence pre-filled)
1c (LLM synthesis)
   └─ consumes: 1a loaders + 1b models
   └─ produces: completed WeekSummary with LLM-filled fields (wins, issues, recs, highlights, trend)
1d (persistence)
   └─ consumes: 1c output
   └─ produces: Notion page in training_week_summaries, updated/bootstrapped PLAN_STATE
```

## Step-2 Spec Update — Delta-Analysis Source

Step-2 currently persists approved plan only in checkpoint. To enable step-1 delta analysis, step-2 must also write the plan to Notion at approval time:

- At plan approval: create (or update) a row in `training_week_summaries` with `Week=W##` and `Plan=<markdown>` property. `Summary` property remains empty until step-1 runs.
- `training_week_summaries` DB needs a `Plan` rich_text property alongside the existing `Week` (text) and whatever property holds the summary body.
- Acceptance: after `weekforge plan` approval, the W## row exists with a non-empty `Plan` property.

This update will be folded into [step-2-planning.md](./step-2-planning.md) as part of the same revision cycle (see decision log DEC-006).

## Reference

- [Patterns](../reference/patterns.md) — Parallelization (concurrent context loading)
- [State Schema](../reference/state-schema.md) — Layer B context state
- [Failure Modes](../reference/failure-modes.md) — Data & context failures, Notion API failures
- [Prompt Style](../reference/prompt-style.md) — Caveman-lite directive
- `source-material/.claude/commands/summarize_week.md` — Legacy authoritative behavior
- `source-material/Claude.md` — Coaching persona
- `source-material/.claude/rules/coaching-guardrails.md` — Safety constraints
- `source-material/.claude/shared/user-profile.md` — User profile seed content
