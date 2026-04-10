---
id: WF-02
title: State Schema Requirements
status: draft
version: 1.0
last-updated: 2026-04-10
depends-on: [WF-00, WF-01]
implements-phase: [0, 1, 2, 3]
---

# State Schema Requirements

The graph state is the shared data bus between all nodes. It must be thin, typed, and JSON-serializable (for checkpoint persistence). State is organized into three layers with distinct lifetimes.

## Layer A — Workflow State (Persistent, Checkpointed)

Core parameters that define the current execution. Small and stable.

| Field | Type | Purpose |
|-------|------|---------|
| `week_target` | `int` | Which week we're planning (e.g., 7) |
| `sessions_total` | `int` | Total sessions in the approved plan (set on plan approval) |

**Note:** LangGraph's checkpoint system **replaces** the legacy stage tracking. The graph knows which node it's at — no explicit `stage` enum needed. This is the single biggest simplification over the legacy Run Log.

## Layer B — Context State (Loaded Fresh, Consumed, Not Carried Forward)

Data fetched by Tier-0 tool nodes at the start of each subgraph. Consumed by the LLM node that needs it, then not persisted to the next checkpoint. This keeps state thin and ensures data freshness.

| Field | Type | Purpose |
|-------|------|---------|
| `template_sessions` | `list[dict]` | Template sessions fetched from Notion by week prefix |
| `feedback_context` | `dict` | Merged 3-week feedback window + PLAN_STATE (loaded via Parallelization) |
| `active_flare` | `bool` | Derived from most recent week's feedback — any SI/pain signal in W(N-1) sets this to `True` |
| `user_profile` | `dict` | User conditions, goals, preferences, HR zones |
| `guardrails` | `dict` | Exercise guardrails, progression protocol, coaching constraints |

## Layer C — Output State (Accumulated During Generation)

Grows as the graph progresses. Uses appropriate reducers to handle checkpoint merging.

| Field | Type | Reducer | Purpose |
|-------|------|---------|---------|
| `week_plan` | `str` | Replace | The approved macro plan text |
| `current_session_index` | `int` | Replace | Which session we're currently drafting (1-based) |
| `current_draft` | `str \| None` | Replace | The current session draft being reviewed — ephemeral, replaced each iteration |
| `written_sessions` | `list[dict]` | Append | Lightweight references to written sessions: `{page_id, session_name}` — NOT full markdown |
| `focus_exercise_count` | `int` | Replace | Running tally of focus exercises used across written sessions vs 8+ target |

## Legacy Run Log Simplifications

The legacy Run Log had 11+ fields. Moving to LangGraph eliminates most of them because the graph tracks its own execution state:

| Legacy Field | Status | Reason |
|-------------|--------|--------|
| `run_id` | **Eliminated** | Use LangGraph's `thread_id` instead |
| `stage` | **Eliminated** | Graph checkpoint IS the stage — no enum needed |
| `previous_week` ×3 | **Eliminated** | Computed as `week_target - 1, -2, -3` by the feedback loader tool |
| `template_week_prefix` | **Eliminated** | Computed as `f"W{week_target:02d}"` by the template loader tool |
| `sessions_written` | **Eliminated** | Derived from `len(written_sessions)` at any time |
| `status_message` | **Eliminated** | Was for human-readable Run Log display — replaced by CLI output |
| `timestamp_started` | **Eliminated** | Bookkeeping only — not needed for graph execution |
| `week_plan` | **Kept** | Moved to Layer C output state |
| `week_target` | **Kept** | Moved to Layer A workflow state |
| `sessions_total` | **Kept** | Moved to Layer A workflow state |

## Design Principles

- **Checkpoint-friendly:** All state values must be JSON-serializable. No file handles, connections, or functions.
- **Avoid state bloat:** Full session markdown lives only in `current_draft` (ephemeral). On approval, it's written to Notion and replaced with a lightweight `{page_id, name}` reference.
- **Reducers matter:** `written_sessions` uses an append reducer so checkpoint resume doesn't reset the list. `stage`-like fields use replace reducers.
- **Context is disposable:** Layer B fields are loaded fresh by tool nodes every time they're needed. Stale context is never reused from a previous checkpoint.
