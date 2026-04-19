"""Tests for convert_blocks_to_markdown() — the Notion-blocks-to-markdown parser."""
import pytest

from weekforge.tools.notion_markdown_converter import convert_blocks_to_markdown


def _block(block_type: str, text: str, **extra: object) -> dict:
    return {
        "type": block_type,
        block_type: {
            "rich_text": [{"text": {"content": text}}],
            **extra,
        },
    }


def test_empty_list_returns_empty_string() -> None:
    assert convert_blocks_to_markdown([]) == ""


@pytest.mark.parametrize(
    "block_type,text,expected",
    [
        ("heading_1", "Title", "# Title"),
        ("heading_2", "Section", "## Section"),
        ("heading_3", "Sub", "### Sub"),
        ("bulleted_list_item", "Item", "- Item"),
        ("paragraph", "Plain text", "Plain text"),
    ],
)
def test_single_block_each_type(block_type: str, text: str, expected: str) -> None:
    assert convert_blocks_to_markdown([_block(block_type, text)]) == expected


def test_todo_unchecked() -> None:
    block = _block("to_do", "Buy milk", checked=False)
    assert convert_blocks_to_markdown([block]) == "- [ ] Buy milk"


def test_todo_checked() -> None:
    block = _block("to_do", "Done", checked=True)
    assert convert_blocks_to_markdown([block]) == "- [x] Done"


def test_unknown_block_type_with_text_falls_back_to_paragraph() -> None:
    block = {"type": "quote", "quote": {"rich_text": [{"text": {"content": "Wise words"}}]}}
    assert convert_blocks_to_markdown([block]) == "Wise words"


def test_unknown_block_type_without_rich_text_is_skipped() -> None:
    block = {"type": "divider", "divider": {}}
    assert convert_blocks_to_markdown([block]) == ""


def test_mixed_blocks_join_with_newlines() -> None:
    blocks = [
        _block("heading_1", "Overview"),
        _block("paragraph", "Intro sentence."),
        _block("bulleted_list_item", "Point one"),
        _block("bulleted_list_item", "Point two"),
    ]
    expected = "# Overview\nIntro sentence.\n- Point one\n- Point two"
    assert convert_blocks_to_markdown(blocks) == expected


def test_multi_segment_rich_text_concatenated() -> None:
    block = {
        "type": "paragraph",
        "paragraph": {
            "rich_text": [
                {"text": {"content": "Hello "}},
                {"text": {"content": "world"}},
            ]
        },
    }
    assert convert_blocks_to_markdown([block]) == "Hello world"
