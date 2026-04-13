# Weekforge Specs — Status Dashboard

> **Status**: ⬜ Not Started | 🔄 In Progress | ✅ Done

## Implementation Steps

| # | Step | Description | Status |
|---|------|-------------|--------|
| 0a | [Minimal Graph](./steps/step-0a-minimal-graph.md) | LangGraph hello world: state, node, HITL, checkpoint | ✅ |
| 0b | [Notion Tools](./steps/step-0b-notion-tools.md) | Notion tool layer: CRUD contracts + integration | ⬜ |
| 0c | [LLM Integration](./steps/step-0c-llm-integration.md) | Model config, LLM calls, metadata capture | ⬜ |
| 0d | [End-to-End](./steps/step-0d-end-to-end.md) | Full loop: Notion -> LLM -> HITL -> Notion + CLI | ⬜ |
| 1 | [Extraction](./steps/step-1-extraction.md) | `summarize_week` — first real feature | ⬜ |
| 2 | [Planning](./steps/step-2-planning.md) | `plan_week` with HITL collaborative shaping | ⬜ |
| 3 | [Generation](./steps/step-3-generation.md) | `draft_session` + Deterministic Evaluator loop | ⬜ |
| 4 | [Terminal Review](./steps/step-4-terminal-review.md) | `summarize_plan` — mesocycle analysis | ⬜ |

## Reference Docs

Background architecture — read once for context, not required during implementation.

- [Architecture](./reference/architecture.md) — System overview, intelligence tiering, CLI, tooling
- [Patterns](./reference/patterns.md) — Agentic design patterns applied to Weekforge
- [State Schema](./reference/state-schema.md) — Three-layer graph state
- [Failure Modes](./reference/failure-modes.md) — Error handling catalog

## Other

- [Decision Log](./decision-log.md) — Append-only record of architectural choices
