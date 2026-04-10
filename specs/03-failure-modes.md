---
id: WF-03
title: Failure Modes and Fallbacks
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-01, WF-02]
implements-phase: [0, 1, 2, 3]
---

# Failure Modes & Fallbacks

Every failure mode below is grounded in a problem that either occurred in the legacy workflow or was explicitly guarded against by the legacy command files.

## LLM Output Failures

These are the most dangerous failures because they can be **silently wrong** — the output looks plausible but is incorrect. The Deterministic Evaluator is the primary defense.

**Model ignores template and copies previous week.** The most common legacy failure — the LLM had template + summaries + PLAN_STATE in context but took the lazy path, repeating last week's parameters without engaging with the template structure. In the legacy system this was undetectable until human review.
- **New defense:** Context grounding verification in the Deterministic Evaluator. The model must cite the specific template used and list what was kept vs changed. Missing citation → auto-reject and retry.

**Model skips progression decision tree.** Instead of walking the protocol (last performed → signal → decision → new parameters), the model just repeats the previous weight/sets/reps. This defeats the "default: push" coaching philosophy.
- **New defense:** Evaluator requires explicit progression justification for every returning exercise. Missing justification → auto-reject.

**Model ignores active flare.** The model programs standard exercises despite `ACTIVE_FLARE = YES`, violating the "pain overrides programming" guardrail.
- **New defense:** Evaluator checks that flare-safe substitutions are applied when flare flag is set. Standard exercises during flare → auto-reject.

**Malformed session format.** The model outputs plain bullet exercises instead of checkboxes, or omits required fields. The legacy system had a dedicated shell hook (`validate-session-format.sh`) specifically because this happened often enough to warrant automation.
- **New defense:** Structural validation in the Evaluator (absorbed from the legacy hook).

**Circuit breaker.** If the Evaluator keeps rejecting and the model keeps failing, a retry storm burns Tier-2 tokens. After a configurable max retry count (e.g., 3 attempts), the system surfaces the best failing draft to the human with a warning listing what checks failed, instead of retrying infinitely.

## Notion API Failures

Every legacy command had explicit error handling for Notion write/query failures. These are transient infrastructure problems.

**Session write fails after drafting.** The session was drafted, reviewed, and approved — but the Notion write fails. The legacy `approve_session` handled this with a simple "display error, ask user to retry."
- **New defense:** Retry with exponential backoff (1s → 2s → 4s). After max retries, fail-fast to the CLI — the checkpoint has saved the approved draft, so the user can retry without re-drafting.

**Query returns 0 results due to format mismatch.** The legacy's most common query bug: searching for `W4` instead of `W04`, or the Notion Week property not matching the expected format. The legacy `summarize_week` error handling explicitly warned about this.
- **New defense:** Week prefix formatting is computed by Tier-0 tool nodes (always zero-padded), never by the LLM. Format mismatches become impossible because the format logic is deterministic Python.

**Notion rate limiting.** Multiple concurrent queries (Parallelization) could hit Notion's API rate limits.
- **New defense:** The Generic Notion Tool Layer handles rate limiting internally — backoff and retry at the tool layer, invisible to the graph. Nodes never see rate limit errors.

## Data & Context Failures

**PLAN_STATE missing or stale.** Both `plan_week` and `draft_session` loaded PLAN_STATE with explicit graceful degradation — if not found, continue with the 3-week feedback window only and warn the user.
- **Strategy:** Graceful degradation. The system works without PLAN_STATE, it just loses long-range context.

**Feedback data partially available.** Not all previous weeks may have summaries (e.g., the user skipped `summarize_week` for W05). The legacy `plan_week` handled this: "If fewer weeks exist, load what is available."
- **Strategy:** Graceful degradation. Load whatever is available, note gaps in the plan's context display.

**Contradictory feedback signals.** The legacy `feedback-interpretation.md` defined a priority order for when multiple signals conflict (e.g., "felt easy" + incomplete sets, or high energy + joint discomfort). The model might resolve these incorrectly.
- **Strategy:** The priority order from `feedback-interpretation.md` is embedded in the system prompt. Pain always wins over other signals. The Evaluator cannot catch semantic misinterpretation — this remains a HITL responsibility.

## Response Strategy Summary

| Failure Type | Strategy | Who Handles It |
|-------------|----------|---------------|
| Malformed LLM output | Auto-reject + retry | Deterministic Evaluator |
| Missing reasoning/citations | Auto-reject + retry | Deterministic Evaluator |
| Flare protocol violation | Auto-reject + retry | Deterministic Evaluator |
| Retry storm (repeated failures) | Circuit breaker → surface to human | Evaluator + CLI |
| Notion write failure | Retry with backoff → fail-fast | Notion Tool Layer |
| Notion query format mismatch | Prevented by design (Tier-0 formatting) | Tool nodes |
| Notion rate limiting | Backoff + retry (transparent) | Notion Tool Layer |
| PLAN_STATE missing | Graceful degradation (3-week window) | Tool nodes + CLI warning |
| Partial feedback data | Graceful degradation (load what exists) | Tool nodes |
| Contradictory feedback signals | Priority rules in prompt + HITL | LLM + Human |
| Semantic hallucination | Human review (last safety net) | HITL |
