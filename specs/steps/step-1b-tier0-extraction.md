# Step 1b: Tier-0 Extraction (Pure Python)

## Goal

Build the deterministic extraction layer: parse Notion session payloads into structured exercise data, classify roles, compute checkbox analysis, compute delta vs. approved plan. Produce a `WeekSummary` Pydantic model with every machine-computable field pre-filled. Zero LLM calls.

This sub-step owns the faithful Python port of `<exercise-extraction>`, `<checkbox-analysis>`, and `<delta-analysis>` from `source-material/.claude/commands/summarize_week.md`.

## Prerequisites

Step 1a complete (settings, loaders, CLI stub).

## What You're Building

| File | Action | Purpose |
|------|--------|---------|
| `src/weekforge/models/week_summary.py` | NEW | Pydantic models for the weekly summary output |
| `src/weekforge/tools/extraction.py` | NEW | Pure-Python parsing, classification, analysis |
| `src/weekforge/tools/focus_exercises.py` | NEW | Constant list of the 10 Focus Exercises + matchers |
| `tests/tools/test_extraction.py` | NEW | Unit tests against canned Notion payloads |

## Specification

### Pydantic models (`models/week_summary.py`)

```python
from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["main", "accessory", "focus", "warmup", "cooldown"]
Status = Literal["done", "done_modified", "skip"]

class ExerciseLogEntry(BaseModel):
    name: str
    planned_weight: str | None          # e.g., "15kg" or "BW" — stringly-typed to preserve legacy format
    planned_sets: int | None
    planned_reps: str | None            # "8" or "3x8" or "20sec" — freeform unit
    actual_weight: str | None = None    # set when comment diverges from plan
    actual_sets: int | None = None
    actual_reps: str | None = None
    role: Role
    status: Status
    feedback: str | None = None         # freeform comment excerpt if any
    section: str | None = None          # raw section heading for traceability

class SessionLine(BaseModel):
    name: str                           # e.g., "W07: Hinge + Core"
    status: Literal["done", "skip", "partial"]
    exercises_done: int
    exercises_total: int
    pain_status: str | None             # "ok", "SI flare", etc.
    comment: str                        # 1-liner brief

class CardioEntry(BaseModel):
    kind: Literal["z1_run", "z2_run", "z3_tempo", "hike", "trail_run", "other"]
    raw: str                            # pre-rendered legacy-format line (Tier-0 emits verbatim)

class ClimbingEntry(BaseModel):
    kind: str                           # "bouldering", "sport", etc.
    raw: str

class PainStatus(BaseModel):
    si_joint: str | None                # "{status}|{triggers}|{what_helped}"
    other: str | None

class SectionRates(BaseModel):
    warmup_pct: float
    main_pct: float
    cooldown_pct: float

class SkippedPattern(BaseModel):
    exercise: str
    skip_rate: float                    # 0.0–1.0

class ImplicitFeedback(BaseModel):
    total_checked: int
    total_exercises: int
    per_session: list[tuple[str, int, int]]     # (session_name, checked, total)
    section_rates: SectionRates
    frequently_skipped: list[SkippedPattern]    # >50% skip rate
    always_completed: list[str]                 # 100% completion

class PlanAdherence(BaseModel):
    planned_total: int
    completed: int
    modified: int
    skipped: int
    modification_patterns: list[tuple[str, str, str]]   # (original, replacement, reason)
    skip_patterns: list[tuple[str, str]]                # (session_type, reason)

class WeekSummary(BaseModel):
    week_prefix: str                    # "W07"
    completion: str                     # "{done}/{total}"
    context: str | None = None          # external factors (illness, travel)
    sessions: list[SessionLine]
    exercise_log: list[ExerciseLogEntry]
    cardio_log: list[CardioEntry] = Field(default_factory=list)
    climbing_log: list[ClimbingEntry] = Field(default_factory=list)
    pain_status: PainStatus
    issues: list[str] = Field(default_factory=list)           # LLM-filled
    wins: list[str] = Field(default_factory=list)             # LLM-filled
    recommendations_next: list[str] = Field(default_factory=list)  # LLM-filled
    plan_adherence: PlanAdherence | None = None
    implicit_feedback: ImplicitFeedback
    # LLM-filled surface fields for the HITL accept panel
    highlights: list[str] = Field(default_factory=list)
    trend: str = ""
```

Tier-0 1b fills: `week_prefix`, `completion`, `sessions`, `exercise_log`, `cardio_log`, `climbing_log`, `pain_status` (structural), `implicit_feedback`, `plan_adherence`. Tier-2 (1c) fills: `context`, `issues`, `wins`, `recommendations_next`, `highlights`, `trend`, and narrative embellishment of `pain_status`.

### Focus exercises (`tools/focus_exercises.py`)

```python
FOCUS_EXERCISES: frozenset[str] = frozenset({
    "bar hang", "bar hangs",
    "side plank",
    "reverse lunge", "multidirectional lunge",
    "bicep curl",
    "elevator press",
    "single arm ohp", "single-arm ohp",
    "carry", "carries",
    "x-press lat walk",
    "face pull", "face pulls",
    "pull-up", "pull up", "pullup",
})

def is_focus_exercise(name: str) -> bool:
    """Case-insensitive substring match against known focus exercises."""
    normalized = name.lower().strip()
    return any(fx in normalized for fx in FOCUS_EXERCISES)
```

### Extraction (`tools/extraction.py`)

Core functions — all pure Python, no LLM:

```python
def parse_sessions(notion_session_pages: list[dict]) -> list[ParsedSession]:
    """For each session page: extract properties, walk block children, parse to_do blocks,
    attach comments. Returns a ParsedSession dataclass per page."""

def parse_to_do_block(block: dict, current_section: str | None) -> ParsedToDo:
    """Extract name, planned params (weight/sets/reps), checked state, section from a to_do."""

def classify_role(exercise_name: str, section: str | None) -> Role:
    """main | accessory | focus | warmup | cooldown.
    Priority: focus (if is_focus_exercise) > section-based (warmup/cooldown) > main/accessory heuristic."""

def reconcile_exercise(todo: ParsedToDo, comments: list[str]) -> ExerciseLogEntry:
    """Extract actual params from freeform comments (regex + keyword passes for
    'did Xkg', 'only managed', 'swapped X for Y', etc.). Produces planned→actual diff."""

def build_session_line(parsed: ParsedSession, log: list[ExerciseLogEntry]) -> SessionLine:
    """Per-session 1-liner: done/skip/partial, exercises_done/total, pain_status from comments."""

def compute_checkbox_analysis(sessions: list[ParsedSession]) -> ImplicitFeedback:
    """Pure arithmetic over to_do checked states. No interpretation."""

def compute_delta_analysis(
    sessions: list[ParsedSession],
    planned_plan_markdown: str | None,
) -> PlanAdherence | None:
    """Match actual sessions to planned sessions by focus-keyword overlap.
    Returns None if planned_plan_markdown is None (no plan persisted — legacy 'n/a' path)."""

def assemble_tier0_summary(
    week_prefix: str,
    sessions: list[ParsedSession],
    planned_plan_markdown: str | None,
) -> WeekSummary:
    """Top-level entry. Wires everything into a partial WeekSummary with Tier-0 fields filled.
    LLM-filled fields left as defaults."""
```

### Parsing rules (from `summarize_week.md`)

- **Section tracking:** iterate block children; `heading_2` / `heading_3` update `current_section`. Subsequent `to_do` blocks inherit that section.
- **Param parsing:** `to_do` rich_text content. Extract name (before ` - ` or before `(`). Extract params from parentheses (e.g., `(15kg x 3x8)`), using regex. Unknown → `None`.
- **Checked state:** `block["to_do"]["checked"]` — boolean.
- **Role classification priority:**
  1. `is_focus_exercise(name)` → `focus` (overrides section).
  2. section name contains `"warm"` (case-insensitive) → `warmup`.
  3. section name contains `"cool"` → `cooldown`.
  4. Compound heuristic (squat/deadlift/press/row/pull-up keywords in name) → `main`.
  5. else → `accessory`.
- **Comment parsing (Tier-0 heuristics):** regex for `did (\d+)kg`, `only managed (\d+x\d+)`, `swapped (.+?) for (.+)`, `bumped (?:weight|to) (\d+)kg`, etc. Best-effort — any comment content that does not match regex flows through to `feedback` freeform and is later interpreted by the LLM.
- **Pain heuristics:** keyword scan for `SI`, `pain`, `flare`, `ache`, `sore` → `pain_status.si_joint` or `.other`. LLM in step 1c enriches with narrative.
- **Checkbox analysis:**
  - `per_session`: list of `(session_name, checked, total)`.
  - `section_rates`: `checked / total` per section bucket, percentage 0–100.
  - `frequently_skipped`: exercises where `skipped_count / appearances > 0.5`.
  - `always_completed`: exercises with `skipped_count == 0` across all appearances.
- **Delta analysis:**
  - Parse `planned_plan_markdown` (numbered list, one session per line). Extract a keyword per line (longest token after removing week prefix).
  - For each planned session, find actual session whose name contains the keyword (case-insensitive).
  - Match → `completed` if all `to_do` checked else `modified`; no match → `skipped`.
  - Build `modification_patterns` from comment swap-regexes, `skip_patterns` from unmatched sessions' freeform reasons.

### Unit tests (`tests/tools/test_extraction.py`)

Cover the critical paths with canned Notion fixture payloads stored under `tests/fixtures/notion/`:

- `test_parse_to_do_weight_sets_reps` — typical `Goblet Squat (15kg x 3x8)` parses correctly.
- `test_parse_to_do_bodyweight` — `Bar Hangs (BW x 3x20sec)` → `weight="BW"`, `reps="20sec"`.
- `test_classify_role_focus_overrides_section` — face pulls in warmup → `focus`, not `warmup`.
- `test_classify_role_warmup_section` — arbitrary mobility drill in `Warm-up` section → `warmup`.
- `test_reconcile_actual_params` — comment `"bumped weight to 17kg"` → `actual_weight="17kg"`.
- `test_compute_checkbox_analysis_rates` — canned session with mixed checks → correct section_rates and skipped_patterns.
- `test_compute_delta_analysis_none_when_no_plan` — `planned_plan_markdown=None` → returns `None`.
- `test_compute_delta_analysis_matches_by_keyword` — planned `Hinge + Core` matches actual `W07: Hinge + Core`.
- `test_assemble_tier0_summary_zero_sessions_raises` — empty `sessions` list → `ValueError` (hard fail; see HITL decision in step-1c).

## Acceptance Criteria

- [ ] All Pydantic models in `week_summary.py` validate round-trip (`model_dump_json()` / `model_validate_json()`).
- [ ] `parse_sessions` produces one `ParsedSession` per Notion page, with all `to_do` blocks captured and sections correctly attributed.
- [ ] `classify_role` returns the expected role for each fixture case (focus override, warmup/cooldown sections, compound-lift detection).
- [ ] `reconcile_exercise` captures planned→actual divergence when comments include weight/reps changes or swaps.
- [ ] `compute_checkbox_analysis` returns arithmetically correct `per_session` counts, `section_rates`, `frequently_skipped`, `always_completed` for the test fixtures.
- [ ] `compute_delta_analysis` returns `None` when no plan markdown is provided, otherwise returns a populated `PlanAdherence`.
- [ ] `assemble_tier0_summary` populates every Tier-0 field and leaves LLM-fill fields at defaults.
- [ ] Zero-session case raises `ValueError` with a message containing the week prefix.
- [ ] Unit test suite passes under `uv run pytest tests/tools/test_extraction.py`.

## Out of Scope

- LLM synthesis (issues, wins, recommendations, highlights, trend) → step-1c
- HITL, workflow orchestration → step-1c
- Notion write, PLAN_STATE → step-1d
