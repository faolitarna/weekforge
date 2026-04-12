# Failure Modes & Fallbacks

Every failure mode below is grounded in a problem that either occurred in the legacy workflow or was explicitly guarded against by the legacy command files.

## LLM Output Failures

The most dangerous failures — they can be **silently wrong**. The Deterministic Evaluator is the primary defense.

**Model ignores template and copies previous week.** Most common legacy failure. The LLM had template + summaries + PLAN_STATE in context but took the lazy path.
- **Defense:** Context grounding verification in the Evaluator. Must cite the specific template used and list what was kept vs changed.

**Model skips progression decision tree.** Repeats previous weight/sets/reps instead of walking the protocol.
- **Defense:** Evaluator requires explicit progression justification for every returning exercise.

**Model ignores active flare.** Programs standard exercises despite `ACTIVE_FLARE = YES`.
- **Defense:** Evaluator checks flare-safe substitutions when flare flag is set.

**Malformed session format.** Plain bullet exercises instead of checkboxes, or missing required fields.
- **Defense:** Structural validation in the Evaluator (absorbed from legacy `validate-session-format.sh` hook).

**Circuit breaker.** After configurable max retries (e.g., 3), surface the best failing draft to the human with a warning listing what checks failed.

## Notion API Failures

**Session write fails after drafting.** Retry with exponential backoff (1s -> 2s -> 4s). After max retries, fail-fast — the checkpoint has saved the approved draft, so the user can retry without re-drafting.

**Query returns 0 results due to format mismatch.** Week prefix formatting is computed by Tier-0 tool nodes (always zero-padded), never by the LLM. Format mismatches become impossible.

**Notion rate limiting.** The Generic Notion Tool Layer handles rate limiting internally — backoff and retry at the tool layer, invisible to the graph.

## Data & Context Failures

**PLAN_STATE missing or stale.** Graceful degradation — system works without PLAN_STATE, it just loses long-range context. CLI surfaces a warning.

**Feedback data partially available.** Load whatever is available, note gaps in the plan's context display.

**Contradictory feedback signals.** Priority order from `feedback-interpretation.md` is embedded in the system prompt. Pain always wins. The Evaluator cannot catch semantic misinterpretation — HITL responsibility.

## Response Strategy Summary

| Failure Type | Strategy | Who Handles It |
|-------------|----------|---------------|
| Malformed LLM output | Auto-reject + retry | Deterministic Evaluator |
| Missing reasoning/citations | Auto-reject + retry | Deterministic Evaluator |
| Flare protocol violation | Auto-reject + retry | Deterministic Evaluator |
| Retry storm | Circuit breaker -> surface to human | Evaluator + CLI |
| Notion write failure | Retry with backoff -> fail-fast | Notion Tool Layer |
| Notion query format mismatch | Prevented by design (Tier-0) | Tool nodes |
| Notion rate limiting | Backoff + retry (transparent) | Notion Tool Layer |
| PLAN_STATE missing | Graceful degradation | Tool nodes + CLI warning |
| Partial feedback data | Graceful degradation | Tool nodes |
| Contradictory signals | Priority rules in prompt + HITL | LLM + Human |
| Semantic hallucination | Human review (last safety net) | HITL |
