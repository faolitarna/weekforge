# Architecture

**Analysis Date:** 2026-04-19

## Summary

Weekforge is a Python CLI application that orchestrates an LLM-assisted training week lifecycle. It follows a layered, sequential pipeline architecture (Agentic Complexity Level 2) using plain Python for orchestration, Pydantic AI for structured LLM calls, Notion as the sole data store, and a SQLite checkpoint store for HITL session persistence. Agents never touch Notion directly — a strict Tier-0 tool layer mediates all external I/O.

## Pattern Overview

**Overall:** Tiered sequential pipeline with human-in-the-loop checkpointing

**Key Characteristics:**
- Intelligence tiering: Tier 0 (pure Python/deterministic), Tier 1 (fast LLM), Tier 2 (reasoning LLM)
- Workflow orchestration via plain `while` loops over a `step` state field — no graph framework
- State fully serialized to SQLite between HITL pauses; resume reconstructs exact position
- LLM agents are thin wrappers: configured at module load, invoked via `run_with_metadata()`
- All Notion I/O mediated exclusively through `tools/notion_api_gateway.py`

## Layers

**CLI Layer:**
- Purpose: Command routing, env validation, checkpoint display, KeyboardInterrupt handling
- Location: `src/weekforge/cli.py`
- Contains: Typer app with commands (`e2e`, `summarize-week`, `plan`, `resume`), `_validate_env_or_exit()`, `_run_or_pause()`
- Depends on: `checkpoint.py`, workflow functions, `config/env.py`
- Used by: End user via `uv run weekforge`

**Workflow Layer:**
- Purpose: Orchestrates step-by-step pipelines; holds all control flow
- Location: `src/weekforge/workflows/`
- Contains: `run_e2e()` in `e2e.py`, `run_summarize_week()` in `summarize_week.py`; each workflow owns its own Pydantic state model
- Depends on: `agents/`, `tools/`, `checkpoint.py`, `hitl.py`, `models/`
- Used by: CLI commands

**Agent Layer:**
- Purpose: Pydantic AI agent definitions and execution harness
- Location: `src/weekforge/agents/`
- Contains: `e2e_agent.py` (single agent instance), `agent_run_with_metadata.py` (generic runner), `openai_model_factory.py` (model construction), `prompt_composer.py` (system prompt assembly)
- Depends on: `config/env.py`, `config/llm_profiles.py`, `models/llm_call_cost.py`, `models/pricing.py`
- Used by: Workflow layer

**Tool Layer (Tier 0):**
- Purpose: All external I/O; the only code that touches Notion API
- Location: `src/weekforge/tools/`
- Contains: `notion_api_gateway.py` (query/fetch/create/update), `notion_markdown_converter.py` (bidirectional markdown↔Notion blocks), `formatting.py` (pure string formatters)
- Depends on: `config/env.py` (for Notion token), `notion-client` SDK, `tenacity` (retry)
- Used by: Workflow layer, `config/user_profile_loader.py`

**Config Layer:**
- Purpose: Environment settings, LLM profile resolution, user profile loading, prompt loading
- Location: `src/weekforge/config/`
- Contains: `env.py` (Pydantic Settings singleton), `llm_profiles.py` (LLMProfile dataclass + profile dict), `user_profile_loader.py` (fetches Notion page → `UserProfile`), `prompts/loader.py` (reads bundled `.md` files via `importlib.resources`)
- Depends on: `tools/notion_api_gateway.py` (profile loader), `pydantic-settings`
- Used by: Agent layer, workflow layer, CLI

**Infrastructure Layer:**
- Purpose: Session persistence and HITL interaction
- Location: `src/weekforge/checkpoint.py`, `src/weekforge/hitl.py`
- Contains: `CheckpointStore` (SQLite CRUD: save/load/list_active/delete), `hitl_confirm()` (save → render Rich panel → read user input → return `HitlDecision`)
- Depends on: `sqlite3` (stdlib), `rich`
- Used by: Workflow layer, CLI

**Models Layer:**
- Purpose: Domain data models not tied to any single workflow
- Location: `src/weekforge/models/`
- Contains: `llm_call_cost.py` (CallMetadata, RunCost), `pricing.py` (per-model EUR cost table), `user_profile.py` (UserProfile Pydantic model)
- Depends on: `pydantic`
- Used by: Agent layer, workflow layer, config layer

## Data Flow

**E2E Workflow (fully implemented):**

1. CLI receives `e2e` command → constructs `CheckpointStore`, generates/reuses `thread_id`
2. `run_e2e()` loads or creates `E2eState` from checkpoint
3. **`query` step**: `notion_api_gateway.query()` fetches records from test database → stored in `state.records`; state saved to SQLite
4. **`agent` step**: State saved pre-call (crash safety); `run_with_metadata(e2e_agent, prompt, message_history)` calls OpenAI → returns `ProcessorResult`, `CallMetadata`, updated message list; all stored on state; `state.step = "review"`
5. **`review` step**: `hitl_confirm()` saves state, renders panel with output + cost summary, waits for user input → approve / feedback / quit; on feedback: `state.pending_feedback` set, step resets to `agent` (feedback loop); on quit: checkpoint preserved, function returns
6. **`write` step**: `notion_api_gateway.create()` writes page with markdown body; `state.step = "done"`
7. **`done`**: checkpoint deleted, run summary panel rendered

**Summarize-Week Workflow (stub):**

1. CLI receives `summarize-week <N>` → constructs store, derives `thread_id = "summarize-week-W07"`
2. `run_summarize_week()` checks for existing summary in Notion (overwrite guard)
3. Loads coaching context: `load_prompt(COACHING_PERSONA)`, `load_prompt(COACHING_GUARDRAILS)`, `load_user_profile()` (Notion fetch → markdown)
4. Raises `NotImplementedError` — summary generation body not yet wired

**State Management:**
- Each workflow owns its own Pydantic `BaseModel` subclass (e.g., `E2eState`)
- State serialized via `model_dump_json()` / `model_validate_json()` into SQLite `checkpoints` table
- `step` field is a string matching named pipeline stages — must not be renamed without a migration
- Message history for multi-turn LLM loops serialized via Pydantic AI's `ModelMessagesTypeAdapter`
- Runtime store at `.weekforge/checkpoints.sqlite` (project-local, relative to CWD)

## Key Abstractions

**CheckpointStore:**
- Purpose: SQLite-backed session persistence enabling CLI resume after terminal close
- Location: `src/weekforge/checkpoint.py`
- Pattern: UPSERT on `thread_id`; `delete()` called only on successful workflow completion

**run_with_metadata():**
- Purpose: Generic synchronous agent runner that captures token usage, latency, and cost
- Location: `src/weekforge/agents/agent_run_with_metadata.py`
- Pattern: Wraps `agent.run_sync()`; returns `(result, CallMetadata, list[ModelMessage])`; workflows accumulate `CallMetadata` into `RunCost`

**LLM Profile system:**
- Purpose: Decouple agent code from specific model names; swap models via `.env`
- Location: `src/weekforge/config/llm_profiles.py`, `src/weekforge/agents/openai_model_factory.py`
- Pattern: Agents reference task classes (`"fast"` or `"reasoning"`) → `resolve_llm_profile()` reads env-configured name → `build_openai_model()` constructs `Model` + `ModelSettings`

**notion_api_gateway:**
- Purpose: Single point of Notion API access; all pagination, rate-limiting, and error mapping here
- Location: `src/weekforge/tools/notion_api_gateway.py`
- Pattern: Module-level `_client`; public interface `query()`, `fetch()`, `create()`, `update()`; 429 retried via `tenacity`; 401/404 raise domain errors immediately

## Entry Points

**CLI entrypoint:**
- Location: `src/weekforge/cli.py` → `app()` (registered as `weekforge` console script in `pyproject.toml`)
- Triggers: `uv run weekforge [command]`
- Responsibilities: Env validation on every invocation, command routing, checkpoint display when called bare, KeyboardInterrupt → resume hint

**E2E workflow:**
- Location: `src/weekforge/workflows/e2e.py` → `run_e2e()`
- Triggers: `weekforge e2e` or `weekforge resume --thread-id <id>`

**Summarize-week workflow:**
- Location: `src/weekforge/workflows/summarize_week.py` → `run_summarize_week()`
- Triggers: `weekforge summarize-week <N>`

## Error Handling

**Strategy:** Fail fast with user-friendly Rich panels; domain errors bubble to CLI, not end users

**Patterns:**
- `_validate_env_or_exit()` in CLI intercepts Pydantic `ValidationError` on missing env vars → renders Rich panel with missing variable names
- `NotionAuthFailedError` / `NotionNotFoundError` / `NotionAPIError` raised by tool layer; 401 and 404 surface immediately, 429 retried up to 4 attempts
- `ConfigError` raised by `config/` modules when Notion-sourced configuration is empty/invalid
- Agents crash at module import if env vars are missing (module-level `settings` instantiation)
- `hitl_confirm()` crash safety: state saved to checkpoint BEFORE rendering user prompt

## Cross-Cutting Concerns

**Logging:** `logging.getLogger(__name__)` per module; used sparingly (tool layer warnings, truncation notices)
**Validation:** Pydantic models throughout; `pydantic-settings` for env; `model_dump_json`/`model_validate_json` for checkpoint serialization
**Authentication:** Notion token and OpenAI API key from `.env` via `Settings`; validated at CLI startup

## Gaps / Unknowns

- `summarize-week` workflow body is a stub (`NotImplementedError`) — step 1b/1c not yet implemented
- `plan` command is a stub — step 2 not started
- `resume` command only dispatches `e2e` workflow; new workflows need explicit dispatch cases added
- The `e2e` workflow and command are transitional (Phase 0 only) — will be removed when `summarize-week` is complete
- No async I/O: `agent.run_sync()` is used throughout; concurrent context loading (planned via `asyncio.gather`) not yet implemented
- Evaluator-Optimizer pattern (pre-HITL deterministic validation) is specified in `specs/reference/patterns.md` but not yet implemented
