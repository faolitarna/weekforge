# Coding Conventions

**Analysis Date:** 2026-04-19

## Summary

weekforge is a Python 3.13 project enforced by Ruff (line-length 88, isort + pyflakes + pyupgrade) and mypy strict mode. Conventions are codified in agent personas: `feature-developer.md` defines implementation standards, `documentation-developer.md` defines comment style, and `code-reviewer.md` defines the quality gate. Together they constitute the authoritative style guide for this project. Code in `src/` is consistent with all three.

## Toolchain Enforcement

**Ruff** (`pyproject.toml [tool.ruff]`):
- Line length: 88
- Rules: `E` pycodestyle, `F` pyflakes, `I` isort, `UP` pyupgrade
- E501 (line-too-long) explicitly ignored — long docstrings and comments are permitted

**mypy** (`pyproject.toml [tool.mypy]`):
- `strict = true`, `warn_return_any = true`, `warn_unused_configs = true`
- Applied to `src/` only — `tests/` is excluded
- Only two `# type: ignore[call-arg]` suppressions exist, both for Pydantic Settings instantiation (a known mypy/pydantic-settings pattern)

**Verification sequence** (from `feature-developer.md`):
```
uv run ruff check .
uv run mypy src/
uv run pytest
```
All three must pass before commit. No CI is configured — this is run manually.

## Intelligence Tiering

Defined in `feature-developer.md`, enforced by `code-reviewer.md`:

- **Tier 0** — Pure Python, no LLM. Validators, parsers, tool layers, formatters. If a task CAN be done in Python, it MUST be done in Python.
- **Tier 1** — Fast/cheap model calls. Low-stakes inference.
- **Tier 2** — Heavy reasoning models. Quality-sensitive, structured-output pipelines.

The distinction is structurally visible in the codebase:
- `src/weekforge/tools/` — Tier 0 (no LLM imports)
- `src/weekforge/models/` — Tier 0 (pure data)
- `src/weekforge/agents/` — Tier 1/2 (LLM calls)

Never use an LLM call for logic that can be deterministic Python.

## Naming Patterns

**Files:** `snake_case.py` — `notion_api_gateway.py`, `user_profile_loader.py`, `agent_run_with_metadata.py`

**Functions:**
- Public: `snake_case` — `load_user_profile()`, `run_with_metadata()`, `estimate_cost_eur()`
- Private helpers: leading underscore — `_retry_api_call()`, `_validate_env_or_exit()`, `_build_prompt()`
- Private module-level singletons: leading underscore — `_client`, `_console`, `_logger`

**Variables / constants:**
- Module-level constants: `UPPER_SNAKE_CASE` — `USD_TO_EUR`, `PRICING`, `WORKFLOW`
- Local variables: `snake_case`

**Classes:**
- `PascalCase` — `CheckpointStore`, `CallMetadata`, `RunCost`, `E2eState`, `UserProfile`
- Exceptions: `PascalCase` + `Error` suffix — `NotionAuthFailedError`, `NotionNotFoundError`, `NotionAPIError`, `ConfigError`

**Enums:** `StrEnum` — `Prompt` in `src/weekforge/prompts/loader.py`

## Type Usage

All public functions carry full annotations. `mypy --strict` must pass.

**Modern union syntax (PEP 604) — use everywhere:**
```python
str | None          # not Optional[str]
dict[str, Any] | None   # not Optional[Dict[str, Any]]
```

**`Any` policy** (from `code-reviewer.md`): permitted only where external SDKs return untyped dicts (`dict[str, Any]` for Notion API responses, Pydantic AI result shapes). Not used for convenience.

**`dataclass` vs `BaseModel` split:**
- `BaseModel` — data that crosses layer boundaries or is JSON-serialized: `CallMetadata`, `E2eState`, `UserProfile`
- `@dataclass` — mutable accumulators and internal structs: `RunCost`, `CheckpointRecord`, `HitlDecision`
- `@dataclass(frozen=True)` — immutable config structs: `LLMProfile` in `src/weekforge/config/llm_profiles.py`

## Documentation Style

Defined in `documentation-developer.md`. The rule: **document the non-obvious WHY, nothing else.**

**Docstrings — use when:** the function is called from outside the module and the signature alone doesn't convey the full contract (ordering constraints, side effects, return shape).

**Inline comments — use when:** a specific line has a non-obvious reason.

**Use nothing when:** the code is self-explanatory to a senior developer.

**What never goes in documentation:**
- Historical context (no "replaces legacy X", no migration notes)
- Forward-looking reservations (no "reserved for future use")
- Step/spec references (no "step-0a", "step-0b" in code comments)
- Personal or private information of any kind

**No duplication rule:** if a module docstring states a fact, the function docstring must not restate it. Keep only the innermost occurrence.

Examples from the codebase:

```python
# GOOD — non-obvious ordering constraint
"""Persist state before a HITL pause.

Must be called BEFORE rendering the prompt — crash safety relies on the
checkpoint existing before the user sees the question.
"""

# GOOD — non-obvious thread constraint
self._conn = sqlite3.connect(db_path, check_same_thread=False)
# Typer and pytest may access from different threads.

# BAD (absent in this codebase) — restates the code
# Connect to the SQLite database
```

Module docstrings are present on all non-trivial modules (`notion_api_gateway.py`, `e2e.py`, `notion_markdown_converter.py`, `formatting.py`, `openai_model_factory.py`) and absent on simple single-class modules (`user_profile.py`, `config/__init__.py`).

## Import Organization

**Order** (enforced by isort via Ruff):
1. Standard library
2. Third-party
3. Internal (`weekforge.*`)

**Lazy imports inside CLI commands** — heavy workflow and settings imports are deferred inside command function bodies to avoid import-time side effects and keep `--help` fast. Example: `src/weekforge/cli.py` lines 99, 118.

**Module alias for namespaced access:**
```python
from weekforge.tools import notion_api_gateway as notion
# Caller uses: notion.query(...), notion.create(...)
```

## Error Handling

**Fail-fast for configuration** — `src/weekforge/config/env.py` instantiates `Settings()` at module import time. Missing env vars crash at import, not inside a workflow. The CLI catches `ValidationError` at the boundary and renders a Rich panel instead of a raw traceback.

**Domain error hierarchy** (all in `src/weekforge/tools/notion_api_gateway.py`):
- `NotionAuthFailedError` — HTTP 401, unrecoverable, raises immediately
- `NotionNotFoundError` — HTTP 404, unrecoverable, raises immediately
- `NotionAPIError` — all other API and network errors

**`ConfigError`** — defined in `src/weekforge/config/__init__.py`, raised when runtime config is invalid (e.g. empty user profile page).

**Raise over silent fallback** — functions raise on invalid input rather than returning sentinel values:
- `format_week_prefix(0)` raises `ValueError`, does not return `"W00"`
- `resolve_llm_profile("fast")` raises `KeyError` on missing profile, no default

**`assert` for workflow preconditions:**
```python
assert state.last_output is not None  # enforced by review-step precondition
```

## Logging

**Framework:** stdlib `logging` only.

**Logger creation:** module-level, named after the module:
```python
logger = logging.getLogger(__name__)
```
Present in `src/weekforge/models/pricing.py` and `src/weekforge/workflows/e2e.py`.

**Log levels in use:**
- `WARNING` — degraded-mode fallbacks (unknown model in pricing) and data truncation (prompt record limit)

**Rich console for all user-facing output** — never `print()`:
- Module-level `console = Console()` in `src/weekforge/cli.py`, `src/weekforge/workflows/summarize_week.py`
- Workflow-private `_console = Console()` in `src/weekforge/workflows/e2e.py`, `src/weekforge/hitl.py`

## Workflow / State Machine Pattern

Established by `src/weekforge/workflows/e2e.py`, applies to all future workflows:

- State is a `BaseModel` subclass — JSON-serializable for checkpointing via `model_dump_json()`
- A `step: str` field drives a `while state.step != "done":` dispatch loop
- Step names are string literals persisted to SQLite — **never rename without a schema migration**
- Checkpoint is saved BEFORE each network call (crash-safe forward progress)
- HITL pause: `hitl_confirm()` saves state then renders the panel — save always precedes prompt

## Commit Convention

From `code-reviewer.md` — conventional commits, tied to spec steps:
```
feat(step-0b): implement Notion tool layer
```
Trunk-based development directly to `main`. No feature branches for solo work.

## Gaps / Unknowns

- No pre-commit hooks configured — the three-command check sequence is manual
- No CI pipeline — checks run only when a developer runs them locally
- `tests/pydantic_models/` directory exists but is empty (only `__pycache__`) — appears to be an abandoned placeholder
- `openai_model_factory.py` routing logic (Chat Completions vs Responses API split on `reasoning_effort`) is only documented in the module docstring, not in `llm_profiles.py` where profiles are defined
