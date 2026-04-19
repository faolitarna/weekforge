# Testing Patterns

**Analysis Date:** 2026-04-19

## Summary

weekforge uses pytest with pytest-mock. The test philosophy is defined in `feature-tester.md`: every test must justify its existence, the suite should be small and sharp rather than exhaustive, and LLM output content is explicitly out of scope. 56 tests across 12 files cover the deterministic core (Tier-0 tools, models, checkpoint, workflow orchestration) while deliberately skipping non-deterministic and visual concerns.

## Test Framework

**Runner:** pytest 8.3+
**Config:** `pyproject.toml [tool.pytest.ini_options]` — `testpaths = ["tests"]`
**Mocking:** `pytest-mock` (via `mocker` fixture) and `unittest.mock` (`patch`, `MagicMock`) — both used, no single enforced preference
**Parametrize:** `@pytest.mark.parametrize` used where meaningful (markdown converter block types)
**No coverage tool configured** — no `pytest-cov` in dependencies, no coverage threshold

**Run commands:**
```bash
uv run pytest              # all tests
uv run pytest tests/tools/ # specific directory
```

## Test File Organization

Tests mirror source structure exactly (defined in `feature-tester.md`):

```
src/weekforge/tools/notion_api_gateway.py  →  tests/tools/test_notion_crud.py
                                            →  tests/tools/test_notion_errors.py
src/weekforge/tools/notion_markdown_converter.py → tests/tools/test_notion_markdown_converter.py
src/weekforge/tools/formatting.py          →  tests/tools/test_formatting.py
src/weekforge/models/llm_call_cost.py      →  tests/models/test_llm_call_cost.py
src/weekforge/models/pricing.py            →  tests/models/test_pricing.py
src/weekforge/agents/agent_run_with_metadata.py → tests/agents/test_agents.py
src/weekforge/agents/prompt_composer.py    →  tests/agents/test_prompt_composer.py
src/weekforge/config/user_profile_loader.py → tests/config/test_user_profile_loader.py
src/weekforge/checkpoint.py                →  tests/test_checkpoint.py
src/weekforge/cli.py                       →  tests/test_cli.py
src/weekforge/workflows/e2e.py             →  tests/workflows/test_e2e.py
```

The `notion_api_gateway.py` tests are split into two files by concern: `test_notion_crud.py` (CRUD operations) and `test_notion_errors.py` (retry + error mapping).

## conftest.py

`tests/conftest.py` sets dummy env vars via `os.environ.setdefault()` before any module import. This prevents tests from requiring a real `.env` file in CI. Real `.env` values take precedence (setdefault only fills gaps).

```python
os.environ.setdefault("NOTION_TOKEN", "test-notion-token")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
# ... all required Settings fields
```

No pytest fixtures are defined in conftest — shared setup is handled by module-level helper functions in each test file.

## Test Structure Pattern

**Arrange-Act-Assert** throughout. One logical assertion per test (multiple `assert` calls allowed if they validate one outcome).

**Naming:** descriptive, behavior-oriented names that encode the scenario:
```python
test_query_resolves_data_source()
test_retry_api_call_rate_limit_gives_up()
test_resume_skips_query_and_agent_when_at_review()
test_load_user_profile_raises_on_whitespace_only_page()
```

**"Why test" comments** — every non-trivial test has a docstring explaining what regression it catches:
```python
def test_run_cost_accumulates_across_calls() -> None:
    """Why test: RunCost is the single source of truth for what the CLI displays
    at run completion — a broken accumulator would silently under-report cost."""
```

**In-module factory helpers** replace fixtures for small test files:
```python
def _mem_store() -> CheckpointStore:
    return CheckpointStore(":memory:")

def _meta(input_t: int = 100, output_t: int = 50, latency: int = 250) -> CallMetadata:
    ...
```

## Mocking Patterns

**`pytest-mock` `mocker.patch`** for patching module-level attributes (Notion SDK client methods):
```python
def test_query_resolves_data_source(mocker):
    mock_db_retrieve = mocker.patch("weekforge.tools.notion_api_gateway._client.databases.retrieve")
    mock_ds_query = mocker.patch("weekforge.tools.notion_api_gateway._client.data_sources.query")
    mock_db_retrieve.return_value = {"id": "db_123", "data_sources": [{"id": "ds_456"}]}
    mock_ds_query.return_value = {"results": [...], "has_more": False}
```

**`unittest.mock.patch` as context manager** for workflow tests (multiple patches in one `with` block):
```python
with (
    patch("weekforge.workflows.e2e.notion.query", return_value=records) as mock_query,
    patch("weekforge.workflows.e2e.run_with_metadata", return_value=(...)) as mock_run,
    patch("weekforge.workflows.e2e.hitl_confirm", return_value=HitlDecision(approved=True)),
    patch("weekforge.workflows.e2e.notion.create", return_value="page-123"),
):
    run_e2e(...)
```

**`MagicMock(spec=Model)`** for typed mock objects — ensures mock only exposes attributes that exist on the real class:
```python
mock_model = MagicMock(spec=Model)
mock_model.model_name = "gpt-5.4"
```

**`side_effect` with iterators** for multi-turn sequences:
```python
hitl_returns = iter([HitlDecision(approved=False, feedback="again"), HitlDecision(approved=True)])
patch("...hitl_confirm", side_effect=lambda **kw: next(hitl_returns))
```

**`tenacity.nap.time.sleep` patched** to prevent real waits in retry tests:
```python
mocker.patch("tenacity.nap.time.sleep")
```

**SQLite `:memory:`** used for all checkpoint store tests — no filesystem side effects:
```python
CheckpointStore(":memory:")
```

## What Is Tested

| Component | Coverage | Notes |
|-----------|----------|-------|
| `CheckpointStore` | High | save/load roundtrip, UPSERT, delete, list_active — `tests/test_checkpoint.py` |
| `NotionAPIError` mapping | High | 401→NotionAuthFailedError, 404→NotionNotFoundError, 500→NotionAPIError — `tests/tools/test_notion_errors.py` |
| Retry policy | High | success-after-429, gives-up-after-4-attempts — `tests/tools/test_notion_errors.py` |
| `query()` / `fetch()` pagination | High | data_source resolution, cursor loop — `tests/tools/test_notion_crud.py` |
| `convert_blocks_to_markdown()` | High | all block types, multi-segment rich text, unknown types — `tests/tools/test_notion_markdown_converter.py` |
| `format_week_prefix()` | High | boundary values, invalid input raises — `tests/tools/test_formatting.py` |
| `estimate_cost_eur()` | High | known models, unknown model fallback + warning, zero tokens — `tests/models/test_pricing.py` |
| `RunCost.add()` / `.summary()` | High | accumulation, formatting, zero-call edge case — `tests/models/test_llm_call_cost.py` |
| `run_with_metadata()` | High | token capture, latency non-negative, cost populated, TypeError on unresolved model — `tests/agents/test_agents.py` |
| `compose_system_prompt()` | High | flag-off no-op, flag-on appends directive, base preserved — `tests/agents/test_prompt_composer.py` |
| `load_user_profile()` | High | happy path, empty page, whitespace-only page, gateway error propagation — `tests/config/test_user_profile_loader.py` |
| `run_e2e()` workflow | High | golden path, feedback loop + history threading, resume from checkpoint, quit preserves checkpoint, cost accumulation — `tests/workflows/test_e2e.py` |
| CLI | Smoke only | `--help` exit code 0 — `tests/test_cli.py` |

## What Is Intentionally Not Tested

Defined by `feature-tester.md` philosophy:

- **LLM output content** — non-deterministic, mocking defeats the purpose
- **Rich formatting details** — visual, changes frequently, low bug risk
- **CLI cosmetics** — Rich panel content, table column styles
- **`openai_model_factory.py`** — model construction is thin wiring; no tests exist
- **`prompts/loader.py`** — `importlib.resources` loading of bundled `.md` files; no tests exist
- **`workflows/summarize_week.py`** — stub (raises `NotImplementedError`); no tests exist
- **`hitl.py` interaction loop** — requires terminal I/O; covered indirectly via workflow tests that mock `hitl_confirm`
- **Live Notion API** — no integration tests; `@pytest.mark.integration` tag is defined in the agent spec but not used in any existing test

## Parametrize Usage

Used in `tests/tools/test_notion_markdown_converter.py` for block type coverage:
```python
@pytest.mark.parametrize(
    "block_type,text,expected",
    [
        ("heading_1", "Title", "# Title"),
        ("heading_2", "Section", "## Section"),
        ("heading_3", "Sub", "### Sub"),
        ("bulleted_list_item", "Item", "- Item"),
        ("paragraph", "Plain text", "Plain text"),
    ],
)
def test_single_block_each_type(block_type, text, expected):
    assert convert_blocks_to_markdown([_block(block_type, text)]) == expected
```

Used sparingly elsewhere — tests are written as separate functions when the "why" rationale differs between cases.

## Gaps / Unknowns

- No coverage measurement configured — there is no enforced threshold and no way to detect regressions in coverage without adding `pytest-cov`
- `tests/pydantic_models/` directory exists but contains only `__pycache__` — empty, purpose unknown
- `openai_model_factory.py` has no tests; the Chat vs Responses API routing logic (based on `reasoning_effort`) is untested
- `prompts/loader.py` caching behaviour (`@functools.cache`) is untested
- `workflows/summarize_week.py` has no tests; the context-loading path (query → confirm overwrite → load prompts + profile) will need tests when the stub is implemented
- No integration test suite exists yet; the `@pytest.mark.integration` tag referenced in `feature-tester.md` is not in use
