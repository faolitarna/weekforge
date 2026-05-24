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


# --- W-prefix stripping edge cases ---

@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_single_digit_prefix(mock_gtp, mock_query):
    """W7 strips to '7'; DB row storing '7' must match."""
    page = {"id": "page-7", "properties": {}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "7" if name == "Week" else ""

    result = find_summary_row("W7")
    assert result == page


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_padded_prefix_does_not_match_unpadded_db(mock_gtp, mock_query):
    """W07 strips to '07'; a DB row storing '7' (no zero-pad) must NOT match."""
    page = {"id": "page-7", "properties": {}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "7" if name == "Week" else ""

    result = find_summary_row("W07")
    assert result is None, "strict string match: '07' != '7'"


@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_summary_row_matches_first_of_multiple(mock_gtp, mock_query):
    """When multiple pages match (bad data), the first matching row is returned."""
    page_a = {"id": "page-a", "properties": {}}
    page_b = {"id": "page-b", "properties": {}}
    mock_query.return_value = [page_a, page_b]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    result = find_summary_row("W07")
    assert result == page_a


# --- find_plan_state_row paragraph block path ---

@patch("weekforge.tools.summaries_db.notion.fetch")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_plan_state_row_paragraph_block(mock_gtp, mock_query, mock_fetch):
    """Paragraph blocks (not code blocks) in the PLAN_STATE page are also concatenated."""
    page = {"id": "ps-2", "properties": {}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "PLAN_STATE" if name == "Week" else ""
    mock_fetch.return_value = {
        "properties": {},
        "content": [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"text": {"content": "from paragraph"}}]
                },
            }
        ],
    }

    raw, page_id = find_plan_state_row()
    assert "from paragraph" in raw
    assert page_id == "ps-2"


@patch("weekforge.tools.summaries_db.notion.fetch")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_find_plan_state_row_mixed_blocks(mock_gtp, mock_query, mock_fetch):
    """Code and paragraph blocks are both concatenated, in order."""
    page = {"id": "ps-3", "properties": {}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "PLAN_STATE" if name == "Week" else ""
    mock_fetch.return_value = {
        "properties": {},
        "content": [
            {"type": "code", "code": {"rich_text": [{"text": {"content": "code-part"}}]}},
            {
                "type": "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": "para-part"}}]},
            },
        ],
    }

    raw, _ = find_plan_state_row()
    assert "code-part" in raw
    assert "para-part" in raw


# --- upsert_summary content format ---

@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.update")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_summary_wraps_content_in_code_block(mock_gtp, mock_query, mock_update, _mock_title):
    """upsert_summary must wrap content in a markdown code block before writing."""
    page = {"id": "page-1", "properties": {}}
    mock_query.return_value = [page]
    mock_gtp.side_effect = lambda p, name: "07" if name == "Week" else ""

    upsert_summary("W07", "raw summary content")

    _, call_kwargs = mock_update.call_args
    content_arg = call_kwargs.get("content", "")
    assert "```text" in content_arg
    assert "raw summary content" in content_arg


@patch("weekforge.tools.summaries_db.notion.get_title_property_name", return_value="Name")
@patch("weekforge.tools.summaries_db.notion.create")
@patch("weekforge.tools.summaries_db.notion.query")
@patch("weekforge.tools.summaries_db.notion.get_text_prop")
def test_upsert_plan_new_creates_with_week_num(mock_gtp, mock_query, mock_create, _mock_title):
    """When no existing row found, upsert_plan must create with stripped week number."""
    mock_query.return_value = []
    mock_create.return_value = "new-id"

    upsert_plan("W03", "my plan text")

    mock_create.assert_called_once()
    _, call_kwargs = mock_create.call_args
    week_prop = call_kwargs["properties"]["Week"]["rich_text"][0]["text"]["content"]
    assert week_prop == "03", f"expected '03', got {week_prop!r}"
