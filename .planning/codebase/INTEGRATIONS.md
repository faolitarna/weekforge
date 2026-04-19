# External Integrations

**Analysis Date:** 2026-04-19

## Summary

Weekforge integrates with two external services: Notion (as the sole data store for training records, summaries, templates, and the user profile page) and OpenAI (for all LLM agent calls). All integration credentials are injected via `.env` / environment variables and validated at startup by `pydantic-settings`. There are no webhooks, queues, or observability services.

## APIs & External Services

**Notion:**
- Used for all persistent data: training sessions, weekly summaries, training templates, and user profile
- SDK/Client: `notion-client==3.0.0` — the only version that supports the `data_sources` query path used in `src/weekforge/tools/notion_api_gateway.py`
- Auth: `NOTION_TOKEN` env var — Notion Integration Token (Bearer auth, passed to `Client(auth=...)`)
- Gateway: `src/weekforge/tools/notion_api_gateway.py` — single module that owns all Notion I/O; exposes `query()`, `fetch()`, `create()`, `update()`
- Retry policy: 429 only, exponential backoff (1s→2s→4s), 4 attempts max via `tenacity`
- Error mapping: 401 → `NotionAuthFailedError`, 404 → `NotionNotFoundError`, everything else → `NotionAPIError`

**OpenAI:**
- Used for all LLM inference; no other AI provider is called from application code
- SDK: `openai` 2.32.0 (transitive via `pydantic-ai`); accessed through `pydantic-ai` model wrappers only
- Auth: `OPENAI_API_KEY` env var — passed to `OpenAIProvider(api_key=...)` in `src/weekforge/agents/openai_model_factory.py`
- Two endpoints in use:
  - Chat Completions (`/v1/chat/completions`) — for `gpt-5.4-nano` (fast tasks)
  - Responses API (`/v1/responses`) — for `gpt-5.4` with `reasoning_effort`; required because OpenAI rejects function-tools + reasoning_effort on Chat Completions

## Data Storage

**Notion (primary data store):**
- All training records live in Notion databases; weekforge has no standalone database beyond checkpoints
- The app resolves `database_id → data_source_id` internally before every query (Notion API detail hidden in `notion_api_gateway.query()`)
- Pagination handled transparently; callers always receive the full record set

**Local SQLite (checkpoint store):**
- Path: `.weekforge/checkpoints.sqlite` relative to the working directory
- Client: Python stdlib `sqlite3` — no ORM
- Purpose: pause/resume workflow state between CLI invocations
- Schema: single `checkpoints` table with columns `(thread_id, workflow, step, state_json, updated_at)`
- Not a shared or remote resource; process-local only

**File Storage:**
- None — no S3, GCS, or local file output beyond `.weekforge/checkpoints.sqlite`

**Caching:**
- None — no Redis or in-process cache; prompt files are cached in-process via `@functools.cache` in `src/weekforge/prompts/loader.py`

## Authentication & Identity

**Notion:**
- Integration Token scoped to specific databases; stored as `NOTION_TOKEN`
- No OAuth flow — token is static, set in `.env`

**OpenAI:**
- API key auth; stored as `OPENAI_API_KEY`
- No per-user identity — single key for all runs

**No user authentication layer:**
- Weekforge is a single-user CLI tool; there is no auth middleware, session management, or identity provider

## Monitoring & Observability

**Error Tracking:**
- None — no Sentry, Datadog, or equivalent integration detected

**Logs:**
- Standard library `logging` used in `src/weekforge/tools/notion_api_gateway.py` and `src/weekforge/workflows/e2e.py`
- No structured log format or log shipper configured

**Cost tracking (in-process only):**
- `src/weekforge/models/pricing.py` — manual per-model pricing table (USD/MTok); estimates EUR cost per call
- `src/weekforge/models/llm_call_cost.py` — `CallMetadata` and `RunCost` accumulate token + latency + cost across a workflow run
- Rendered in terminal at run completion; not persisted beyond the SQLite checkpoint (which is deleted on success)

## CI/CD & Deployment

**Hosting:**
- None detected — no Dockerfile, `fly.toml`, Heroku `Procfile`, or cloud config files present

**CI Pipeline:**
- None detected — no `.github/workflows/`, `.circleci/`, or equivalent

**Distribution:**
- `dist/` directory present, suggesting a wheel has been built locally (`hatchling` build system)
- Installed and run via `uv run weekforge <cmd>`

## Environment Configuration

**Required env vars** (all validated at startup by `src/weekforge/config/env.py`):

| Variable | Purpose |
|---|---|
| `NOTION_TOKEN` | Notion Integration Token for API access |
| `NOTION_TEST_DB_ID` | Notion database ID for E2E validation workflow |
| `OPENAI_API_KEY` | OpenAI API key for all LLM calls |
| `NOTION_DB_TRAINING_SESSIONS` | Notion DB backing training session records |
| `NOTION_DB_TRAINING_WEEK_SUMMARIES` | Notion DB for weekly summary pages |
| `NOTION_DB_TRAINING_TEMPLATES` | Notion DB for training plan templates |
| `NOTION_USER_PROFILE_PAGE_ID` | ID of the Notion page holding the user profile (not a DB) |

**Optional env vars** (have defaults):

| Variable | Default | Purpose |
|---|---|---|
| `FAST_PROFILE` | `gpt-5.4-nano` | LLM profile name for low-latency tasks |
| `REASONING_PROFILE` | `gpt-5.4` | LLM profile name for quality-sensitive tasks |
| `CAVEMAN_MODE` | `false` | Strips pleasantries/hedging from LLM outputs |

**Secrets location:**
- `.env` file in project root (present, not committed)
- Template at `.env.template` (committed, values empty)
- No secret manager (Vault, AWS Secrets Manager, etc.) in use

## Webhooks & Callbacks

**Incoming:**
- None — no HTTP server, so no webhook endpoints

**Outgoing:**
- None — all API calls are synchronous, request-response; no event emission

## Notion Database Layout

Five Notion resources are referenced by the application:

| Env var | Notion type | Used by |
|---|---|---|
| `NOTION_TEST_DB_ID` | Database | `e2e` workflow |
| `NOTION_DB_TRAINING_SESSIONS` | Database | `summarize-week` workflow (planned) |
| `NOTION_DB_TRAINING_WEEK_SUMMARIES` | Database | `summarize-week` workflow |
| `NOTION_DB_TRAINING_TEMPLATES` | Database | not yet wired |
| `NOTION_USER_PROFILE_PAGE_ID` | Page (not DB) | `load_user_profile()` in `src/weekforge/config/user_profile_loader.py` |

## Gaps / Unknowns

- `anthropic` 0.96.0 is resolved in `uv.lock` (transitive via `pydantic-ai`) but no Anthropic model is configured in `llm_profiles.py`. It is available but unused.
- No CI pipeline or deployment target is configured; the project is run exclusively as a local developer CLI.
- `NOTION_DB_TRAINING_TEMPLATES` is declared in `Settings` and `.env.template` but no workflow currently reads from it.
- Cost pricing table in `src/weekforge/models/pricing.py` is hardcoded and will silently return `0.0` for any model not in the table — including future models. No alerting when pricing data is missing.

---

*Integration audit: 2026-04-19*
