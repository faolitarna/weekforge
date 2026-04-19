# System Architecture

## System Overview & Legacy Context

Weekforge migrates legacy declarative text-based recipes (used manually with Claude Code) into structured workflow app using **Pydantic AI** for LLM integration and **plain Python** for orchestration. Migration introduces Agentic Patterns, optimizes token usage via Python tooling, builds rich local CLI, employs model-agnostic routing to balance cost and cognitive power.

**Agentic Complexity Level: 2 — Strategic Problem-Solver** (per Agentic Design Patterns Guide). Weekforge uses Context Engineering as systematic discipline — curates model context via PLAN_STATE, 3-week feedback windows, summary-first loading. Implements automated feedback loops (Evaluator-Optimizer) for output quality self-improvement. Does **not** reach Level 3 (Collaborative Multi-Agent) — single reasoning agent. Intentional: multi-agent coordination adds complexity without benefit for single-user, single-domain workflow.

**Framework choice (DEC-004):** Every workflow = sequential pipeline with at most one loop. Plain Python `async def` functions with `for`/`while`/`if` handle orchestration. Pydantic AI handles LLM calls with structured output validation and model-agnostic bindings. Lightweight custom checkpoint store (~60 lines) handles CLI session persistence.

## Intelligence Tiering & Task Abstraction

- **Tier 0 (Pure Python, Zero LLM):** All DB querying, data formatting, structural validation, deterministic logic. Tool nodes, Deterministic Evaluator, state management live here. Every operation that *can* be Python *must* be Python.
- **Tier 1 (Cheap/Fast Models):** Routing, classification, lightweight decisions where deterministic rules insufficient.
- **Tier 2 (Heavy Cognitive Models):** `plan_week`, `draft_session`, `summarize_week` — macro-planning, session generation, feedback synthesis.

### Task Classes (Configuration Interface)

| Task Class | Maps to | Purpose | Default |
|-----------|---------|---------|---------|
| `deterministic` | Tier 0 | Pure Python, no LLM | N/A |
| `fast` | Tier 1 | Routing, classification | `gpt-5.4-nano` |
| `reasoning` | Tier 2 | Planning, generation, synthesis | `gpt-5.4` |

Agent and workflow code references task classes (`fast`, `reasoning`), never specific model names. Swapping model = changing one config entry.

### Model Configuration Structure

Model profiles = Python dict (`src/weekforge/config/llm_profiles.py`). `.env` names which profile each task class uses (`FAST_PROFILE`, `REASONING_PROFILE`); defaults in Pydantic Settings class make `.env` override optional.

```python
@dataclass(frozen=True)
class LLMProfile:
    provider: str
    model: str
    temperature: float | None = None
    reasoning_effort: Literal["low", "medium", "high"] | None = None


LLM_PROFILES: dict[str, LLMProfile] = {
    "gpt-5.4-nano": LLMProfile(provider="openai", model="gpt-5.4-nano", temperature=0.1),
    "gpt-5.4":      LLMProfile(provider="openai", model="gpt-5.4", reasoning_effort="medium"),
}
```

Profile keys are OpenAI model IDs — no separate naming layer until multiple tunings of same model needed. `temperature` and `reasoning_effort` mutually exclusive per model family (reasoning models like `gpt-5.4` ignore `temperature`; non-reasoning models don't take `reasoning_effort`).

Task classes resolve to `LLMProfile` via `resolve_llm_profile("reasoning")`. Agents instantiated with `Agent(model=f"{spec.provider}:{spec.model}", model_settings=...)`, wiring only non-`None` fields into `model_settings` (see [step-0c](../steps/step-0c-llm-integration.md) for full pattern).

### Response Metadata

Every LLM call returns metadata via Pydantic AI's `result.usage()`: `input_tokens`, `output_tokens`. Latency captured via timing wrapper. `RunCost` accumulator tracks cost from every LLM call during workflow run — CLI displays total at completion.

For multi-turn flows (feedback loops), `run_with_metadata` also accepts an optional `message_history` and returns the post-call message list via `result.all_messages()`. Workflows persist that list across HITL pauses using `ModelMessagesTypeAdapter.dump_python(..., mode="json")` / `validate_python`, so closing the terminal mid-conversation does not lose context on resume.

## Generic Notion Tool Layer

All Notion interactions encapsulated in reusable Tier-0 tool layer. LLM never touches Notion directly; receives structured data from tools, returns structured outputs that tools write.

**Generic operations:** Query, Fetch, Create, Update.

**Design principles:**
- Tool inputs/outputs are typed data structures, not free text
- Notion API specifics (pagination, rate limiting, property type mapping) hidden inside tool layer
- Specific tool nodes (e.g., "fetch templates by week prefix") defined in step specs, composing these primitives

> Full interface contracts for tool layer specified in [step-0b](../steps/step-0b-notion-tools.md).

## CLI Architecture

### Library Stack

- **Typer** — Command routing, argument parsing, auto-generated help text
- **Rich** — Output formatting: tables, progress bars, panels, markdown rendering

### Command Structure

| Command | Behavior |
|---------|----------|
| `weekforge` | Show available commands + active checkpoint status |
| `weekforge plan` | Start or resume planning lifecycle (Lifecycle A) |
| `weekforge summarize` | Start or resume extraction lifecycle (Lifecycle B) |
| `weekforge resume` | Resume from last checkpoint (any lifecycle) |
| `weekforge e2e` | **Transitional (Phase 0 only).** End-to-end validation workflow — removed when `summarize` lands in step 1. |

### AuDHD-Informed Design Principles

Grounded in user's cognitive profile (`references/szymi-blueprint.md`):

- **Zero-decision entry.** Single command, no arguments, shows what's available.
- **Progressive disclosure.** Summary first, depth on request.
- **Scannable output.** Fixed, predictable section headers. No prose walls.
- **Clear decision points.** Every HITL pause: (1) what you're looking at, (2) options, (3) recommendation.
- **Flow-compatible momentum.** Approve -> auto-resume -> next draft preserves flow state.
- **Dopamine milestones.** Progress visualization (`3/8 ████░░░░`), completion celebrations.
- **Refinement over generation.** Present draft, ask "what would you change?" — never "what do you want?"

### HITL Presentation Pattern

Every interrupt renders Rich panel with: **Context** (what you're looking at), **Options** (what you can do), **Recommendation** (suggested action).

### Output Formatting

| Content Type | Rich Component |
|-------------|----------------|
| Structured data | `Table` |
| Session drafts, summaries | `Markdown` renderer |
| Decision points | `Panel` with bordered sections |
| Progress tracking | `Progress` bar |
| Errors and warnings | `Console` markup |
| Run completion | Cost summary + session count in `Panel` |

## Secrets Management

- **`.env`** — Secret values. In `.gitignore`.
- **`.env.template`** — Committed. Variable names with placeholders and comments.
- On startup, validate all required env vars present. Fail immediately with clear error if missing.

## Project Tooling Standards

- **Python 3.13+** (enforced via `pyproject.toml`)
- **UV** — Package and dependency manager (`uv sync`, `uv run weekforge`)
- **Ruff** — Linting and formatting
- **mypy** — Static type checking in strict mode

### Key Dependencies

- **Pydantic AI** — LLM agent framework (structured output, model-agnostic bindings)
- **Pydantic** — Data validation and state schemas
- **Typer + Rich** — CLI framework and terminal UI
- **Notion Client** — Notion API SDK
- **Tenacity** — Retry logic for Notion tool layer

### Project Layout

```
weekforge/
├── src/
│   └── weekforge/
│       ├── __init__.py
│       ├── cli.py            # Typer application entry point
│       ├── checkpoint.py     # SQLite checkpoint store
│       ├── hitl.py           # HITL presentation helpers
│       ├── workflows/        # Orchestrator functions (plain Python)
│       ├── agents/           # Pydantic AI agent definitions
│       ├── tools/            # Notion tool layer + other tools
│       ├── config/           # Model config, env loading
│       └── models/           # Domain data: pricing, LLM cost, workflow state
├── tests/
├── pyproject.toml
├── uv.lock
├── .env
├── .env.template
└── .gitignore
```

### Development Workflow

1. `uv sync` — Install/update dependencies
2. `uv run weekforge` — Run application
3. `uv run ruff check .` — Lint
4. `uv run ruff format .` — Format
5. `uv run mypy src/` — Type check
6. `uv run pytest` — Run tests

## User Configuration

User profiles and guardrails stored in Notion. `ConfigLoader` node fetches at runtime.