# Agentic Design Patterns

This specification details how Weekforge applies theoretical Agentic Patterns (per `Agentic Design Patterns.pdf`) to solve its workflows.

## Checkpoint Store (HITL)

Weekforge workflows checkpoint state to a lightweight SQLite store before each HITL pause. Because the app is a CLI tool, this allows the user to close the terminal and later resume the execution thread exactly where they left it.

**Legacy `resume` command — eliminated.** The legacy system needed a 162-line `resume` command because Claude Code chat sessions lost all context on terminal close. The checkpoint store makes this unnecessary — workflow state (Pydantic models) is serialized via `model_dump_json()` after each significant step and restored via `model_validate_json()` on the next invocation with the same `thread_id`.

**Checkpoint store design.** A single SQLite table with columns: `thread_id`, `workflow`, `step`, `state_json`, `updated_at`. Methods: `save()`, `load()`, `list_active()`, `delete()`. Each workflow function saves checkpoints at explicit points (before HITL pauses, after writes). The `step` label identifies where to resume.

**HITL pattern.** Each HITL pause is a function call that: (1) saves state to checkpoint, (2) renders a Rich panel with Context/Options/Recommendation, (3) reads user input, (4) returns a decision (approve, feedback, quit). If the user quits or the process crashes, the checkpoint is already saved. On next CLI invocation, the workflow loads state and jumps to the correct step.

**Idempotent writes (crash safety).** If the process crashes after a Notion write succeeds but before the checkpoint saves, the workflow would retry the write on resume. To prevent duplicates, all Notion write operations must be **idempotent** — check if the target (e.g., session with matching name + week) already exists before creating. This single guard replaces the legacy's stage validation, session reconciliation, and context reload logic.

## Evaluator-Optimizer (Two-Stage Validation Gate)

The session review loop uses an automated evaluator **before** HITL. The user only ever sees pre-validated, reasoning-verified output.

**Stage 1 — Deterministic Evaluator (Python, Tier-0, pre-HITL).** Runs automatically after every session draft. Pure Python, zero LLM cost. If any check fails, the draft is auto-retried with specific error feedback — the user is never shown a failing draft.

- **Structural validation:** Checkbox format (`- [ ]`), required fields (Duration, Location, Objective, Intensity, Equipment), no plain bullet exercises.
- **Guardrail enforcement:** Flare substitution compliance when `ACTIVE_FLARE = YES`, progression protocol adherence, duration budget, focus exercise pacing vs 8+ weekly target.
- **Context grounding verification** (prevents the LLM from ignoring template/feedback data):
  - **Template reference:** Reasoning block must name the specific template session used and list what was kept vs changed.
  - **Feedback citation:** Must cite at least one specific data point from feedback with its source week.
  - **Progression justification:** Each returning exercise must show: last performed -> signal -> decision tree path -> new parameters.
  - **Flare acknowledgment:** If `ACTIVE_FLARE = YES`, must list which exercises were substituted and why.

The Evaluator checks for **presence and structure** of reasoning, not quality. Quality judgment remains with the human.

**Stage 2 — HITL Review (Human, pre-validated output).** Human focus shifts to qualitative judgment ("Does this feel right?") rather than catching formatting errors. Human can: approve, provide freeform feedback (-> re-draft), or abort.

## Prompt Chaining

For linear data pipelines where the output of one step feeds directly into the next.

## Parallelization (Concurrent Context Loading)

The legacy system loads PLAN_STATE and 3 previous weeks of feedback sequentially — each is an independent Notion query. These are I/O-bound operations with no data dependencies between them, making them ideal for concurrent execution.

**Approach.** When a node needs the feedback context, fire all queries concurrently (e.g., `asyncio.gather`) and merge results into a single structured feedback context. This is a Tier-0 operation.

**Expected benefit.** ~3-4x latency reduction on context loading.

## Planning (Collaborative Shaping)

The macro week plan is not a one-shot generation — it is an iterative **collaborative shaping** loop between the LLM and the user. The LLM generates a plan based on templates, feedback, and PLAN_STATE; the user reviews it and can provide freeform feedback to reshape priorities before any sessions are generated.

**Plan Revision Loop.** A `while True` loop calls `planning_agent.run()` with conversation history, pauses for HITL review, and breaks on user approval. User feedback is appended to the message history so the agent sees its previous plan and the user's corrections. The loop repeats until the user explicitly approves. Only then does the workflow transition to the generation phase.
