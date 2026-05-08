# Step 2b: Context Loading (Tier-0)

## Status
ready (facilitator pass — contract sections to be filled by specs-developer)

## Goal

Implement the `load_context` step of `plan_week`: gather every input the agent needs in 2c, packaged as a typed `PlanWeekDeps` payload. Pure deterministic Python — no LLM, all data from Notion + local prompts.

## Decisions

- **Inputs gathered (sequential per DEC-P9):**
  1. **Templates** — `query(notion_db_training_templates)` filtered to rows whose title starts with `week_prefix` (matches legacy plan_week.md template-loading section). Title-prefix filter via Python — Notion API has no startswith filter. Reuse pattern from `summarize_week.load_context` for filter-after-query.
  2. **3-week feedback window** — for each of `(week-1, week-2, week-3)`, query `notion_db_training_week_summaries`. Per row: read `Plan` rich-text property and body content (look for `code` block, fallback to plain text). Skip weeks not present. Result: `list[WeekFeedbackRow{week_prefix, plan_md, summary_text}]` (length 0..3).
  3. **PLAN_STATE** — re-implement the `plan_state_check` logic from `summarize_week.py:282-312` in a small reusable helper, OR extract into `tools/plan_state_loader.py` so both workflows share it. Returns `(parsed: PlanState | None, raw: str | None, page_id: str | None)`.
  4. **User profile** — `load_user_profile()` (existing). Returns `UserProfile{page_id, markdown}`.
  5. **`active_flare` derivation (DEC-P15)** — pure function:
     - From most recent feedback row's body text: detect non-empty pain markers (legacy summary format renders pain via JointEntry — parse the rendered text for SI/spine/joint markers, OR add a structured re-parse if the format is stable enough).
     - From PLAN_STATE `active_issues` list: any item containing keywords (`SI`, `spine`, `flare`, `pain`, `tendon`, joint names).
     - `active_flare = bool(recent_pain or chronic_active_issue)`.
- **`PlanWeekDeps` dataclass (frozen, agent input):**
  ```python
  @dataclass
  class PlanWeekDeps:
      week_prefix: str
      template_sessions: list[dict]          # raw Notion pages (or thin extracted view)
      feedback_window: list[WeekFeedbackRow] # 0..3 entries
      plan_state: PlanState | None
      plan_state_raw: str | None             # passed-through for verbatim agent context
      user_profile: UserProfile
      active_flare: bool
      bootstrap: bool                        # True if plan_state is None OR feedback_window empty
  ```
- **Bootstrap path (DEC-P16):** when `plan_state is None` AND/OR `feedback_window == []`, set `bootstrap = True` and emit a Rich-formatted CLI warning. Workflow continues — agent receives empty/partial context and prompt hints at conservative defaults.
- **Verbose CLI display:** under `settings.verbose`, print one-line summaries of each load (template count, feedback-week count, PLAN_STATE incremental/bootstrap, profile loaded, active_flare flag).
- **Step transition:** `load_context → agent` (next sub-step). Checkpoint saved at boundary.
- **State carry strategy:** `PlanWeekDeps` is rebuilt fresh from Notion on every resume (Layer B per state-schema.md is *consumed-not-carried*). Only the `step` literal is checkpointed between 2b and 2c. Heavy raw payloads (`template_sessions`, `feedback_window`) are not serialized into `PlanWeekState`.

## Open questions

None.

## Inputs

(specs-developer to fill — `week_prefix`, settings, Notion DBs)

## Outputs

(specs-developer to fill — `PlanWeekDeps` instance available for 2c)

## Files

(specs-developer to fill — expected: workflows/plan_week.py [edit, add load_context step], possibly tools/plan_state_loader.py [create — extract shared loader], possibly models/plan_week_deps.py [create] or inline in agent file)

## Data contracts

(specs-developer to fill — `WeekFeedbackRow`, `PlanWeekDeps`, `active_flare` predicate signature)

## Workflow

(specs-developer to fill — load_context step pseudocode)

## Tier split

- Tier 0: all loaders, parsers, `active_flare` predicate, CLI display
- Tier 1: —
- Tier 2: —

## Failure modes

- Templates empty for prefix → fail loud with clear error pointing to template naming convention. Do not silently proceed.
- `notion_db_training_week_summaries` query fails → if it is the 3-week window, log warning and treat as `bootstrap=True`. If it is the PLAN_STATE check, surface the underlying error (path is critical).
- User profile page empty → existing `ConfigError` from `load_user_profile`.
- Pain marker parse heuristic fails → default `active_flare=False` (conservative — agent will still apply guardrails on any reported pain it sees in raw feedback).

## Acceptance criteria

(specs-developer to fill — must populate all `PlanWeekDeps` fields, must trigger bootstrap warning correctly, must surface verbose load summary)

## Out of scope

- Agent run (2c).
- Tier-0 plan validation (2d).
- Caching loaded context across runs — always fresh per state-schema.md Layer B.
- Async/parallel queries — DEC-P9.

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P5..P9, P15..P16
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — `load_context` (lines 51-103) and `plan_state_check` (lines 282-312) patterns to copy/extract
- [tools/plan_state.py](../../src/weekforge/tools/plan_state.py) — `parse_plan_state`, `PlanState`
- [config/user_profile_loader.py](../../src/weekforge/config/user_profile_loader.py) — `load_user_profile`
- `source-material/.claude/commands/plan_week.md` — `<context-loading>`, `<template-loading>`, `<feedback-loading>` sections (legacy authoritative behavior)
