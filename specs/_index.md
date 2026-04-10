# Weekforge Specs — Status Dashboard

This is the control center for the Spec-Driven Development of Weekforge. 

> **Legend**: 
> 📝 Draft | 🔄 In Review | ✅ Approved | 🚀 Implemented | 🗑️ Deprecated

## Core Artifacts
- **[SDD Practices](../.agents/skills/specs-management/SKILL.md)** — Specs management process (project skill)
- **[Decision Log](./decision-log.md)** — Append-only record of architectural choices
- **[Traceability Matrix](./traceability-matrix.md)** — Mapping between spec features, code, and tests

## Specifications

| ID | Spec | Status | Version | Phase |
|----|------|--------|---------|-------|
| WF-00 | [System Overview](./00-system-overview.md) | 📝 Draft | 1.0 | 0 |
| WF-01 | [Agentic Patterns](./01-agentic-patterns.md) | 📝 Draft | 1.0 | 0-3 |
| WF-02 | [State Schema](./02-state-schema.md) | 📝 Draft | 1.0 | 0-3 |
| WF-03 | [Failure Modes](./03-failure-modes.md) | 📝 Draft | 1.0 | 0-3 |
| WF-04 | [Migration Phases](./04-migration-phases.md) | 📝 Draft | 1.0 | 0-4 |
| WF-LA1 | [Lifecycle A: Planning](./features/lifecycle-a-planning.md) | 📝 Draft | 1.0 | 2 |
| WF-LA2 | [Lifecycle A: Generation](./features/lifecycle-a-generation.md) | 📝 Draft | 1.0 | 3 |
| WF-LB | [Lifecycle B: Extraction](./features/lifecycle-b-extraction.md) | 📝 Draft | 1.0 | 1 |
| WF-LC | [Lifecycle C: Terminal](./features/lifecycle-c-terminal.md) | 📝 Draft | 1.0 | 4 |
| WF-OBS | [Observability](./cross-cutting/observability.md) | 📝 Draft | 0.1 | 0 |
| WF-TEST | [Testing Strategy](./cross-cutting/testing-strategy.md) | 📝 Draft | 0.1 | 0 |
| WF-PROMPT | [Prompt Architecture](./cross-cutting/prompt-architecture.md) | 📝 Draft | 0.1 | 0 |

## Dependency Graph

```mermaid
graph LR
    subgraph Core System
        WF00["[WF-00]<br>System Overview"] --> WF01["[WF-01]<br>Agentic Patterns"]
        WF00 --> WF02["[WF-02]<br>State Schema"]
        WF01 --> WF02
        WF01 --> WF03["[WF-03]<br>Failure Modes"]
        WF02 --> WF03
    end

    subgraph Features
        WF01 --> WFLB["[WF-LB]<br>Lifecycle B: Extraction"]
        WF02 --> WFLB

        WF01 --> WFLA1["[WF-LA1]<br>Lifecycle A: Planning"]
        WF02 --> WFLA1

        WF01 --> WFLA2["[WF-LA2]<br>Lifecycle A: Generation"]
        WF02 --> WFLA2
        WFLA1 --> WFLA2

        WFLB --> WFLC["[WF-LC]<br>Lifecycle C: Terminal"]
    end
    
    subgraph Cross-Cutting
        WF00 -.-> WFOBS["[WF-OBS]<br>Observability"]
        WF00 -.-> WFPROMPT["[WF-PROMPT]<br>Prompt Architecture"]
        WFOBS -.-> WFTEST["[WF-TEST]<br>Testing Strategy"]
    end

    WF04["[WF-04]<br>Migration Phases"]
```
