# Structure

**Analysis Date:** 2026-04-19

## Summary

Weekforge is a Python CLI package installed via `uv`/`hatchling` with a `src/` layout. Application code lives exclusively under `src/weekforge/`, organized into six sub-packages by responsibility (agents, config, models, prompts, tools, workflows). Tests mirror the source tree under `tests/`. A parallel non-code structure (`specs/`, `references/`, `.agents/`, `.planning/`) supports spec-driven development and AI-assisted tooling. `source-material/` holds the original pure-markdown Claude Code project that weekforge was migrated from; it is read-only reference, not active code.

---

## Directory Layout

```
weekforge/
├── src/
│   └── weekforge/              # Installable package (weekforge.cli:app entry point)
│       ├── agents/             # Pydantic AI agent definitions and runners
│       ├── config/             # Env settings, LLM profiles, user-profile loader
│       ├── models/             # Pydantic data models (cost, pricing, user profile)
│       ├── prompts/            # Bundled prompt .md files + loader
│       ├── tools/              # Notion API gateway and markdown converter
│       ├── workflows/          # Workflow orchestrators (e2e, summarize_week)
│       ├── checkpoint.py       # SQLite-backed CheckpointStore
│       ├── hitl.py             # Human-in-the-loop confirm/pause helper
│       └── cli.py              # Typer app — sole public entry point
│
├── tests/                      # Mirrors src/weekforge sub-package layout
│   ├── agents/
│   ├── config/
│   ├── models/
│   ├── pydantic_models/        # LEGACY — marked for deletion; no source counterpart
│   ├── tools/                  # Needs reorganisation (see Concerns)
│   ├── workflows/
│   ├── conftest.py             # Shared fixtures
│   ├── test_checkpoint.py
│   └── test_cli.py
│
├── specs/                      # Spec-driven development artefacts
│   ├── _index.md               # Step status dashboard
│   ├── decision-log.md         # Append-only architectural decision log
│   ├── reference/              # Architecture, patterns, state schema, failure modes
│   └── steps/                  # Per-step implementation specs (step-0a … step-4)
│
├── references/                 # Background reading (agentic design patterns, blueprint)
│
├── .agents/                    # AI dev persona definitions (Antigravity convention)
│   ├── agents/                 # feature-developer, specs-developer, code-reviewer, etc.
│   └── skills/                 # prompt-review, specs-management skill packs
│
├── .planning/
│   └── codebase/               # GSD codebase map documents (STACK, ARCHITECTURE, etc.)
│
├── .weekforge/                 # Runtime data dir (gitignored)
│   └── checkpoints.sqlite      # SQLite checkpoint DB, created on first run
│
├── source-material/            # READ-ONLY — the original .md-driven Claude Code project
│                               # weekforge migrated from. Not related to active .agents/.
│                               # Kept for design reference only; do not import or execute.
│
├── .langgraph/                 # ARTIFACT — leftover from an earlier LangGraph prototype.
│                               # Replaced by the custom CheckpointStore. Safe to delete.
│
├── pyproject.toml              # Package metadata, deps, tool config (ruff, mypy, pytest)
├── uv.lock                     # Locked dependency tree
├── AGENTS.md                   # AI persona index (top-level entry for Claude Code)
├── SKILLS.md                   # Skill index
├── CLAUDE.md                   # Claude Code project pointer
└── .env / .env.template        # Runtime secrets (gitignored) / public template
```

---

## Module Organization

The source package is layered; lower layers have no upward imports:

```
cli.py
  └── workflows/          (orchestrators — compose all layers)
        ├── agents/       (Pydantic AI agents + runners)
        ├── tools/        (Notion API gateway)
        ├── models/       (data models)
        ├── config/       (env settings, LLM profiles, user-profile loader)
        ├── prompts/      (bundled .md prompt files)
        ├── checkpoint.py (SQLite persistence)
        └── hitl.py       (terminal HITL prompt)
```

Key relationships:

- `cli.py` constructs a `CheckpointStore` and delegates to a workflow function; it does not touch agents or tools directly.
- `workflows/e2e.py` and `workflows/summarize_week.py` are the only orchestrators; each imports from all other sub-packages.
- `tools/notion_api_gateway.py` is the sole Notion-touching module. Agents never import it directly.
- `agents/e2e_agent.py` imports from `config/` to build its model via `openai_model_factory`; agent definitions do not import workflows or tools.
- `config/user_profile_loader.py` sits inside `config/` but depends on `tools/` (Notion fetch) — a shallow cross-layer call that is intentional and documented.
- `prompts/loader.py` reads `.md` files bundled inside the package via `importlib.resources`; no filesystem path assumptions.
- `models/` contains only Pydantic models and a pricing helper; no external calls.

---

## Naming Conventions

**Files:**
- All lowercase with underscores: `notion_api_gateway.py`, `user_profile_loader.py`, `llm_call_cost.py`
- Workflow files named after the command they implement: `summarize_week.py` → `weekforge summarize-week`, `e2e.py` → `weekforge e2e`
- Test files prefixed `test_`: `test_notion_crud.py`, `test_cli.py`, `test_checkpoint.py`

**Directories:**
- All lowercase with underscores: `src/weekforge/`, `tools/`, `workflows/`
- Test mirror: `tests/agents/` mirrors `src/weekforge/agents/`
- Exception: `tests/pydantic_models/` is a legacy name pending deletion

**Classes:**
- PascalCase throughout: `CheckpointStore`, `E2eState`, `CallMetadata`, `UserProfile`, `LLMProfile`
- State models suffixed `State`: `E2eState`
- Error classes suffixed `Error`: `NotionAuthFailedError`, `NotionNotFoundError`, `NotionAPIError`, `ConfigError`

**Functions:**
- snake_case; workflow entry points prefixed `run_`: `run_e2e()`, `run_summarize_week()`
- Private helpers prefixed `_`: `_make_store()`, `_validate_env_or_exit()`, `_build_prompt()`

**Enums:**
- `StrEnum` with UPPER_CASE members: `Prompt.COACHING_PERSONA`

**Step labels (SQLite):**
- Lowercase single-word strings: `"query"`, `"agent"`, `"review"`, `"write"`, `"done"` — these are persisted and must not be renamed without a migration.

---

## Key Files

| File | Role |
|------|------|
| `src/weekforge/cli.py` | Typer app; all CLI commands; env validation on every invocation |
| `src/weekforge/checkpoint.py` | `CheckpointStore` — SQLite upsert/load/delete for workflow state |
| `src/weekforge/hitl.py` | `hitl_confirm()` — renders HITL panel, saves checkpoint, returns `HitlDecision` |
| `src/weekforge/config/env.py` | `Settings` (pydantic-settings); `settings` module-level singleton |
| `src/weekforge/config/llm_profiles.py` | `LLM_PROFILES` dict; `resolve_llm_profile()` maps task class → `LLMProfile` |
| `src/weekforge/config/user_profile_loader.py` | `load_user_profile()` — fetches Notion page, converts to `UserProfile` |
| `src/weekforge/agents/e2e_agent.py` | `e2e_agent` — the only active Pydantic AI `Agent` instance |
| `src/weekforge/agents/agent_run_with_metadata.py` | `run_with_metadata()` — wraps `agent.run_sync()`, returns result + `CallMetadata` + messages |
| `src/weekforge/agents/prompt_composer.py` | `compose_system_prompt()` — appends caveman-lite directive when `caveman_mode` is true |
| `src/weekforge/agents/openai_model_factory.py` | `build_openai_model(profile)` → `(Model, ModelSettings)`. Routing logic: profiles with `reasoning_effort` use the Responses API (`OpenAIResponsesModel`); profiles with `temperature` use Chat Completions (`OpenAIChatModel`). Currently OpenAI-only; generalize when a second provider is added. |
| `src/weekforge/tools/notion_api_gateway.py` | `query()`, `fetch()`, `create()`, `update()` — sole Notion API surface; handles retry/errors |
| `src/weekforge/tools/notion_markdown_converter.py` | `convert_blocks_to_markdown()`, `convert_markdown_to_blocks()` |
| `src/weekforge/tools/formatting.py` | `format_week_prefix()` — formats week number to standard string |
| `src/weekforge/models/llm_call_cost.py` | `CallMetadata` (frozen Pydantic), `RunCost` (dataclass accumulator) |
| `src/weekforge/models/pricing.py` | `estimate_cost_eur()` — per-model token cost lookup |
| `src/weekforge/models/user_profile.py` | `UserProfile` — page_id + raw markdown; no structured field parsing |
| `src/weekforge/prompts/loader.py` | `load_prompt(Prompt)` — cached `importlib.resources` read of bundled `.md` files |
| `src/weekforge/prompts/coaching_persona.md` | Bundled coaching persona system prompt |
| `src/weekforge/prompts/coaching_guardrails.md` | Bundled coaching guardrails system prompt |
| `src/weekforge/workflows/e2e.py` | Phase-0 validation workflow: query → agent → HITL → write |
| `src/weekforge/workflows/summarize_week.py` | Step-1 stub: loads context, raises `NotImplementedError` |
| `src/weekforge/config/__init__.py` | Defines `ConfigError` |
| `pyproject.toml` | Package metadata, entry point, dependencies, ruff/mypy/pytest config |
| `specs/_index.md` | Step status dashboard — source of truth for implementation progress |
| `.env.template` | Documents all required environment variables |
| `.weekforge/checkpoints.sqlite` | Runtime checkpoint DB; per-project, not committed |

---

## Where to Add New Code

**New workflow (e.g. step-1b):**
- Orchestrator: `src/weekforge/workflows/<name>.py` with a `run_<name>()` entry function
- CLI command: add `@app.command()` in `src/weekforge/cli.py`
- Tests: `tests/workflows/test_<name>.py`

**New agent:**
- Definition: `src/weekforge/agents/<name>_agent.py`
- Tests: `tests/agents/test_<name>.py`

**New Notion tool operation:**
- Add to `src/weekforge/tools/notion_api_gateway.py` only; do not create additional Notion modules

**New prompt file:**
- Add `.md` file to `src/weekforge/prompts/`
- Add enum member to `Prompt` in `src/weekforge/prompts/loader.py`
- Force-include is already configured in `pyproject.toml` via `[tool.hatch.build.targets.wheel.force-include]`

**New Pydantic model:**
- `src/weekforge/models/<name>.py`
- Tests: `tests/models/test_<name>.py`

**New config value:**
- Add field to `Settings` in `src/weekforge/config/env.py`
- Document in `.env.template`

---

## Concerns

**Delete `tests/pydantic_models/`:**
- Legacy directory with no corresponding source module. Should be removed; any surviving tests should be moved to `tests/models/`.

**Delete `.langgraph/`:**
- Leftover artefact from an earlier LangGraph prototype that was replaced by the custom `CheckpointStore`. Contains no active code. Safe to delete.

**`tests/tools/` needs reorganisation:**
- Currently splits Notion tests across `test_notion_crud.py`, `test_notion_errors.py`, and `test_notion_markdown_converter.py` with no clear structural rationale. The split may reflect an ad-hoc growth pattern rather than intentional design. Worth consolidating or establishing explicit naming conventions before the test suite grows further.

**`source-material/` is read-only reference:**
- The `.claude/` subtree inside `source-material/` (commands, hooks, rules) belongs to the old project and has no relationship to the active `.agents/` tree. Nothing in `source-material/` should be imported, executed, or used as a pattern source.
