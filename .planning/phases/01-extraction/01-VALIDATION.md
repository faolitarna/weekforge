# Phase 01: Validation Strategy

## Goal-Backward Validation
Goal: parse, synthesize, review, and persist weekly training data reliably.

## Verification Matrix
1. **Tier-0 Isolation**: `collect_blocks` does not parse string structure. It only accesses Notion fields by `.get()`. (Grep verification).
2. **LLM Output Strictness**: `WeekSummary` outputs parsed attributes reliably into loose strings where needed but structure is consistent.
3. **State Recovery**: If we kill the process at `HITL`, resume restores the prompt window correctly.
4. **Bootstrapping**: If `PLAN_STATE` row is deleted, running extraction creates it successfully.
5. **No Terminal Flooding**: The HITL output prints `highlights` and not the full JSON string.
