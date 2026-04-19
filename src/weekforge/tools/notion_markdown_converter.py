"""Narrow markdown ↔ Notion-blocks converter — only what weekforge flows need.

Supports: h1/h2/h3 headings, checked/unchecked to-do items, bullets, paragraphs.
No inline rich text. In both directions, unrecognised content silently becomes
plain paragraphs (or is dropped when empty) — no warning or log entry; callers
cannot detect mistranslation.
"""
from typing import Any


def convert_markdown_to_blocks(content: str) -> list[dict[str, Any]]:
    if not content:
        return []

    blocks = []
    lines = content.split('\n')

    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue  # blank lines are dropped entirely; visual spacing in source is lost in Notion output

        if line_stripped.startswith('# '):
            blocks.append({
                "object": "block",
                "type": "heading_1",
                "heading_1": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped[2:].strip()}}]
                }
            })
        elif line_stripped.startswith('## '):
            blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped[3:].strip()}}]
                }
            })
        elif line_stripped.startswith('### '):
            blocks.append({
                "object": "block",
                "type": "heading_3",
                "heading_3": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped[4:].strip()}}]
                }
            })
        elif line_stripped.startswith('- [x] ') or line_stripped.startswith('- [X] '):
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped[6:].strip()}}],
                    "checked": True
                }
            })
        elif line_stripped.startswith('- [ ] '):
            blocks.append({
                "object": "block",
                "type": "to_do",
                "to_do": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped[6:].strip()}}],
                    "checked": False
                }
            })
        elif line_stripped.startswith('- ') or line_stripped.startswith('* '):
            blocks.append({
                "object": "block",
                "type": "bulleted_list_item",
                "bulleted_list_item": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped[2:].strip()}}]
                }
            })
        else:
            blocks.append({
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": line_stripped}}]
                }
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
        else:
            if text:
                lines.append(text)
    return "\n".join(lines)
