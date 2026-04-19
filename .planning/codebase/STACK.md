# Technology Stack

**Analysis Date:** 2026-04-19

## Summary

Weekforge is a pure-Python CLI application targeting Python 3.13+. It is built around Pydantic AI for structured LLM agent calls, Typer/Rich for the CLI layer, and a custom SQLite checkpoint store for pause/resume workflows. There is no web server, message queue, or container runtime involved.

## Languages

**Primary:**
- Python 3.13+ — all application code in `src/weekforge/`

**Secondary:**
- Markdown — prompt files bundled into the wheel via hatchling (`src/weekforge/prompts/`)

## Runtime

**Environment:**
- CPython 3.13 (`.venv/bin/python3.13` present; `requires-python = ">=3.13"` in `pyproject.toml`)

**Package Manager:**
- `uv` — lockfile at `uv.lock` (revision 3, `requires-python = ">=3.13"`)
- Lockfile: present and committed
- Run commands use `uv run weekforge <cmd>`

## Frameworks

**Core:**
- `pydantic-ai` 1.83.0 — structured LLM agent framework; used for all agent definitions, model wrappers, and message history handling (`src/weekforge/agents/`)
- `pydantic` 2.13.0 — data validation, settings, and serialization throughout
- `pydantic-settings` 2.13.1 — env-var-backed settings class (`src/weekforge/config/env.py`)

**CLI:**
- `typer` 0.24.1 — CLI entry point and command definitions (`src/weekforge/cli.py`)
- `rich` 15.0.0 — terminal rendering (panels, tables, prompts) used in CLI, HITL, and workflows

**Build:**
- `hatchling` — build backend declared in `pyproject.toml`; wheel bundles `src/weekforge/prompts/` as package data via `force-include`

**Testing:**
- `pytest` 9.0.3 — test runner; config in `pyproject.toml` (`testpaths = ["tests"]`)
- `pytest-mock` 3.15.1 — mocking support

## Key Dependencies

**Critical:**
- `pydantic-ai` 1.83.0 — all LLM calls go through this; provides `Agent`, `OpenAIChatModel`, `OpenAIResponsesModel`, `OpenAIProvider`, `ModelMessagesTypeAdapter`
- `notion-client` 3.0.0 — pinned exact version; sole interface to Notion REST API (`src/weekforge/tools/notion_api_gateway.py`)
- `tenacity` 9.1.4 — retry logic for Notion 429 rate-limit errors (exponential backoff, 4 attempts)
- `python-dotenv` 1.2.2 — `.env` file loading for `pydantic-settings`

**Infrastructure:**
- `openai` 2.32.0 — pulled in transitively by `pydantic-ai`; used implicitly via `OpenAIProvider`
- `anthropic` 0.96.0 — present in lockfile as a transitive `pydantic-ai` dependency; not directly imported in application code
- `sqlite3` — Python stdlib; used directly for the checkpoint store (`src/weekforge/checkpoint.py`)

**Dev tooling:**
- `ruff` 0.15.10 — linting and formatting; config in `pyproject.toml` (`line-length=88`, selects E/F/I/UP, ignores E501)
- `mypy` 1.20.1 — strict type checking; excludes `tests/`

## Configuration

**Environment:**
- All config flows through `src/weekforge/config/env.py` → `Settings(BaseSettings)`
- Required vars: `NOTION_TOKEN`, `NOTION_TEST_DB_ID`, `OPENAI_API_KEY`, `NOTION_DB_TRAINING_SESSIONS`, `NOTION_DB_TRAINING_WEEK_SUMMARIES`, `NOTION_DB_TRAINING_TEMPLATES`, `NOTION_USER_PROFILE_PAGE_ID`
- Optional vars: `FAST_PROFILE` (default `gpt-5.4-nano`), `REASONING_PROFILE` (default `gpt-5.4`), `CAVEMAN_MODE` (default `false`)
- Template at `.env.template`; actual `.env` present but not committed

**Build:**
- `pyproject.toml` — single source of truth for project metadata, dependencies, tool config
- `uv.lock` — full resolved dependency tree committed to repo

## Model Profiles

**Defined in** `src/weekforge/config/llm_profiles.py`:

| Profile name | Provider | Model | Notes |
|---|---|---|---|
| `gpt-5.4-nano` | openai | gpt-5.4-nano | Chat Completions endpoint, temperature 0.1 |
| `gpt-5.4` | openai | gpt-5.4 | Responses API (`/v1/responses`), reasoning_effort=medium |

Profile selection is env-driven: `FAST_PROFILE` / `REASONING_PROFILE` env vars resolve to a profile name, which is looked up in `LLM_PROFILES`. Unrecognized names raise `KeyError` at import time (fail-fast).

## Platform Requirements

**Development:**
- macOS (`.venv` resolves macOS wheels); also builds Linux/Windows wheels in lockfile
- `uv` must be installed; no Makefile or shell scripts — all commands via `uv run`

**Production:**
- CLI tool only — no server, no container definition, no deployment config detected
- Requires `.env` file or equivalent environment variable injection at runtime

## Local State

**Checkpoint database:**
- `.weekforge/checkpoints.sqlite` — SQLite file in the project working directory
- Created on first run; not committed; stores paused workflow state keyed by `thread_id`

---

*Stack analysis: 2026-04-19*
