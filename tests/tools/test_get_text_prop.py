from weekforge.tools.notion_api_gateway import get_text_prop


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
