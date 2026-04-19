"""Unit tests for load_user_profile() with mocked Notion gateway."""

from unittest.mock import patch

import pytest

from weekforge.config import ConfigError
from weekforge.config.user_profile_loader import load_user_profile
from weekforge.models.user_profile import UserProfile
from weekforge.tools.notion_api_gateway import NotionNotFoundError

_SAMPLE_BLOCKS = [
    {
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"text": {"content": "Baseline"}}],
        },
    },
    {
        "type": "bulleted_list_item",
        "bulleted_list_item": {
            "rich_text": [{"text": {"content": "Training age: 5 years"}}],
        },
    },
    {
        "type": "heading_2",
        "heading_2": {
            "rich_text": [{"text": {"content": "Goals"}}],
        },
    },
    {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"text": {"content": "Alpine mountaineering prep."}}],
        },
    },
]

_PAGE_ID = "test-user-profile-page"  # matches conftest.py env default


def test_load_user_profile_returns_markdown() -> None:
    with patch(
        "weekforge.config.user_profile_loader.fetch",
        return_value={"properties": {}, "content": _SAMPLE_BLOCKS},
    ):
        profile = load_user_profile()

    assert isinstance(profile, UserProfile)
    assert profile.page_id == _PAGE_ID
    assert "Baseline" in profile.markdown
    assert "Training age: 5 years" in profile.markdown
    assert "Goals" in profile.markdown


def test_load_user_profile_raises_on_empty_page() -> None:
    with patch(
        "weekforge.config.user_profile_loader.fetch",
        return_value={"properties": {}, "content": []},
    ):
        with pytest.raises(ConfigError, match="User profile page is empty"):
            load_user_profile()


def test_load_user_profile_raises_on_whitespace_only_page() -> None:
    whitespace_blocks = [
        {
            "type": "paragraph",
            "paragraph": {"rich_text": [{"text": {"content": "   "}}]},
        }
    ]
    with patch(
        "weekforge.config.user_profile_loader.fetch",
        return_value={"properties": {}, "content": whitespace_blocks},
    ):
        with pytest.raises(ConfigError, match="User profile page is empty"):
            load_user_profile()


def test_load_user_profile_propagates_gateway_errors() -> None:
    with patch(
        "weekforge.config.user_profile_loader.fetch",
        side_effect=NotionNotFoundError("Page not found"),
    ):
        with pytest.raises(NotionNotFoundError):
            load_user_profile()
