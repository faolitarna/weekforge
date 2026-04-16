"""Narrow markdown-to-Notion-blocks converter — only what session drafts need.

Supports: h1/h2/h3 headings, checked/unchecked to-do items, bullets, paragraphs.
No inline rich text. Unrecognised lines silently become paragraphs.
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
            continue

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
