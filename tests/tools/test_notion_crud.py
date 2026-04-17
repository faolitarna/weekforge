
import pytest

from weekforge.tools.notion_api_gateway import NotionAPIError, fetch, query


def test_query_resolves_data_source(mocker):
    """
    Test that query() correctly retrieves the database first to extract its data_source_id,
    and then queries that data_source_id.
    Why: SDK 3.0.0 uses data_sources. We want to ensure database_id is resolved properly.
    """
    mock_db_retrieve = mocker.patch("weekforge.tools.notion_api_gateway._client.databases.retrieve")
    mock_ds_query = mocker.patch("weekforge.tools.notion_api_gateway._client.data_sources.query")
    
    # Mock database retrieve returning a connected data source
    mock_db_retrieve.return_value = {
        "id": "db_123",
        "data_sources": [{"id": "ds_456", "name": "Test Data Source"}]
    }
    
    # Mock a single page of results from the data source
    mock_ds_query.return_value = {
        "results": [{"id": "record_1"}, {"id": "record_2"}],
        "has_more": False
    }

    results = query("db_123")
    
    # Assert database retrieve was called with correct ID
    mock_db_retrieve.assert_called_once_with(database_id="db_123")
    
    # Assert data_source query was executed using the extracted data_source_id
    mock_ds_query.assert_called_once_with(data_source_id="ds_456")
    
    assert len(results) == 2
    assert results[0]["id"] == "record_1"


def test_query_fails_on_missing_data_source(mocker):
    """
    Test that query() throws a NotionAPIError if the retrieved database lacks a data source.
    Why: Assures missing or misconfigured schemas don't cause obscure KeyErrors later.
    """
    mock_db_retrieve = mocker.patch("weekforge.tools.notion_api_gateway._client.databases.retrieve")
    
    # Return a malformed database with no data sources
    mock_db_retrieve.return_value = {
        "id": "db_123",
        "data_sources": []
    }

    with pytest.raises(NotionAPIError, match="does not expose a valid data_source"):
        query("db_123")


def test_fetch_paginates_blocks(mocker):
    """
    Test that fetch() correctly loops and flattens paginated block cursors.
    Why: If has_more loop breaks, we lose page content silently.
    """
    mock_retrieve = mocker.patch("weekforge.tools.notion_api_gateway._client.pages.retrieve")
    mock_blocks = mocker.patch("weekforge.tools.notion_api_gateway._client.blocks.children.list")
    
    mock_retrieve.return_value = {
        "id": "page_123",
        "properties": {"Title": {}}
    }
    
    # Return two pages of blocks
    mock_blocks.side_effect = [
        {
            "results": [{"id": "block_1"}],
            "has_more": True,
            "next_cursor": "cursor_xyz"
        },
        {
            "results": [{"id": "block_2"}],
            "has_more": False,
            "next_cursor": None
        }
    ]

    result = fetch("page_123")
    
    # Ensure properties exist
    assert "Title" in result["properties"]
    
    # Ensure blocks were merged
    assert len(result["content"]) == 2
    assert result["content"][0]["id"] == "block_1"
    assert result["content"][1]["id"] == "block_2"
    
    assert mock_blocks.call_count == 2
    
    # Verify second call used the cursor
    mock_blocks.assert_called_with(block_id="page_123", start_cursor="cursor_xyz")
