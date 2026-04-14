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
from weekforge.tools.notion_markdown import convert_markdown_to_blocks

logger = logging.getLogger(__name__)


class NotionAuthFailedError(Exception):
    """Raised when the Notion API token is invalid or expired."""
    pass


class NotionNotFoundError(Exception):
    """Raised when a Notion page or database is not found."""
    pass


class NotionAPIError(Exception):
    """Raised for other general Notion API errors."""
    pass


# Initialize the synchronous Tier-0 client using the validated settings
# Private instance to prevent upstream exposure to leaky untested tools
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
    """
    Executes a Notion API function with exponential backoff for rate limits.
    For non-rate-limit 4xx errors, we capture and re-raise explicit domain errors.
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
    """
    Query a Notion database.
    Pagination is handled internally, returning the complete result set.
    """
    results = []
    has_more = True
    next_cursor = None
    
    # In SDK 3.0.0 (Notion API 2025-09-03), databases are distinct from data sources.
    # We must retrieve the database to resolve its underlying data_source.
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
    """
    Fetch a page properties and its full block content.
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
    """
    Create a new page in a database with the given properties and markdown content.
    Returns the ID of the new page.
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
    """
    Idempotent update of a Notion page properties and content.
    """
    if properties:
        _retry_api_call(
            _client.pages.update,
            page_id=page_id,
            properties=properties
        )
        
    if content is not None:
        # NOTE: Notion API does not currently support bulk block deletion.
        # This executes sequentially (O(N) operations) which is standard but slow.
        # It will be affected by rate-limits strictly if N > 100 components.
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
