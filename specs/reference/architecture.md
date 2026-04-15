# System Architecture

## System Overview & Legacy Context

The Weekforge project migrates legacy declarative text-based recipes (used manually with Claude Code) into a structured workflow application using **Pydantic AI** for LLM integration and **plain Python** for orchestration. The migration introduces Agentic Patterns, optimizes token usage via Python tooling, constructs a rich local CLI environment, and employs model-agnostic routing to balance cost and cognitive power.

**Agentic Complexity Level: 2 — Strategic Problem-Solver** (per Agentic Design Patterns Guide). Weekforge uses Context Engineering as a systematic discipline — strategically curating the model's context through PLAN_STATE, 3-week feedback windows, and summary-first loading. It implements automated feedback loops (Evaluator-Optimizer) for self-improvement of output quality. It does **not** reach Level 3 (Collaborative Multi-Agent) — there is a single reasoning agent. This is intentional: multi-agent coordination adds complexity without benefit for a single-user, single-domain workflow.

**Framework choice (DEC-004):** Every workflow is a sequential pipeline with at most one loop. Plain Python `async def` functions with `for`/`while`/`if` handle orchestration. Pydantic AI handles LLM calls with structured output validation and model-agnostic bindings. A lightweight custom checkpoint store (~60 lines) handles CLI session persistence.

## Intelligence Tiering & Task Abstraction

- **Tier 0 (Pure Python, Zero LLM):** All database querying, data formatting, structural validation, and deterministic logic. Tool nodes, the Deterministic Evaluator, and state management live here. Every operation that *can* be Python *must* be Python.
- **Tier 1 (Cheap/Fast Models):** Routing, classification, and lightweight decisions where deterministic rules aren't sufficient.
- **Tier 2 (Heavy Cognitive Models):** `plan_week`, `draft_session`, `summarize_week` — macro-planning, session generation, and feedback synthesis.

### Task Classes (Configuration Interface)

| Task Class | Maps to | Purpose | Default |
|-----------|---------|---------|---------|
| `deterministic` | Tier 0 | Pure Python, no LLM | N/A |
| `fast` | Tier 1 | Routing, classification | `gpt-5.4-nano` |
| `reasoning` | Tier 2 | Planning, generation, synthesis | `gpt-5.4` |

Agent and workflow code references task classes (`fast`, `reasoning`), never specific model names. Swapping a model means changing one config entry.

### Model Configuration Structure

```yaml
models:
  fast:
    provider: openai
    model: gpt-5.4-nano
    reasoning: medium
    temperature: 0.1
  reasoning:
    provider: openai
    model: gpt-5.4
    reasoning: medium
    temperature: 0.7
```

Task classes resolve to Pydantic AI model strings (e.g., `"openai:gpt-5.4"`). Agents are instantiated with `Agent(model=get_model("reasoning"), ...)`.

### Response Metadata

Every LLM call returns metadata via Pydantic AI's `result.cost()`: `request_tokens`, `response_tokens`, `total_tokens`. Latency is captured via a timing wrapper. A `RunCost` accumulator tracks cost from every LLM call during a workflow run — the CLI displays the total at completion.

## Generic Notion Tool Layer

All Notion interactions are encapsulated in a reusable Tier-0 tool layer. The LLM never touches Notion directly; it receives structured data from tools and returns structured outputs that tools write.

**Generic operations:** Query, Fetch, Create, Update.

**Design principles:**
- Tool inputs and outputs are typed data structures, not free text
- Notion API specifics (pagination, rate limiting, property type mapping) are hidden inside the tool layer
- Specific tool nodes (e.g., "fetch templates by week prefix") are defined in step specs, composing these primitives

> Full interface contracts for the tool layer are specified in [step-0b](../steps/step-0b-notion-tools.md).

## CLI Architecture

### Library Stack

- **Typer** — Command routing, argument parsing, auto-generated help text
- **Rich** — Output formatting: tables, progress bars, panels, markdown rendering

### Command Structure

| Command | Behavior |
|---------|----------|
| `weekforge` | Show available commands + active checkpoint status |
| `weekforge plan` | Start or resume the planning lifecycle (Lifecycle A) |
| `weekforge summarize` | Start or resume the extraction lifecycle (Lifecycle B) |
| `weekforge continue` | Resume from the last checkpoint (any lifecycle) |

### AuDHD-Informed Design Principles

Grounded in the user's cognitive profile (`references/szymi-blueprint.md`):

- **Zero-decision entry.** Single command with no arguments shows what's available.
- **Progressive disclosure.** Summary first, depth on request.
- **Scannable output.** Fixed, predictable section headers. No walls of prose.
- **Clear decision points.** Every HITL pause: (1) what you're looking at, (2) options, (3) recommendation.
- **Flow-compatible momentum.** Approve -> auto-continue -> next draft preserves flow state.
- **Dopamine milestones.** Progress visualization (`3/8 ████░░░░`), completion celebrations.
- **Refinement over generation.** Present a draft, ask "what would you change?" — never "what do you want?"

### HITL Presentation Pattern

Every interrupt renders a Rich panel with: **Context** (what you're looking at), **Options** (what you can do), **Recommendation** (suggested action).

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
- On startup, validate all required env vars are present. Fail immediately with clear error if missing.

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
│       └── models/           # State schemas, result types
├── tests/
├── pyproject.toml
├── uv.lock
├── .env
├── .env.template
└── .gitignore
```

### Development Workflow

1. `uv sync` — Install/update dependencies
2. `uv run weekforge` — Run the application
3. `uv run ruff check .` — Lint
4. `uv run ruff format .` — Format
5. `uv run mypy src/` — Type check
6. `uv run pytest` — Run tests

## User Configuration

User profiles and guardrails are stored in Notion. A `ConfigLoader` node fetches this data at runtime.
