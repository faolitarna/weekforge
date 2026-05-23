# Weekforge

Weekforge is an automated training coach that reads workout data from Notion, uses LLMs to generate week summaries and training plans, and maintains longitudinal coaching state across mesocycles. It replaces a manual Claude Code workflow with structured Python + Pydantic AI pipelines.

## Language

### Training structure

**Week**:
A calendar week (Monday–Sunday) within a mesocycle, identified by a zero-padded prefix like `W01`, `W07`.
_Avoid_: training block, microcycle

**Session**:
The smallest schedulable training event within a week. Can be a gym workout, run, climb, mobility work, correction work, or active recovery. Rest days are not sessions.
_Avoid_: workout (too narrow — excludes mobility/recovery sessions)

**Mesocycle**:
A multi-week training block with a name and total week count. Length and structure are flexible — no enforced pattern. Deload placement varies per mesocycle.
_Avoid_: program, training plan (overloaded with weekly plan)

**Exercise**:
A single movement prescribed within a session. Has a **role** — one of: `main` (primary compound lifts), `accessory` (supporting movements), `focus` (user-designated priority exercises), `warmup`, or `cooldown`.

**Focus exercise**:
A user-designated priority exercise — can target a lagging muscle group, a corrective need, or a specialization goal. The planner aims to include 8+ focus exercises per mesocycle. Not a synonym for "main."
_Avoid_: priority lift, key exercise

### Data flow

**Training Template**:
A session blueprint stored in Notion, prefixed by week (e.g., "W01 - Upper Body"). Templates provide structural starting points for planning — the LLM adapts them based on current progress, needs, and PLAN_STATE. Deviations must be justified.
_Avoid_: program, prescription

**Week Summary**:
A structured snapshot of one completed week. Contains session completion, exercise log, pain status, cardio/climbing logs, plan adherence, implicit feedback, highlights, and trend. Written to Notion after HITL approval. One data point feeding into PLAN_STATE.
_Avoid_: weekly report, recap

**Plan State**:
The rolling longitudinal coaching memory — accumulated across all completed weeks. Tracks main lift progressions, adherence chains, injury timeline, active issues, session preferences, and more. Planning reads PLAN_STATE plus the last three Week Summaries for detail.
_Avoid_: training history, coaching log

**Implicit feedback**:
Training signals derived mechanically (Tier 0) from checkbox completion data — completion rates per section (warmup/main/cooldown), skip patterns, always-completed exercises. No LLM involved.
_Avoid_: automated feedback, checkbox analysis

**Explicit feedback**:
Training signals from user comments on Notion session pages. Interpreted by the LLM.
_Avoid_: user notes, annotations

### Lifecycles

**Extraction lifecycle**:
The `summarize-week` workflow. Reads completed sessions from Notion → Tier-0 mechanical analysis → LLM summarization → HITL review → writes Week Summary to Notion → updates Plan State. Recommended to run before planning, but independent.
_Avoid_: summarization pipeline

**Planning lifecycle**:
The `plan` workflow. Reads PLAN_STATE + recent Week Summaries + Training Templates → LLM generates week plan and sessions → HITL review → writes sessions to Notion. Independent from extraction but better-informed when extraction runs first.
_Avoid_: generation pipeline

**Workflow execution**:
One run of a lifecycle from start to finish (or pause). Can be interrupted and resumed via checkpoint. No special jargon — just "workflow execution."
_Avoid_: thread, run (collides with running), pass, cycle (collides with mesocycle)

### System concepts

**Flare**:
An ankylosing spondylitis episode affecting SI joints. Triggers programming modifications: flare-safe substitutions (split-stance, elevated pulls, isometrics), reduced range, or full pause with physio referral. General injuries tracked separately.
_Avoid_: episode, inflammation event

**Active flare**:
Boolean derived from recent week feedback. When true, planning activates flare-safe exercise substitutions.

**HITL (Human-in-the-loop)**:
A workflow pause that shows LLM output to the user in the terminal for review. Primarily a quality gate before writing to Notion. Expanding to general decision points (discussion, approvals). User can approve, give feedback (re-runs agent), or quit (checkpoints and exits).

**Tier 0 / Tier 2**:
Intelligence tiering. Tier 0 = pure Python, zero LLM — all deterministic work (data fetching, checkbox counting, formatting, validation). Tier 2 = heavy cognitive LLM — planning, summarization, trend synthesis. Tier 1 (fast/cheap model for routing) is defined but not yet implemented.
_Avoid_: layer (reserved for state schema layers A/B/C)

**User Profile**:
A Notion page containing the user's training context: baseline, goals, conditions, preferences, injuries, HR zones, and optionally logistics (equipment, schedule, gym access). Loaded at workflow start and injected into LLM prompts as-is.
_Avoid_: athlete profile, config

**Caveman mode**:
A terse, data-dense output style for LLM coaching responses. Reduces token usage while preserving all technical substance. A domain-level coaching style choice, not just a formatting flag.

**Checkpoint**:
SQLite-persisted workflow state that enables quit-and-resume. One checkpoint per workflow execution, keyed by a unique ID.
_Avoid_: save state, snapshot

### Notion data model

**training_sessions** (database): One page per session. Has a "Week" property (number as text). Contains exercise checkboxes and user comments.

**training_week_summaries** (database): One page per Week Summary. Also holds the special PLAN_STATE row (Week = "PLAN_STATE").

**training_templates** (database): One page per template session, prefixed by week.

**User Profile page** (single page): Not a database — a standalone Notion page loaded by page ID.

## Example dialogue

> **Dev:** The user completed W05 and wants to plan W06. What happens?
>
> **Domain expert:** First, run the extraction lifecycle on W05. It pulls the raw sessions from training_sessions, does Tier-0 analysis on checkbox completion — that gives you implicit feedback. Then the LLM reads the raw sessions plus the Tier-0 output and produces a Week Summary. User reviews it via HITL, approves, it writes to training_week_summaries and updates Plan State.
>
> **Dev:** And then planning?
>
> **Domain expert:** Separate workflow execution. Planning reads Plan State (the rolling memory), the last three Week Summaries for detail, and the Training Templates for W06's structure. The LLM adapts the templates — maybe swaps an exercise because Plan State shows a stall, or because there's an active flare. User reviews each session via HITL before it gets written to training_sessions.
>
> **Dev:** What if a focus exercise gets skipped three weeks in a row?
>
> **Domain expert:** Implicit feedback catches the skip pattern in Tier-0. The Week Summary surfaces it. Plan State accumulates it across weeks. Next planning cycle, the LLM sees the pattern and either reprioritizes or flags it. The 8+ focus exercise target is a mesocycle-level goal, not per-week — so occasional skips are fine, but a trend triggers action.
