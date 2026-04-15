# State Schema

Workflow state is the shared data model passed through orchestrator functions. It must be thin, typed, and JSON-serializable (for checkpoint persistence via `model_dump_json()`). State is organized into three layers with distinct lifetimes.

Each workflow has its own focused state model (not one monolithic class). The layers below describe the conceptual organization — concrete fields appear in each workflow's Pydantic model.

## Layer A — Workflow State (Persistent, Checkpointed)

Core parameters that define the current execution. Small and stable.

| Field | Type | Purpose |
|-------|------|---------|
| `week_target` | `int` | Which week we're planning (e.g., 7) |
| `sessions_total` | `int` | Total sessions in the approved plan (set on plan approval) |

The checkpoint store tracks which workflow step execution paused at — no explicit `stage` enum needed.

## Layer B — Context State (Loaded Fresh, Consumed, Not Carried Forward)

Data fetched by Tier-0 tool functions at the start of each workflow. Consumed by the Pydantic AI agent that needs it, then not persisted to the next checkpoint. Keeps state thin and ensures data freshness. These fields can be modeled as a `deps` dataclass for Pydantic AI dependency injection.

| Field | Type | Purpose |
|-------|------|---------|
| `template_sessions` | `list[dict]` | Template sessions fetched from Notion by week prefix |
| `feedback_context` | `dict` | Merged 3-week feedback window + PLAN_STATE (loaded via Parallelization) |
| `active_flare` | `bool` | Derived from most recent week's feedback — any SI/pain signal sets this to `True` |
| `user_profile` | `dict` | User conditions, goals, preferences, HR zones |
| `guardrails` | `dict` | Exercise guardrails, progression protocol, coaching constraints |

## Layer C — Output State (Accumulated During Generation)

Grows as the workflow progresses. Stored on the Pydantic state model as plain fields.

| Field | Type | Purpose |
|-------|------|---------|
| `week_plan` | `str` | The approved macro plan text |
| `current_session_index` | `int` | Which session we're currently drafting (1-based) |
| `current_draft` | `str \| None` | Current session draft being reviewed — ephemeral (local variable, not checkpointed) |
| `written_sessions` | `list[dict]` | Lightweight references: `{page_id, session_name}` — NOT full markdown |
| `focus_exercise_count` | `int` | Running tally of focus exercises vs 8+ target |

## Legacy Run Log Simplifications

| Legacy Field | Status | Reason |
|-------------|--------|--------|
| `run_id` | Eliminated | Use checkpoint store's `thread_id` |
| `stage` | Eliminated | Checkpoint `step` field IS the stage |
| `previous_week` x3 | Eliminated | Computed by feedback loader tool |
| `template_week_prefix` | Eliminated | Computed as `f"W{week_target:02d}"` |
| `sessions_written` | Eliminated | Derived from `len(written_sessions)` |
| `status_message` | Eliminated | Replaced by CLI output |
| `timestamp_started` | Eliminated | Not needed for graph execution |
| `week_plan` | Kept | Layer C |
| `week_target` | Kept | Layer A |
| `sessions_total` | Kept | Layer A |

## Design Principles

- **Pydantic-native:** State models use `BaseModel` with `model_dump_json()` / `model_validate_json()` for checkpoint serialization.
- **Avoid state bloat:** Full session markdown lives only in `current_draft` (ephemeral local variable). On approval, written to Notion and replaced with a lightweight reference.
- **Workflow-scoped models:** Each workflow defines its own state model with only the fields it needs. No monolithic shared state class.
- **Context is disposable:** Layer B fields are loaded fresh every time they're needed. Stale context is never reused from a previous checkpoint.
