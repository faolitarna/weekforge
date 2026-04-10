---
id: WF-LC
title: Lifecycle C - Terminal Review
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-LB]
implements-phase: [4]
---

# Lifecycle C: Mesocycle Terminal Review (`summarize_plan`)

Run completely independently on-demand after a prolonged training block (8-12 weeks) is completed.

Aggregates all weekly summaries to deduce macro strength progressions and persistent pain patterns.

## Graph Topology

```mermaid
graph TD
    A["Entry"] --> B["Query All Summaries<br/>(Notion Tool)"]
    B --> C{"HITL:<br/>Verify Summaries"}
    C -->|"user confirms"| D["Analyze & Generate<br/>(Tier-2 LLM)"]
    D --> E["Write Plan Summary<br/>(Notion Tool)"]
    E --> F["Complete"]
```

## Edge Conditions

| From | To | Condition |
|------|-----|-----------|
| Entry | Query All Summaries | Always — fetch all weekly summaries |
| Query All Summaries | HITL Verify Summaries | Summaries found — confirm correct set |
| HITL Verify Summaries | Analyze & Generate | User confirms |
| Analyze & Generate | Write Plan Summary | Plan summary generated (Tier-2 LLM) |
| Write Plan Summary | Complete | Written to Notion as `PLAN_SUMMARY` |
