"""Tier-0 Notion tool layer — the only code that touches the Notion API.

LLM agents never call Notion directly; they receive structured data from these
functions and return structured outputs that these functions write back. Keeping
the API boundary here means all pagination, rate-limiting, and error mapping are
handled in one place and are invisible to callers.

Public interface: query(), fetch(), create(), update().
Error contract: 429 retries transparently (exponential backoff, 4 attempts max).
401 and 404 raise immediately — both are unrecoverable without human intervention.
All other errors surface as NotionAPIError.
"""
import logging
from typing import Any

from notion_client import Client
from notion_client.errors import APIResponseError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from weekforge.config.env import settings
from weekforge.tools.notion_markdown_converter import convert_markdown_to_blocks

logger = logging.getLogger(__name__)


class NotionAuthFailedError(Exception):
    """Raised on HTTP 401 — invalid or expired Notion integration token.

    Unrecoverable without a new token. Surfaces immediately without retry.
    """
    pass


class NotionNotFoundError(Exception):
    """Raised on HTTP 404 — page or database does not exist.

    Common causes: stale page_id from a deleted page, wrong database_id in .env.
    Surfaces immediately without retry.
    """
    pass


class NotionAPIError(Exception):
    """Raised for all other Notion API errors (5xx, unexpected shapes, etc.).

    Also wraps non-API exceptions that escape the tool layer (e.g., network errors).
    """
    pass


# Module-level client — one connection shared across all calls in a process.
# Private to prevent callers from bypassing the error-mapping and retry wrapper.
_client = Client(auth=settings.notion_token)


def _is_rate_limit_error(e: Exception) -> bool:
    """Check if the Notion API error is specifically a rate limit error (429)."""
    if isinstance(e, APIResponseError):
        return e.status == 429
    return False


@retry(
    retry=retry_if_exception_type(APIResponseError),
    wait=wait_exponential(multiplier=1, min=1, max=4),
    stop=stop_after_attempt(4),
    reraise=True,
)
def _retry_api_call(func: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute a Notion API call with rate-limit retry and domain error mapping.

    Retry policy: 429 only, exponential backoff (1s→2s→4s), 4 attempts total.
    The 4-attempt cap is intentional — tests assert on it (test_retry_api_call_rate_limit_gives_up).
    401 and 404 are not transient; they map immediately to domain errors without retry.
    All other APIResponseError codes become NotionAPIError.
    """
    try:
        return func(*args, **kwargs)
    except APIResponseError as e:
        if e.status == 429:
            # Let tenacity handle the retry
            raise
        elif e.status == 401:
            raise NotionAuthFailedError("Invalid or expired Notion token") from e
        elif e.status == 404:
            raise NotionNotFoundError("The requested Notion resource was not found") from e
        else:
            raise NotionAPIError(f"Notion API error: {e}") from e
    except Exception as e:
        raise NotionAPIError(f"Unexpected error interfacing with Notion: {e}") from e


def query(database_id: str, filters: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Query a Notion database and return the complete record set.

    Notion's API separates Databases (views/schema) from Data Sources (records).
    Internally resolves database_id → data_source_id before querying, so callers
    only need the database_id and the indirection is hidden here.

    Filter composition: a single filter dict is passed directly; multiple filters
    are AND-composed. Pagination is handled internally — callers always get the
    full result set.
    """
    results = []
    has_more = True
    next_cursor = None

    db_obj = _retry_api_call(_client.databases.retrieve, database_id=database_id)
    try:
        data_source_id = db_obj["data_sources"][0]["id"]
    except (KeyError, IndexError) as e:
        raise NotionAPIError(f"Database {database_id} does not expose a valid data_source.") from e

    query_args: dict[str, Any] = {"data_source_id": data_source_id}
    if filters:
        if len(filters) == 1:
            query_args["filter_properties"] = filters[0]
        else:
            query_args["filter_properties"] = {"and": filters}

    while has_more:
        if next_cursor:
            query_args["start_cursor"] = next_cursor

        response = _retry_api_call(_client.data_sources.query, **query_args)
        results.extend(response.get("results", []))
        has_more = response.get("has_more", False)
        next_cursor = response.get("next_cursor")

    return results


def fetch(page_id: str) -> dict[str, Any]:
    """Fetch a page's properties and full block content.

    Returns `{"properties": {...}, "content": [block, ...]}` where `content` is
    the flat list of all child blocks (paginated internally). Callers that need
    the body text should iterate `content` — Notion's block tree is not recursed
    beyond the top level here.
    """
    page = _retry_api_call(_client.pages.retrieve, page_id=page_id)

    blocks = []
    has_more = True
    next_cursor = None

    while has_more:
        block_args = {"block_id": page_id}
        if next_cursor:
            block_args["start_cursor"] = next_cursor

        block_response = _retry_api_call(_client.blocks.children.list, **block_args)
        blocks.extend(block_response.get("results", []))
        has_more = block_response.get("has_more", False)
        next_cursor = block_response.get("next_cursor")

    return {
        "properties": page.get("properties", {}),
        "content": blocks
    }


def create(database_id: str, properties: dict[str, Any], content: str) -> str:
    """Create a new page in a database with markdown body content.

    `content` is plain markdown — the function converts it to Notion block JSON
    internally via convert_markdown_to_blocks(). Callers never hand-craft block
    objects. Returns the new page's ID.
    """
    blocks = convert_markdown_to_blocks(content)

    response = _retry_api_call(
        _client.pages.create,
        parent={"database_id": database_id},
        properties=properties,
        children=blocks
    )

    return str(response["id"])


def update(page_id: str, properties: dict[str, Any] | None = None, content: str | None = None) -> None:
    """Update a page's properties and/or body content.

    Content update strategy: delete all existing blocks then append new ones
    (Notion has no bulk replace API). This is final-state idempotent — running
    it twice with the same content produces the same page — but not operation-
    idempotent: each call issues O(N) delete requests. Avoid calling repeatedly
    on large pages (N > 100 blocks risks rate-limiting).

    If `content` is None, only properties are updated (and vice versa).
    """
    if properties:
        _retry_api_call(
            _client.pages.update,
            page_id=page_id,
            properties=properties
        )

    if content is not None:
        existing_blocks = fetch(page_id)["content"]
        for block in existing_blocks:
            _retry_api_call(_client.blocks.delete, block_id=block["id"])

        new_blocks = convert_markdown_to_blocks(content)
        if new_blocks:
            _retry_api_call(
                _client.blocks.children.append,
                block_id=page_id,
                children=new_blocks
            )
