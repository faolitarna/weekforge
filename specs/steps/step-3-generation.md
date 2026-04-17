# Step 3: Generative Loop (`draft_session`)

## Goal

Build the iterative session generation loop — draft, evaluate, review, write — the core of Lifecycle A.

## Prerequisites

Step 2 complete (planning engine, approved `week_plan` in state).

## What You're Building

| File | Purpose |
|------|---------|
| `src/weekforge/workflows/generation.py` | Generation loop (Lifecycle A, part 2) |
| `src/weekforge/workflows/evaluator.py` | Deterministic Evaluator (Tier-0 Python validation) |
| `src/weekforge/tools/generation.py` | Session writing tool functions (idempotent Notion writes) |
| `src/weekforge/agents/ (e2e_agent.py, openai_model_factory.py, agent_run_with_metadata.py, prompt_composer.py)` | Add `generation_agent` definition |
| `src/weekforge/models/workflow_state.py` | Extend with generation-specific state model |

## Specification

### Overview

On plan approval (step 2), the workflow automatically loops over the session array. Each session is drafted (Tier-2 agent), passed through the Deterministic Evaluator (Tier-0 Python), then paused for HITL review. On approval, the session is written to Notion and the next is drafted automatically.

### Workflow (Generation Phase)

```mermaid
graph TD
    E["From Plan Approval"] --> F["Draft Session\n(Tier-2 Agent)"]
    F --> G["Deterministic Evaluator\n(Tier-0 Python)"]
    G -->|"validation fails\n(retry <= max)"| F
    G -->|"circuit breaker\n(retry > max)"| H
    G -->|"validation passes"| H{"HITL:\nSession Review"}
    H -->|"user provides feedback"| F
    H -->|"user approves"| I["Write to Notion\n(idempotent)"]
    I -->|"written < total"| F
    I -->|"written == total"| J["Complete"]
```

Nested loops — outer `for` over sessions, inner `while` for evaluator retries:

```python
def run_generation(state: GenerationState, checkpoint: CheckpointStore, thread_id: str):
    for i in range(state.current_session_index, state.sessions_total + 1):
        state.current_session_index = i
        
        # Draft-evaluate loop
        retry_count = 0
        feedback = None
        while True:
            result = generation_agent.run_sync(
                user_prompt=format_session_prompt(state, i, feedback),
            )
            draft = result.data
            run_cost.add(result)
            
            # Deterministic evaluator (Tier-0)
            eval_result = evaluate_session(draft, state)
            if eval_result.passed or retry_count >= MAX_RETRIES:
                break
            feedback = eval_result.errors
            retry_count += 1
        
        # HITL review (pre-validated or circuit-breaker with warning)
        decision = hitl_session_review(draft, eval_result, checkpoint, thread_id, ...)
        if decision.approved:
            page_id = write_session_idempotent(state, draft)
            state.written_sessions.append({"page_id": page_id, "session_name": draft.name})
            checkpoint.save(thread_id, "generation", f"session_{i}_written", state)
        elif decision.feedback:
            feedback = decision.feedback
            continue  # re-draft with human feedback
    
    checkpoint.delete(thread_id)
```

### Edge Conditions

| From | To | Condition |
|------|-----|-----------|
| Draft Session | Evaluator | Always — every draft is validated |
| Evaluator | Draft Session | Validation fails AND retry count <= max |
| Evaluator | HITL Session Review | Validation passes OR circuit breaker triggers (with warning) |
| HITL Session Review | Draft Session | User provides feedback -> re-draft |
| HITL Session Review | Write to Notion | User approves |
| Write to Notion | Draft Session | `len(written_sessions) < sessions_total` -> next session |
| Write to Notion | Complete | `len(written_sessions) == sessions_total` -> done |

### Deterministic Evaluator (Tier-0, Zero LLM Cost)

Runs automatically after every draft. Pure Python. User never sees a failing draft.

**Structural validation:**
- Checkbox format (`- [ ]`), required fields (Duration, Location, Objective, Intensity, Equipment)
- No plain bullet exercises

**Guardrail enforcement:**
- Flare substitution compliance when `active_flare = True`
- Progression protocol adherence for every returning exercise
- Duration budget (exercises + rest fit session length)
- Focus exercise pacing vs 8+ weekly target

**Context grounding verification:**
- **Template reference:** Reasoning must name the specific template session used, list what was kept vs changed
- **Feedback citation:** Must cite at least one specific data point from feedback with its source week
- **Progression justification:** Each returning exercise: last performed -> signal -> decision path -> new parameters
- **Flare acknowledgment:** If `active_flare = True`, must list substituted exercises and why

The Evaluator checks for **presence and structure** of reasoning, not quality. Quality judgment remains with the human.

**Circuit breaker:** After max retries (e.g., 3), surface the best failing draft to the human with a warning listing what checks failed.

### State Fields Used

**Layer C (Output, accumulated):**
- `current_session_index` — Which session we're drafting (1-based)
- `current_draft` — Current draft being reviewed — ephemeral local variable, not checkpointed
- `written_sessions` — Lightweight references `{page_id, session_name}`, plain `list.append()`
- `focus_exercise_count` — Running tally vs 8+ target

### Idempotent Writes

All Notion writes check if the target session (matching name + week) already exists before creating. This prevents duplicates if the process crashes after a write succeeds but before the checkpoint saves.

### Failure Handling

- **LLM ignores template:** Context grounding verification catches it -> auto-reject
- **LLM skips progression:** Evaluator requires explicit justification -> auto-reject
- **LLM ignores flare:** Evaluator checks substitutions -> auto-reject
- **Malformed format:** Structural validation catches it -> auto-reject
- **Retry storm:** Circuit breaker after max attempts -> surface to human with warning
- **Notion write failure:** Retry with backoff. Checkpoint has the approved draft.

## Acceptance Criteria

- [ ] After plan approval, generation loop starts automatically
- [ ] Tier-2 agent drafts each session with reasoning block (structured `result_type`)
- [ ] Deterministic Evaluator validates every draft (structural, guardrails, context grounding)
- [ ] Failed validation auto-retries with specific error feedback
- [ ] Circuit breaker triggers after max retries, surfaces draft with warning
- [ ] HITL: user can approve or provide feedback for re-draft
- [ ] Approved sessions written to Notion idempotently
- [ ] `written_sessions` list persists correctly across checkpoint resume
- [ ] Auto-progression: after writing, next session drafts automatically
- [ ] Completion when `len(written_sessions) == sessions_total`
- [ ] Full end-to-end: plan -> approve plan -> draft all sessions -> write all to Notion
- [ ] Progress visualization (`3/8 ████░░░░`)
- [ ] Run cost displayed at completion

## Reference

- [Patterns](../reference/patterns.md) — Evaluator-Optimizer (Two-Stage Validation Gate)
- [State Schema](../reference/state-schema.md) — Layer C output state
- [Failure Modes](../reference/failure-modes.md) — LLM output failures, circuit breaker
