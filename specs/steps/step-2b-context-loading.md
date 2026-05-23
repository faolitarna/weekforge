# Step 2b: Context Loading (Tier-0)

## Status
ready

## Goal

Implement the `load_context` step of `draft_week`: gather every input the agent needs in 2c, packaged as a typed `DraftWeekDeps` dataclass. Pure deterministic Python — no LLM, all data from Notion + local prompts.

## Decisions

- **Inputs gathered (sequential per DEC-P9):**
  1. **Templates** — `notion.query(settings.notion_db_training_templates)` filtered to rows whose title starts with `week_prefix`. Title-prefix filter via Python post-query (Notion API has no startswith filter). Reuse pattern from `summarize_week.load_context`.
  2. **3-week feedback window** — for each of `(week-1, week-2, week-3)`, call `summaries_db.find_summary_row(prev_prefix)` (DEC-P26). Per row: read `Plan` via `summaries_db.read_plan_property(page)` and body content (code block text). Skip weeks not present. Result: `list[WeekFeedbackRow]` (length 0..3).
  3. **PLAN_STATE** — `summaries_db.find_plan_state_row()` (DEC-P26, subsumes DEC-P22). Returns `(raw_text: str | None, page_id: str | None)`. `is_bootstrap = raw_text is None`.
  4. **User profile** — `load_user_profile()` (existing). Returns `UserProfile`.
  5. **`active_flare` derivation (DEC-P15)** — pure function:
     - From most recent feedback row's body text: detect non-empty pain markers (SI/spine/joint keywords).
     - From PLAN_STATE `active_issues` list: any item containing keywords (`SI`, `spine`, `flare`, `pain`, `tendon`, joint names).
     - `active_flare = bool(recent_pain or chronic_active_issue)`.
- **`DraftWeekDeps` dataclass (frozen, agent input):**
  ```python
  @dataclass(frozen=True)
  class DraftWeekDeps:
      week_prefix: str
      template_sessions: list[dict]
      feedback_window: list[WeekFeedbackRow]
      plan_state: PlanState | None
      plan_state_raw: str | None
      user_profile: UserProfile
      active_flare: bool
      bootstrap: bool
  ```
- **Bootstrap path (DEC-P16):** when `plan_state is None` AND/OR `feedback_window == []`, set `bootstrap = True` and emit CLI warning. Workflow continues — agent receives empty/partial context.
- **State carry strategy:** `DraftWeekDeps` is rebuilt fresh from Notion on every resume (Layer B per state-schema.md). Only `step` literal checkpointed between 2b and 2c. Heavy raw payloads not serialized into `DraftWeekState`.
- **Plan state raw stored on state:** `state.plan_state_raw` and `state.plan_state_page_id` set during load for downstream use (plan_state_update in future).

## Open questions

None.

## Inputs

- `state.week_prefix` — from 2a
- `settings.notion_db_training_templates` — templates DB ID
- `settings.notion_db_training_week_summaries` — summaries DB ID
- `settings.notion_user_profile_page_id` — user profile page ID

## Outputs

- `DraftWeekDeps` instance — passed to agent in 2c
- `state.is_bootstrap`, `state.plan_state_raw`, `state.plan_state_page_id` — set on `DraftWeekState`
- Side-effect: CLI bootstrap warning if context is partial

## Files

- `src/weekforge/workflows/draft_week.py`: edit — implement `load_context` step function
- `src/weekforge/agents/draft_week_agent.py`: create — `DraftWeekDeps` dataclass lives here (matches `SummarizeDeps` placement in `summarize_week_agent.py`)

Note: `load_plan_state` extraction and `summarize_week` refactor handled in step-2-prep (DEC-P26).

## Data contracts

### `WeekFeedbackRow`

```python
@dataclass(frozen=True)
class WeekFeedbackRow:
    week_prefix: str
    plan_md: str | None
    summary_text: str | None
```

### `DraftWeekDeps`

```python
@dataclass(frozen=True)
class DraftWeekDeps:
    week_prefix: str
    template_sessions: list[dict]
    feedback_window: list[WeekFeedbackRow]
    plan_state: PlanState | None
    plan_state_raw: str | None
    user_profile: UserProfile
    active_flare: bool
    bootstrap: bool
```

### `find_plan_state_row()` (from `summaries_db`, DEC-P26)

```python
def find_plan_state_row() -> tuple[str | None, str | None]:
    """Returns (raw_text, page_id). Both None if no PLAN_STATE row."""
```

### `active_flare` predicate

```python
def derive_active_flare(
    feedback_window: list[WeekFeedbackRow],
    plan_state: PlanState | None,
) -> bool:
```

## Workflow

1. Enter `load_context` step.
2. Load templates: query templates DB, filter by `week_prefix` title prefix.
3. Load feedback window: for weeks `(N-1, N-2, N-3)`, call `summaries_db.find_summary_row()`, read `Plan` + body code-block.
4. Load PLAN_STATE: call `summaries_db.find_plan_state_row()`. Set `state.plan_state_raw`, `state.plan_state_page_id`, `state.is_bootstrap`.
5. Load user profile: call `load_user_profile()`.
6. Derive `active_flare`: call `derive_active_flare(feedback_window, plan_state)`.
7. Compute `bootstrap`: `plan_state is None or len(feedback_window) == 0`.
8. If `bootstrap`: print Rich warning.
9. Build `DraftWeekDeps`.
10. `state.step = "agent"`, checkpoint save.

## Tier split

- Tier 0: all loaders, parsers, `active_flare` predicate, CLI display
- Tier 1: —
- Tier 2: —

## Failure modes

- Templates empty for prefix → fail loud with clear error pointing to template naming convention. Do not silently proceed.
- `notion_db_training_week_summaries` query fails for 3-week window → log warning, treat as `bootstrap=True`.
- PLAN_STATE query fails → surface underlying error (path is critical for existing mesocycles).
- User profile page empty → existing `ConfigError` from `load_user_profile`.
- Pain marker parse heuristic fails → default `active_flare=False` (conservative — agent still applies guardrails on any reported pain it sees in raw feedback).

## Acceptance criteria

- [ ] `DraftWeekDeps` populated with all fields from Notion sources
- [ ] Templates filtered correctly by `week_prefix` title prefix
- [ ] Feedback window contains 0..3 rows for previous weeks
- [ ] `summaries_db.find_plan_state_row()` shared by both `summarize_week` and `draft_week` — no duplication
- [ ] Bootstrap warning printed when PLAN_STATE missing or feedback window empty
- [ ] `active_flare` correctly derived from pain markers and PLAN_STATE active_issues
- [ ] Verbose mode prints one-line summary per load step
- [ ] No LLM calls in this sub-step (zero cost)

## Out of scope

- Agent run (2c).
- Tier-0 plan validation (2d).
- Caching loaded context across runs — always fresh per state-schema.md Layer B.
- Async/parallel queries — DEC-P9.

## Reference

- [step-2-planning.md](./step-2-planning.md) — index, DEC-P5..P9, P15..P16, P26
- [workflows/summarize_week.py](../../src/weekforge/workflows/summarize_week.py) — `load_context` and `plan_state_check` patterns
- [tools/plan_state.py](../../src/weekforge/tools/plan_state.py) — `parse_plan_state`, `PlanState`
- [config/user_profile_loader.py](../../src/weekforge/config/user_profile_loader.py) — `load_user_profile`
- `source-material/.claude/commands/plan_week.md` — legacy template/feedback loading
