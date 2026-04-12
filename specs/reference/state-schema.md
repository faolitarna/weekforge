# State Schema

The graph state is the shared data bus between all nodes. It must be thin, typed, and JSON-serializable (for checkpoint persistence). State is organized into three layers with distinct lifetimes.

## Layer A — Workflow State (Persistent, Checkpointed)

Core parameters that define the current execution. Small and stable.

| Field | Type | Purpose |
|-------|------|---------|
| `week_target` | `int` | Which week we're planning (e.g., 7) |
| `sessions_total` | `int` | Total sessions in the approved plan (set on plan approval) |

LangGraph's checkpoint system replaces the legacy stage tracking. The graph knows which node it's at — no explicit `stage` enum needed.

## Layer B — Context State (Loaded Fresh, Consumed, Not Carried Forward)

Data fetched by Tier-0 tool nodes at the start of each subgraph. Consumed by the LLM node that needs it, then not persisted to the next checkpoint. Keeps state thin and ensures data freshness.

| Field | Type | Purpose |
|-------|------|---------|
| `template_sessions` | `list[dict]` | Template sessions fetched from Notion by week prefix |
| `feedback_context` | `dict` | Merged 3-week feedback window + PLAN_STATE (loaded via Parallelization) |
| `active_flare` | `bool` | Derived from most recent week's feedback — any SI/pain signal sets this to `True` |
| `user_profile` | `dict` | User conditions, goals, preferences, HR zones |
| `guardrails` | `dict` | Exercise guardrails, progression protocol, coaching constraints |

## Layer C — Output State (Accumulated During Generation)

Grows as the graph progresses. Uses appropriate reducers to handle checkpoint merging.

| Field | Type | Reducer | Purpose |
|-------|------|---------|---------|
| `week_plan` | `str` | Replace | The approved macro plan text |
| `current_session_index` | `int` | Replace | Which session we're currently drafting (1-based) |
| `current_draft` | `str \| None` | Replace | Current session draft being reviewed — ephemeral |
| `written_sessions` | `list[dict]` | Append | Lightweight references: `{page_id, session_name}` — NOT full markdown |
| `focus_exercise_count` | `int` | Replace | Running tally of focus exercises vs 8+ target |

## Legacy Run Log Simplifications

| Legacy Field | Status | Reason |
|-------------|--------|--------|
| `run_id` | Eliminated | Use LangGraph's `thread_id` |
| `stage` | Eliminated | Graph checkpoint IS the stage |
| `previous_week` x3 | Eliminated | Computed by feedback loader tool |
| `template_week_prefix` | Eliminated | Computed as `f"W{week_target:02d}"` |
| `sessions_written` | Eliminated | Derived from `len(written_sessions)` |
| `status_message` | Eliminated | Replaced by CLI output |
| `timestamp_started` | Eliminated | Not needed for graph execution |
| `week_plan` | Kept | Layer C |
| `week_target` | Kept | Layer A |
| `sessions_total` | Kept | Layer A |

## Design Principles

- **Checkpoint-friendly:** All state values must be JSON-serializable.
- **Avoid state bloat:** Full session markdown lives only in `current_draft` (ephemeral). On approval, written to Notion and replaced with a lightweight reference.
- **Reducers matter:** `written_sessions` uses an append reducer so checkpoint resume doesn't reset the list.
- **Context is disposable:** Layer B fields are loaded fresh every time they're needed. Stale context is never reused from a previous checkpoint.
