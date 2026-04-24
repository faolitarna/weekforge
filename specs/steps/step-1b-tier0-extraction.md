# Step 1b: Raw Session Collection (Thin Tier-0)

## Implementation Status

✅ **Done.** Models, collectors, and checkbox arithmetic land in `src/weekforge/models/week_summary.py`, `src/weekforge/models/raw_week_data.py`, and `src/weekforge/tools/raw_session_collector.py`. Tests at `tests/tools/test_raw_collector.py`.

**Deviations from draft:**
- `ImplicitFeedback.per_session` is `list[SessionCheckCount]` (Pydantic model with `name`/`checked`/`total`), not `list[tuple[str, int, int]]`. Named fields survive schema evolution; tuples don't.
- `PlanAdherence.modification_patterns` is `list[ModificationPattern]` (`exercise`/`planned`/`actual`); `PlanAdherence.skip_patterns` is `list[SkipPattern]` (`exercise`/`reason`). Same reasoning.
- `PainStatus` class replaced by `JointEntry` (step-1e). `WeekSummary.pain_status` is `list[JointEntry]`. See DEC-010.
- `collect_raw_sessions` title extraction scans all properties for `type == "title"` instead of hardcoding `"Name"`. Fallback to `page_id` if no title property found. Fixes UUID session names when Notion DB uses a different property name.
- `compute_checkbox_analysis` requires `t >= 2` appearances before an exercise enters `frequently_skipped` or `always_completed`. Single-session exercises (especially from fully-skipped sessions) were generating noise lists of 70+ items.

## Goal

Build the thin data-collection layer: fetch Notion session pages, collect all block children
and page comments into a structured `RawWeekData` bundle, and compute checkbox arithmetic.
Zero semantic parsing. Zero LLM calls.

Tier-0 deliberately does NOT parse exercise params, classify roles, interpret comments, or
perform delta analysis — all semantic work belongs to Tier-2 (step-1c LLM agent).

## Prerequisites

Step 1a complete (settings, loaders, CLI stub).

## Rationale

Session types vary widely (gym, climbing, hiking, trail run) with fundamentally different
block structures. Comment content is unstructured user free-text. The original
`source-material` approach — LLM reads raw blocks directly — worked well. Tier-0 only owns
what is genuinely deterministic: fetching blocks and counting booleans.

See `.planning/notes/tier0-thin-extraction.md` for full decision rationale.

## What You're Building

| File | Action | Purpose |
|------|--------|---------|
| `src/weekforge/models/week_summary.py` | NEW | Pydantic output schema — contract for step-1c LLM to fill |
| `src/weekforge/models/raw_week_data.py` | NEW | `RawSession` + `RawWeekData` dataclasses for the collection bundle |
| `src/weekforge/tools/raw_session_collector.py` | NEW | Block/comment collection + checkbox arithmetic |
| `tests/tools/test_raw_collector.py` | NEW | Unit tests for checkbox math only |

## Specification

### Output schema (`models/week_summary.py`)

Define Pydantic models — these are the **contract** that step-1c fills. Tier-0 does not
populate them directly (except `implicit_feedback`, which is checkbox math).

```python
from typing import Literal
from pydantic import BaseModel, Field

Role = Literal["main", "accessory", "focus", "warmup", "cooldown"]
Status = Literal["done", "done_modified", "skip"]

class ExerciseLogEntry(BaseModel):
    name: str
    planned_weight: str | None
    planned_sets: int | None
    planned_reps: str | None
    actual_weight: str | None = None
    actual_sets: int | None = None
    actual_reps: str | None = None
    role: Role
    status: Status
    feedback: str | None = None
    section: str | None = None

class SessionLine(BaseModel):
    name: str
    status: Literal["done", "skip", "partial"]
    exercises_done: int
    exercises_total: int
    pain_status: str | None
    comment: str

class CardioEntry(BaseModel):
    kind: Literal["z1_run", "z2_run", "z3_tempo", "hike", "trail_run", "other"]
    raw: str

class ClimbingEntry(BaseModel):
    kind: str
    raw: str

class JointEntry(BaseModel):
    name: str           # e.g. "si_joint", "other"
    status: str         # always present
    triggers: str | None = None
    what_helped: str | None = None

class SectionRates(BaseModel):
    warmup_pct: float
    main_pct: float
    cooldown_pct: float

class SkippedPattern(BaseModel):
    exercise: str
    skip_rate: float

class SessionCheckCount(BaseModel):
    name: str
    checked: int
    total: int

class ModificationPattern(BaseModel):
    exercise: str
    planned: str
    actual: str

class SkipPattern(BaseModel):
    exercise: str
    reason: str

class ImplicitFeedback(BaseModel):
    total_checked: int
    total_exercises: int
    per_session: list[SessionCheckCount]
    section_rates: SectionRates
    frequently_skipped: list[SkippedPattern]
    always_completed: list[str]

class PlanAdherence(BaseModel):
    planned_total: int
    completed: int
    modified: int
    skipped: int
    modification_patterns: list[ModificationPattern]
    skip_patterns: list[SkipPattern]

class WeekSummary(BaseModel):
    week_prefix: str
    completion: str
    context: str | None = None
    sessions: list[SessionLine]
    exercise_log: list[ExerciseLogEntry]
    cardio_log: list[CardioEntry] = Field(default_factory=list)
    climbing_log: list[ClimbingEntry] = Field(default_factory=list)
    pain_status: list[JointEntry]
    issues: list[str] = Field(default_factory=list)
    wins: list[str] = Field(default_factory=list)
    recommendations_next: list[str] = Field(default_factory=list)
    plan_adherence: PlanAdherence | None = None
    implicit_feedback: ImplicitFeedback
    highlights: list[str] = Field(default_factory=list)
    trend: str = ""
```

Tier-0 fills: `implicit_feedback` (checkbox arithmetic only).
Tier-2 (step-1c) fills: everything else.

### Collection bundle (`models/raw_week_data.py`)

```python
from dataclasses import dataclass, field

@dataclass
class RawBlock:
    block_type: str          # "to_do", "heading_2", "heading_3", "paragraph", etc.
    text: str                # concatenated plain text from rich_text array
    checked: bool | None     # only set for to_do blocks
    raw: dict                # original Notion block dict (for any downstream access)

@dataclass
class RawSession:
    page_id: str
    name: str
    blocks: list[RawBlock]
    comments: list[str]      # plain text of each Notion comment on the page

@dataclass
class RawWeekData:
    week_prefix: str
    sessions: list[RawSession]
    planned_plan_markdown: str | None   # from run_log, None if no plan persisted
```

### Collector (`tools/raw_session_collector.py`)

```python
def collect_blocks(page_id: str, notion_client) -> list[RawBlock]:
    """Fetch block children for a page. Flatten rich_text to plain string.
    Access all fields via .get() — never assume key exists."""

def collect_comments(page_id: str, notion_client) -> list[str]:
    """Fetch page comments. Return list of plain-text comment bodies."""

def collect_raw_sessions(
    session_pages: list[dict],
    notion_client,
) -> list[RawSession]:
    """For each session page: collect blocks + comments. Return RawSession per page.
    Raise ValueError if session_pages is empty."""

def compute_checkbox_analysis(sessions: list[RawSession]) -> ImplicitFeedback:
    """Pure arithmetic over to_do block checked states.
    - per_session: (name, checked_count, total_count) per session
    - section_rates: track current_section from heading blocks; bucket to_do blocks
    - frequently_skipped: exercise text where skip_count / appearances > 0.5
    - always_completed: exercise text where skip_count == 0 across all appearances
    No interpretation — counts only."""

def assemble_raw_week(
    week_prefix: str,
    session_pages: list[dict],
    notion_client,
    planned_plan_markdown: str | None,
) -> RawWeekData:
    """Top-level entry. Calls collect_raw_sessions, returns RawWeekData bundle.
    Raise ValueError(f'{week_prefix}: no sessions found') when empty."""
```

### Unit tests (`tests/tools/test_raw_collector.py`)

Use minimal inline fixtures (dicts), not file-based fixtures — simpler to maintain.

- `test_collect_blocks_extracts_text` — to_do block with rich_text → `text` field populated
- `test_collect_blocks_checked_state` — checked=True and checked=False both captured correctly
- `test_compute_checkbox_analysis_counts` — 3 sessions with mixed checks → correct totals
- `test_compute_checkbox_analysis_section_rates` — heading_2 sets section → to_do bucketed correctly
- `test_compute_checkbox_analysis_frequently_skipped` — exercise unchecked 2/3 times → in frequently_skipped
- `test_assemble_raw_week_empty_raises` — empty session_pages → ValueError with week_prefix

## Acceptance Criteria

- [x] `WeekSummary` and all sub-models validate round-trip (`model_dump_json` / `model_validate_json`)
- [x] `collect_raw_sessions` returns one `RawSession` per page with all `to_do` + heading blocks captured
- [x] `compute_checkbox_analysis` returns arithmetically correct counts for all fixture cases
- [x] `assemble_raw_week` raises `ValueError` containing week prefix when session list is empty
- [x] All field access in collector uses `.get()` — no `KeyError` on malformed Notion responses
- [x] `uv run pytest tests/tools/test_raw_collector.py` passes

## Out of Scope

- Exercise param parsing (sets/reps/weight) → step-1c LLM
- Role classification → step-1c LLM (system prompt)
- Comment interpretation → step-1c LLM
- Delta analysis → step-1c LLM
- Focus exercises constant → step-1c (embed in system prompt, not a Python module)
- HITL, workflow orchestration → step-1c
- Notion write, PLAN_STATE → step-1d
