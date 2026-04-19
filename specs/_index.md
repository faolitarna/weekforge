# Weekforge Specs — Status Dashboard

> **Status**: ⬜ Not Started | 🔄 In Progress | ✅ Done

## Implementation Steps

| # | Step | Description | Status |
|---|------|-------------|--------|
| 0a | [Minimal Workflow](./steps/step-0a-minimal-workflow.md) | Workflow foundation: state, checkpoint, HITL, Pydantic AI | ✅ |
| 0b | [Notion Tools](./steps/step-0b-notion-tools.md) | Notion tool layer: CRUD contracts + integration | ✅ |
| 0c | [LLM Integration](./steps/step-0c-llm-integration.md) | Pydantic AI agent setup, model config, metadata capture | ✅ |
| 0d | [End-to-End](./steps/step-0d-end-to-end.md) | Full loop: Notion -> Agent -> HITL -> Notion + CLI | ✅ |
| 1 | [Extraction](./steps/step-1-extraction.md) | `summarize_week` — first real feature (index → sub-steps 1a–1d) | ⬜ |
| 1a | [Context & CLI](./steps/step-1a-context-and-cli.md) | Prompts dir, DB IDs, user-profile Notion DB + loader, `summarize <week>` CLI | ⬜ |
| 1b | [Tier-0 Extraction](./steps/step-1b-tier0-extraction.md) | Pure-Python parsing, role classification, checkbox + delta analysis | ⬜ |
| 1c | [Summary Agent & Workflow](./steps/step-1c-summary-agent.md) | `summarize_agent`, workflow, single HITL accept gate with feedback loop | ⬜ |
| 1d | [Notion Write & PLAN_STATE](./steps/step-1d-notion-write-and-plan-state.md) | Legacy-format renderer, Notion row update, PLAN_STATE incremental/bootstrap | ⬜ |
| 2 | [Planning](./steps/step-2-planning.md) | `plan_week` with HITL collaborative shaping | ⬜ |
| 3 | [Generation](./steps/step-3-generation.md) | `draft_session` + Deterministic Evaluator loop | ⬜ |
| 4 | [Terminal Review](./steps/step-4-terminal-review.md) | `summarize_plan` — mesocycle analysis | ⬜ |

## Reference Docs

Background architecture — read once for context, not required during implementation.

- [Architecture](./reference/architecture.md) — System overview, intelligence tiering, CLI, tooling
- [Patterns](./reference/patterns.md) — Agentic design patterns applied to Weekforge
- [State Schema](./reference/state-schema.md) — Three-layer workflow state
- [Failure Modes](./reference/failure-modes.md) — Error handling catalog
- [Prompt Style](./reference/prompt-style.md) — Caveman-lite directive, global `CAVEMAN_MODE` toggle

## Other

- [Decision Log](./decision-log.md) — Append-only record of architectural choices
