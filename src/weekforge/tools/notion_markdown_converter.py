"""Narrow markdown ↔ Notion-blocks converter — only what weekforge flows need.

Supports: h1/h2/h3 headings, checked/unchecked to-do items, bullets, paragraphs,
fenced code blocks. No inline rich text. In both directions, unrecognised content
silently becomes plain paragraphs (or is dropped when empty) — no warning or log
entry; callers cannot detect mistranslation.

Notion API imposes a 2000-char limit per rich_text item. All block emitters use
_rich_text_chunks() to split long content across multiple items automatically.
"""
from typing import Any

_NOTION_TEXT_LIMIT = 2000


def _rich_text_chunks(content: str) -> list[dict[str, Any]]:
    """Split content into ≤2000-char rich_text items (Notion API per-item limit)."""
    if not content:
        # Notion requires ≥1 rich_text item per block even when content is empty.
        return [{"type": "text", "text": {"content": ""}}]
    return [
        {"type": "text", "text": {"content": content[i : i + _NOTION_TEXT_LIMIT]}}
        for i in range(0, len(content), _NOTION_TEXT_LIMIT)
    ]


def convert_markdown_to_blocks(content: str) -> list[dict[str, Any]]:
    if not content:
        return []

    blocks: list[dict[str, Any]] = []
    lines = content.split("\n")
    inside_code = False
    code_lines: list[str] = []
    code_language = "plain text"

    for line in lines:
        line_stripped = line.strip()

        if inside_code:
            if line_stripped == "```":
                blocks.append({
                    "object": "block",
                    "type": "code",
                    "code": {
                        "rich_text": _rich_text_chunks("\n".join(code_lines)),
                        "language": code_language,
                    },
                })
                inside_code = False
                code_lines = []
            else:
                code_lines.append(line)  # preserve original indentation
            continue

        if line_stripped.startswith("```"):
            inside_code = True
            lang = line_stripped[3:].strip()
            # "text" is not a valid Notion language identifier
            code_language = lang if lang and lang != "text" else "plain text"
            code_lines = []
            continue

        if not line_stripped:
            continue  # blank lines dropped; visual spacing in source lost in Notion output

        if line_stripped.startswith("# "):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {"rich_text": _rich_text_chunks(line_stripped[2:].strip())},
            })
        elif line_stripped.startswith("## "):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {"rich_text": _rich_text_chunks(line_stripped[3:].strip())},
            })
        elif line_stripped.startswith("### "):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {"rich_text": _rich_text_chunks(line_stripped[4:].strip())},
            })
        elif line_stripped.startswith("- [x] ") or line_stripped.startswith("- [X] "):
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": _rich_text_chunks(line_stripped[6:].strip()),
                    "checked": True,
                },
            })
        elif line_stripped.startswith("- [ ] "):
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": _rich_text_chunks(line_stripped[6:].strip()),
                    "checked": False,
                },
            })
        elif line_stripped.startswith("- ") or line_stripped.startswith("* "):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {"rich_text": _rich_text_chunks(line_stripped[2:].strip())},
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {"rich_text": _rich_text_chunks(line_stripped)},
            })

    # flush unclosed code block (malformed fence)
    if inside_code:
        blocks.append({
            "object": "block",
            "type": "code",
            "code": {
                "rich_text": _rich_text_chunks("\n".join(code_lines)),
                "language": code_language,
            },
        })

    return blocks


def convert_blocks_to_markdown(blocks: list[dict[str, Any]]) -> str:
    lines = []
    for block in blocks:
        block_type = block.get("type", "")
        data = block.get(block_type, {})
        rich_text = data.get("rich_text", [])
        text = "".join(rt.get("text", {}).get("content", "") for rt in rich_text)
        if block_type == "heading_1":
            lines.append(f"# {text}")
        elif block_type == "heading_2":
            lines.append(f"## {text}")
        elif block_type == "heading_3":
            lines.append(f"### {text}")
        elif block_type == "bulleted_list_item":
            lines.append(f"- {text}")
        elif block_type == "to_do":
            mark = "x" if data.get("checked", False) else " "
            lines.append(f"- [{mark}] {text}")
        elif block_type == "code":
            lang = data.get("language", "")
            fence = f"```{lang}" if lang and lang != "plain text" else "```"
            lines.append(f"{fence}\n{text}\n```")
        else:
            if text:
                lines.append(text)
    return "\n".join(lines)
