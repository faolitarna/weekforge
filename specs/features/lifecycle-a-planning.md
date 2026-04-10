---
id: WF-LA1
title: Lifecycle A - Unified Planning Engine
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-01, WF-02]
implements-phase: [2]
---

# Lifecycle A: Planning Engine (`plan_week`)

The legacy system required the user to manually trigger isolated CLI commands in exact sequence (`init` → `plan` → `draft` → `approve`). The migration optimizes this by creating a unified graph state.

Instead of typing separate commands, the system offers a unified CLI entry point. The LangGraph state machine will automatically traverse:

1. **Initialize State**
2. **Plan Macro Strategy**
   - → graph pauses for HITL review of macro plan.
   - → if user provides feedback, graph loops back to re-plan with user input (Planning pattern).
   - → if user approves, graph transitions to generation.

## Full Lifecycle A Graph Topology

> Note: This diagram covers both Planning (this spec) and Generation ([WF-LA2](./lifecycle-a-generation.md)).

```mermaid
graph TD
    A["Entry"] --> B["Load Context<br/>(template + feedback, parallel)"]
    B --> C["Plan Week<br/>(Tier-2 LLM)"]
    C --> D{"HITL:<br/>Plan Review"}
    D -->|"user provides feedback"| C
    D -->|"user approves"| E["Draft Session<br/>(Tier-2 LLM)"]
    E --> F["Deterministic Evaluator<br/>(Tier-0 Python)"]
    F -->|"validation fails<br/>(retry ≤ max)"| E
    F -->|"circuit breaker<br/>(retry > max)"| G
    F -->|"validation passes"| G{"HITL:<br/>Session Review"}
    G -->|"user provides feedback"| E
    G -->|"user approves"| H["Write to Notion<br/>(idempotent)"]
    H -->|"written < total"| E
    H -->|"written == total"| I["Complete"]
```

## Planning Edge Conditions

The subset of edge routing representing the planning phase:

| From | To | Condition |
|------|-----|-----------|
| Entry | Load Context | Always — first node on every invocation |
| Load Context | Plan Week | Context loaded (template + feedback merged) |
| Plan Week | HITL Plan Review | Always — plan generated, interrupt for review |
| HITL Plan Review | Plan Week | User provides freeform feedback → re-plan |
| HITL Plan Review | Draft Session | User approves → begin generation |
