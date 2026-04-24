"""Tests for notion_markdown_converter — both directions."""
import pytest

from weekforge.tools.notion_markdown_converter import (
    _NOTION_TEXT_LIMIT,
    _rich_text_chunks,
    convert_blocks_to_markdown,
    convert_markdown_to_blocks,
)


# ---------------------------------------------------------------------------
# _rich_text_chunks
# ---------------------------------------------------------------------------

def test_rich_text_chunks_empty() -> None:
    chunks = _rich_text_chunks("")
    assert len(chunks) == 1
    assert chunks[0]["text"]["content"] == ""


def test_rich_text_chunks_short() -> None:
    chunks = _rich_text_chunks("hello")
    assert len(chunks) == 1
    assert chunks[0]["text"]["content"] == "hello"


def test_rich_text_chunks_exact_limit() -> None:
    content = "x" * _NOTION_TEXT_LIMIT
    chunks = _rich_text_chunks(content)
    assert len(chunks) == 1
    assert chunks[0]["text"]["content"] == content


def test_rich_text_chunks_over_limit() -> None:
    content = "a" * (_NOTION_TEXT_LIMIT * 2 + 1)
    chunks = _rich_text_chunks(content)
    assert len(chunks) == 3
    assert len(chunks[0]["text"]["content"]) == _NOTION_TEXT_LIMIT
    assert len(chunks[1]["text"]["content"]) == _NOTION_TEXT_LIMIT
    assert len(chunks[2]["text"]["content"]) == 1
    assert "".join(c["text"]["content"] for c in chunks) == content


# ---------------------------------------------------------------------------
# convert_markdown_to_blocks — existing block types (unchanged behaviour)
# ---------------------------------------------------------------------------

def _block(block_type: str, text: str, **extra: object) -> dict:
    return {
        "type": block_type,
        block_type: {
            "rich_text": [{"text": {"content": text}}],
            **extra,
        },
    }


def test_empty_input_returns_empty_list() -> None:
    assert convert_markdown_to_blocks("") == []


@pytest.mark.parametrize("md,expected_type,expected_text", [
    ("# Title", "heading_1", "Title"),
    ("## Section", "heading_2", "Section"),
    ("### Sub", "heading_3", "Sub"),
    ("- bullet", "bulleted_list_item", "bullet"),
    ("* bullet", "bulleted_list_item", "bullet"),
    ("plain paragraph", "paragraph", "plain paragraph"),
])
def test_single_line_block_types(md: str, expected_type: str, expected_text: str) -> None:
    blocks = convert_markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["type"] == expected_type
    rt = blocks[0][expected_type]["rich_text"]
    assert rt[0]["text"]["content"] == expected_text


def test_todo_checked() -> None:
    blocks = convert_markdown_to_blocks("- [x] done item")
    assert blocks[0]["type"] == "to_do"
    assert blocks[0]["to_do"]["checked"] is True
    assert blocks[0]["to_do"]["rich_text"][0]["text"]["content"] == "done item"


def test_todo_unchecked() -> None:
    blocks = convert_markdown_to_blocks("- [ ] pending item")
    assert blocks[0]["type"] == "to_do"
    assert blocks[0]["to_do"]["checked"] is False


def test_blank_lines_dropped() -> None:
    blocks = convert_markdown_to_blocks("line one\n\nline two")
    assert len(blocks) == 2


# ---------------------------------------------------------------------------
# convert_markdown_to_blocks — fenced code blocks
# ---------------------------------------------------------------------------

def test_fenced_code_block_plain_text_language() -> None:
    md = "```text\nfoo\nbar\n```"
    blocks = convert_markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["language"] == "plain text"
    assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "foo\nbar"


def test_fenced_code_block_known_language() -> None:
    md = "```python\nprint('hi')\n```"
    blocks = convert_markdown_to_blocks(md)
    assert blocks[0]["code"]["language"] == "python"


def test_fenced_code_block_no_language_defaults_plain_text() -> None:
    md = "```\ncontent\n```"
    blocks = convert_markdown_to_blocks(md)
    assert blocks[0]["code"]["language"] == "plain text"


def test_fenced_code_block_preserves_indentation() -> None:
    md = "```\n    indented\n```"
    blocks = convert_markdown_to_blocks(md)
    assert "    indented" in blocks[0]["code"]["rich_text"][0]["text"]["content"]


def test_fenced_code_block_surrounded_by_other_blocks() -> None:
    md = "# Header\n```text\ncode here\n```\nparagraph"
    blocks = convert_markdown_to_blocks(md)
    assert len(blocks) == 3
    assert blocks[0]["type"] == "heading_1"
    assert blocks[1]["type"] == "code"
    assert blocks[2]["type"] == "paragraph"


def test_fenced_code_block_content_chunked_when_over_limit() -> None:
    long_content = "x" * (_NOTION_TEXT_LIMIT + 1)
    md = f"```\n{long_content}\n```"
    blocks = convert_markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert len(blocks[0]["code"]["rich_text"]) == 2


def test_unclosed_fence_flushed_as_code_block() -> None:
    md = "```python\norphan line"
    blocks = convert_markdown_to_blocks(md)
    assert len(blocks) == 1
    assert blocks[0]["type"] == "code"
    assert blocks[0]["code"]["rich_text"][0]["text"]["content"] == "orphan line"


# ---------------------------------------------------------------------------
# convert_markdown_to_blocks — long content chunking
# ---------------------------------------------------------------------------

def test_long_bullet_produces_multiple_rich_text_items() -> None:
    long_text = "a" * (_NOTION_TEXT_LIMIT + 500)
    md = f"- {long_text}"
    blocks = convert_markdown_to_blocks(md)
    assert blocks[0]["type"] == "bulleted_list_item"
    rt = blocks[0]["bulleted_list_item"]["rich_text"]
    assert len(rt) == 2
    assert all(len(item["text"]["content"]) <= _NOTION_TEXT_LIMIT for item in rt)
    assert "".join(item["text"]["content"] for item in rt) == long_text


def test_long_paragraph_produces_multiple_rich_text_items() -> None:
    long_text = "b" * (_NOTION_TEXT_LIMIT * 3)
    blocks = convert_markdown_to_blocks(long_text)
    rt = blocks[0]["paragraph"]["rich_text"]
    assert len(rt) == 3


# ---------------------------------------------------------------------------
# convert_blocks_to_markdown — existing behaviour (unchanged)
# ---------------------------------------------------------------------------

def test_empty_list_returns_empty_string() -> None:
    assert convert_blocks_to_markdown([]) == ""


@pytest.mark.parametrize("block_type,text,expected", [
    ("heading_1", "Title", "# Title"),
    ("heading_2", "Section", "## Section"),
    ("heading_3", "Sub", "### Sub"),
    ("bulleted_list_item", "Item", "- Item"),
    ("paragraph", "Plain text", "Plain text"),
])
def test_single_block_each_type(block_type: str, text: str, expected: str) -> None:
    assert convert_blocks_to_markdown([_block(block_type, text)]) == expected


def test_todo_unchecked_roundtrip() -> None:
    block = _block("to_do", "Buy milk", checked=False)
    assert convert_blocks_to_markdown([block]) == "- [ ] Buy milk"


def test_todo_checked_roundtrip() -> None:
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


# ---------------------------------------------------------------------------
# convert_blocks_to_markdown — code block roundtrip
# ---------------------------------------------------------------------------

def test_code_block_roundtrip_plain_text() -> None:
    block = {
        "type": "code",
        "code": {
            "language": "plain text",
            "rich_text": [{"text": {"content": "line1\nline2"}}],
        },
    }
    result = convert_blocks_to_markdown([block])
    assert result == "```\nline1\nline2\n```"


def test_code_block_roundtrip_named_language() -> None:
    block = {
        "type": "code",
        "code": {
            "language": "python",
            "rich_text": [{"text": {"content": "x = 1"}}],
        },
    }
    result = convert_blocks_to_markdown([block])
    assert result == "```python\nx = 1\n```"
