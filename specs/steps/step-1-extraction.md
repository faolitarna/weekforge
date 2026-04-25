# Step 1: Extraction Subsystem (`summarize_week`) — Index

## Goal

Build post-execution extraction. Summarize a completed training week, generate feedback, and manage PLAN_STATE. Faithfully recreates `source-material/.claude/commands/summarize_week.md` in the Weekforge architecture (Tier-0 Python for deterministic work, Tier-2 Pydantic AI for synthesis).

## Prerequisites

Step 0d complete (all infrastructure validated end-to-end).

## Sub-Step Sequence

Step 1 is split into four sub-steps so each can be implemented independently by a weaker model. Each sub-step has its own input contract (the artifacts produced by the previous sub-step) and acceptance criteria.

| # | Sub-Step | Focus | Status |
|---|----------|-------|--------|
| 1a | [Context & CLI](./step-1a-context-and-cli.md) | Prompts dir (persona, guardrails), `.env` DB IDs, user-profile Notion page + loader, `weekforge summarize-week <week>` CLI | ✅ |
| 1b | [Tier-0 Extraction](./step-1b-tier0-extraction.md) | Thin Tier-0: block/comment collection + checkbox arithmetic. Pydantic `WeekSummary` contract. | ✅ |
| 1c | [Summary Agent & Workflow](./step-1c-summary-agent.md) | `summarize_week_agent` (Pydantic AI), `summarize_week.py` workflow, single HITL acceptance gate with feedback loop | ✅ |
| 1d | [Notion Write & PLAN_STATE](./step-1d-notion-write-and-plan-state.md) | `WeekSummary` → legacy text renderer, Notion write, PLAN_STATE incremental/bootstrap | ✅ |
| 1e | [Summary Format Alignment](./step-1e-summary-formatting.md) | Align renderer to source-material `<summary-format>` — pipe-delimited, token-optimized for LLM consumption | ✅ |
| 1f | [Exercise Log Extraction](./step-1f-exercise-log-extraction.md) | Pass raw session blocks + PLAN_STATE to summary agent; populate exercise_log, cardio_log, climbing_log; reorder plan_state_check before agent | ✅ |

## Implementation Status

All sub-steps (1a–1f) complete. 136 tests pass.

**Post-completion refinements (DEC-010):**
- Agent renames: `summarize_agent.py` → `summarize_week_agent.py`, `plan_state_agent.py` → `update_plan_state_agent.py`.
- Prompt extraction: all embedded LLM text moved to `src/weekforge/prompts/*.md` files. `CAVEMAN_LITE_DIRECTIVE` and `_PLAN_STATE_TASK` no longer inline in Python.
- `prompt_composer.compose_static_instructions()` parameterized — accepts `task: Prompt` so each agent gets correct task instructions.
- Model class split: `summarize_week_agent` uses `fast` profile (`gpt-5.4-mini`, Chat Completions, no reasoning overhead). `update_plan_state_agent` uses `reasoning` profile (`gpt-5.4`, Responses API). See DEC-010.
- LLM profiles expanded: `gpt-5.4-mini`, `gpt-5.4-medium`, `gpt-5.4-low` added. Defaults: `FAST_PROFILE=gpt-5.4-mini`, `REASONING_PROFILE=gpt-5.4-medium`.
- `update-plan-state-task.md` prompt strengthened with field-by-field specs (trends not lists, issue lifecycle, progression-protocol awareness).
- `_filter_week_for_plan_state()` strips noise (warmup exercises) from WeekSummary before sending to plan_state agent.
- `pricing.py` updated with `gpt-5.4-mini` rates.
- Verbose debug output + Rich spinner animation during LLM calls, gated behind `VERBOSE` env setting.

**Remaining follow-ups (not blockers, tracked at the spec level):**
- `overwrite_check` workflow step is a no-op pass-through in [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — the prompt described in 1a/1c is not wired yet.
- **Test isolation: prevent accidental real Notion API calls.** `notion_api_gateway` creates `_client = Client(auth=...)` at module import time. Any test that imports from that module gets a live client; incomplete mocks silently leak real HTTP requests. Fix: (a) add a conftest fixture that globally patches `_client` for all unit tests, (b) consider lazy client initialization or a factory, (c) mark intentional integration tests with `@pytest.mark.integration` per feature-tester agent guidelines. See also: `workflows/summarize_week.py` still imports `_client` directly for `assemble_raw_week` — another private API boundary violation to clean up.

## Architectural Summary

- **Source material fidelity.** Every behavior from `summarize_week.md` — week-prefix parse, existing-summary overwrite check, exercise role classification, checkbox analysis, delta analysis, summary format, PLAN_STATE update — maps to a named acceptance criterion in one of the sub-steps.
- **Tier split.** Deterministic work (parsing, arithmetic, format rendering) is Tier-0 Python in `tools/raw_session_collector.py`, `tools/plan_state.py`, and `tools/week_summary_renderer.py`. Synthesis (interpretation, wins/issues, recommendations, highlights/trend) is Tier-2 in `summarize_week_agent`. Trend analysis and issue lifecycle in `update_plan_state_agent`.
- **HITL shape.** One gate only: *accept summary*. Fetch validation removed — Notion API fetch is trusted; a genuinely empty result is a hard fail with a clear message. The accept gate renders `highlights` + `trend` for quick review, with the full `WeekSummary` available as a collapsed panel; feedback re-runs the agent with message history (same pattern as [e2e.py](../../src/weekforge/workflows/e2e.py)).
- **Prompt composition.** Both agents use `compose_static_instructions(task: Prompt, caveman_mode)` — shared coaching prefix (persona + guardrails + feedback-interpretation + progression-protocol) plus per-agent task section. `@agent.instructions` decorators inject dynamic per-run context via `RunContext`. See sub-step 1c for the composition.
- **Model class split (DEC-010).** `summarize_week_agent` uses `fast` profile (extraction, no reasoning needed). `update_plan_state_agent` uses `reasoning` profile (trend interpretation, issue lifecycle). Both env-configurable via `FAST_PROFILE` / `REASONING_PROFILE`.
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
