---
phase: 01-extraction
reviewed: 2026-04-19T00:00:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/weekforge/models/raw_week_data.py
  - src/weekforge/models/week_summary.py
  - src/weekforge/tools/raw_session_collector.py
  - tests/tools/test_raw_collector.py
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-04-19
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

The Tier-0 layer is well-structured overall. The dataclasses are clean, the Pydantic schemas are reasonable, and the block collection logic follows a straightforward paginated pattern. Three warnings were found: a potential infinite loop in the pagination cursor logic, a silent empty-string page ID that produces misleading downstream API errors, and a Pydantic tuple serialization round-trip issue. Three info-level items cover dead code, a swallowed exception losing its detail, and a test whose assertions do not fully cover the case its name implies.

---

## Warnings

### WR-01: Infinite loop if Notion returns `has_more=True` with `next_cursor=None`

**File:** `src/weekforge/tools/raw_session_collector.py:33-35`

**Issue:** The pagination loop breaks only when `has_more` is falsy. If Notion ever returns `{"has_more": true, "next_cursor": null}` (a malformed but not impossible API response), `cursor` stays `None`, the loop never sets `start_cursor`, and the same first page is fetched forever, hanging the process with no timeout or guard.

**Fix:**
```python
cursor = response.get("next_cursor")
if not response.get("has_more") or not cursor:
    break
```
This exits cleanly when pagination is exhausted *or* when the next cursor is missing, rather than silently looping on stale data.

---

### WR-02: Silent empty-string page ID creates confusing downstream API errors

**File:** `src/weekforge/tools/raw_session_collector.py:59`

**Issue:** `page_id = page.get("id", "")` defaults to `""` when the Notion page dict has no `id` key. The empty string is then passed to `collect_blocks("")` and `collect_comments("")`, both of which invoke the Notion API with `block_id=""`. The resulting API error (likely a 400 or 404) surfaces far from the root cause with no reference to which page entry was malformed.

**Fix:**
```python
page_id = page.get("id")
if not page_id:
    logger.warning("Skipping page entry with missing id: %s", page)
    continue
```
Or raise a `ValueError` early if a missing page ID should be treated as fatal.

---

### WR-03: Pydantic `tuple` fields lose type on JSON round-trip

**File:** `src/weekforge/models/week_summary.py:60,71,72`

**Issue:** `ImplicitFeedback.per_session: list[tuple[str, int, int]]`, `PlanAdherence.modification_patterns: list[tuple[str, str, str]]`, and `PlanAdherence.skip_patterns: list[tuple[str, str]]` are declared as `list[tuple[...]]`. Pydantic v2 serializes tuples as JSON arrays. On deserialization from JSON (e.g., model round-trip, LLM structured output parsing, test fixture loading), Pydantic v2 re-validates these as lists, not tuples — so `isinstance(entry, tuple)` checks in any downstream consumer will silently fail.

This is not a problem today if `WeekSummary` is only ever constructed in-memory, but becomes a correctness bug the moment it is serialized to JSON and re-parsed (e.g., caching, LangGraph state persistence).

**Fix:** Replace with named dataclasses or Pydantic sub-models for safety:
```python
class PerSessionEntry(BaseModel):
    session_name: str
    checked: int
    total: int

class ImplicitFeedback(BaseModel):
    ...
    per_session: list[PerSessionEntry]
```
Alternatively, accept the current representation and add a note that consumers must not rely on `isinstance(..., tuple)` after deserialization.

---

## Info

### IN-01: `section_buckets` is allocated but never read

**File:** `src/weekforge/tools/raw_session_collector.py:76-78`

**Issue:** A three-level nested `defaultdict` called `section_buckets` is created and apparently intended for per-section-per-exercise breakdown, but it is never populated (no writes after declaration) and never accessed when building the `ImplicitFeedback` return value. It is pure dead code.

**Fix:** Remove lines 76-78:
```python
# delete these three lines
section_buckets: dict[str, dict[str, dict[str, int]]] = defaultdict(
    lambda: defaultdict(lambda: {"checked": 0, "total": 0})
)
```

---

### IN-02: Swallowed exception loses diagnostic detail

**File:** `src/weekforge/tools/raw_session_collector.py:47-49`

**Issue:** The bare `except Exception:` in `collect_comments` does not capture the exception instance, so the log message contains no error type or message. A Notion auth failure (401), rate limit (429), or network error will all produce the same opaque warning with no distinguishing information.

**Fix:**
```python
except Exception as exc:
    logger.warning(
        "Failed to fetch comments for page %s — continuing with empty list: %s",
        page_id,
        exc,
    )
```

---

### IN-03: Test name implies non-`to_do` block but only tests missing `checked` key within `to_do`

**File:** `tests/tools/test_raw_collector.py:59-64`

**Issue:** `test_collect_blocks_no_keyerror_on_missing_fields` asserts `result[0].checked is False`, which validates the `bool(..., False)` default. However, the test name implies it covers missing fields generically, while the actual gap it could also cover — that a non-`to_do` block correctly yields `checked=None` — is not asserted. The current assertion passes for the right reason, but the test scope is narrower than its name suggests, which can cause false confidence during future refactors.

**Fix:** Either rename the test to `test_collect_blocks_to_do_missing_checked_defaults_false` and add a separate test for non-`to_do` blocks returning `checked=None`, or extend the existing test:
```python
# Add a non-to_do block to the same test
paragraph = {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "note"}]}}
client = _notion_client_returning([malformed, paragraph])
result = collect_blocks("page-1", client)
assert result[1].checked is None
```

---

_Reviewed: 2026-04-19_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
