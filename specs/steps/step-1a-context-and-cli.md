# Step 1a: Context Loading & CLI

## Implementation Status

✅ **Done.** Code implemented; unit tests pass; Real-Notion integration verified via CLI and `uv build` packaging confirmed.

**Deviations from spec:**
- **Prompt loader API:** single `load_prompt(Prompt.X)` with `StrEnum` + `functools.cache`, replacing named `load_coaching_persona()` / `load_coaching_guardrails()`. Reason: scales to N prompts without adding a function per file. Step-1c call sites adjust accordingly.
- **`tools/week_prefix.py` → `tools/formatting.py`:** single-function module promoted to shared formatting layer; same `format_week_prefix()` signature.
- **CLI overwrite prompt:** uses `typer.confirm()` directly rather than `hitl.py`'s `hitl_confirm()`. Reason: `hitl_confirm` requires checkpoint state which doesn't exist pre-workflow.
- **User profile: Notion DB → single Notion page (DEC-007).** Typed properties (`Name`, `Training Age`, `LTHR`, `Max HR`, `Conditions`) and `HRAnchors` model deleted. Profile is now a single page loaded as markdown. `UserProfile` model simplified to `{page_id, markdown}`. `NOTION_DB_USER_PROFILE` → `NOTION_USER_PROFILE_PAGE_ID`.

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
| `src/weekforge/models/user_profile.py` | NEW | Pydantic `UserProfile` model (`page_id` + `markdown`) |
| `src/weekforge/config/user_profile_loader.py` | NEW | `load_user_profile() -> UserProfile` — fetch page blocks, convert to markdown |
| `src/weekforge/tools/formatting.py` | NEW | `format_week_prefix(week: int) -> str` — zero-pad, `"W{week:02d}"`. Landed at `tools/formatting.py` (shared formatting module) rather than a dedicated `week_prefix.py`. |
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

Extend [.env.template](../../.env.template) (order below, with inline comments):

```
# Notion Training Databases
# IDs of the Notion databases that back weekforge workflows.
NOTION_DB_TRAINING_SESSIONS=
NOTION_DB_TRAINING_WEEK_SUMMARIES=
NOTION_DB_TRAINING_TEMPLATES=

# Notion User Profile Page
# ID of the Notion page containing user profile (not a database).
NOTION_USER_PROFILE_PAGE_ID=
```

Extend [env.py](../../src/weekforge/config/env.py) `Settings`:

```python
class Settings(BaseSettings):
    # ... existing fields ...
    notion_db_training_sessions: str
    notion_db_training_week_summaries: str
    notion_db_training_templates: str
    notion_user_profile_page_id: str
```

Keep `notion_test_db_id` (e2e workflow still needs it). Module-level instantiation already fails fast on missing vars.

### User profile Notion page

The user profile is the single source of truth for everything user-specific. Coaching prompts contain zero user facts — they delegate to this profile. The profile is a **document for the LLM**, not a data structure for Python — all semantic sections live in prose and are injected into agent instructions as-is.

#### Setup (one-time, in Notion)

1. Create a new Notion **page** (not a database). Name it anything (e.g. `Training — User Profile`).
2. Share the page with the integration token used by `NOTION_TOKEN`.
3. Copy the page ID into `.env` as `NOTION_USER_PROFILE_PAGE_ID`.
4. Write the page content following the recommended template below.

#### Recommended template

The page body should cover:

- **Baseline** — training age, experience level, current capacity.
- **Goals** — ranked training priorities, time horizon, accepted trade-offs.
- **Conditions** — medical/neurodivergent conditions with risk levels and programming adaptations.
- **Preferences** — likes, dislikes, motivation drivers.
- **Injuries** — current/past injuries, status, exercise impact.
- **Heart Rate Zones** — method, LTHR, Max HR, zone boundaries.

These sections are **guidance, not enforcement**. If a section doesn't apply (e.g. no injuries), skip it. If the user wants to add sections (e.g. Nutrition), they just add them — the LLM uses whatever is there.

Seed prose can be lifted from `source-material/.claude/shared/user-profile.md`.

#### Pydantic model — already implemented

[src/weekforge/models/user_profile.py](../../src/weekforge/models/user_profile.py):

```python
class UserProfile(BaseModel):
    page_id: str = Field(..., min_length=1)
    markdown: str = Field(..., min_length=1)
```

No typed fields — all semantic content lives in the markdown prose.

#### Loader behavior

[src/weekforge/config/user_profile_loader.py](../../src/weekforge/config/user_profile_loader.py):

- Calls `fetch(settings.notion_user_profile_page_id)` to get page blocks.
- Converts blocks to markdown via `convert_blocks_to_markdown`.
- Validates non-empty content; raises `ConfigError` with actionable message if page is empty.
- No caching at loader level. Fresh fetch per workflow start.

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

- [x] `src/weekforge/prompts/coaching_persona.md` matches `source-material/Claude.md` byte-for-byte.
- [x] `src/weekforge/prompts/coaching_guardrails.md` matches `source-material/.claude/rules/coaching-guardrails.md` byte-for-byte.
- [x] ~~`load_coaching_persona()` and `load_coaching_guardrails()`~~ `load_prompt(Prompt.X)` returns full file contents as `str`, uses `importlib.resources`, `functools.cache`'d. (API deviation, see Implementation Status.)
- [x] `uv build` produces a wheel that contains `weekforge/prompts/*.md`.
- [x] `Settings` loads four new DB IDs from `.env`. Startup fails with a clear error if any missing.
- [x] `.env.template` updated with the four DB IDs + inline comments.
- [x] `UserProfile` Pydantic model validates correctly (`page_id` + `markdown`, both non-empty). (Simplified from typed fields per DEC-007.)
- [x] `load_user_profile()` fetches a real Notion page and returns `UserProfile` with markdown content.
- [x] `load_user_profile()` raises `ConfigError` when page content is empty.
- [x] `format_week_prefix(7) == "W07"`, `format_week_prefix(12) == "W12"`, invalid input raises `ValueError`.
- [x] `uv run weekforge summarize-week 7` runs, triggers overwrite prompt when a W07 summary exists, loads persona + guardrails + user profile, prints a "context ready" panel, and exits with `NotImplementedError` (stub behavior).
- [x] `uv run weekforge summarize-week` without arg fails with a clear Typer error.
- [x] Tests: `tests/prompts/test_prompts_sync.py`, `tests/tools/test_formatting.py`, `tests/config/test_user_profile_loader.py`, `tests/tools/test_notion_markdown_converter.py`.

## Out of Scope (Next Sub-Steps)

- Session parsing, role classification, checkbox analysis → step-1b
- `summarize_agent` and the workflow body → step-1c
- Writing the summary to Notion, PLAN_STATE → step-1d
