---
id: WF-LA2
title: Lifecycle A - Generative Loop
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-01, WF-02, WF-LA1]
implements-phase: [3]
---

# Lifecycle A: Generative Loop (`draft_session`)

Following the completion of the Planning Engine ([WF-LA1](./lifecycle-a-planning.md)), the workflow transitions into an iterative Generation Loop.

**Iterative Generation Loop** — On plan approval, the graph automatically loops over the session array. Each session is drafted, passed through the Deterministic Evaluator, then paused for HITL review. On approval, the session is written and the next is drafted automatically.

> **Graph Topology:** See the Full Lifecycle A Diagram in [WF-LA1](./lifecycle-a-planning.md).

## Generation Edge Conditions

The subset of edge routing representing the generation loop:

| From | To | Condition |
|------|-----|-----------|
| Draft Session | Evaluator | Always — every draft is validated |
| Evaluator | Draft Session | Validation fails AND retry count ≤ max |
| Evaluator | HITL Session Review | Validation passes OR circuit breaker triggers (with warning) |
| HITL Session Review | Draft Session | User provides feedback → re-draft |
| HITL Session Review | Write to Notion | User approves |
| Write to Notion | Draft Session | `len(written_sessions) < sessions_total` → next session |
| Write to Notion | Complete | `len(written_sessions) == sessions_total` → done |
