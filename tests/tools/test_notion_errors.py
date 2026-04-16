import httpx
import pytest
from notion_client.errors import APIResponseError

from weekforge.tools.notion import (
    NotionAPIError,
    NotionAuthFailedError,
    NotionNotFoundError,
    _retry_api_call,
)


def mock_api_response_error(status: int, code: str = "error") -> APIResponseError:
    """Helper to construct APIResponseError for notion-client==3.0.0"""
    return APIResponseError(
        code=code,
        status=status,
        message="Mock error",
        headers=httpx.Headers(),
        raw_body_text=""
    )


def test_retry_api_call_rate_limit(mocker):
    """
    Test that 429 errors actually trigger tenacity retries and eventually succeed.
    Why: Assures our rate limits are handled transparently.
    """
    # Patch time.sleep to avoid actually sleeping during tests
    mocker.patch("tenacity.nap.time.sleep")
    
    call_count = 0

    def mock_rate_limited_func():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Throw 429 for the first two attempts
            raise mock_api_response_error(429, "rate_limited")
        return "success"

    result = _retry_api_call(mock_rate_limited_func)
    
    assert result == "success"
    assert call_count == 3


def test_retry_api_call_rate_limit_gives_up(mocker):
    """
    Test that 429 errors stop retrying after the configured attempt limit (4).
    Why: Assures we don't loop infinitely on frozen APIs.
    """
    mocker.patch("tenacity.nap.time.sleep")
    
    call_count = 0

    def mock_always_rate_limited_func():
        nonlocal call_count
        call_count += 1
        raise mock_api_response_error(429, "rate_limited")

    with pytest.raises(APIResponseError):
        _retry_api_call(mock_always_rate_limited_func)
        
    assert call_count == 4  # stop_after_attempt(4)


def test_api_call_404_mapping():
    """
    Test that 404 maps to NotionNotFoundError immediately.
    Why: Domain-specific errors keep workflow logic clean.
    """
    def mock_not_found():
        raise mock_api_response_error(404, "object_not_found")

    with pytest.raises(NotionNotFoundError):
        _retry_api_call(mock_not_found)


def test_api_call_401_mapping():
    """
    Test that 401 maps to NotionAuthFailedError immediately.
    Why: Auth failures are unrecoverable and need immediate escalation.
    """
    def mock_unauthorized():
        raise mock_api_response_error(401, "unauthorized")

    with pytest.raises(NotionAuthFailedError):
        _retry_api_call(mock_unauthorized)


def test_api_call_general_error_mapping():
    """
    Test that generic API errors map to NotionAPIError.
    Why: Fallback contract for weird edge cases from Notion API.
    """
    def mock_internal_error():
        raise mock_api_response_error(500, "internal_server_error")

    with pytest.raises(NotionAPIError):
        _retry_api_call(mock_internal_error)
