# Step 1a: Context Loading & CLI

## Goal

Prepare the config and loader surface that every subsequent sub-step depends on: coaching prompts bundled with the package, user profile fetchable from Notion, `.env` wired with all training DB IDs, and `weekforge summarize <week>` CLI entry with week-prefix formatting and existing-summary overwrite check.

Zero LLM calls. Pure plumbing.

## Prerequisites

Step 0d complete.

## What You're Building

| File | Action | Purpose |
|------|--------|---------|
| `src/weekforge/prompts/__init__.py` | NEW | Package marker so markdown files are importable resources |
| `src/weekforge/prompts/coaching_persona.md` | NEW | Verbatim copy of `source-material/Claude.md` |
| `src/weekforge/prompts/coaching_guardrails.md` | NEW | Verbatim copy of `source-material/.claude/rules/coaching-guardrails.md` |
| `src/weekforge/prompts/loader.py` | NEW | `load_coaching_persona()`, `load_coaching_guardrails()` — `@lru_cache`, uses `importlib.resources` |
| [pyproject.toml](../../pyproject.toml) | UPDATE | Ensure `*.md` under `weekforge.prompts` is packaged |
| [src/weekforge/config/env.py](../../src/weekforge/config/env.py) | UPDATE | Add four training DB ID settings |
| [.env.template](../../.env.template) | UPDATE | Add four training DB ID vars with comments |
| `src/weekforge/models/user_profile.py` | NEW | Pydantic `HRZones`, `UserProfile` models |
| `src/weekforge/config/user_profile_loader.py` | NEW | `load_user_profile() -> UserProfile` — Notion query, parse typed properties + page body |
| `src/weekforge/tools/week_prefix.py` | NEW | `format_week_prefix(week: int) -> str` — zero-pad, `"W{week:02d}"` |
| [src/weekforge/cli.py](../../src/weekforge/cli.py) | UPDATE | Add `summarize <week>` command, stub target for 1c workflow |

## Specification

### Prompts directory

- `coaching_persona.md` = byte-for-byte copy of `source-material/Claude.md`. Source file stays in repo as historical reference; the copy in `src/weekforge/prompts/` is the live one consumed at runtime.
- `coaching_guardrails.md` = byte-for-byte copy of `source-material/.claude/rules/coaching-guardrails.md`.
- Loader uses `importlib.resources.files("weekforge.prompts").joinpath(<name>).read_text(encoding="utf-8")` and wraps with `@functools.lru_cache(maxsize=1)`.
- Loader API:
  ```python
  def load_coaching_persona() -> str: ...
  def load_coaching_guardrails() -> str: ...
  ```
- Sync copies of source-material files are checked at commit time by a lightweight test: `tests/prompts/test_prompts_sync.py` asserts file contents match `source-material/…`. Keeps drift visible.

### Packaging

`pyproject.toml` must ship the `.md` files. Weekforge uses Hatch; add:
```toml
[tool.hatch.build.targets.wheel]
packages = ["src/weekforge"]

[tool.hatch.build.targets.wheel.force-include]
"src/weekforge/prompts" = "weekforge/prompts"
```
Or equivalent `package-data` if the project switches build backend. Verify with `uv build` + `unzip -l dist/*.whl | grep prompts`.

### `.env` additions

Extend [.env.template](../../.env.template) with four lines (order below, with inline comments):

```
# Notion Training Databases
# IDs of the four Notion databases that back weekforge workflows.
NOTION_DB_TRAINING_SESSIONS=
NOTION_DB_TRAINING_WEEK_SUMMARIES=
NOTION_DB_TRAINING_TEMPLATES=
NOTION_DB_USER_PROFILE=
```

Extend [env.py](../../src/weekforge/config/env.py) `Settings`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    notion_db_training_sessions: str
    notion_db_training_week_summaries: str
    notion_db_training_templates: str
    notion_db_user_profile: str
```

Keep `notion_test_db_id` (e2e workflow still needs it). Module-level instantiation already fails fast on missing vars.

### User profile Notion DB

**DB schema** (created by user in Notion, one-time). Acceptance-level documentation of the required shape:

| Property | Type | Required | Notes |
|----------|------|----------|-------|
| `Name` | Title | yes | Row identifier. Use e.g. `"Szymon"`. |
| `Active` | Checkbox | yes | Exactly one row with `Active=true` at any time. |
| `Training Age (years)` | Number | yes | Integer. |
| `LTHR` | Number | yes | Lactate threshold HR (bpm). |
| `Max HR` | Number | yes | Max HR (bpm). |
| `Conditions` | Multi-select | yes | e.g., `AS`, `Scheuermann`, `AuDHD`. |
| Page body | Prose | yes | Goals, preferences, injuries, narrative — copied from `user-profile.md`. |

Seed the row with content from `source-material/.claude/shared/user-profile.md`. The spec includes this shape so the user can set it up before running `weekforge summarize`.

### User profile models

`src/weekforge/models/user_profile.py`:

```python
from pydantic import BaseModel, Field

class HRZones(BaseModel):
    lthr: int
    max_hr: int
    # Zone boundaries derived deterministically from LTHR (%LTHR method).
    # z1_max, z2_max, etc. as computed properties or explicit fields.

class UserProfile(BaseModel):
    name: str
    training_age_years: int
    hr_zones: HRZones
    conditions: list[str] = Field(default_factory=list)
    prose_markdown: str          # full page body
```

### User profile loader

`src/weekforge/config/user_profile_loader.py`:

- Query `training_user_profile` DB filtered by `Active == true`, `limit=1`.
- Parse typed properties → structured fields. Read page body (child blocks → markdown) → `prose_markdown`. Reuse [notion_markdown_converter.py](../../src/weekforge/tools/notion_markdown_converter.py).
- Raise `ConfigError` with actionable message if zero rows (`"No active user profile row in Notion. See step-1a spec for required DB schema."`).
- No caching at loader level — workflow caches on its state. Fresh fetch per workflow start. (Profile is small; network latency dominated by the summary run.)

### Week prefix formatter

`src/weekforge/tools/week_prefix.py`:

```python
def format_week_prefix(week: int) -> str:
    """Zero-pad to 2 digits with 'W' prefix. 7 -> 'W07', 12 -> 'W12'."""
    if not 1 <= week <= 99:
        raise ValueError(f"week must be in [1, 99], got {week}")
    return f"W{week:02d}"
```

Pure function. Unit-tested standalone.

### CLI: `weekforge summarize <week>`

Extend [cli.py](../../src/weekforge/cli.py):

```python
@app.command()
def summarize(week: int = typer.Argument(..., help="Week number, e.g. 7")) -> None:
    """Generate a weekly summary from completed training sessions."""
    week_prefix = format_week_prefix(week)
    thread_id = f"summarize-{week_prefix}"
    store = CheckpointStore(...)
    run_summarize(week_prefix, thread_id, store)  # stub target for step-1c
```

Typer's positional `int` argument fails fast if missing or non-integer — no custom validation needed. Error output: standard Typer error panel.

### Existing-summary overwrite check

Before the workflow proper begins (spec lives in step-1c, but the CLI prologue handles the pre-workflow prompt here for 1a's stub target):

1. Query `training_week_summaries` for rows where `Week == W##`, limit 1.
2. If hit → prompt via [hitl.py](../../src/weekforge/hitl.py): `"Summary for {W##} already exists. Overwrite? [y/N]"`. On `n` or quit → exit cleanly with message pointing at the existing page.
3. If no hit → proceed.

Implementation of the `run_summarize` stub in 1a: perform the overwrite check, load prompts + user profile, print a "context ready" summary panel (Rich), then raise `NotImplementedError("Workflow body lands in step-1c")`. This proves the loader + CLI wiring end-to-end without blocking on 1b/1c.

## Acceptance Criteria

- [ ] `src/weekforge/prompts/coaching_persona.md` matches `source-material/Claude.md` byte-for-byte.
- [ ] `src/weekforge/prompts/coaching_guardrails.md` matches `source-material/.claude/rules/coaching-guardrails.md` byte-for-byte.
- [ ] `load_coaching_persona()` and `load_coaching_guardrails()` return the full file contents as `str`, use `importlib.resources`, and are `lru_cache`'d.
- [ ] `uv build` produces a wheel that contains `weekforge/prompts/*.md`.
- [ ] `Settings` loads four new DB IDs from `.env`. Startup fails with a clear error if any missing.
- [ ] `.env.template` updated with the four DB IDs + inline comments.
- [ ] `UserProfile` and `HRZones` Pydantic models validate correctly for a sample payload.
- [ ] `load_user_profile()` queries Notion, parses a real DB row (structured properties + body → markdown) into `UserProfile`.
- [ ] `load_user_profile()` raises `ConfigError` when no active row exists.
- [ ] `format_week_prefix(7) == "W07"`, `format_week_prefix(12) == "W12"`, invalid input raises `ValueError`.
- [ ] `uv run weekforge summarize 7` runs, triggers overwrite prompt when a W07 summary exists, loads persona + guardrails + user profile, prints a "context ready" panel, and exits with `NotImplementedError` (stub behavior).
- [ ] `uv run weekforge summarize` without arg fails with a clear Typer error.
- [ ] Tests: `tests/prompts/test_prompts_sync.py`, `tests/tools/test_week_prefix.py`, `tests/config/test_user_profile_loader.py` (with a Notion fixture or integration flag).

## Out of Scope (Next Sub-Steps)

- Session parsing, role classification, checkbox analysis → step-1b
- `summarize_agent` and the workflow body → step-1c
- Writing the summary to Notion, PLAN_STATE → step-1d
