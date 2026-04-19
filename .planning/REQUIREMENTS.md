# Requirements

## Extraction
- [ ] **EXT-01**: Parse 1a CLI arguments and load context.
- [ ] **EXT-02**: Extract data via pure-Python validation and delta analysis (Tier-0).
- [ ] **EXT-03**: Summarize weekly training data via LLM with HITL acceptance gate.
- [ ] **EXT-04**: Save updated weekly summary state back to Notion.

## Planning
- [ ] **PLN-01**: Provide interactive collaborative CLI loop for creating next week's training plan.

## Generation
- [ ] **GEN-01**: Draft session using Deterministic Evaluator loop to ensure validation before saving.

## Review
- [ ] **REV-01**: Summarize multi-week mesocycle via terminal reports.

## Out of Scope
- Direct Data Mutation by LLMs — Agents never touch Notion directly; strict Tier-0 tools mediate to prevent data corruption.
- Heavy Workflow Frameworks — Migrated away from LangGraph; plain Python while loops suffice and reduce dependency weight.

### Traceability

| Requirement | Phase |
|-------------|-------|
| EXT-01 | Phase 1 |
| EXT-02 | Phase 1 |
| EXT-03 | Phase 1 |
| EXT-04 | Phase 1 |
| PLN-01 | Phase 2 |
| GEN-01 | Phase 3 |
| REV-01 | Phase 4 |
