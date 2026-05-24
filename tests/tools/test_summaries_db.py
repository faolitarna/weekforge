from unittest.mock import patch

from weekforge.tools.summaries_db import (
    find_plan_state_row,
    find_summary_row,
    read_plan_property,
    upsert_plan,
    upsert_summary,
)


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_found(mock_gtp, mock_query):
    page = {"id": "page-1", "properties": {"Week": {"rich_text": [{"plain_text": "07"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    result = find_summary_row("W07")
    assert result == page


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_not_found(mock_gtp, mock_query):
    mock_query.return_value = []
    result = find_summary_row("W99")
    assert result is None


@patch("weekforge.tools.summaries_db.notion.fetch")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_plan_state_row_found(mock_gtp, mock_query, mock_fetch):
    page = {"id": "ps-1", "properties": {"Week": {"rich_text": [{"plain_text": "PLAN_STATE"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "PLAN_STATE" if name == "Week" else ""
    mock_fetch.return_value = {
        "properties": {},
        "content": [{"type": "code", "code": {"rich_text": [{"text": {"content": "hello"}}]}}],
    }

    raw, page_id = find_plan_state_row()
    assert raw == "hello\n"
    assert page_id == "ps-1"


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_plan_state_row_not_found(mock_gtp, mock_query):
    mock_query.return_value = []
    raw, page_id = find_plan_state_row()
    assert raw is None
    assert page_id is None


def test_read_plan_property():
    page = {"properties": {"Plan": {"rich_text": [{"plain_text": "Push day focus"}]}}}
    result = read_plan_property(page)
    assert result == "Push day focus"


def test_read_plan_property_empty():
    page = {"properties": {}}
    result = read_plan_property(page)
    assert result is None


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.update")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_summary_existing(mock_gtp, mock_query, mock_update, _mock_title):
    page = {"id": "page-1", "properties": {"Week": {"rich_text": [{"plain_text": "07"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    result = upsert_summary("W07", "summary content")
    assert result == "page-1"
    mock_update.assert_called_once()


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.create")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_summary_new(mock_gtp, mock_query, mock_create, _mock_title):
    mock_query.return_value = []
    mock_create.return_value = "new-page-id"

    result = upsert_summary("W07", "summary content")
    assert result == "new-page-id"
    mock_create.assert_called_once()


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.update")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_plan_existing(mock_gtp, mock_query, mock_update, _mock_title):
    page = {"id": "page-1", "properties": {"Week": {"rich_text": [{"plain_text": "07"}]}}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    result = upsert_plan("W07", "plan text")
    assert result == "page-1"
    mock_update.assert_called_once()
