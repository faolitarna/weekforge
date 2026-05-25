from weekforge.tools.notion_api_gateway import get_text_prop, get_page_title


def test_get_text_prop_reads_rich_text():
    page = {"properties": {"Week": {"rich_text": [{"plain_text": "W07"}]}}}
    assert get_text_prop(page, "Week") == "W07"


def test_get_text_prop_concatenates_multiple_items():
    page = {"properties": {"Plan": {"rich_text": [
        {"plain_text": "Part 1"},
        {"plain_text": " Part 2"},
    ]}}}
    assert get_text_prop(page, "Plan") == "Part 1 Part 2"


def test_get_text_prop_missing_property_returns_empty():
    page = {"properties": {}}
    assert get_text_prop(page, "Week") == ""


def test_get_text_prop_empty_rich_text_returns_empty():
    page = {"properties": {"Week": {"rich_text": []}}}
    assert get_text_prop(page, "Week") == ""


def test_get_text_prop_no_properties_key_returns_empty():
    page = {}
    assert get_text_prop(page, "Week") == ""


def test_get_page_title_extracts_title():
    page = {"properties": {"Name": {"type": "title", "title": [{"plain_text": "W15: Push + Hinge"}]}}}
    assert get_page_title(page) == "W15: Push + Hinge"


def test_get_page_title_concatenates_multiple_items():
    page = {"properties": {"Name": {"type": "title", "title": [
        {"plain_text": "W15: "},
        {"plain_text": "Push + Hinge"},
    ]}}}
    assert get_page_title(page) == "W15: Push + Hinge"


def test_get_page_title_no_title_property_returns_empty():
    page = {"properties": {"Week": {"type": "rich_text", "rich_text": []}}}
    assert get_page_title(page) == ""


def test_get_page_title_empty_properties_returns_empty():
    page = {"properties": {}}
    assert get_page_title(page) == ""


def test_get_page_title_no_properties_key_returns_empty():
    page = {}
    assert get_page_title(page) == ""
