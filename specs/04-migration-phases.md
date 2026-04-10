---
id: WF-04
title: Migration Strategy & Phases
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-00, WF-01, WF-02, WF-03]
implements-phase: [0, 1, 2, 3, 4]
---

# Iterative Migration Strategy

## Phase 0: Project Bootstrap & Hello World

**Goal:** Establish a working LangGraph project with all integrations verified end-to-end before any feature work begins.

- Project scaffold — Python project structure, dependency management, virtual environment
- LangGraph hello-world graph — a minimal state graph with one node, one checkpoint, and one HITL interrupt to validate the framework works
- Notion API integration — connect to the existing Notion workspace, verify CRUD operations against a test database
- Secrets management — API keys (LLM providers, Notion) stored securely, never in source control
- Model abstraction layer — basic Tier-1/Tier-2 provider switching so the first real feature can already use tiered intelligence
- CLI skeleton — minimal entry point using rich terminal libraries, validating the developer experience

**Exit criteria:** A runnable graph that loads data from Notion, passes it through an LLM node, pauses for HITL input, and writes a result back to Notion. All infrastructure decisions validated before committing to feature development.

## Phase 1: The Extractor Subsystem (`summarize_week`)

**Goal:** Build the first real feature on top of Phase 0 infrastructure. `summarize_week` is the ideal starting point — it has no HITL, no generation loops, and heavily exercises the Notion tool layer.

- Build the Generic Notion Tool Layer (Query, Fetch, Create, Update primitives)
- Implement session data extraction — parse Notion `to_do` blocks, comments, properties into structured exercise logs
- Implement the PLAN_STATE lifecycle — create/incremental-update logic for the cumulative mesocycle tracker
- First real use of Tier-2 intelligence — feedback synthesis and recommendation generation
- Validate the Parallelization pattern with concurrent feedback queries

**Exit criteria:** Run `summarize_week` against real Notion training data, produce a correctly formatted summary, and create/update PLAN_STATE.

## Phase 2: The Unified Planning Engine (`plan_week`)

**Goal:** Build the macro planner — the first feature requiring HITL and checkpointer persistence.

- Implement state initialization (user provides `week_target`, graph computes everything else)
- Build template loading and feedback loading tool nodes
- Implement the Planning pattern — collaborative shaping with HITL plan revision loop
- First real use of `interrupt_before` / checkpoint resume across terminal sessions
- Validate the State Schema — workflow state, context loading, and plan output

**Exit criteria:** Generate a macro week plan from templates + feedback, pause for human review, accept feedback and re-plan, persist across terminal close/reopen via checkpoint.

## Phase 3: The Generative Loop & Evaluators (`draft_session`, `approve_session`)

**Goal:** Build the iterative session generation loop — the core of Lifecycle A.

- Implement the Evaluator-Optimizer two-stage gate — Deterministic Evaluator with structural validation, guardrail enforcement, and context grounding verification
- Build the draft → evaluate → HITL → write → next loop with automatic session progression
- Implement idempotent writes for crash safety during Notion writes
- Validate append reducer on `written_sessions` across checkpoint resume
- Full end-to-end test of Lifecycle A: init → plan → approve plan → draft all sessions → write all to Notion

**Exit criteria:** Complete a full week generation (8-12 sessions) with at least one re-draft triggered by the Deterministic Evaluator and one by human feedback, all sessions written to Notion.

## Phase 4: Final Analytics (`summarize_plan`)

**Goal:** Build the mesocycle terminal review — Lifecycle C.

- Aggregate all weekly summaries into a single plan-level analysis
- Trace strength progressions, SI joint patterns, adherence trends across the full block
- Produce recommendations for the next training cycle
- Straightforward extension of the Notion tool layer from Phase 1 — no new infrastructure

**Exit criteria:** Generate a plan summary from real weekly summaries spanning multiple weeks, written to Notion as `PLAN_SUMMARY`.
