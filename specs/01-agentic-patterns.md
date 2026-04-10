---
id: WF-01
title: Agentic Design Patterns
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-00]
implements-phase: [0, 1, 2, 3]
---

# Agentic Design Patterns

This specification details how the Weekforge application applies theoretical Agentic Patterns (per `Agentic Design Patterns.pdf`) to solve its workflows.

## State Graph with Checkpointers (HITL)

Implements explicit `interrupt_before` / `interrupt_after` boundaries. Because the app is a CLI tool, LangGraph's persistent checkpointer allows the user to close the terminal, and later resume the execution thread exactly where they left it.

**Legacy `resume` command — eliminated.** The legacy system needed a 162-line `resume` command because Claude Code chat sessions lost all context on terminal close. LangGraph's checkpoint system makes this unnecessary — state is persisted to disk after every node transition and restored automatically on the next invocation with the same `thread_id`.

**Idempotent writes (crash safety).** If the process crashes after a Notion write succeeds but before the checkpoint saves, the graph would retry the write on resume. To prevent duplicates, all Notion write operations must be **idempotent** — check if the target (e.g., session with matching name + week) already exists before creating. This single guard replaces the legacy's stage validation, session reconciliation, and context reload logic.

## Evaluator-Optimizer (Two-Stage Validation Gate)

The session review loop uses an automated evaluator **before** HITL. The user only ever sees pre-validated, reasoning-verified output.

**Stage 1 — Deterministic Evaluator (Python, Tier-0, pre-HITL).** Runs automatically after every session draft. Pure Python, zero LLM cost. If any check fails, the draft is auto-retried with specific error feedback — the user is never shown a failing draft.

- **Structural validation:** Checkbox format (`- [ ]`), required fields (Duration, Location, Objective, Intensity, Equipment), no plain bullet exercises. *(Absorbs the legacy `validate-session-format.sh` hook.)*
- **Guardrail enforcement:** Flare substitution compliance when `ACTIVE_FLARE = YES` (from exercise guardrails), progression protocol adherence for every returning exercise (from progression protocol), duration budget (exercises + rest fit session length), focus exercise pacing vs 8+ weekly target.
- **Context grounding verification** *(prevents the LLM from ignoring template/feedback data):*
  - **Template reference:** Reasoning block must name the specific template session used and list what was kept vs changed.
  - **Feedback citation:** Must cite at least one specific data point from feedback (weight, pain report, adherence %) with its source week — proves summaries/PLAN_STATE were actually processed, not just loaded.
  - **Progression justification:** Each returning exercise must show: last performed → signal → decision tree path → new parameters.
  - **Flare acknowledgment:** If `ACTIVE_FLARE = YES`, must list which exercises were substituted and why.

The Evaluator checks for **presence and structure** of reasoning, not quality. It answers: "Did the model show its work?" Quality judgment remains with the human.

**Stage 2 — HITL Review (Human, pre-validated output).** The human reviews sessions that have already passed all codified guardrails. Human focus shifts to qualitative judgment ("Does this feel right for how my body feels?") rather than catching formatting errors or missed progressions. Human can: approve, provide freeform feedback (→ re-draft), or abort.

## Prompt Chaining

For linear data pipelines where the output of one step feeds directly into the next.

## Parallelization (Concurrent Context Loading)

The legacy system loads PLAN_STATE and 3 previous weeks of feedback sequentially — each is an independent Notion query. These are I/O-bound operations with no data dependencies between them, making them ideal for concurrent execution.

**Approach.** When a node needs the feedback context (used by both `plan_week` and `draft_session`), fire all queries concurrently (e.g., `asyncio.gather`) and merge results into a single structured feedback context. This is a Tier-0 operation — pure Python, no LLM involvement.

**Expected benefit.** ~3-4x latency reduction on context loading, which is the longest synchronous wait in the legacy workflow. Applies anywhere multiple independent Notion queries feed the same downstream node.

## Planning (Collaborative Shaping)

The macro week plan is not a one-shot generation — it is an iterative **collaborative shaping** loop between the LLM and the user. The LLM generates a plan based on templates, feedback, and PLAN_STATE; the user reviews it and can provide freeform feedback to reshape priorities, session distribution, or intensity before any sessions are generated.

**Plan Revision Loop.** The graph edge from HITL plan review routes back to the planner node when the user provides feedback, carrying the user's input as additional context. The loop repeats until the user explicitly approves. Only then does the graph transition to the generation phase. This prevents the common failure mode of generating 8-12 sessions from a plan the user wasn't satisfied with.
