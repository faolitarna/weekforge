# Concerns

## Summary
Weekforge is ~20% implemented — 9 of ~11 planned source files don't exist yet. Several bugs exist in the small amount of live code, and there are structural cleanup items (orphaned dirs, deprecated API usage).

## Technical Debt

- `e2e_agent.py:30` — uses deprecated `system_prompt=` param; DEC-006 flags for migration to `instructions=` but not done
- `tests/pydantic_models/` — empty orphaned test dir, only `__pycache__` artifacts remain; safe to delete
- `.langgraph/` — leftover LangGraph prototype artifact; safe to delete
- `source-material/` — original markdown-driven coach project, read-only reference; `.claude/` inside is not an active pattern source

## Security Risks

- No secrets in codebase (env vars used correctly)
- Hardcoded USD→EUR rate of 0.92 in source with no update mechanism — financial data risk if used in calculations

## Bugs

- **Retry policy bug** (`src/weekforge/tools/notion_api_gateway.py`): `retry_if_exception_type(APIResponseError)` retries ALL API errors, not just 429. `_is_rate_limit_error` helper defined but never called — 5xx errors silently retried
- **`run_summarize_week` hard-crashes** (`src/weekforge/workflows/summarize_week.py:54`): raises bare `NotImplementedError`, not caught by `_run_or_pause` — users get raw traceback
- **`resume` command misses `summarize-week`** (`src/weekforge/cli.py:127-145`): only dispatches on `workflow == "e2e"` — paused summarize-week checkpoints hit unknown-workflow error
- **`filter_properties` API key may be wrong** (`src/weekforge/tools/notion_api_gateway.py:119-124`): Notion `data_sources.query` uses `filter`, not `filter_properties` — untested against live API
- **`fetch()` doesn't recurse nested blocks** — nested to-do lists in Notion pages silently drop child blocks
- **Markdown converter silently drops rich formatting** — inline bold/italic, code spans, numbered lists, nested bullets all lost
- **SQLite connection never closed** in `CheckpointStore` — potential resource leak

## Incomplete / Missing

80% of planned code not yet implemented:
- Step 1b, 1c, 1d: unimplemented
- Steps 2, 3, 4: unimplemented
- ~9 planned source files missing

## TODOs & FIXMEs

- Prompt sync test never created despite being required by step-1a spec

## Gaps / Unknowns

- Full scope of step 2-4 features not fully defined in current code
