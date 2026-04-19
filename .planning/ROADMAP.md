# Project Roadmap

**4 phases** | **7 requirements mapped** | All v1 requirements covered ✓

| # | Phase | Goal | Requirements | Success Criteria |
|---|-------|------|--------------|------------------|
| 1 | Extraction | Parse and summarize training week | EXT-01, EXT-02, EXT-03, EXT-04 | 4 |
| 2 | Planning | Collaborative week planning | PLN-01 | 1 |
| 3 | Generation | Draft single session via Evaluator | GEN-01 | 1 |
| 4 | Terminal Review | Mesocycle summary | REV-01 | 1 |

### Phase Details

**Phase 1: Extraction**
Goal: Extract and summarize training week
Requirements: EXT-01, EXT-02, EXT-03, EXT-04
Success criteria:
1. `summarize-week` command extracts all necessary context.
2. Tier-0 tools correctly parse and analyze the data deterministically.
3. LLM summarizes the data with HITL approval gate.
4. Notion updates successfully with new state.

**Phase 2: Planning**
Goal: Interactive collaborative CLI loop for creating next week's training plan
Requirements: PLN-01
Success criteria:
1. User successfully completes a CLI-based interactive planning loop.

**Phase 3: Generation**
Goal: Draft single session via Evaluator
Requirements: GEN-01
Success criteria:
1. Agent creates training session meeting deterministic evaluation criteria before completion.

**Phase 4: Terminal Review**
Goal: Mesocycle summary
Requirements: REV-01
Success criteria:
1. CLI terminal outputs a mesocycle aggregation visualization.
