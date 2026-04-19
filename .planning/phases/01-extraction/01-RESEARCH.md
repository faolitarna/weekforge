# Phase 01: Research

## Technical Approach

### 1. Notion Data Extraction (Tier 0)
- **Data Source**: Fetch session pages from the Notion DB.
- **Data Structure**: `notion_api_gateway.py` handles rate limits (via tenacity). We need to fetch child blocks for each page synchronously based on the *Synchronous Loop* decision.
- **Block Types**: Notion blocks come as `type`, `paragraph`, `heading_2`, `to_do`, etc. Checkbox state is stored in `to_do.checked`. We must iterate these blocks safely using `.get()` to avoid KeyErrors.

### 2. LLM Summarization (Tier 1)
- **Framework**: `pydantic-ai` with `summarize_agent`.
- **Output Model**: The `WeekSummary` model should accept loose strings for narrative fields (and metadata like `trend`) per the *Loose Strings* decision to accommodate creative variation across weeks.
- **Agent Metadata**: Use `agent_run_with_metadata.py` to capture token usage and costs.

### 3. HITL Terminal Review
- **Library**: `rich` and `typer`.
- **Presentation**: Extract only the `highlights` field from `WeekSummary` for terminal UX to prevent flooding, respecting the *Just Highlights* decision.
- **Feedback Loop**: Provide a simple input loop using `rich.prompt.Prompt.ask()`. Append the user feedback to message history and re-run the agent with original source info + new user instruction.

### 4. Writing & State Management
- **Formatting**: The legacy format is Markdown. We need a `notion_markdown_converter.py` or simple string builder to assemble the result block.
- **PLAN_STATE Bootstrapping**: Inside the extraction loop, verify if `Week="PLAN_STATE"` exists in `training_week_summaries`. If missing, generate defaults dynamically before merging the current week's update per the *Inside Extraction Loop* decision.
- **Persistence**: Save workflow state with `CheckpointStore` continuously.

## Validation Architecture
- Pass unit tests for checkbox arithmetic and block extraction.
- Assert fallback logic for absent PLAN_STATE works.
- End-to-end integration test mock.
